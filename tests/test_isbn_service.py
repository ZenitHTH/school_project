import concurrent.futures
import json
import sqlite3
import urllib.error
import pytest

from core.library.services.isbn_providers import (
    _clean_primo_field,
    _collect_label_tokens,
    _collect_lexical_texts,
    _collect_multi_label_tokens,
    _collect_single_label_token,
    _extract_primo_text,
    _extract_seed_detail,
    _fetch_json,
    _fetch_openlibrary,
    _fetch_primo,
    _fetch_seed,
    _find_multi_text,
    _find_next_text,
    _find_single_text,
    _match_seed_sku,
    fetch_remote_providers,
    is_arabic_isbn,
    is_valid_isbn,
    normalize_isbn,
    parse_nlt_primo_json,
    parse_openlibrary_json,
    parse_seed_product,
)
from core.library.services.isbn_service import IsbnLookupService


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
    assert is_valid_isbn("๑๒๓๔๕๖๗๘๙๐๑๒๓") is False


def test_is_arabic_isbn():
    assert is_arabic_isbn("9786167706955") is True
    assert is_arabic_isbn("978-616-7706-95-5") is True
    assert is_arabic_isbn("020161622X") is True
    assert is_arabic_isbn("0-201-61622-x") is True
    assert is_arabic_isbn("ตึค-ภุภ-จจ-๑๒๓๔-๕") is False
    assert is_arabic_isbn("ตึคภุภ") is False
    assert is_arabic_isbn("๑๒๓๔๕๖๗๘๙๐") is False
    assert is_arabic_isbn("abc") is False
    assert is_arabic_isbn("978-616-abc") is False
    assert is_arabic_isbn("020161622Y") is False
    assert is_arabic_isbn("") is False
    assert is_arabic_isbn("   ") is False
    assert is_arabic_isbn("-") is False
    assert is_arabic_isbn(" - ") is False


def test_fetch_json(monkeypatch):
    class DummyHeaders:
        def __init__(self, charset="utf-8"):
            self._charset = charset

        def get_content_charset(self):
            return self._charset

    class DummyResponse:
        def __init__(self, charset="utf-8"):
            self.headers = DummyHeaders(charset)

        def read(self):
            return b'{"status": "ok"}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout, context: DummyResponse("utf-8"))
    res = _fetch_json("https://example.com/api")
    assert res == {"status": "ok"}

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout, context: DummyResponse(None))
    res2 = _fetch_json("https://example.com/api")
    assert res2 == {"status": "ok"}


def test_primo_helpers_and_parser():
    assert _clean_primo_field("") == ""
    assert _clean_primo_field("Title$$QExtra") == "Title"
    assert _extract_primo_text({}, "missing") == ""
    assert _extract_primo_text({"k": []}, "k") == ""
    assert _extract_primo_text({"k": [""]}, "k") == ""
    assert _extract_primo_text({"k": ["  Val$$Sub  "]}, "k") == "Val"

    assert parse_nlt_primo_json({}, "9786167706955") is None
    assert parse_nlt_primo_json({"docs": []}, "9786167706955") is None
    assert parse_nlt_primo_json({"docs": ["not a dict"]}, "9786167706955") is None
    assert parse_nlt_primo_json({"docs": [{"pnx": {}}]}, "9786167706955") is None

    sample_doc = {
        "docs": [{
            "pnx": {
                "addata": {
                    "btitle": ["คณิตศาสตร์ ม.ต้น"],
                    "au": ["อาจารย์ ก."],
                    "pub": ["สำนักพิมพ์ ธรรม"]
                },
                "display": {
                    "creator": ["อาจารย์ ก.$$QSub"],
                    "publisher": ["สำนักพิมพ์ ธรรม"]
                }
            }
        }]
    }
    parsed = parse_nlt_primo_json(sample_doc, "9786167706955")
    assert parsed is not None
    assert parsed["title"] == "คณิตศาสตร์ ม.ต้น"
    assert parsed["author"] == "อาจารย์ ก"
    assert parsed["publisher"] == "สำนักพิมพ์ ธรรม"

    # Fallback author to publisher when author is missing
    sample_no_author = {
        "docs": [{
            "pnx": {
                "display": {
                    "title": ["คู่มือฟิสิกส์"],
                    "publisher": ["จุฬาลงกรณ์มหาวิทยาลัย"]
                }
            }
        }]
    }
    parsed_no_au = parse_nlt_primo_json(sample_no_author, "9786167706955")
    assert parsed_no_au is not None
    assert parsed_no_au["author"] == "จุฬาลงกรณ์มหาวิทยาลัย"
    assert parsed_no_au["publisher"] == "จุฬาลงกรณ์มหาวิทยาลัย"


def test_seed_helpers_and_parser():
    texts = []
    _collect_lexical_texts({"text": "หัวข้อ", "other": 123}, texts)
    _collect_lexical_texts([{"text": "เนื้อหา"}], texts)
    assert texts == ["หัวข้อ", "เนื้อหา"]
    assert _find_next_text(["a", "b"], "a") == "b"
    assert _find_next_text(["a"], "a") == ""
    assert _find_next_text(["x"], "a") == ""
    assert _find_next_text(["ผู้เขียน", "สำนักพิมพ์"], "ผู้เขียน") == ""
    assert _find_next_text(["ผู้เขียน", ":", "หมอ ก.", ",", "หมอ ข."], "ผู้เขียน") == "หมอ ก., หมอ ข."
    assert _find_next_text(["ผู้เขียน", ":", "หมอ ก.", "หมอ ข."], "ผู้เขียน") == "หมอ ก."
    assert _find_next_text(["ผู้เขียน : สมชาย"], "ผู้เขียน") == "สมชาย"
    assert _find_next_text(["สำนักพิมพ์:\xa0หจก.ซีเอ็ด"], "สำนักพิมพ์") == "หจก.ซีเอ็ด"
    assert _find_next_text(["สำนักพิมพ์ :", "รัชพล", "เดือนปีที่พิมพ์ :", "1/2025"], "สำนักพิมพ์", allow_multi=False) == "รัชพล"
    assert _find_single_text(["สำนักพิมพ์ :", "รัชพล", "เดือนปีที่พิมพ์ :", "1/2025"], "สำนักพิมพ์") == "รัชพล"
    assert _find_multi_text(["ผู้เขียน", ":", "หมอ ก.", ",", "หมอ ข."], "ผู้เขียน") == "หมอ ก., หมอ ข."
    assert _collect_single_label_token(["-", "เดี่ยว", "คู่"]) == "เดี่ยว"
    assert _collect_multi_label_tokens(["-", "หนึ่ง", ",", "สอง"]) == "หนึ่ง, สอง"

    assert _extract_seed_detail(None) == ("", "")
    assert _extract_seed_detail({}) == ("", "")
    assert _extract_seed_detail({"physicalProduct": None}) == ("", "")
    assert _extract_seed_detail({"physicalProduct": {"detail": "invalid json"}}) == ("", "")

    detail_json = json.dumps({
        "root": {
            "children": [
                {"text": "ผู้เขียน"},
                {"text": "ณัฐวุฒิ ขานภูเขียว"},
                {"text": "สำนักพิมพ์"},
                {"text": "ธรรมบัณฑิต, สนพ."}
            ]
        }
    })
    au, pub = _extract_seed_detail({"physicalProduct": {"detail": detail_json}})
    assert au == "ณัฐวุฒิ ขานภูเขียว"
    assert pub == "ธรรมบัณฑิต, สนพ."

    assert _match_seed_sku([], "9786167706603") is True
    assert _match_seed_sku(["bad"], "9786167706603") is False
    assert _match_seed_sku([{"sku": "978-616-7706-60-3"}], "9786167706603") is True
    assert _match_seed_sku([{"sku": "9999999999999"}], "9786167706603") is False

    assert parse_seed_product({}, None, "9786167706603") is None
    assert parse_seed_product({"products": ["bad"]}, None, "9786167706603") is None
    assert parse_seed_product({"products": [{"physicalProduct": None}]}, {"physicalProduct": None}, "9786167706603") is None
    mismatch_search = {
        "products": [{"physicalProduct": {"physicalProduct": {"variants": [{"sku": "111"}]}}}]
    }
    assert parse_seed_product(mismatch_search, None, "9786167706603") is None

    no_name_search = {
        "products": [{"physicalProduct": {"physicalProduct": {"name": ""}}}]
    }
    assert parse_seed_product(no_name_search, None, "9786167706603") is None

    valid_search = {
        "products": [{
            "id": "prod123",
            "physicalProduct": {
                "physicalProduct": {
                    "name": "ลุยโจทย์คณิตศาสตร์",
                    "variants": [{"sku": "9786167706603"}]
                }
            }
        }]
    }
    res = parse_seed_product(valid_search, {"physicalProduct": {"detail": detail_json}}, "9786167706603")
    assert res is not None
    assert res["title"] == "ลุยโจทย์คณิตศาสตร์"
    assert res["author"] == "ณัฐวุฒิ ขานภูเขียว"
    assert res["publisher"] == "ธรรมบัณฑิต, สนพ."

    tag_search = {
        "products": [{
            "id": "prod456",
            "physicalProduct": {
                "physicalProduct": {
                    "name": "[สกลนคร] ชีววิทยาสำหรับนักเรียนมัธยมปลาย : Biology",
                    "variants": [{"sku": "9786166088694"}]
                }
            }
        }]
    }
    dummy_pub_detail = json.dumps({
        "root": {
            "children": [
                {"text": "ผู้เขียน"},
                {"text": ":"},
                {"text": "หมอ ก."},
                {"text": "สำนักพิมพ์"},
                {"text": "-ไม่ปรากฏสำนักพิมพ์"}
            ]
        }
    })
    res_tag = parse_seed_product(tag_search, {"physicalProduct": {"detail": dummy_pub_detail}}, "9786166088694")
    assert res_tag is not None
    assert res_tag["title"] == "ชีววิทยาสำหรับนักเรียนมัธยมปลาย : Biology"
    assert res_tag["author"] == "หมอ ก."
    assert res_tag["publisher"] == ""


def test_openlibrary_parser():
    assert parse_openlibrary_json({}, "9780132350884") is None
    assert parse_openlibrary_json({"ISBN:9780132350884": "not dict"}, "9780132350884") is None
    assert parse_openlibrary_json({"ISBN:9780132350884": {"title": ""}}, "9780132350884") is None

    ol_data = {
        "ISBN:9780132350884": {
            "title": "Clean Code",
            "authors": [{"name": "Robert C. Martin"}],
            "publishers": [{"name": "Prentice Hall"}]
        }
    }
    parsed = parse_openlibrary_json(ol_data, "9780132350884")
    assert parsed is not None
    assert parsed["title"] == "Clean Code"
    assert parsed["author"] == "Robert C. Martin"
    assert parsed["publisher"] == "Prentice Hall"

    # Fallback author to publisher if authors empty
    ol_no_author = {
        "ISBN:9780132350884": {
            "title": "Clean Architecture",
            "authors": [],
            "publishers": [{"name": "Prentice Hall"}]
        }
    }
    parsed_no_au = parse_openlibrary_json(ol_no_author, "9780132350884")
    assert parsed_no_au is not None
    assert parsed_no_au["author"] == "Prentice Hall"


def test_fetch_remote_providers_chain(monkeypatch):
    # Provider 1: Primo hit
    monkeypatch.setattr(
        "core.library.services.isbn_providers._fetch_primo",
        lambda isbn, timeout: {"isbn": isbn, "title": "Primo Book", "author": "A1", "publisher": "P1"}
    )
    res_primo = fetch_remote_providers("9786167706955")
    assert res_primo["title"] == "Primo Book"

    # Provider 2: Primo miss, SE-ED hit
    monkeypatch.setattr("core.library.services.isbn_providers._fetch_primo", lambda isbn, timeout: None)
    monkeypatch.setattr(
        "core.library.services.isbn_providers._fetch_seed",
        lambda isbn, timeout: {"isbn": isbn, "title": "SEED Book", "author": "A2", "publisher": "P2"}
    )
    res_seed = fetch_remote_providers("9786167706603")
    assert res_seed["title"] == "SEED Book"

    # Provider 3: Primo & SE-ED miss, Open Library hit
    monkeypatch.setattr("core.library.services.isbn_providers._fetch_seed", lambda isbn, timeout: None)
    monkeypatch.setattr(
        "core.library.services.isbn_providers._fetch_openlibrary",
        lambda isbn, timeout: {"isbn": isbn, "title": "OL Book", "author": "A3", "publisher": "P3"}
    )
    res_ol = fetch_remote_providers("9780132350884")
    assert res_ol["title"] == "OL Book"

    # All miss
    monkeypatch.setattr("core.library.services.isbn_providers._fetch_openlibrary", lambda isbn, timeout: None)
    assert fetch_remote_providers("9780000000000") is None


def test_provider_fetch_exceptions(monkeypatch):
    monkeypatch.setattr(
        "core.library.services.isbn_providers._fetch_json",
        lambda *a, **k: (_ for _ in ()).throw(urllib.error.URLError("network error"))
    )
    assert _fetch_primo("9786167706955", 1.0) is None
    assert _fetch_seed("9786167706603", 1.0) is None
    assert _fetch_openlibrary("9780132350884", 1.0) is None


def test_fetch_seed_with_valid_json(monkeypatch):
    def fake_fetch_json(url, timeout=5.0):
        if "search-product" in url:
            return {
                "products": [{
                    "id": "prod123",
                    "physicalProduct": {
                        "physicalProduct": {
                            "name": "Hi-Speed Math",
                            "variants": [{"sku": "9786167706603"}]
                        }
                    }
                }]
            }
        return {
            "physicalProduct": {
                "detail": json.dumps({"root": {"children": [{"text": "ผู้เขียน"}, {"text": "ชินวัตร"}]}})
            }
        }

    monkeypatch.setattr("core.library.services.isbn_providers._fetch_json", fake_fetch_json)
    book = _fetch_seed("9786167706603", 1.0)
    assert book is not None
    assert book["title"] == "Hi-Speed Math"
    assert book["author"] == "ชินวัตร"

    monkeypatch.setattr("core.library.services.isbn_providers._fetch_json", lambda url, timeout: {"products": []})
    assert _fetch_seed("9786167706603", 1.0) is None

    def fake_detail_error(url, timeout=5.0):
        if "search-product" in url:
            return {
                "products": [{
                    "id": "prod123",
                    "physicalProduct": {
                        "physicalProduct": {
                            "name": "Hi-Speed Math",
                            "variants": [{"sku": "9786167706603"}]
                        }
                    }
                }]
            }
        raise urllib.error.URLError("detail error")

    monkeypatch.setattr("core.library.services.isbn_providers._fetch_json", fake_detail_error)
    book_partial = _fetch_seed("9786167706603", 1.0)
    assert book_partial is not None
    assert book_partial["title"] == "Hi-Speed Math"
    assert book_partial["author"] == ""


def test_service_cache_and_save_cache():
    conn = sqlite3.connect(":memory:")
    svc = IsbnLookupService(conn)
    svc.save_cache("9786167706955", "คู่มือ", "ผู้แต่ง")
    res = svc.lookup("9786167706955")
    assert res.ok is True
    assert res.data["title"] == "คู่มือ"

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
    svc.save_cache("978-616-7706-95-5", "ชื่อหนังสือเก่าในแคช", "ผู้แต่งเดิม")

    conn.execute(
        "INSERT INTO books (book_id, title, author, publisher, isbn, active) "
        "VALUES (1, 'คณิตศาสตร์ ฉบับใช้งาน', 'ฝ่ายวิชาการ', 'ภูมิบัณฑิต', '978-616-7706-95-5', 1)"
    )
    conn.execute(
        "INSERT INTO books (book_id, title, author, publisher, isbn, active) "
        "VALUES (2, 'คณิตศาสตร์ เล่มจำหน่ายออก', 'ฝ่ายวิชาการ', 'ภูมิบัณฑิต', '978-616-7706-95-5', 0)"
    )
    conn.commit()

    res = svc.lookup("9786167706955")
    assert res.ok is True
    assert res.data["title"] == "คณิตศาสตร์ ฉบับใช้งาน"
    assert res.data["publisher"] == "ภูมิบัณฑิต"

    conn.execute("UPDATE books SET title = 'คณิตศาสตร์ ฉบับปรับปรุงใหม่' WHERE book_id = 1")
    conn.commit()
    res_updated = svc.lookup("9786167706955")
    assert res_updated.ok is True
    assert res_updated.data["title"] == "คณิตศาสตร์ ฉบับปรับปรุงใหม่"

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
            return {"isbn": "9786167706955", "title": "Step Book", "author": "A", "publisher": "P"}

    res_step = svc._wait_for_future(SteppingFuture())
    assert res_step is not None
    assert res_step["title"] == "Step Book"

    monkeypatch.setattr(
        "core.library.services.isbn_service.fetch_remote_providers",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    res_err = svc.lookup("9786167706955")
    assert res_err.ok is False
    assert res_err.error == "cannot fetch data"

    class HangingFuture:
        def result(self, timeout=None):
            raise concurrent.futures.TimeoutError()

    assert svc._wait_for_future(HangingFuture()) is None
    conn.close()


def test_lookup_thai_keyboard_warning():
    conn = sqlite3.connect(":memory:")
    svc = IsbnLookupService(conn)
    res_thai = svc.lookup("ตึค-ภุภ")
    assert res_thai.ok is False
    assert res_thai.error == "ลืมเปลี่ยนภาษา"

    res_thai_num = svc.lookup("๑๒๓๔๕")
    assert res_thai_num.ok is False
    assert res_thai_num.error == "ลืมเปลี่ยนภาษา"

    res_empty = svc.lookup("")
    assert res_empty.ok is False
    assert res_empty.error == "cannot fetch data"

    res_none = svc.lookup(None)
    assert res_none.ok is False
    assert res_none.error == "cannot fetch data"
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
        "core.library.services.isbn_service.fetch_remote_providers",
        lambda isbn, timeout: {"isbn": isbn, "title": "Adapter Book", "author": "Auth", "publisher": "Pub"},
    )
    raw_json = adapter.fetchIsbnMetadata("9786167706955")
    payload = json.loads(raw_json)
    assert payload["ok"] is True
    assert started is True
    assert completed is True

    thai_json = adapter.fetchIsbnMetadata("ตึค-ภุภ")
    thai_payload = json.loads(thai_json)
    assert thai_payload["ok"] is False
    assert thai_payload["error"] == "ลืมเปลี่ยนภาษา"

    bad_json = adapter.fetchIsbnMetadata("invalid")
    assert json.loads(bad_json)["ok"] is False
    conn.close()
