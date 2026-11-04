"""
tests/test_id_jump_repro.py
Reproduction tests for:
1. Duplicate ISBN insertion allowed for active books.
2. Accidental duplicate book creation and deletion causing book_id jumps in SQLite.
3. Desync between previewBarcodes and actual assigned book_id / barcode.
4. BarcodeGeneratorView condition flaw when existingBook.total_copies >= count.
"""

import json
import sqlite3
import pytest
from data.db import get_connection
from data.migrate import apply_migrations
from core.library.services.catalog_service import CatalogService
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter


@pytest.fixture
def test_db(tmp_path):
    """Provide an isolated, fully migrated library database connection."""
    db_path = str(tmp_path / "test_library.sqlite")
    conn = get_connection(db_path, pin="123456")
    apply_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def services(test_db):
    """Provide initialized CatalogService and LibrarianAdminAdapter."""
    catalog_svc = CatalogService(test_db)
    adapter = LibrarianAdminAdapter(test_db)
    return {"catalog": catalog_svc, "adapter": adapter, "conn": test_db}


def test_duplicate_isbn_should_be_rejected(services):
    """
    Contract: add_book should reject creating a new book record if an active book
    with the same ISBN already exists in the catalog.
    """
    catalog = services["catalog"]
    
    # 1. Insert initial Book A
    res1 = catalog.add_book(title="Book A", isbn="9780132350884", copy_count=1)
    assert res1.ok is True, f"Failed to insert Book A: {res1.error}"
    assert res1.data["book_id"] == 1

    # 2. Attempt duplicate scan of identical ISBN
    res2 = catalog.add_book(title="Book A Duplicate", isbn="9780132350884", copy_count=1)
    
    # Expected: System should reject duplicate ISBN for active books
    # Observed on unfixed code: res2.ok is True, creates duplicate book_id = 2
    assert res2.ok is False, "Expected add_book to reject duplicate ISBN for active book"
    assert "already exists" in (res2.error or "").lower()


def test_id_jump_after_deleting_accidental_last_book(services):
    """
    Contract: If the last inserted book was added by mistake (0 loans, 0 copy activity)
    and is deleted/cancelled, the sequence should rewind/recycle so the next book
    receives the reclaimed ID instead of jumping/skipping IDs.
    """
    catalog = services["catalog"]
    adapter = services["adapter"]
    conn = services["conn"]

    # 1. Insert Book 1
    res1 = catalog.add_book(title="Book A", isbn="9780132350884", copy_count=1)
    assert res1.ok is True
    assert res1.data["book_id"] == 1

    # 2. Accidental entry creates Book 2 (e.g. without ISBN or mistyped)
    res2 = catalog.add_book(title="Book A Mistake", isbn=None, copy_count=1)
    assert res2.ok is True
    book_id_2 = res2.data["book_id"]
    assert book_id_2 == 2

    # 3. User realizes mistake and deletes Book 2 (0 loans)
    del_res = json.loads(adapter.deleteBook(book_id_2))
    assert del_res["ok"] is True

    # 4. Insert Book 3 (a new distinct book)
    res3 = catalog.add_book(title="Book B", isbn="9780131103627", copy_count=1)
    assert res3.ok is True

    # Expected: Book 3 should reuse ID 2 (or sequence rewound to 2) avoiding barcode jump
    # Observed on unfixed code: res3.data["book_id"] == 3, jumping over ID 2
    assert res3.data["book_id"] == 2, (
        f"ID jumped! Expected book_id 2 for next book after deleting accidental book 2, "
        f"but got book_id {res3.data['book_id']}"
    )


def test_barcode_preview_matches_actual_created_barcode(services):
    """
    Contract: previewBarcodes(0, count) must match the actual barcode assigned
    by addBook when the book is subsequently inserted, and retiring an unloaned
    book rewinds sequence so preview and next inserted book both reuse the reclaimed ID.
    """
    adapter = services["adapter"]

    # 1. Insert Book 1
    res1 = json.loads(adapter.addBook("Book 1", "9780132350884", barcodes_csv="1"))
    assert res1["ok"] is True
    assert res1["data"]["book_id"] == 1

    # 2. Accidental Book 2 inserted (with distinct ISBN)
    res2 = json.loads(adapter.addBook("Book 2", "9780131103627", barcodes_csv="1"))
    assert res2["ok"] is True
    assert res2["data"]["book_id"] == 2

    # 3. Book 2 is retired via adapter (0 loans/reservations -> hard-deleted & sequence rewound)
    del_res = json.loads(adapter.deleteBook(2))
    assert del_res["ok"] is True

    # 4. Preview barcodes for next new book
    preview_res = json.loads(adapter.previewBarcodes(0, 1))
    assert preview_res["ok"] is True
    assert preview_res["target_book_id"] == 2
    previewed_barcode = preview_res["barcodes"][0]
    assert previewed_barcode == "SMTE-00002-01"

    # 5. Actually add the next new book
    add_res = json.loads(adapter.addBook("Book 3", "9781491950357"))
    assert add_res["ok"] is True
    assert add_res["data"]["book_id"] == 2
    actual_barcode = add_res["data"]["barcodes"][0]

    # Expected: previewed barcode must match actual assigned barcode
    assert previewed_barcode == actual_barcode


def test_qml_condition_double_scan_decision_logic(services):
    """
    Verify BarcodeGeneratorView.qml decision logic & adapter behavior:
    When an existing book is detected, adding copies must increment the existing
    book's copy count rather than creating a duplicate book row.
    """
    adapter = services["adapter"]

    # 1. Verify QML source contains the corrected routing logic
    qml_file = "apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml"
    with open(qml_file, "r", encoding="utf-8") as f:
        qml_src = f.read()

    assert "existingBook.total_copies < count" not in qml_src, (
        "Flawed condition 'existingBook.total_copies < count' still present in BarcodeGeneratorView.qml"
    )
    assert "if (existingBook)" in qml_src, (
        "Expected 'if (existingBook)' branch in BarcodeGeneratorView.qml"
    )

    # 2. Assert real adapter behavior on double scan / copy increment
    add_res = json.loads(adapter.addBook("Clean Code", "9780132350884", barcodes_csv="1"))
    assert add_res["ok"] is True
    book_id = add_res["data"]["book_id"]

    # Simulating double scan routing: calls addCopies on existing book
    add_copy_res = json.loads(adapter.addCopies(book_id, "1"))
    assert add_copy_res["ok"] is True
    assert len(add_copy_res["data"]["copy_ids"]) == 1

    # Book copy detail verifies total_copies is now 2
    detail_res = json.loads(adapter.getBookCopiesDetail(book_id))
    assert detail_res["ok"] is True
    assert detail_res["data"]["total_copies"] == 2

    # Attempting duplicate addBook with same ISBN is rejected
    dup_res = json.loads(adapter.addBook("Clean Code Duplicate", "9780132350884", barcodes_csv="1"))
    assert dup_res["ok"] is False
    assert "already exists" in dup_res["error"].lower()


def test_retire_book_with_reservation_retains_soft_delete(services):
    """
    Verify that a book with reservation history is soft-deleted (active = 0)
    rather than hard-deleted, preserving foreign key integrity and reservation trails.
    """
    catalog = services["catalog"]
    adapter = services["adapter"]
    conn = services["conn"]

    # 1. Add student and book
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES (101, 'Test Student', 'active')"
    )
    res = catalog.add_book(title="Reserved Book", isbn="9780321125217", copy_count=1)
    assert res.ok is True
    book_id = res.data["book_id"]

    # 2. Place reservation on book
    conn.execute(
        "INSERT INTO reservations (book_id, student_id, reserved_at, status) VALUES (?, 101, '2026-11-03T00:00:00Z', 'waiting')",
        (book_id,),
    )

    # 3. Retire book
    del_res = json.loads(adapter.deleteBook(book_id))
    assert del_res["ok"] is True

    # 4. Verify book is soft-deleted (active = 0), NOT hard deleted
    row = conn.execute("SELECT active FROM books WHERE book_id = ?", (book_id,)).fetchone()
    assert row is not None
    assert row["active"] == 0

    # Reservation row is intact
    res_row = conn.execute("SELECT 1 FROM reservations WHERE book_id = ?", (book_id,)).fetchone()
    assert res_row is not None
