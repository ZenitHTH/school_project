"""ISBN metadata lookup service using local SQLite cache and chained remote JSON providers."""

import concurrent.futures
import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor  # explicit import: 3.15 lazy module attr is not callable
from typing import Dict, Optional

logger = logging.getLogger("smte.isbn")

from core.library.services.isbn_providers import (
    _fetch_json,
    fetch_remote_providers,
    is_arabic_isbn,
    is_valid_isbn,
    normalize_isbn,
    parse_nlt_primo_json,
    parse_openlibrary_json,
    parse_seed_product,
)
from core.shared.mock_qt import HAVE_QT
from core.shared.result import Err, Ok, Result

if HAVE_QT:
    from PySide6.QtCore import QCoreApplication, QEventLoop

__all__ = [
    "normalize_isbn",
    "is_valid_isbn",
    "is_arabic_isbn",
    "_fetch_json",
    "parse_nlt_primo_json",
    "parse_seed_product",
    "parse_openlibrary_json",
    "fetch_remote_providers",
    "IsbnLookupService",
]


class IsbnLookupService:
    """Lookup ISBN metadata via authoritative catalog, local cache, and chained remote providers."""

    def __init__(self, conn: sqlite3.Connection, timeout: float = 5.0) -> None:
        self.conn = conn
        self.timeout = timeout
        self._init_cache_table()

    def _init_cache_table(self) -> None:
        with self.conn:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS isbn_cache ("
                "isbn TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT, "
                "publisher TEXT, published_year TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )

    def _query_cache(self, isbn: str) -> Optional[Dict[str, str]]:
        cur = self.conn.cursor()
        cur.execute("SELECT title, author, publisher FROM isbn_cache WHERE isbn = ?", (isbn,))
        row = cur.fetchone()
        return {"isbn": isbn, "title": row[0] or "", "author": row[1] or "", "publisher": row[2] or ""} if row else None

    def _query_books_table(self, isbn: str) -> Optional[Dict[str, str]]:
        cur = self.conn.cursor()
        try:
            sql = (
                "SELECT title, author, publisher FROM books "
                "WHERE REPLACE(REPLACE(UPPER(isbn), '-', ''), ' ', '') = ? "
                "AND title IS NOT NULL AND title != '' "
                "ORDER BY active DESC, book_id DESC LIMIT 1"
            )
            cur.execute(sql, (isbn,))
            row = cur.fetchone()
            return {"isbn": isbn, "title": row[0] or "", "author": row[1] or "", "publisher": row[2] or ""} if row else None
        except sqlite3.OperationalError:
            return None

    def _wait_for_future(self, future: concurrent.futures.Future) -> Optional[Dict[str, str]]:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                return future.result(timeout=0.02)
            except concurrent.futures.TimeoutError:
                if HAVE_QT and QCoreApplication.instance() is not None:
                    QCoreApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
        return None

    def _fetch_remote(self, isbn: str) -> Optional[Dict[str, str]]:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(fetch_remote_providers, isbn, timeout=self.timeout)
        try:
            return self._wait_for_future(future)
        except Exception:
            return None
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _save_metadata(self, meta: Dict[str, str]) -> None:
        sql = "INSERT OR REPLACE INTO isbn_cache (isbn, title, author, publisher, published_year) VALUES (?, ?, ?, ?, ?)"
        with self.conn:
            self.conn.execute(sql, (
                meta.get("isbn", ""), meta.get("title", ""),
                meta.get("author", ""), meta.get("publisher", ""),
                meta.get("published_year", "")
            ))

    def save_cache(self, isbn: str, title: str, author: str = "") -> None:
        """Cache book metadata in SQLite."""
        clean_isbn = normalize_isbn(isbn)
        self._save_metadata({"isbn": clean_isbn, "title": title, "author": author, "publisher": ""})

    def _lookup_local(self, isbn: str) -> Optional[Dict[str, str]]:
        local = self._query_books_table(isbn)
        if local:
            return local
        return self._query_cache(isbn)

    def lookup(self, raw_isbn: Optional[str]) -> Result[Dict[str, str], str]:
        """Lookup book metadata by ISBN from books, cache, or remote providers."""
        t0 = time.monotonic()
        clean_raw = (raw_isbn or "").strip()
        if clean_raw and not is_arabic_isbn(clean_raw):
            logger.warning("lookup rejected: input %r is not Western digits (Thai/Arabic keyboard layout?)", clean_raw)
            return Err("ลืมเปลี่ยนภาษา")
        isbn = normalize_isbn(clean_raw)
        if not is_valid_isbn(isbn):
            logger.warning("lookup rejected: invalid ISBN %r (normalized=%s)", clean_raw, isbn)
            return Err("cannot fetch data")
        local_data = self._lookup_local(isbn)
        if local_data:
            logger.info("lookup %s: local hit (books/isbn_cache) in %.2fs — title=%r", isbn, time.monotonic() - t0, local_data.get("title", ""))
            return Ok(local_data)
        remote = self._fetch_remote(isbn)
        if not remote:
            logger.warning("lookup %s: no remote provider hit in %.2fs", isbn, time.monotonic() - t0)
            return Err("cannot fetch data")
        self._save_metadata(remote)
        logger.info("lookup %s: remote hit saved to isbn_cache in %.2fs — title=%r", isbn, time.monotonic() - t0, remote.get("title", ""))
        return Ok(remote)
