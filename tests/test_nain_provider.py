"""
tests/test_nain_provider.py
Covers:
  - Nain Book (naiin.com) parsers: search-page embedded items, product JSON-LD
  - _fetch_nain two-step fetch (search -> detail) and failure paths
  - _fetch_text HTML fetch helper (success + failure logging)
  - fetch_remote_providers chain: Nain Book is the LAST fallback
  Fixtures are trimmed captures of the live site (2026-11-12).
"""
import logging
from pathlib import Path

import pytest

from core.library.services import isbn_providers
from core.library.services.isbn_providers import (
    NAIIN_BASE,
    _fetch_nain,
    _fetch_text,
    fetch_remote_providers,
    parse_nain_product_ld,
    parse_nain_search_items,
)

FIXTURES = Path(__file__).parent / "fixtures" / "nain"
SEARCH_HTML = (FIXTURES / "search_result_9786161894856.html").read_text(encoding="utf-8")
DETAIL_HTML = (FIXTURES / "product_detail_715593.html").read_text(encoding="utf-8")
ISBN = "9786161894856"
SEARCH_URL = f"{NAIIN_BASE}/search-result?title={ISBN}"
DETAIL_URL = f"{NAIIN_BASE}/product/detail/715593"


def test_parse_nain_search_items_real_fixture():
    items = parse_nain_search_items(SEARCH_HTML)
    assert len(items) == 1
    assert items[0]["ProductID"] == 715593
    assert items[0]["ProductName"].startswith("Money Monster")
    assert items[0]["AuthorName"] == "ทราย Money Monster"


def test_parse_nain_search_items_no_product_list_tag():
    assert parse_nain_search_items("<html><body>no results</body></html>") == []


def test_parse_nain_search_items_entity_escaped_apostrophe():
    html_text = "<product-list :items='[{\"ProductID\": 1, \"ProductName\": \"O'Neal&#x27;s book\"}]' :default-error='null'>"
    items = parse_nain_search_items(html_text)
    assert len(items) == 1 and items[0]["ProductName"] == "O'Neal's book"


def test_parse_nain_search_items_skips_rows_without_product_id():
    html_text = "<product-list :items='[{\"ProductName\": \"x\"}, {\"ProductID\": 9}]' :default-error='null'>"
    items = parse_nain_search_items(html_text)
    assert [it.get("ProductID") for it in items] == [9]


def test_parse_nain_product_ld_real_fixture():
    meta = parse_nain_product_ld(DETAIL_HTML, ISBN)
    assert meta["isbn"] == ISBN
    assert meta["title"].startswith("Money Monster A Guide Through Crisis")
    assert meta["author"] == "ทราย Money Monster"
    assert meta["publisher"] == "อมรินทร์ How to"


def test_parse_nain_product_ld_isbn_mismatch():
    assert parse_nain_product_ld(DETAIL_HTML, "9786160000001") is None


def test_parse_nain_product_ld_dash_isbn_normalizes():
    assert parse_nain_product_ld(DETAIL_HTML, "978-616-1894-85-6") is not None


def test_parse_nain_product_ld_author_list_shape():
    html_text = (
        '<script type="application/ld+json">'
        '{"@context": "https://schema.org", "@type": ["Product", "Book"], '
        '"name": "T", "isbn": "9786160000001", '
        '"author": [{"@type": "Person", "name": "A One"}, {"@type": "Person", "name": "A Two"}]}'
        "</script>"
    )
    assert parse_nain_product_ld(html_text, "9786160000001")["author"] == "A One, A Two"


def _patch_fetch(monkeypatch, pages: dict):
    calls = []

    def fake(url, timeout=5.0, extra_headers=None):
        calls.append(url)
        return pages.get(url)

    monkeypatch.setattr(isbn_providers, "_fetch_text", fake)
    return calls


def test_fetch_nain_hit(monkeypatch):
    calls = _patch_fetch(monkeypatch, {SEARCH_URL: SEARCH_HTML, DETAIL_URL: DETAIL_HTML})
    meta = _fetch_nain(ISBN, timeout=10.0)
    assert meta["title"].startswith("Money Monster")
    assert meta["publisher"] == "อมรินทร์ How to"
    assert calls == [SEARCH_URL, DETAIL_URL]


def test_fetch_nain_search_empty(monkeypatch):
    calls = _patch_fetch(monkeypatch, {SEARCH_URL: "<html>0 รายการ</html>"})
    assert _fetch_nain(ISBN, timeout=10.0) is None
    assert calls == [SEARCH_URL]  # no detail fetch attempted


def test_fetch_nain_detail_isbn_mismatch(monkeypatch):
    other = "9786160000001"
    calls = _patch_fetch(monkeypatch, {f"{NAIIN_BASE}/search-result?title={other}": SEARCH_HTML, DETAIL_URL: DETAIL_HTML})
    # detail page's JSON-LD ISBN (9786161894856) does not match the queried ISBN
    assert _fetch_nain(other, timeout=10.0) is None
    assert calls == [f"{NAIIN_BASE}/search-result?title={other}", DETAIL_URL]


def test_fetch_nain_network_failure_retries_once(monkeypatch):
    calls = []

    def fake(url, timeout=5.0, extra_headers=None):
        calls.append(url)
        return None

    monkeypatch.setattr(isbn_providers, "_fetch_text", fake)
    import core.library.services.isbn_providers as mod

    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    assert _fetch_nain(ISBN, timeout=10.0) is None
    assert calls == [SEARCH_URL, SEARCH_URL]  # one retry, then give up


def test_fetch_text_logs_failure_and_returns_none(monkeypatch, caplog):
    def boom(req, timeout=None, context=None):
        raise OSError("offline")

    monkeypatch.setattr(isbn_providers.urllib.request, "urlopen", boom)
    with caplog.at_level(logging.WARNING, logger="smte.isbn"):
        assert _fetch_text("https://example.invalid/x", timeout=0.2) is None
    assert any("failed after" in m and "OSError" in m for m in caplog.messages)


def test_chain_nain_book_is_last_fallback(monkeypatch, caplog):
    monkeypatch.setattr(isbn_providers, "_fetch_primo", lambda *a, **k: None)
    monkeypatch.setattr(isbn_providers, "_fetch_seed", lambda *a, **k: None)
    monkeypatch.setattr(isbn_providers, "_fetch_openlibrary", lambda *a, **k: None)
    monkeypatch.setattr(isbn_providers, "_fetch_chulabook", lambda *a, **k: None)
    meta = {"isbn": ISBN, "title": "Nain Only", "author": "A", "publisher": "P"}
    monkeypatch.setattr(isbn_providers, "_fetch_nain", lambda *a, **k: meta)
    with caplog.at_level(logging.INFO, logger="smte.isbn"):
        assert fetch_remote_providers(ISBN, timeout=1.0) == meta
    assert any("HIT at Nain Book" in m for m in caplog.messages)
