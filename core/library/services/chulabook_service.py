"""Detect catalog books that exist only in the Chulabook store.

A book is flagged when its (normalized) ISBN resolves in the Chulabook API
but in no standard ISBN database (NLT Primo / SE-ED / Open Library) and is
not already known-good via the local isbn_cache.
"""
import sqlite3
from concurrent.futures import ThreadPoolExecutor  # explicit import: 3.15 lazy module attr is not callable
from typing import Dict, List

from core.library.services.isbn_providers import (
    _fetch_chulabook,
    _fetch_openlibrary,
    _fetch_primo,
    _fetch_seed,
    is_valid_isbn,
    normalize_isbn,
)
from core.shared.result import Err, Ok, Result

__all__ = ["detect_chulabook_books"]


def _classify(row, cache, timeout: float):
    """One book row -> flagged dict, or None. Per-row exceptions -> None."""
    book_id, raw_isbn, title, author = row
    isbn = normalize_isbn(raw_isbn or "")
    if not is_valid_isbn(isbn):
        return None
    try:
        if not _fetch_chulabook(isbn, timeout):
            return None
        if isbn in cache:
            return None
        step = min(timeout, 2.0)
        if _fetch_primo(isbn, step) or _fetch_seed(isbn, step) or _fetch_openlibrary(isbn, timeout):
            return None
        return {"book_id": book_id, "isbn": isbn, "title": title or "", "author": author or ""}
    except Exception:
        return None


def detect_chulabook_books(
    conn: sqlite3.Connection, timeout: float = 5.0, workers: int = 8
) -> Result[List[Dict[str, object]], str]:
    """Flag books found in Chulabook but in no standard ISBN database."""
    try:
        rows = conn.execute(
            "SELECT book_id, isbn, title, author FROM books "
            "WHERE isbn IS NOT NULL AND TRIM(isbn) != ''"
        ).fetchall()
    except sqlite3.OperationalError:
        return Err("books table missing")
    try:
        cache = {r[0] for r in conn.execute("SELECT isbn FROM isbn_cache")}
    except sqlite3.OperationalError:
        cache = set()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda r: _classify(r, cache, timeout), rows))
    return Ok([r for r in results if r is not None])