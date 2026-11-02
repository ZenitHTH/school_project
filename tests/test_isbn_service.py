import concurrent.futures
import json
import sqlite3
import urllib.error
import pytest
from core.library.services.isbn_service import (
    IsbnLookupService,
    _TableRowParser,
    _fetch_nlt_page,
    is_valid_isbn,
    normalize_isbn,
    parse_nlt_html,
)

SAMPLE_NLT_TABLE_HTML = """
<html><body>
<table class="table">
  <thead><tr><th>ลำดับ</th><th>ชื่อเรื่อง</th><th>ผู้แต่ง</th><th>สำนักพิมพ์</th><th>ISBN</th></tr></thead>
  <tbody>
    <tr>
      <td>1</td>
      <td>คณิตศาสตร์คิดเรียงลำดับเป็นระบบ : ชุดเรขาคณิต เล่ม 2</td>
      <td>ฝ่ายวิชาการ</td>
      <td>ภูมิบัณฑิต</td>
      <td>9786167706955</td>
    </tr>
  </tbody>
</table>
</body></html>
"""

SAMPLE_NEWS_ONLY_HTML = "<html><body><table><tr><td>27/09/2569</td><td>ปิดทำการ</td></tr></table></body></html>"


def test_normalize_and_validate_isbn():
    assert normalize_isbn("") == ""
    assert normalize_isbn(" 978-616-7706-95-5 ") == "9786167706955"
    assert normalize_isbn("020161622x") == "020161622X"
    assert is_valid_isbn("") is False
    assert is_valid_isbn("12345") is False
    assert is_valid_isbn("020161622X") is True
    assert is_valid_isbn("0306406152") is True
    assert is_valid_isbn("020161622A") is False
    assert is_valid_isbn("9786167706955") is True
    assert is_valid_isbn("SMTE-00001-01") is False


def test_parse_nlt_html():
    assert parse_nlt_html("", "9786167706955") is None
    parsed = parse_nlt_html(SAMPLE_NLT_TABLE_HTML, "9786167706955")
    assert parsed is not None
    assert parsed["title"] == "คณิตศาสตร์คิดเรียงลำดับเป็นระบบ : ชุดเรขาคณิต เล่ม 2"
    assert parsed["author"] == "ฝ่ายวิชาการ"
    assert parsed["publisher"] == "ภูมิบัณฑิต"
    assert parse_nlt_html(SAMPLE_NEWS_ONLY_HTML, "9786167706955") is None

    class ExplodingParser(_TableRowParser):
        def feed(self, data):
            raise RuntimeError("parse error")

    orig = _TableRowParser.feed
    _TableRowParser.feed = ExplodingParser.feed
    assert parse_nlt_html(SAMPLE_NLT_TABLE_HTML, "9786167706955") is None
    _TableRowParser.feed = orig


def test_fetch_nlt_page(monkeypatch):
    class DummyHeaders:
        def __init__(self, charset="utf-8"):
            self._charset = charset

        def get_content_charset(self):
            return self._charset

    class DummyResponse:
        def __init__(self, charset="utf-8"):
            self.headers = DummyHeaders(charset)

        def read(self):
            return "<html>ทดสอบ</html>".encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout, context: DummyResponse("utf-8"))
    res = _fetch_nlt_page("9786167706955")
    assert "ทดสอบ" in res

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout, context: DummyResponse(None))
    res2 = _fetch_nlt_page("9786167706955")
    assert "ทดสอบ" in res2


def test_service_cache_and_save_cache():
    conn = sqlite3.connect(":memory:")
    svc = IsbnLookupService(conn)
    svc.save_cache("9786167706955", "คู่มือ", "ผู้แต่ง")
    res = svc.lookup("9786167706955")
    assert res.ok is True
    assert res.data["title"] == "คู่มือ"

    # Verify save_cache normalizes hyphenated input
    svc.save_cache("978-616-7706-95-5", "คู่มือฉบับขีดคั่น", "ผู้แต่ง")
    res_hyphen = svc.lookup("9786167706955")
    assert res_hyphen.ok is True
    assert res_hyphen.data["title"] == "คู่มือฉบับขีดคั่น"
    cur = conn.cursor()
    cur.execute("SELECT isbn FROM isbn_cache WHERE title = 'คู่มือฉบับขีดคั่น'")
    assert cur.fetchone()[0] == "9786167706955"
    conn.close()


def test_service_books_table_matching():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE books ("
        "book_id INTEGER PRIMARY KEY, "
        "title TEXT, author TEXT, publisher TEXT, isbn TEXT, "
        "active INTEGER DEFAULT 1)"
    )
    svc = IsbnLookupService(conn)
    # Stale cache entry should be shadowed by authoritative books row
    svc.save_cache("978-616-7706-95-5", "ชื่อหนังสือเก่าในแคช", "ผู้แต่งเดิม")

    # Insert retired book (active=0, newer ID) and active book (active=1, older ID)
    conn.execute(
        "INSERT INTO books (book_id, title, author, publisher, isbn, active) "
        "VALUES (1, 'คณิตศาสตร์ ฉบับใช้งาน', 'ฝ่ายวิชาการ', 'ภูมิบัณฑิต', '978-616-7706-95-5', 1)"
    )
    conn.execute(
        "INSERT INTO books (book_id, title, author, publisher, isbn, active) "
        "VALUES (2, 'คณิตศาสตร์ เล่มจำหน่ายออก', 'ฝ่ายวิชาการ', 'ภูมิบัณฑิต', '978-616-7706-95-5', 0)"
    )
    conn.commit()

    # Active book (active=1) must take precedence and override stale isbn_cache
    res = svc.lookup("9786167706955")
    assert res.ok is True
    assert res.data["title"] == "คณิตศาสตร์ ฉบับใช้งาน"
    assert res.data["publisher"] == "ภูมิบัณฑิต"

    # When books table is edited, new title is returned immediately (not cached/shadowed)
    conn.execute("UPDATE books SET title = 'คณิตศาสตร์ ฉบับปรับปรุงใหม่' WHERE book_id = 1")
    conn.commit()
    res_updated = svc.lookup("9786167706955")
    assert res_updated.ok is True
    assert res_updated.data["title"] == "คณิตศาสตร์ ฉบับปรับปรุงใหม่"

    # Case-insensitivity check with ISBN-10 'X'
    conn.execute(
        "INSERT INTO books (book_id, title, author, publisher, isbn, active) "
        "VALUES (3, 'Refactoring', 'Martin Fowler', 'Addison-Wesley', '0-201-61622-x', 1)"
    )
    conn.commit()
    res_x = svc.lookup("020161622X")
    assert res_x.ok is True
    assert res_x.data["title"] == "Refactoring"

    assert svc._query_books_table("9780000000000") is None
    conn.close()


def test_service_operational_error_and_timeout(monkeypatch):
    conn = sqlite3.connect(":memory:")
    svc = IsbnLookupService(conn, timeout=0.05)
    assert svc._query_books_table("9786167706955") is None

    attempts = 0

    class SteppingFuture:
        def result(self, timeout=None):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise concurrent.futures.TimeoutError()
            return SAMPLE_NLT_TABLE_HTML

    res_step = svc._wait_for_future(SteppingFuture(), "9786167706955")
    assert res_step is not None
    assert res_step["isbn"] == "9786167706955"

    monkeypatch.setattr(
        "core.library.services.isbn_service._fetch_nlt_page",
        lambda *a, **k: (_ for _ in ()).throw(urllib.error.URLError("fail")),
    )
    res_err = svc.lookup("9786167706955")
    assert res_err.ok is False
    assert res_err.error == "cannot fetch data"

    class HangingFuture:
        def result(self, timeout=None):
            raise concurrent.futures.TimeoutError()

    assert svc._wait_for_future(HangingFuture(), "9786167706955") is None
    conn.close()


def test_adapter_fetch_isbn_metadata_and_signals(tmp_path, monkeypatch):
    from data.db import get_connection
    from data.migrate import apply_migrations
    from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter

    db_path = str(tmp_path / "lib.sqlite")
    conn = get_connection(db_path)
    apply_migrations(conn)
    adapter = LibrarianAdminAdapter(conn)

    started, completed = False, False

    def on_started():
        nonlocal started
        started = True

    def on_completed(payload):
        nonlocal completed
        completed = True

    adapter.isbnLookupStarted.connect(on_started)
    adapter.isbnLookupCompleted.connect(on_completed)

    monkeypatch.setattr(
        "core.library.services.isbn_service._fetch_nlt_page",
        lambda *a, **k: SAMPLE_NLT_TABLE_HTML,
    )
    raw_json = adapter.fetchIsbnMetadata("9786167706955")
    payload = json.loads(raw_json)
    assert payload["ok"] is True
    assert started is True
    assert completed is True

    bad_json = adapter.fetchIsbnMetadata("invalid")
    assert json.loads(bad_json)["ok"] is False
    conn.close()
