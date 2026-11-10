"""Detect catalog books that exist only in the Chulabook store.

A book is flagged when its (normalized) ISBN resolves in the Chulabook API
but in no standard ISBN database (NLT Primo / SE-ED / Open Library) and is
not already known-good via the local isbn_cache.
"""
import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor  # explicit import: 3.15 lazy module attr is not callable
from typing import Dict, List

logger = logging.getLogger("smte.isbn")

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
            logger.debug("book %s (%s): skip — not found in chulabook", book_id, isbn)
            return None
        if isbn in cache:
            logger.debug("book %s (%s): skip — already in isbn_cache", book_id, isbn)
            return None
        step = min(timeout, 2.0)
        if _fetch_primo(isbn, step) or _fetch_seed(isbn, step) or _fetch_openlibrary(isbn, timeout):
            logger.debug("book %s (%s): skip — found in standard providers", book_id, isbn)
            return None
        logger.info("book %s (%s): FLAGGED chulabook-only — title=%r", book_id, isbn, title)
        return {"book_id": book_id, "isbn": isbn, "title": title or "", "author": author or ""}
    except Exception as exc:
        logger.warning("book %s (%s): classify error: %s: %s", book_id, isbn, type(exc).__name__, exc)
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
    t0 = time.monotonic()
    logger.info("detect start: %d books with ISBN, workers=%d", len(rows), workers)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda r: _classify(r, cache, timeout), rows))
    flagged = [r for r in results if r is not None]
    logger.info("detect done: %d flagged of %d books in %.1fs", len(flagged), len(rows), time.monotonic() - t0)
    return Ok(flagged)