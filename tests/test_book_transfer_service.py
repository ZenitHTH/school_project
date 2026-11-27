"""Tests for core.library.services.book_transfer_service."""

import sqlite3

from core.library.services.book_transfer_service import (
    apply_books_import,
    export_books_db,
    preview_books_import,
)
from core.shared.db_transfer.manifest import build_manifest
from core.shared.db_transfer.sqlite_io import write_sqlite_bundle
from data.db import get_connection
from data.migrate import apply_migrations
from data.repositories import book_repo


def _seed_books(conn):
    cat_id = book_repo.add_category(conn, "วิทยาศาสตร์")
    bid = book_repo.add_book(
        conn,
        title="ฟิสิกส์ ม.4",
        author="สมชาย",
        isbn="978-616-0001",
        category_id=cat_id,
        shelf_location="A-1",
    )
    book_repo.add_copies(conn, bid, barcodes=["SMTE-00001-01", "SMTE-00001-02"])
    conn.commit()
    return cat_id, bid


def test_books_sqlite_and_xlsx_export_preview_merge(tmp_path):
    src = get_connection(str(tmp_path / "src.sqlite"), pin="123456")
    apply_migrations(src)
    _seed_books(src)

    dst_db = tmp_path / "dst.sqlite"
    dst = get_connection(str(dst_db), pin="123456")
    apply_migrations(dst)

    for ext in ("sqlite", "xlsx"):
        bundle = tmp_path / f"books_export.{ext}"
        exp = export_books_db(src, str(bundle), fmt=ext)
        assert exp.is_ok(), exp.error

        prev = preview_books_import(dst, str(bundle), mode="merge")
        assert prev.is_ok(), prev.error
        summary = prev.unwrap()
        assert summary["new_books"] == 1
        assert summary["new_copies"] == 2

    applied = apply_books_import(
        dst, str(tmp_path / "books_export.sqlite"), mode="merge", db_path=str(dst_db), actor="TEST"
    )
    assert applied.is_ok(), applied.error
    assert len(book_repo.search_books(dst, "ฟิสิกส์")) == 1

    # Re-importing the same XLSX bundle in merge mode produces zero duplicate books/copies
    dup_prev = preview_books_import(dst, str(tmp_path / "books_export.xlsx"), mode="merge")
    assert dup_prev.is_ok()
    assert dup_prev.unwrap()["new_books"] == 0
    assert dup_prev.unwrap()["new_copies"] == 0
    src.close()
    dst.close()


def test_books_replace_blocked_with_active_loans_and_unpaid_fines(tmp_path):
    db_file = tmp_path / "lib.sqlite"
    conn = get_connection(str(db_file), pin="123456")
    apply_migrations(conn)
    _seed_books(conn)
    conn.execute("INSERT INTO students (student_id, full_name, status) VALUES (1001, 'Test Student', 'active')")
    conn.execute(
        "INSERT INTO loans (copy_id, student_id, borrowed_at, due_at, status) "
        "VALUES (1, 1001, '2026-11-01T00:00:00Z', '2026-11-15T00:00:00Z', 'active')"
    )
    conn.commit()

    empty_bundle = tmp_path / "empty_books.sqlite"
    empty_conn = get_connection(str(tmp_path / "empty.sqlite"), pin="123456")
    apply_migrations(empty_conn)
    assert export_books_db(empty_conn, str(empty_bundle), fmt="sqlite").is_ok()

    res = apply_books_import(conn, str(empty_bundle), mode="replace", db_path=str(db_file), actor="TEST")
    assert res.is_err()
    assert "loan" in (res.error or "").lower()

    # Returned loan with unpaid fine still blocks replace
    conn.execute("UPDATE loans SET status = 'returned', returned_at = '2026-11-16T00:00:00Z' WHERE loan_id = 1")
    conn.execute("INSERT INTO fines (loan_id, amount, reason, paid) VALUES (1, 20.0, 'Overdue', 0)")
    conn.commit()

    res_fine = apply_books_import(conn, str(empty_bundle), mode="replace", db_path=str(db_file), actor="TEST")
    assert res_fine.is_err()
    assert "fine" in (res_fine.error or "").lower()

    # Once fine is paid, replace succeeds with backup
    conn.execute("UPDATE fines SET paid = 1, paid_at = '2026-11-17T00:00:00Z' WHERE fine_id = 1")
    conn.commit()
    res_ok = apply_books_import(conn, str(empty_bundle), mode="replace", db_path=str(db_file), actor="TEST")
    assert res_ok.is_ok(), res_ok.error
    assert conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0
    assert res_ok.unwrap().get("backup_path")

    empty_conn.close()
    conn.close()


def test_books_merge_preserves_on_loan_copy_and_matches_normalized_isbn(tmp_path):
    src = get_connection(str(tmp_path / "src_norm.sqlite"), pin="123456")
    apply_migrations(src)
    cat_id = book_repo.add_category(src, "คณิตศาสตร์")
    bid = book_repo.add_book(src, title="แคลคูลัส", author="อ.ก", isbn="9786160009", category_id=cat_id)
    book_repo.add_copies(src, bid, barcodes=["SMTE-00001-01"])
    src.commit()
    bundle = tmp_path / "norm.xlsx"
    assert export_books_db(src, str(bundle), fmt="xlsx").is_ok()

    dst_db = tmp_path / "dst_norm.sqlite"
    dst = get_connection(str(dst_db), pin="123456")
    apply_migrations(dst)
    dst_cat = book_repo.add_category(dst, "คณิตศาสตร์")
    # Dashed ISBN + lowercase/dash barcode already present and on_loan
    dst_bid = book_repo.add_book(dst, title="แคลคูลัสเดิม", author="อ.ก", isbn="978-616-0009", category_id=dst_cat)
    dst.execute("INSERT INTO book_copies (book_id, barcode, status) VALUES (?, 'smte0000101', 'on_loan')", (dst_bid,))
    dst.commit()

    res = apply_books_import(dst, str(bundle), mode="merge", db_path=str(dst_db), actor="TEST")
    assert res.is_ok(), res.error
    assert dst.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 1
    assert dst.execute("SELECT status FROM book_copies").fetchone()[0] == "on_loan"
    src.close()
    dst.close()


def test_books_import_rejects_wrong_domain_and_active_db_overwrite(tmp_path):
    db_file = tmp_path / "active.sqlite"
    conn = get_connection(str(db_file), pin="123456")
    apply_migrations(conn)

    # Active DB overwrite blocked
    assert export_books_db(conn, str(db_file), fmt="sqlite").is_err()

    # Wrong domain bundle rejected
    wrong_bundle = tmp_path / "students.sqlite"
    schemas = {
        "categories": "CREATE TABLE categories (category_id INTEGER PRIMARY KEY, name TEXT NOT NULL)",
        "books": "CREATE TABLE books (book_id INTEGER PRIMARY KEY, title TEXT NOT NULL)",
        "book_copies": "CREATE TABLE book_copies (copy_id INTEGER PRIMARY KEY, book_id INTEGER, barcode TEXT, status TEXT)",
    }
    rows = {"categories": [], "books": [], "book_copies": []}
    write_sqlite_bundle(str(wrong_bundle), build_manifest("students", 1, rows), schemas, rows)
    assert preview_books_import(conn, str(wrong_bundle), mode="merge").is_err()
    assert apply_books_import(conn, str(wrong_bundle), mode="merge", db_path=str(db_file)).is_err()

    # Unsupported extension & missing file rejected
    assert preview_books_import(conn, str(tmp_path / "bad.csv"), mode="merge").is_err()
    assert export_books_db(conn, str(tmp_path / "bad.csv"), fmt="csv").is_err()  # type: ignore[arg-type]

    # Symlink export rejected
    sym = tmp_path / "link.xlsx"
    sym.symlink_to(tmp_path / "target.xlsx")
    assert export_books_db(conn, str(sym), fmt="xlsx").is_err()
    conn.close()


def test_books_export_with_circulation_and_file_uri_and_null_thai_fields(tmp_path):
    db_file = tmp_path / "circ.sqlite"
    conn = get_connection(str(db_file), pin="123456")
    apply_migrations(conn)
    bid = book_repo.add_book(conn, title="ภาษาไทย ป.๖ — ฉบับพิเศษ", author=None, isbn=None)
    book_repo.add_copies(conn, bid, barcodes=["TH-001"])
    conn.execute("INSERT INTO students (student_id, full_name, status) VALUES (1, 'สมชาย', 'active')")
    conn.execute(
        "INSERT INTO reservations (book_id, student_id, reserved_at, status) "
        "VALUES (?, 1, '2026-11-27T00:00:00Z', 'waiting')",
        (bid,),
    )
    conn.commit()

    # Active reservation blocks replace
    out_uri = (tmp_path / "circ_export.sqlite").as_uri()
    exp = export_books_db(conn, out_uri, fmt="sqlite", include_circulation=True)
    assert exp.is_ok(), exp.error
    assert apply_books_import(conn, out_uri, mode="replace", db_path=str(db_file)).is_err()

    # Thai title & NULL fields round-trip cleanly via XLSX merge into fresh DB
    xlsx_uri = (tmp_path / "thai_null.xlsx").as_uri()
    assert export_books_db(conn, xlsx_uri, fmt="xlsx").is_ok()
    fresh = get_connection(str(tmp_path / "fresh.sqlite"), pin="123456")
    apply_migrations(fresh)
    prev = preview_books_import(fresh, xlsx_uri, mode="merge")
    assert prev.is_ok() and prev.unwrap()["new_books"] == 1
    res = apply_books_import(fresh, xlsx_uri, mode="merge")
    assert res.is_ok(), res.error
    row = fresh.execute("SELECT title, author, isbn FROM books").fetchone()
    assert row["title"] == "ภาษาไทย ป.๖ — ฉบับพิเศษ"
    assert row["author"] is None and row["isbn"] is None
    fresh.close()
    conn.close()
