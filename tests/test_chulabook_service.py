"""
tests/test_chulabook_service.py
Covers detect_chulabook_books: flags catalog books found in Chulabook but in
no standard ISBN database (NLT Primo / SE-ED / Open Library / isbn_cache).
All providers monkeypatched — no network in tests.
"""
import sqlite3

import pytest

from core.library.services import chulabook_service
from core.library.services.chulabook_service import detect_chulabook_books
from data.db import get_connection
from data.migrate import apply_migrations
from data.repositories import book_repo

META = lambda isbn: {"isbn": isbn, "title": "CB", "author": "CB-A", "publisher": ""}


@pytest.fixture
def conn():
    con = get_connection(":memory:")
    apply_migrations(con)
    yield con
    con.close()


def _patch_providers(monkeypatch, chulabook=..., primo=..., seed=..., openlibrary=...):
    monkeypatch.setattr(chulabook_service, "_fetch_chulabook", chulabook)
    monkeypatch.setattr(chulabook_service, "_fetch_primo", primo)
    monkeypatch.setattr(chulabook_service, "_fetch_seed", seed)
    monkeypatch.setattr(chulabook_service, "_fetch_openlibrary", openlibrary)


def _none(isbn, timeout):
    return None


def test_flags_chulabook_only_book(conn, monkeypatch):
    book_repo.add_book(conn, title="ท", isbn="9786169444541", author="A")
    _patch_providers(monkeypatch, chulabook=lambda i, t: META(i), primo=_none, seed=_none, openlibrary=_none)
    res = detect_chulabook_books(conn)
    assert res.ok is True
    assert len(res.data) == 1
    assert res.data[0]["isbn"] == "9786169444541"
    assert res.data[0]["title"] == "ท"


def test_cached_isbn_never_flagged(conn, monkeypatch):
    book_repo.add_book(conn, title="ท", isbn="9786169444541", author="A")
    # isbn_cache is created lazily by IsbnLookupService, not by migrations
    conn.execute(
        "CREATE TABLE IF NOT EXISTS isbn_cache ("
        "isbn TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT, "
        "publisher TEXT, published_year TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.execute("INSERT INTO isbn_cache (isbn, title) VALUES (?, 'cached')", ("9786169444541",))
    conn.commit()
    _patch_providers(monkeypatch, chulabook=lambda i, t: META(i), primo=_none, seed=_none, openlibrary=_none)
    res = detect_chulabook_books(conn)
    assert res.ok is True
    assert res.data == []


def test_standard_db_hit_not_flagged(conn, monkeypatch):
    book_repo.add_book(conn, title="ท", isbn="9786169444541", author="A")
    _patch_providers(monkeypatch, chulabook=lambda i, t: META(i), primo=lambda i, t: META(i), seed=_none, openlibrary=_none)
    assert detect_chulabook_books(conn).data == []


def test_chulabook_miss_not_flagged(conn, monkeypatch):
    book_repo.add_book(conn, title="ท", isbn="9786169444541", author="A")
    _patch_providers(monkeypatch, chulabook=_none, primo=_none, seed=_none, openlibrary=_none)
    assert detect_chulabook_books(conn).data == []


def test_invalid_isbn_skipped(conn, monkeypatch):
    book_repo.add_book(conn, title="ท", isbn="SMTE-00001-01", author="A")
    calls = []
    _patch_providers(monkeypatch, chulabook=lambda i, t: calls.append(i) or META(i), primo=_none, seed=_none, openlibrary=_none)
    res = detect_chulabook_books(conn)
    assert res.ok is True
    assert res.data == []
    assert calls == []  # no provider call for invalid ISBN


def test_thai_digit_isbn_skipped_no_crash(conn, monkeypatch):
    book_repo.add_book(conn, title="ท", isbn="๙๗๘๖๑๖๙๔๔๔๕๔๑", author="A")
    _patch_providers(monkeypatch, chulabook=lambda i, t: META(i), primo=_none, seed=_none, openlibrary=_none)
    res = detect_chulabook_books(conn)
    assert res.ok is True
    assert res.data == []


def test_dashed_db_isbn_normalized_and_flagged(conn, monkeypatch):
    book_repo.add_book(conn, title="ท", isbn="978-616-9444-54-1", author="A")
    _patch_providers(monkeypatch, chulabook=lambda i, t: META(i), primo=_none, seed=_none, openlibrary=_none)
    res = detect_chulabook_books(conn)
    assert len(res.data) == 1
    assert res.data[0]["isbn"] == "9786169444541"


def test_duplicate_isbn_each_row_flagged(conn, monkeypatch):
    book_repo.add_book(conn, title="เล่ม1", isbn="9786169444541", author="A")
    # repo guard blocks duplicate active ISBNs; raw insert simulates legacy data
    conn.execute("INSERT INTO books (isbn, title, author, total_copies, active) VALUES (?, ?, ?, 1, 1)",
                 ("9786169444541", "เล่ม2", "A"))
    conn.commit()
    _patch_providers(monkeypatch, chulabook=lambda i, t: META(i), primo=_none, seed=_none, openlibrary=_none)
    res = detect_chulabook_books(conn)
    assert len(res.data) == 2
    assert len({r["book_id"] for r in res.data}) == 2


def test_missing_books_table_returns_err(monkeypatch):
    con = sqlite3.connect(":memory:")  # no migrations
    _patch_providers(monkeypatch, chulabook=_none, primo=_none, seed=_none, openlibrary=_none)
    res = detect_chulabook_books(con)
    con.close()
    assert res.ok is False


def test_worker_exception_skips_row(conn, monkeypatch):
    book_repo.add_book(conn, title="ดี", isbn="9786160000001", author="A")
    book_repo.add_book(conn, title="พัง", isbn="9786160000002", author="A")

    def flaky(isbn, timeout):
        if isbn == "9786160000002":
            raise RuntimeError("boom")
        return META(isbn)

    _patch_providers(monkeypatch, chulabook=flaky, primo=_none, seed=_none, openlibrary=_none)
    res = detect_chulabook_books(conn)
    assert res.ok is True
    assert [r["isbn"] for r in res.data] == ["9786160000001"]
