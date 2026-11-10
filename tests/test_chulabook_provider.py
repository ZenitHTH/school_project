"""
tests/test_chulabook_provider.py
Covers:
  - Chulabook API parsers (search exact-barcode match, detail mapping)
  - _fetch_chulabook two-step fetch (search -> detail) and failure paths
  - _fetch_json extra_headers (Origin/Referer) behavior
  - fetch_remote_providers chain: chulabook is the LAST fallback
"""
import json
import urllib.error
from pathlib import Path

import pytest

from core.library.services import isbn_providers
from core.library.services.isbn_providers import (
    _fetch_json,
    _fetch_chulabook,
    fetch_remote_providers,
    parse_chulabook_detail,
    parse_chulabook_products,
)

FIXTURES = Path(__file__).parent / "fixtures" / "chulabook"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


SEARCH_FIXTURE = _load("products_search_9786169444541.json")
DETAIL_FIXTURE = _load("product_258216.json")


def test_parse_chulabook_products_exact_match():
    assert parse_chulabook_products(SEARCH_FIXTURE, "9786169444541") == "258216"


def test_parse_chulabook_products_no_exact_match():
    other = {"rows": [dict(SEARCH_FIXTURE["rows"][0], barcode="9999999999999")]}
    assert parse_chulabook_products(other, "9786169444541") is None


def test_parse_chulabook_products_dash_isbn():
    assert parse_chulabook_products(SEARCH_FIXTURE, "978-616-9444-54-1") == "258216"


def test_parse_chulabook_detail_mapping():
    meta = parse_chulabook_detail(DETAIL_FIXTURE, "9786169444541")
    assert meta["isbn"] == "9786169444541"
    assert meta["title"] == DETAIL_FIXTURE["name"]
    assert meta["author"] == DETAIL_FIXTURE["author"]
    assert meta["publisher"] == ""


def test_parse_chulabook_detail_author_falls_back_to_translator():
    data = {"name": "T", "author": None, "translator": "ผู้แปล"}
    assert parse_chulabook_detail(data, "9786160000001")["author"] == "ผู้แปล"


def test_fetch_chulabook_success(monkeypatch):
    calls = []

    def fake_fetch_json(url, timeout=5.0, extra_headers=None):
        calls.append(url)
        if "/products?" in url:
            return SEARCH_FIXTURE
        return DETAIL_FIXTURE

    monkeypatch.setattr(isbn_providers, "_fetch_json", fake_fetch_json)
    meta = _fetch_chulabook("9786169444541", timeout=5.0)
    assert meta is not None
    assert meta["title"] == DETAIL_FIXTURE["name"]
    assert meta["isbn"] == "9786169444541"
    assert any("/products/258216" in u for u in calls)


def test_fetch_chulabook_no_match_returns_none(monkeypatch):
    calls = []
    no_match = {"count": 0, "rows": [dict(SEARCH_FIXTURE["rows"][0], barcode="9999999999999")]}

    def fake_fetch_json(url, timeout=5.0, extra_headers=None):
        calls.append(url)
        return no_match

    monkeypatch.setattr(isbn_providers, "_fetch_json", fake_fetch_json)
    assert _fetch_chulabook("9786169444541", timeout=5.0) is None
    assert all("/products/258216" not in u for u in calls)  # detail never requested


def test_fetch_chulabook_network_error(monkeypatch):
    def boom(url, timeout=5.0, extra_headers=None):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(isbn_providers, "_fetch_json", boom)
    assert _fetch_chulabook("9786169444541", timeout=5.0) is None


def test_fetch_json_extra_headers(monkeypatch):
    captured = {}

    class DummyResponse:
        class _Headers:
            def get_content_charset(self):
                return None

        headers = _Headers()

        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout, context):
        captured["headers"] = dict(req.headers)
        return DummyResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    _fetch_json("https://api.chulabook.com/x", extra_headers={"Origin": "https://www.chulabook.com"})
    assert captured["headers"].get("Origin") == "https://www.chulabook.com"
    captured.clear()
    _fetch_json("https://api.chulabook.com/x")
    assert "Origin" not in captured["headers"]


def test_fetch_remote_providers_chulabook_last_fallback(monkeypatch):
    meta = {"isbn": "9786169444541", "title": "C", "author": "A", "publisher": ""}
    monkeypatch.setattr(isbn_providers, "_fetch_primo", lambda isbn, timeout: None)
    monkeypatch.setattr(isbn_providers, "_fetch_seed", lambda isbn, timeout: None)
    monkeypatch.setattr(isbn_providers, "_fetch_openlibrary", lambda isbn, timeout: None)
    monkeypatch.setattr(isbn_providers, "_fetch_chulabook", lambda isbn, timeout: meta)
    assert fetch_remote_providers("9786169444541", timeout=5.0) == meta
