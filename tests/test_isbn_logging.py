"""
tests/test_isbn_logging.py
Covers:
  - fetch_remote_providers logs each provider attempt (INFO) and the final outcome
  - _fetch_json logs failed HTTP requests with elapsed time + exception (WARNING)
  - IsbnLookupService.lookup logs local hit / remote miss / invalid input
  - detect_chulabook_books logs per-book skip reasons and a run summary
  - setup_app_logging: idempotent, single RotatingFileHandler, records land in the file
"""
import logging
import sqlite3
import urllib.error

import pytest

from core.library.services import chulabook_service
from core.library.services import isbn_providers
from core.library.services import isbn_service as isbn_service_module
from core.library.services.isbn_providers import fetch_remote_providers
from core.library.services.isbn_service import IsbnLookupService
from core.shared import app_logging
from core.shared.app_logging import setup_app_logging

ISBN = "9786160000001"
META = {"isbn": ISBN, "title": "Test Book", "author": "A", "publisher": ""}


def test_chain_logs_each_provider_and_hit(monkeypatch, caplog):
    monkeypatch.setattr(isbn_providers, "_fetch_primo", lambda isbn, timeout: None)
    monkeypatch.setattr(isbn_providers, "_fetch_seed", lambda isbn, timeout: None)
    monkeypatch.setattr(isbn_providers, "_fetch_openlibrary", lambda isbn, timeout: None)
    monkeypatch.setattr(isbn_providers, "_fetch_chulabook", lambda isbn, timeout: META)
    with caplog.at_level(logging.INFO, logger="smte.isbn"):
        assert fetch_remote_providers(ISBN, timeout=1.0) == META
    msgs = caplog.messages
    assert any("miss at NLT Primo" in m for m in msgs)
    assert any("miss at SE-ED" in m for m in msgs)
    assert any("miss at Open Library" in m for m in msgs)
    assert any("HIT at Chulabook" in m and "Test Book" in m for m in msgs)


def test_chain_logs_final_not_found(monkeypatch, caplog):
    monkeypatch.setattr(isbn_providers, "_fetch_primo", lambda isbn, timeout: None)
    monkeypatch.setattr(isbn_providers, "_fetch_seed", lambda isbn, timeout: None)
    monkeypatch.setattr(isbn_providers, "_fetch_openlibrary", lambda isbn, timeout: None)
    monkeypatch.setattr(isbn_providers, "_fetch_chulabook", lambda isbn, timeout: None)
    with caplog.at_level(logging.INFO, logger="smte.isbn"):
        assert fetch_remote_providers(ISBN, timeout=0.5) is None
    assert any("not found by any remote provider" in m for m in caplog.messages)


def test_fetch_json_logs_failure_with_elapsed_time(monkeypatch, caplog):
    def boom(req, timeout=None, context=None):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with caplog.at_level(logging.WARNING, logger="smte.isbn"):
        with pytest.raises(urllib.error.URLError):
            isbn_providers._fetch_json("https://api.chulabook.com/products", 0.2)
    assert any("failed after" in m and "URLError" in m and "api.chulabook.com" in m for m in caplog.messages)


def test_lookup_logs_local_hit(caplog):
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE isbn_cache (isbn TEXT PRIMARY KEY, title TEXT, author TEXT, "
        "publisher TEXT, published_year TEXT)"
    )
    conn.execute("INSERT INTO isbn_cache (isbn, title, author) VALUES (?, ?, ?)", (ISBN, "Cached Book", "C"))
    conn.commit()
    svc = IsbnLookupService(conn)
    with caplog.at_level(logging.INFO, logger="smte.isbn"):
        res = svc.lookup(ISBN)
    assert res.ok is True
    assert any("local hit" in m and ISBN in m for m in caplog.messages)


def test_lookup_logs_remote_miss(monkeypatch, caplog):
    conn = sqlite3.connect(":memory:")
    svc = IsbnLookupService(conn)
    monkeypatch.setattr(isbn_service_module, "fetch_remote_providers", lambda isbn, timeout: None)
    with caplog.at_level(logging.WARNING, logger="smte.isbn"):
        res = svc.lookup(ISBN)
    assert res.ok is False
    assert any("no remote provider hit" in m and ISBN in m for m in caplog.messages)


def test_lookup_logs_invalid_input(caplog):
    conn = sqlite3.connect(":memory:")
    svc = IsbnLookupService(conn)
    with caplog.at_level(logging.WARNING, logger="smte.isbn"):
        res = svc.lookup("12345")
    assert res.ok is False
    assert any("invalid ISBN" in m for m in caplog.messages)


def test_detect_logs_skip_reason_and_summary(monkeypatch, caplog):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE books (book_id INTEGER PRIMARY KEY, isbn TEXT, title TEXT, author TEXT)")
    conn.execute("INSERT INTO books VALUES (1, ?, 'T', 'A')", (ISBN,))
    conn.commit()
    monkeypatch.setattr(chulabook_service, "_fetch_chulabook", lambda isbn, timeout: None)
    with caplog.at_level(logging.DEBUG, logger="smte.isbn"):
        res = chulabook_service.detect_chulabook_books(conn, timeout=1.0, workers=1)
    assert res.ok is True and res.data == []
    msgs = caplog.messages
    assert any("book 1" in m and "not found in chulabook" in m for m in msgs)
    assert any("detect start: 1 books" in m for m in msgs)
    assert any("detect done: 0 flagged of 1" in m for m in msgs)


def test_setup_app_logging_idempotent_and_writes_file(tmp_path, monkeypatch):
    smte = logging.getLogger("smte")
    monkeypatch.setattr(app_logging, "get_app_log_dir", lambda name: tmp_path)
    monkeypatch.setattr(smte, "_smte_app", None, raising=False)
    try:
        setup_app_logging("SMTE-Test")
        setup_app_logging("SMTE-Test")  # second call must not duplicate handlers
        file_handlers = [h for h in smte.handlers if isinstance(h, app_logging.logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        logging.getLogger("smte.isbn").info("hello log test")
        assert "hello log test" in (tmp_path / "app.log").read_text(encoding="utf-8")
    finally:
        for handler in list(smte.handlers):
            smte.removeHandler(handler)
            handler.close()
        monkeypatch.setattr(smte, "_smte_app", None, raising=False)