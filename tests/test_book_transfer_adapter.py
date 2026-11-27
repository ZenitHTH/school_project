"""Adapter tests for LibrarianAdminAdapter book database export/preview/import slots."""

import json
from data.db import get_connection
from data.migrate import apply_migrations
from data.repositories import book_repo
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter


def _seed_sample_book(conn) -> None:
    cat_id = book_repo.add_category(conn, "วิทยาศาสตร์")
    book_id = book_repo.add_book(
        conn,
        title="ฟิสิกส์ ม.4",
        author="สมชาย",
        isbn="978-616-0001",
        category_id=cat_id,
        shelf_location="A-1",
    )
    book_repo.add_copies(conn, book_id, barcodes=["SMTE-00001-01", "SMTE-00001-02"])
    conn.commit()


def test_librarian_adapter_book_transfer_and_active_db_guard(tmp_path):
    lib_db = tmp_path / "lib.sqlite"
    lib_conn = get_connection(str(lib_db), pin="123456")
    apply_migrations(lib_conn)
    _seed_sample_book(lib_conn)
    lib_adapter = LibrarianAdminAdapter(lib_conn)

    try:
        bad_lib = json.loads(lib_adapter.exportBooksDatabase(str(lib_db), "sqlite", False))
        assert bad_lib["ok"] is False

        out_books = tmp_path / "books_out.xlsx"
        res_b = json.loads(lib_adapter.exportBooksDatabase(out_books.as_uri(), "xlsx", False))
        assert res_b["ok"] is True
        assert res_b["data"]["books_count"] == 1
        assert res_b["data"]["copies_count"] == 2

        prev_b = json.loads(lib_adapter.previewBooksImport(out_books.as_uri(), "merge"))
        assert prev_b["ok"] is True
        assert prev_b["data"]["total_source_books"] == 1

        # Also test SQLite roundtrip into a second empty library database
        out_sqlite = tmp_path / "books_out.sqlite"
        res_sq = json.loads(lib_adapter.exportBooksDatabase(str(out_sqlite), "sqlite", False))
        assert res_sq["ok"] is True

        dst_db = tmp_path / "dst_lib.sqlite"
        dst_conn = get_connection(str(dst_db), pin="123456")
        apply_migrations(dst_conn)
        dst_adapter = LibrarianAdminAdapter(dst_conn)
        try:
            prev_dst = json.loads(dst_adapter.previewBooksImport(out_sqlite.as_uri(), "merge"))
            assert prev_dst["ok"] is True
            assert prev_dst["data"]["new_books"] == 1
            assert prev_dst["data"]["new_copies"] == 2

            applied = json.loads(dst_adapter.applyBooksImport(out_sqlite.as_uri(), "merge", "LIBRARIAN"))
            assert applied["ok"] is True
            assert applied["data"]["added_books"] == 1
            assert applied["data"]["added_copies"] == 2
            assert applied["data"]["backup_path"]

            books = json.loads(dst_adapter.searchBooks("ฟิสิกส์", 0))
            assert len(books) == 1
        finally:
            dst_conn.close()
    finally:
        lib_conn.close()


def test_librarian_adapter_book_transfer_rejects_bad_paths_and_symlinks(tmp_path):
    lib_db = tmp_path / "lib.sqlite"
    conn = get_connection(str(lib_db), pin="123456")
    apply_migrations(conn)
    adapter = LibrarianAdminAdapter(conn)

    try:
        bad_txt = tmp_path / "bad.txt"
        bad_txt.write_text("nope", encoding="utf-8")
        assert json.loads(adapter.exportBooksDatabase(str(bad_txt), "sqlite", False))["ok"] is False
        assert json.loads(adapter.previewBooksImport(str(bad_txt), "merge"))["ok"] is False
        assert json.loads(adapter.applyBooksImport(str(bad_txt), "merge", "LIBRARIAN"))["ok"] is False

        sym = tmp_path / "sym.sqlite"
        sym.symlink_to(lib_db)
        assert json.loads(adapter.exportBooksDatabase(str(sym), "sqlite", False))["ok"] is False
        assert json.loads(adapter.previewBooksImport(str(sym), "merge"))["ok"] is False
        assert json.loads(adapter.applyBooksImport(str(lib_db), "replace", "LIBRARIAN"))["ok"] is False
    finally:
        conn.close()
