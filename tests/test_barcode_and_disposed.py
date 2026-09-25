import json
import os
import sqlite3
import pytest
from core.library.services.catalog_service import CatalogService
from core.library.services.label_service import export_label_sheet_pdf
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from data.migrate import apply_migrations
from data.repositories import book_repo


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    apply_migrations(c)
    return c


def test_migration_disposed_status_and_books_trigram(conn):
    # Test book creation
    book_id = book_repo.add_book(conn, title="คู่มือวิทยาศาสตร์ ม.1", author="สมชาย")
    
    # Test disposed status allowed
    copy_id = book_repo.insert_copy(conn, book_id, "TEST-BARCODE-01", status="disposed")
    assert copy_id > 0
    row = conn.execute("SELECT status FROM book_copies WHERE copy_id = ?", (copy_id,)).fetchone()
    assert row["status"] == "disposed"

    # Test books_fts trigram matches substring in Thai title
    rows = book_repo.search_books(conn, query="วิทยาศาสตร์")
    assert len(rows) == 1
    assert rows[0]["book_id"] == book_id


def test_add_book_and_copies_auto_barcode(conn):
    svc = CatalogService(conn)
    # Add book with 3 copies
    res1 = svc.add_book(title="ฟิสิกส์ ม.2", copy_count=3)
    assert res1.ok
    book_id = res1.data["book_id"]
    assert len(res1.data["copy_ids"]) == 3
    assert res1.data["barcodes"] == [
        f"SMTE-{book_id:05d}-01",
        f"SMTE-{book_id:05d}-02",
        f"SMTE-{book_id:05d}-03",
    ]

    # Add 2 more copies to same book
    res2 = svc.add_copies(book_id=book_id, additional_count=2)
    assert res2.ok
    assert len(res2.data["copy_ids"]) == 2
    assert res2.data["barcodes"] == [
        f"SMTE-{book_id:05d}-04",
        f"SMTE-{book_id:05d}-05",
    ]

    # Mark copy 05 as disposed and retire copy 04
    copy_05_id = res2.data["copy_ids"][1]
    res_disp = svc.mark_copy(copy_05_id, "disposed", reason="โดนน้ำท่วมชำรุดเสียหาย")
    assert res_disp.ok

    # Add 1 more copy -> seq must be 06 (never reuses retired or disposed sequence numbers)
    res3 = svc.add_copies(book_id=book_id, additional_count=1)
    assert res3.ok
    assert res3.data["barcodes"] == [f"SMTE-{book_id:05d}-06"]


def test_mark_copy_disposed_requires_reason(conn):
    svc = CatalogService(conn)
    res = svc.add_book(title="เคมี ม.3", copy_count=1)
    copy_id = res.data["copy_ids"][0]

    # Empty reason fails for disposed
    fail_res = svc.mark_copy(copy_id, "disposed", reason="")
    assert not fail_res.ok
    assert "Disposed status requires a documented reason" in fail_res.error

    fail_res2 = svc.mark_copy(copy_id, "disposed", reason="   ")
    assert not fail_res2.ok

    # Valid reason succeeds
    ok_res = svc.mark_copy(copy_id, "disposed", reason="หน้าหนังสือฉีกขาดเกิน 50%")
    assert ok_res.ok
    assert ok_res.data["status"] == "disposed"

    # Damaged without reason is allowed (intermediate report)
    dmg_res = svc.mark_copy(copy_id, "damaged")
    assert dmg_res.ok
    assert dmg_res.data["status"] == "damaged"


def test_export_label_sheet_pdf(tmp_path):
    output_pdf = str(tmp_path / "labels.pdf")
    copies = [f"SMTE-00042-{i:02d}" for i in range(1, 26)]  # 26 labels = spans 2 pages (24 per page)

    export_label_sheet_pdf(copies, output_pdf, cols=3, rows=8)
    assert os.path.exists(output_pdf)
    assert os.path.getsize(output_pdf) > 2000


def test_librarian_admin_adapter_barcodes_and_pdf(conn, tmp_path):
    adapter = LibrarianAdminAdapter(conn)
    output_pdf = str(tmp_path / "adapter_labels.pdf")

    # Add book with count string "2"
    add_resp = json.loads(adapter.addBook(
        title="ชีววิทยา ม.1",
        isbn="9780123456789",
        author="ดร. สมปอง",
        barcodes_csv="2"
    ))
    assert add_resp["ok"]
    book_id = add_resp["data"]["book_id"]
    barcodes = add_resp["data"]["barcodes"]
    assert len(barcodes) == 2
    assert barcodes[0] == f"SMTE-{book_id:05d}-01"
    assert barcodes[1] == f"SMTE-{book_id:05d}-02"

    # Add copies via adapter with count string "1"
    add_copies_resp = json.loads(adapter.addCopies(book_id, "1"))
    assert add_copies_resp["ok"]
    assert add_copies_resp["data"]["barcodes"] == [f"SMTE-{book_id:05d}-03"]

    # Export labels PDF via adapter
    all_barcodes = barcodes + add_copies_resp["data"]["barcodes"]
    pdf_resp = json.loads(adapter.exportLabelsPdf(json.dumps(all_barcodes), output_pdf))
    assert pdf_resp["ok"]
    assert os.path.exists(output_pdf)
    assert os.path.getsize(output_pdf) > 1000
