"""ISBN metadata lookup service using local SQLite cache and NLT web scraper."""

import concurrent.futures
import html.parser
import sqlite3
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from core.shared.mock_qt import HAVE_QT
from core.shared.result import Err, Ok, Result

if HAVE_QT:
    from PySide6.QtCore import QCoreApplication, QEventLoop

NLT_SEARCH_URL = "https://e-service.nlt.go.th/ISBNReq/ListSearchPub"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def normalize_isbn(raw: str) -> str:
    """Strip whitespace and hyphens from raw ISBN and convert to uppercase."""
    if not raw:
        return ""
    return "".join(raw.split()).replace("-", "").upper()


def is_valid_isbn(isbn: str) -> bool:
    """Validate whether normalized ISBN is a valid 10 or 13-character string."""
    if not isbn:
        return False
    if len(isbn) == 13 and isbn.isdigit():
        return True
    if len(isbn) == 10 and isbn[:-1].isdigit() and (isbn[-1].isdigit() or isbn[-1].upper() == "X"):
        return True
    return False


class _TableRowParser(html.parser.HTMLParser):
    """Parse table rows and cells into a list of row values."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: List[List[str]] = []
        self._current_row: Optional[List[str]] = None
        self._current_cell: Optional[List[str]] = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th") and self._current_row is not None:
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._current_cell is not None:
            self._current_row.append("".join(self._current_cell).strip())  # type: ignore
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = None


def _extract_book_from_row(row: List[str], isbn: str) -> Optional[Dict[str, str]]:
    """Extract book dict from table row matching the target ISBN."""
    if len(row) < 5 or normalize_isbn(row[4]) != isbn:
        return None
    return {"title": row[1].strip(), "author": row[2].strip(), "publisher": row[3].strip(), "isbn": isbn}


def parse_nlt_html(html_text: str, isbn: str) -> Optional[Dict[str, str]]:
    """Parse NLT HTML table to extract book metadata matching ISBN."""
    if not html_text:
        return None
    parser = _TableRowParser()
    try:
        parser.feed(html_text)
    except Exception:
        return None
    for row in parser.rows:
        book = _extract_book_from_row(row, isbn)
        if book:
            return book
    return None


def _fetch_nlt_page(isbn: str, timeout: float = 5.0) -> str:
    """Fetch raw HTML from NLT search endpoint."""
    query = urllib.parse.urlencode({"KeywordTypeKey": "4", "Keyword": isbn, "ISBNReqTypeKey": ""})
    url = f"{NLT_SEARCH_URL}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


class IsbnLookupService:
    """Lookup ISBN metadata via cache and National Library of Thailand."""

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

    def _wait_for_future(
        self, future: concurrent.futures.Future, isbn: str
    ) -> Optional[Dict[str, str]]:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                html_text = future.result(timeout=0.02)
                return parse_nlt_html(html_text, isbn)
            except concurrent.futures.TimeoutError:
                if HAVE_QT:
                    QCoreApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
        return None

    def _fetch_remote(self, isbn: str) -> Optional[Dict[str, str]]:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_fetch_nlt_page, isbn, timeout=self.timeout)
        try:
            return self._wait_for_future(future, isbn)
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

    def lookup(self, raw_isbn: str) -> Result[Dict[str, str], str]:
        """Lookup book metadata by ISBN from cache, books, or NLT."""
        isbn = normalize_isbn(raw_isbn)
        if not is_valid_isbn(isbn):
            return Err("cannot fetch data")
        local_data = self._lookup_local(isbn)
        if local_data:
            return Ok(local_data)
        remote = self._fetch_remote(isbn)
        if not remote:
            return Err("cannot fetch data")
        self._save_metadata(remote)
        return Ok(remote)
