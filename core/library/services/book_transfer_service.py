"""Book database export, diff preview, and merge/replace import orchestrator."""

import os
import sqlite3
from typing import Any, Literal, Optional, Tuple

from core.shared.db_transfer import (
    build_manifest, create_pre_import_backup, read_sqlite_bundle,
    read_xlsx_bundle, write_sqlite_bundle, write_xlsx_bundle,
)
from core.shared.log_service import record_activity
from core.shared.mock_qt import normalize_file_path
from core.shared.result import Err, Ok, Result
from data.repositories.book_repo import _normalize_isbn

_CORE_TABLES = ("categories", "books", "book_copies")
_CIRC_TABLES = ("loans", "reservations", "fines", "book_copy_status_log")
_VALID_COPY_STATUSES = {"available", "on_loan", "lost", "damaged", "retired", "disposed"}
_TABLE_SPECS = {
    "categories": (("category_id", "INTEGER PRIMARY KEY"), ("name", "TEXT NOT NULL")),
    "books": (
        ("book_id", "INTEGER PRIMARY KEY"), ("isbn", "TEXT"), ("title", "TEXT NOT NULL"),
        ("author", "TEXT"), ("publisher", "TEXT"), ("category_id", "INTEGER"),
        ("category", "TEXT"), ("shelf_location", "TEXT"),
        ("total_copies", "INTEGER NOT NULL DEFAULT 0"), ("active", "INTEGER NOT NULL DEFAULT 1"),
    ),
    "book_copies": (("copy_id", "INTEGER PRIMARY KEY"), ("book_id", "INTEGER NOT NULL"), ("barcode", "TEXT"), ("status", "TEXT NOT NULL")),
    "loans": (("loan_id", "INTEGER PRIMARY KEY"), ("copy_id", "INTEGER NOT NULL"), ("student_id", "INTEGER NOT NULL"), ("borrowed_at", "TEXT NOT NULL"), ("due_at", "TEXT NOT NULL"), ("returned_at", "TEXT"), ("status", "TEXT NOT NULL")),
    "reservations": (("reservation_id", "INTEGER PRIMARY KEY"), ("book_id", "INTEGER NOT NULL"), ("student_id", "INTEGER NOT NULL"), ("reserved_at", "TEXT NOT NULL"), ("status", "TEXT NOT NULL")),
    "fines": (("fine_id", "INTEGER PRIMARY KEY"), ("loan_id", "INTEGER NOT NULL"), ("amount", "REAL NOT NULL"), ("reason", "TEXT NOT NULL"), ("paid", "INTEGER NOT NULL"), ("paid_at", "TEXT")),
    "book_copy_status_log": (("id", "INTEGER PRIMARY KEY"), ("copy_id", "INTEGER NOT NULL"), ("old_status", "TEXT NOT NULL"), ("new_status", "TEXT NOT NULL"), ("reason", "TEXT"), ("changed_at", "TEXT NOT NULL")),
}


def _table_cols(table: str) -> tuple[str, ...]:
    return tuple(col for col, _ in _TABLE_SPECS[table])


def _table_ddl(table: str) -> str:
    cols = ", ".join(f"{col} {typ}" for col, typ in _TABLE_SPECS[table])
    return f"CREATE TABLE {table} ({cols})"


def _main_db_path(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    return str(row[2]) if row and row[2] else ""


def _reject_active_db_target(conn: sqlite3.Connection, target_path: str) -> Optional[str]:
    active, clean = _main_db_path(conn), normalize_file_path(target_path)
    if active and clean and os.path.realpath(active) == os.path.realpath(clean):
        return "Cannot overwrite the active application database"
    return None


def _norm_text(val: Any) -> str:
    return str(val).strip().lower() if val is not None else ""


def _norm_barcode(val: Any) -> str:
    return str(val).strip().replace("-", "").lower() if val is not None else ""


def _book_match_key(title: Any, author: Any, isbn: Any) -> Tuple[str, Any]:
    norm_isbn = _normalize_isbn(str(isbn)) if isbn is not None else None
    return ("isbn", norm_isbn) if norm_isbn else ("title_author", (_norm_text(title), _norm_text(author)))


def export_books_db(
    conn: sqlite3.Connection,
    output_path: str,
    fmt: Literal["sqlite", "xlsx"],
    include_circulation: bool = False,
) -> Result[dict[str, Any], str]:
    """Export books domain tables to checksummed .sqlite or .xlsx bundle."""
    try:
        err = _reject_active_db_target(conn, output_path)
        if err:
            return Err(err)
        if fmt not in ("sqlite", "xlsx"):
            return Err(f"Unsupported export format: {fmt}")
        tables = _CORE_TABLES + (_CIRC_TABLES if include_circulation else ())
        rows_by_table = {t: [tuple(r) for r in conn.execute(f"SELECT {', '.join(_table_cols(t))} FROM {t}").fetchall()] for t in tables}
        if fmt == "sqlite":
            res = write_sqlite_bundle(output_path, build_manifest("books", 10, rows_by_table), {t: _table_ddl(t) for t in tables}, rows_by_table)
        else:
            res = write_xlsx_bundle(output_path, [(t, _table_cols(t), rows_by_table[t]) for t in tables])
        if res.is_err():
            return Err(res.error or "Export failed")
        return Ok({"output_path": res.unwrap(), "format": fmt, "books_count": len(rows_by_table["books"]), "copies_count": len(rows_by_table["book_copies"]), "categories_count": len(rows_by_table["categories"])})
    except Exception as exc:
        return Err(f"Export failed: {exc}")


def _load_import_bundle(input_path: str) -> Result[tuple[str, dict[str, list[dict[str, Any]]]], str]:
    clean = normalize_file_path(input_path)
    ext = os.path.splitext(clean)[1].lower()
    if ext in (".sqlite", ".db"):
        res = read_sqlite_bundle(clean, expected_domain="books", required_tables=_CORE_TABLES)
        return Err(res.error or "Invalid SQLite bundle") if res.is_err() else Ok(("sqlite", res.unwrap()[1]))
    if ext == ".xlsx":
        res = read_xlsx_bundle(clean, required_sheets=_CORE_TABLES)
        return Err(res.error or "Invalid XLSX bundle") if res.is_err() else Ok(("xlsx", res.unwrap()))
    return Err("Unsupported file extension (expected .sqlite or .xlsx)")


def _check_replace_blockers(conn: sqlite3.Connection) -> Optional[str]:
    checks = (
        ("SELECT COUNT(*) FROM loans WHERE status IN ('active', 'overdue')", "active loan(s)"),
        ("SELECT COUNT(*) FROM fines WHERE paid = 0", "unpaid fine(s)"),
        ("SELECT COUNT(*) FROM reservations WHERE status IN ('waiting', 'ready')", "active reservation(s)"),
    )
    for sql, label in checks:
        count = conn.execute(sql).fetchone()[0]
        if count > 0:
            return f"Cannot replace while {count} {label} exist"
    return None


def _compute_preview(conn: sqlite3.Connection, bundle: dict[str, list[dict[str, Any]]], mode: str) -> dict[str, Any]:
    src_cats = [c for c in bundle["categories"] if _norm_text(c.get("name"))]
    src_books = [b for b in bundle["books"] if _norm_text(b.get("title"))]
    src_copies = [cp for cp in bundle["book_copies"] if _norm_barcode(cp.get("barcode"))]
    if mode == "replace":
        blocker = _check_replace_blockers(conn)
        return {"mode": mode, "new_categories": len(src_cats), "new_books": len(src_books), "updated_books": 0, "new_copies": len(src_copies), "skipped_copies": 0, "total_source_books": len(src_books), "total_source_copies": len(src_copies), "can_apply": blocker is None, "blocked_reason": blocker or ""}

    local_cats = {_norm_text(r[0]) for r in conn.execute("SELECT name FROM categories").fetchall()}
    local_books = {_book_match_key(r["title"], r["author"], r["isbn"]) for r in conn.execute("SELECT title, author, isbn FROM books").fetchall()}
    local_copies = {_norm_barcode(r[0]) for r in conn.execute("SELECT barcode FROM book_copies WHERE barcode IS NOT NULL").fetchall()}
    new_books = sum(1 for b in src_books if _book_match_key(b.get("title"), b.get("author"), b.get("isbn")) not in local_books)
    new_copies = sum(1 for cp in src_copies if _norm_barcode(cp.get("barcode")) not in local_copies)
    return {"mode": mode, "new_categories": sum(1 for c in src_cats if _norm_text(c.get("name")) not in local_cats), "new_books": new_books, "updated_books": len(src_books) - new_books, "new_copies": new_copies, "skipped_copies": len(src_copies) - new_copies, "total_source_books": len(src_books), "total_source_copies": len(src_copies), "can_apply": True, "blocked_reason": ""}


def preview_books_import(conn: sqlite3.Connection, input_path: str, mode: Literal["merge", "replace"] = "merge") -> Result[dict[str, Any], str]:
    """Load bundle and preview book/copy diff without mutating the database."""
    if mode not in ("merge", "replace"):
        return Err(f"Unsupported import mode: {mode}")
    loaded = _load_import_bundle(input_path)
    if loaded.is_err():
        return Err(loaded.error or "Failed to load bundle")
    fmt, bundle = loaded.unwrap()
    try:
        summary = _compute_preview(conn, bundle, mode)
        summary["format"] = fmt
        return Ok(summary)
    except Exception as exc:
        return Err(f"Preview failed: {exc}")


def _resolve_categories(cur: sqlite3.Cursor, src_cats: list[dict[str, Any]]) -> tuple[dict[Any, int], dict[str, int]]:
    local = {_norm_text(r[1]): r[0] for r in cur.execute("SELECT category_id, name FROM categories").fetchall()}
    id_map: dict[Any, int] = {}
    for c in src_cats:
        name = str(c.get("name") or "").strip()
        if not name:
            continue
        if name.lower() not in local:
            cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            local[name.lower()] = cur.lastrowid
        if c.get("category_id") is not None:
            id_map[c["category_id"]] = local[name.lower()]
    return id_map, local


def _upsert_books(cur: sqlite3.Cursor, src_books: list[dict[str, Any]], cat_id_map: dict[Any, int], cat_name_map: dict[str, int]) -> tuple[dict[Any, int], int]:
    local_books = {_book_match_key(r["title"], r["author"], r["isbn"]): r["book_id"] for r in cur.execute("SELECT book_id, title, author, isbn FROM books").fetchall()}
    book_id_map: dict[Any, int] = {}
    added = 0
    for b in src_books:
        title = str(b.get("title") or "").strip()
        if not title:
            continue
        cid = cat_id_map.get(b.get("category_id")) or cat_name_map.get(_norm_text(b.get("category")))
        cname = str(b.get("category") or "").strip() or None
        key = _book_match_key(title, b.get("author"), b.get("isbn"))
        vals = (b.get("isbn"), title, b.get("author"), b.get("publisher"), cid, cname, b.get("shelf_location"), 1 if b.get("active", 1) in (1, True, "1") else 0)
        if key in local_books:
            bid = local_books[key]
            cur.execute("UPDATE books SET isbn=?, title=?, author=?, publisher=?, category_id=?, category=?, shelf_location=?, active=? WHERE book_id=?", (*vals, bid))
        else:
            cur.execute("INSERT INTO books (isbn, title, author, publisher, category_id, category, shelf_location, total_copies, active) VALUES (?,?,?,?,?,?,?,0,?)", vals)
            bid = cur.lastrowid
            local_books[key] = bid
            added += 1
        if b.get("book_id") is not None:
            book_id_map[b["book_id"]] = bid
    return book_id_map, added


def _upsert_copies(cur: sqlite3.Cursor, src_copies: list[dict[str, Any]], book_id_map: dict[Any, int]) -> int:
    local_copies = {_norm_barcode(r[1]): (r[0], r[2]) for r in cur.execute("SELECT copy_id, barcode, status FROM book_copies WHERE barcode IS NOT NULL").fetchall()}
    added = 0
    for cp in src_copies:
        bc, target_bid = str(cp.get("barcode") or "").strip(), book_id_map.get(cp.get("book_id"))
        if not bc or not target_bid:
            continue
        raw_st = str(cp.get("status") or "available").strip()
        st = raw_st if (raw_st in _VALID_COPY_STATUSES and raw_st != "on_loan") else "available"
        bkey = _norm_barcode(bc)
        if bkey in local_copies:
            cid, cur_st = local_copies[bkey]
            if cur_st != "on_loan":
                cur.execute("UPDATE book_copies SET status = ? WHERE copy_id = ?", (st, cid))
        else:
            cur.execute("INSERT INTO book_copies (book_id, barcode, status) VALUES (?, ?, ?)", (target_bid, bc, st))
            local_copies[bkey] = (cur.lastrowid, st)
            added += 1
    cur.execute("UPDATE books SET total_copies = (SELECT COUNT(*) FROM book_copies bc WHERE bc.book_id = books.book_id)")
    return added


def apply_books_import(conn: sqlite3.Connection, input_path: str, mode: Literal["merge", "replace"] = "merge", db_path: str = "", actor: str = "ADMIN") -> Result[dict[str, Any], str]:
    """Import books bundle atomically in merge or replace mode with pre-import backup."""
    if mode not in ("merge", "replace"):
        return Err(f"Unsupported import mode: {mode}")
    loaded = _load_import_bundle(input_path)
    if loaded.is_err():
        return Err(loaded.error or "Failed to load bundle")
    fmt, bundle = loaded.unwrap()
    if mode == "replace":
        blocker = _check_replace_blockers(conn)
        if blocker:
            return Err(blocker)
    target_db = db_path or _main_db_path(conn)
    backup_path = ""
    if target_db and target_db != ":memory:":
        b_res = create_pre_import_backup(conn, target_db)
        if b_res.is_err():
            return Err(b_res.error or "Backup failed")
        backup_path = b_res.unwrap()
    try:
        with conn:
            cur = conn.cursor()
            if mode == "replace":
                for tbl in ("fines", "loans", "reservations", "book_copy_status_log", "book_copies", "books", "categories"):
                    cur.execute(f"DELETE FROM {tbl}")
            cat_id_map, cat_name_map = _resolve_categories(cur, bundle["categories"])
            book_id_map, added_books = _upsert_books(cur, bundle["books"], cat_id_map, cat_name_map)
            added_copies = _upsert_copies(cur, bundle["book_copies"], book_id_map)
            record_activity(conn, action=f"library.import_{mode}", entity_type="catalog", entity_id="bulk", detail=f"Imported {added_books} books, {added_copies} copies ({fmt}, {mode})", actor=actor)
        return Ok({"mode": mode, "format": fmt, "added_books": added_books, "added_copies": added_copies, "backup_path": backup_path})
    except Exception as exc:
        return Err(f"Import failed: {exc}")
