# ISBN Lookup & Auto-fill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one-click ISBN metadata lookup (local SQLite cache + NLT web scraper) to the Librarian Book Registration screens so Title and Author auto-fill when blank without overwriting manual edits.

**Architecture:** `IsbnLookupService` in `core/library/services/isbn_service.py` validates ISBN-10/13, checks local SQLite (`isbn_cache` and `books`), and scrapes the NLT search table via Python stdlib `urllib.request` and `html.parser`, returning `Result[Dict[str, str], str]`. `LibrarianAdminAdapter.fetchIsbnMetadata` exposes the lookup to QML, and `BarcodeGeneratorView.qml` / `BookActionDialogs.qml` populate `Title` and `Author` only when currently empty.

**Tech Stack:** Python 3.14, PySide6 (Qt Quick/QML), SQLite3, stdlib `urllib.request` & `html.parser`, `pytest`.

**Spec:** `docs/superpowers/specs/2026-11-02-isbn-lookup-design.md`

## Global Constraints

- Use `Result[T, E]`, `Ok`, and `Err` from `core.shared.result`. Never raise unhandled exceptions across service boundaries.
- Zero new external dependencies (`requests`, `beautifulsoup4` forbidden); use Python stdlib `urllib.request` and `html.parser`.
- Sanitize all dictionaries with `_sanitize_for_qml` before JSON serialization in adapters.
- Only fill blank `Title` and `Author` fields in QML; never overwrite existing user-typed text.
- On lookup failure, timeout, or redirect, return `Err("cannot fetch data")` and leave inputs untouched.
- Keep files under 200 lines and functions under 20 lines following Clean Code rules.
- Maintain 100% test coverage across modified/new services and adapters.

## Review Focus

1. **Hyphenated or whitespace-padded ISBN input** (e.g., `" 978-616-7706-95-5 "`): Normalizer must strip hyphens and spaces to `"9786167706955"` before validation and lookup.
2. **NLT login redirect or reCAPTCHA page** (HTTP 200 HTML containing login form instead of book result `<table>`): Parser must not mistake layout/news tables for book records and must return `Err("cannot fetch data")`.
3. **Partial existing user input in QML** (Librarian already typed Title `"คณิต ม.ต้น"`, leaves Author blank, then clicks Fetch): Title must remain `"คณิต ม.ต้น"` while Author fills from fetched metadata.
4. **Malformed / non-ISBN barcode scan** (e.g., `"SMTE-00001-01"` or `"12345"`): Service rejects immediately with `Err("cannot fetch data")` without making any network request.
5. **Network timeout / SSL / URLError**: Caught cleanly inside boundary helper, returning `Err("cannot fetch data")` within timeout.

---

### Task 1: Core ISBN Lookup Service & HTML Parser (`IsbnLookupService`)

**Files:**
- Create: `core/library/services/isbn_service.py`
- Test: `tests/test_isbn_service.py`

**Interfaces:**
- Consumes: `core.shared.result.Result`, `core.shared.result.Ok`, `core.shared.result.Err`
- Produces:
  - `normalize_isbn(raw: str) -> str`
  - `is_valid_isbn(isbn: str) -> bool`
  - `parse_nlt_html(html_text: str, isbn: str) -> Optional[Dict[str, str]]`
  - `class IsbnLookupService`:
    - `__init__(self, conn: sqlite3.Connection, timeout: float = 5.0)`
    - `save_cache(self, isbn: str, title: str, author: str = "", publisher: str = "") -> None`
    - `lookup(self, raw_isbn: str) -> Result[Dict[str, str], str]`

- [ ] **Step 1: Write the failing unit tests in `tests/test_isbn_service.py`**

```python
import sqlite3
import urllib.error
import pytest
from core.library.services.isbn_service import (
    IsbnLookupService,
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

SAMPLE_NEWS_ONLY_HTML = """
<html><body>
<table>
  <tr><td>27/09/2569</td><td>แจ้งปิดทำการ</td></tr>
</table>
</body></html>
"""


def test_normalize_and_validate_isbn():
    assert normalize_isbn(" 978-616-7706-95-5 ") == "9786167706955"
    assert is_valid_isbn("9786167706955") is True
    assert is_valid_isbn("9786167082493") is True
    assert is_valid_isbn("9786162137792") is True
    assert is_valid_isbn("SMTE-00001-01") is False
    assert is_valid_isbn("12345") is False


def test_parse_nlt_html_extracts_book_row():
    parsed = parse_nlt_html(SAMPLE_NLT_TABLE_HTML, "9786167706955")
    assert parsed is not None
    assert parsed["title"] == "คณิตศาสตร์คิดเรียงลำดับเป็นระบบ : ชุดเรขาคณิต เล่ม 2"
    assert parsed["author"] == "ฝ่ายวิชาการ"
    assert parsed["publisher"] == "ภูมิบัณฑิต"
    assert parsed["isbn"] == "9786167706955"


def test_parse_nlt_html_ignores_unrelated_tables():
    assert parse_nlt_html(SAMPLE_NEWS_ONLY_HTML, "9786167706955") is None


def test_service_cache_hit_and_miss(monkeypatch):
    conn = sqlite3.connect(":memory:")
    svc = IsbnLookupService(conn)

    calls = []

    def fake_fetch(isbn: str, timeout: float):
        calls.append(isbn)
        return SAMPLE_NLT_TABLE_HTML

    monkeypatch.setattr("core.library.services.isbn_service._fetch_nlt_page", fake_fetch)

    res1 = svc.lookup("978-616-7706-95-5")
    assert res1.ok is True
    assert res1.data["title"] == "คณิตศาสตร์คิดเรียงลำดับเป็นระบบ : ชุดเรขาคณิต เล่ม 2"
    assert len(calls) == 1

    # Second lookup hits SQLite isbn_cache without calling network
    res2 = svc.lookup("9786167706955")
    assert res2.ok is True
    assert res2.data["author"] == "ฝ่ายวิชาการ"
    assert len(calls) == 1


def test_service_invalid_and_network_error(monkeypatch):
    conn = sqlite3.connect(":memory:")
    svc = IsbnLookupService(conn)

    res_bad = svc.lookup("SMTE-00001")
    assert res_bad.ok is False
    assert res_bad.error == "cannot fetch data"

    def fail_fetch(isbn: str, timeout: float):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr("core.library.services.isbn_service._fetch_nlt_page", fail_fetch)
    res_err = svc.lookup("9786167082493")
    assert res_err.ok is False
    assert res_err.error == "cannot fetch data"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_isbn_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.library.services.isbn_service'`

- [ ] **Step 3: Implement `core/library/services/isbn_service.py`**

Implement `normalize_isbn`, `is_valid_isbn`, `_TableRowParser(HTMLParser)`, `parse_nlt_html`, `_fetch_nlt_page`, and `IsbnLookupService` (creates `isbn_cache` table with `CREATE TABLE IF NOT EXISTS`, checks `isbn_cache` and `books`, fetches NLT URL `https://e-service.nlt.go.th/ISBNReq/ListSearchPub?KeywordTypeKey=4&Keyword=<isbn>&ISBNReqTypeKey=`, caches result on hit, returns `Err("cannot fetch data")` on any miss/exception).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_isbn_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/library/services/isbn_service.py tests/test_isbn_service.py
git commit -m "feat(library): add IsbnLookupService with SQLite cache and NLT parser"
```

---

### Task 2: Adapter Slot `fetchIsbnMetadata` in `LibrarianAdminAdapter`

**Files:**
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py:25-35,395-402`
- Test: `tests/test_isbn_service.py`

**Interfaces:**
- Consumes: `IsbnLookupService.lookup(raw_isbn: str) -> Result[Dict[str, str], str]`
- Produces: `LibrarianAdminAdapter.fetchIsbnMetadata(isbn: str) -> str` (JSON `{"ok": bool, "error": str|None, "data": {"isbn": str, "title": str, "author": str, "publisher": str}}`)

- [ ] **Step 1: Write failing adapter test in `tests/test_isbn_service.py`**

```python
import json
from data.db import get_connection
from data.migrate import apply_migrations
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter


def test_adapter_fetch_isbn_metadata(tmp_path, monkeypatch):
    db_path = str(tmp_path / "lib.sqlite")
    conn = get_connection(db_path)
    apply_migrations(conn)
    adapter = LibrarianAdminAdapter(conn)

    monkeypatch.setattr(
        "core.library.services.isbn_service._fetch_nlt_page",
        lambda isbn, timeout: SAMPLE_NLT_TABLE_HTML,
    )

    raw_json = adapter.fetchIsbnMetadata("9786167706955")
    payload = json.loads(raw_json)
    assert payload["ok"] is True
    assert payload["data"]["title"] == "คณิตศาสตร์คิดเรียงลำดับเป็นระบบ : ชุดเรขาคณิต เล่ม 2"
    assert payload["data"]["author"] == "ฝ่ายวิชาการ"

    bad_json = adapter.fetchIsbnMetadata("invalid")
    bad_payload = json.loads(bad_json)
    assert bad_payload["ok"] is False
    assert bad_payload["error"] == "cannot fetch data"
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_isbn_service.py::test_adapter_fetch_isbn_metadata -v`
Expected: FAIL with `AttributeError: 'LibrarianAdminAdapter' object has no attribute 'fetchIsbnMetadata'`

- [ ] **Step 3: Implement `fetchIsbnMetadata` on `LibrarianAdminAdapter`**

Instantiate `self.isbn_svc = IsbnLookupService(conn)` in `LibrarianAdminAdapter.__init__` and add `@Slot(str, result=str) def fetchIsbnMetadata(self, isbn: str) -> str:` sanitizing `res.data` with `_sanitize_for_qml`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_isbn_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/librarian_management_app/adapters/librarian_admin_adapter.py tests/test_isbn_service.py
git commit -m "feat(adapter): expose fetchIsbnMetadata slot on LibrarianAdminAdapter"
```

---

### Task 3: QML Fetch Button, Non-Overwrite Auto-fill & Wiki Update

**Files:**
- Modify: `apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml:15-30,215-230,406-417`
- Modify: `apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml:11-16,150-160`
- Modify: `tests/test_ui_librarian.py`
- Modify: `wiki/services/library-services.md`
- Modify: `wiki/log.md`

**Interfaces:**
- Consumes: `librarianAdmin.fetchIsbnMetadata(isbn)`
- Produces:
  - `BarcodeGeneratorView.qml`: `btnFetchIsbn` (`objectName: "btnFetchIsbn"`), `fetchIsbnAndAutofill()` function
  - `BookActionDialogs.qml`: `btnDialogFetchIsbn` (`objectName: "btnDialogFetchIsbn"`), `fetchDialogIsbnAndAutofill()` function

- [ ] **Step 1: Write failing UI test in `tests/test_ui_librarian.py`**

```python
def test_isbn_autofill_does_not_overwrite_existing_fields(lib_ui, monkeypatch):
    win = lib_ui["window"]
    adapter = lib_ui["adapter"]
    from PySide6.QtCore import QObject

    # Seed cache for 9786162137792
    adapter.isbn_svc.save_cache("9786162137792", "รวมสูตรคณิต", "สกายบุ๊กส์", "สกายบุ๊กส์")

    barcode_view = win.findChild(QObject, "barcodeGenScreen")
    assert barcode_view is not None

    title_input = win.findChild(QObject, "genBookTitle")
    author_input = win.findChild(QObject, "genBookAuthor")
    isbn_input = win.findChild(QObject, "genBookIsbn")
    status_msg = win.findChild(QObject, "genStatusMessage")

    # 1. Both blank -> fills both
    title_input.setProperty("text", "")
    author_input.setProperty("text", "")
    isbn_input.setProperty("text", "9786162137792")
    barcode_view.fetchIsbnAndAutofill()
    assert title_input.property("text") == "รวมสูตรคณิต"
    assert author_input.property("text") == "สกายบุ๊กส์"

    # 2. Title already typed -> preserves Title, fills blank Author
    title_input.setProperty("text", "ชื่อที่พิมพ์เอง")
    author_input.setProperty("text", "")
    barcode_view.fetchIsbnAndAutofill()
    assert title_input.property("text") == "ชื่อที่พิมพ์เอง"
    assert author_input.property("text") == "สกายบุ๊กส์"

    # 3. Unknown ISBN -> does not overwrite, shows cannot fetch data
    monkeypatch.setattr("core.library.services.isbn_service._fetch_nlt_page", lambda i, t: "")
    isbn_input.setProperty("text", "9786167082493")
    barcode_view.fetchIsbnAndAutofill()
    assert title_input.property("text") == "ชื่อที่พิมพ์เอง"
    assert "cannot fetch data" in status_msg.property("text")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_ui_librarian.py -k test_isbn_autofill -v`
Expected: FAIL

- [ ] **Step 3: Add Fetch Button and `fetchIsbnAndAutofill()` to `BarcodeGeneratorView.qml` and `BookActionDialogs.qml`, and update Wiki**

In `BarcodeGeneratorView.qml`:
- Place `genBookIsbn` and `Button { id: btnFetchIsbn; objectName: "btnFetchIsbn"; text: "🔍 ดึงข้อมูล"; onClicked: barcodeGenScreen.fetchIsbnAndAutofill() }` inside a `RowLayout`.
- Implement `function fetchIsbnAndAutofill()`: calls `JSON.parse(librarianAdmin.fetchIsbnMetadata(genBookIsbn.text))`, if `res.ok`, sets `genBookTitle.text = res.data.title` only when `!genBookTitle.text.trim()` and `genBookAuthor.text = res.data.author` only when `!genBookAuthor.text.trim()`; if `!res.ok`, sets `genStatusMessage.text = "✗ cannot fetch data"`.
- Mirror the same button and helper in `BookActionDialogs.qml` (`addBookDialog`).
- Document `IsbnLookupService` in `wiki/services/library-services.md` and log the addition in `wiki/log.md`.

- [ ] **Step 4: Run full test suite to verify 100% pass**

Run: `.venv/bin/pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml tests/test_ui_librarian.py wiki/services/library-services.md wiki/log.md
git commit -m "feat(ui): add ISBN fetch button and non-overwriting autofill in Add Book views"
```
