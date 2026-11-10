# Chulabook Detection & Fetching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Librarian Management app detects catalog books that exist only in the Chulabook store (ISBN matches no standard ISBN database) and auto-fills their title/author from the Chulabook API during registration.

**Architecture:** Chulabook becomes the 4th (last) provider in the existing chained ISBN lookup (`core/library/services/isbn_providers.py`), so the existing autofill resolves Chulabook ISBNs with zero UI change. A new detection service (`chulabook_service.py`) classifies catalog books; one new adapter slot + one button/dialog in `BookCatalogView.qml` expose it.

**Tech Stack:** Python 3.14, PySide6 (Qt Quick/QML), SQLite3, stdlib `urllib.request`/`concurrent.futures`, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-10-chulabook-detect-fetch-design.md`

## Global Constraints
- Service boundaries return `Result[T, E]` (`Ok`/`Err` from `core.shared.result`) — no unhandled exceptions across boundaries.
- All dicts going to QML pass through `_sanitize_for_qml` (null-role crash protection).
- Autofill never overwrites manual Title/Author (existing policy).
- HTTP: reuse `_fetch_json`; browser `User-Agent` + `Origin`/`Referer: https://www.chulabook.com` headers; 5s timeout; chulabook requests are last in the provider chain.
- QML layout rules (AGENTS.md §6/7): no hardcoded pixel heights on buttons/delegates; text sizes reactive to `window.fontScale`; inputs/combo left-aligned + vertically centered; reuse `apps/common_qml/` components (`StyledButton`, `StyledTextInput`, `ActionFeedbackBanner`).
- Tests: `.venv/bin/pytest tests/` must pass; unit tests never hit the network (monkeypatch `urllib.request.urlopen` or module-level `_fetch_*` names — house pattern in `tests/test_isbn_service.py`).
- Branch invariant: commit to `dev` only.

## Review Focus
1. **Dash/space/mixed ISBNs in `books.isbn`** — normalized before every comparison and before every API query (tests: dashed ISBN in DB still flags).
2. **Thai-digit / non-ASCII ISBNs** — `is_valid_isbn` rejects; detection skips them silently, no crash (test included).
3. **Per-book network failure** — any provider exception → `None` → book simply not flagged; `Err` only for missing `books` table.
4. **NULL author/title in QML** — `_sanitize_for_qml` applied to `books[]`; UI binds with `|| ""` fallbacks.
5. **Duplicate ISBNs across book rows** — each `book_id` flagged individually (no book-level dedupe; HTTP dedupe is out of scope for 186 books).
6. **GUI-thread duration** — slot runs detection synchronously (house pattern of `fetchIsbnMetadata`); ~186 books / 8 workers ≈ 30–60s with the status text "กำลังตรวจสอบ..." showing. Acceptable for v1; upgrade to QThread only if measured > 90s.
7. **`isbn_cache` semantics** — cache rows are only written on remote success, so cache presence ⇒ standard-database hit; the detection rule relies on this (assert in Task 2 test that a cached ISBN is never flagged even when chulabook has it).

## File Structure
- `core/library/services/isbn_providers.py` — MODIFIED: chulabook constants, 4 new functions, `_fetch_json` gains `extra_headers` param, chain extended.
- `core/library/services/chulabook_service.py` — NEW: `detect_chulabook_books(conn, timeout, workers)`.
- `apps/librarian_management_app/adapters/librarian_admin_adapter.py` — MODIFIED: `detectChulabookBooks` slot + 2 signals.
- `apps/librarian_management_app/qml/views/BookCatalogView.qml` — MODIFIED: button, status text, results dialog.
- `apps/librarian_management_app/qml/Main.qml` — MODIFIED: signal wiring + `detectChulabook()` function.
- `tests/test_chulabook_provider.py`, `tests/test_chulabook_service.py`, `tests/test_ui_chulabook_detection.py` — NEW.
- `tests/fixtures/chulabook/*.json` — NEW: real API payloads captured 2026-11-10 (search response for `9786169444541`, detail for product `258216`).
- `tests/test_isbn_service.py` — MODIFIED: chain test gains chulabook-last case.
- `wiki/services/library-services.md`, `wiki/log.md` — MODIFIED.

## Task 1: Chulabook provider in `isbn_providers.py`

**Interfaces (exact):**
- `CHULABOOK_API = "https://api.chulabook.com"`
- `CHULABOOK_HEADERS = {"Origin": "https://www.chulabook.com", "Referer": "https://www.chulabook.com/"}`
- `_fetch_json(url: str, timeout: float = 5.0, extra_headers: Optional[dict] = None) -> dict` — merged into the existing `User-Agent` header; default `None` keeps today's behavior (existing tests unmodified must still pass).
- `parse_chulabook_products(data: dict, isbn: str) -> Optional[str]` — returns the `id` (str) of the first row in `data["rows"]` whose `normalize_isbn(str(row["barcode"])) == isbn` (EXACT match only — no fuzzy/first-row fallback); `None` when no exact match or malformed rows.
- `parse_chulabook_detail(data: dict, isbn: str) -> Dict[str, str]` — `{"isbn": isbn, "title": data.get("name") or "", "author": data.get("author") or data.get("translator") or "", "publisher": ""}`; returns that shape only if `data.get("name")` is truthy, else the caller gets `None` from `_fetch_chulabook`.
- `_fetch_chulabook(isbn: str, timeout: float) -> Optional[Dict[str, str]]` — GET `/products?search={isbn}&limit=5` (headers, `min(timeout, 2.5)`) → `parse_chulabook_products` → GET `/products/{pid}` → `parse_chulabook_detail`; any exception or empty title → `None`.
- `fetch_remote_providers` chain becomes `_fetch_primo or _fetch_seed or _fetch_openlibrary or _fetch_chulabook` (chulabook LAST, spec §4.1).
- All five new public names added to `__all__`.

**Fixtures (create first, captured live 2026-11-10):**
- `tests/fixtures/chulabook/products_search_9786169444541.json` — capture via `curl -s 'https://api.chulabook.com/products?search=9786169444541&limit=5' -H 'User-Agent: Mozilla/5.0'` (expect `count: 1`, row id `"258216"`, barcode `"9786169444541"`).
- `tests/fixtures/chulabook/product_258216.json` — `curl -s 'https://api.chulabook.com/products/258216' -H 'User-Agent: Mozilla/5.0'` (detail; includes `isbn`, `pub_year`, `edition`, `detail_th`).

**Tests (`tests/test_chulabook_provider.py`):**
- `test_parse_chulabook_products_exact_match` — fixture rows → `"258216"`.
- `test_parse_chulabook_products_no_exact_match` — rows with other barcodes → `None` (asserts the no-fuzzy rule).
- `test_parse_chulabook_products_dash_isbn` — query ISBN `"978-616-9444-54-1"` matches barcode `"9786169444541"` (normalization).
- `test_parse_chulabook_detail_mapping` — detail fixture → title/author/isbn correct, `publisher == ""`, author falls back to `translator` when `author` null.
- `test_fetch_chulabook_success(monkeypatch)` — monkeypatch `_fetch_json` (module path) returning search-then-detail fixtures → meta dict matches fixture mapping.
- `test_fetch_chulabook_no_match_returns_none(monkeypatch)` — search fixture with no exact barcode → `None`, detail URL never requested (assert call list).
- `test_fetch_chulabook_network_error(monkeypatch)` — `_fetch_json` raises `urllib.error.URLError` → `None`.
- `test_fetch_json_extra_headers(monkeypatch)` — capture the `Request` passed to `urlopen`; assert `Origin`/`Referer` present when `extra_headers` given and absent by default.
- `tests/test_isbn_service.py::test_fetch_remote_providers_chain` — APPEND case: all three existing `_fetch_*` → `None`, `_fetch_chulabook` → meta ⇒ chain returns chulabook meta (proves last-position fallback).

**Steps:**
- [ ] Create both fixture JSON files by running the two curl commands above into `tests/fixtures/chulabook/` (verify: `python3 -m json.tool` on each; search fixture `count == 1`).
- [ ] Write the failing tests in `tests/test_chulabook_provider.py` + the appended chain case.
- [ ] Run `.venv/bin/pytest tests/test_chulabook_provider.py tests/test_isbn_service.py -q` — confirm the new tests FAIL (functions missing).
- [ ] Implement `_fetch_json` `extra_headers`, the 4 new functions, `__all__`, and the chain edit in `core/library/services/isbn_providers.py`.
- [ ] Run `.venv/bin/pytest tests/test_chulabook_provider.py tests/test_isbn_service.py -q` — all pass (existing tests included).
- [ ] Commit: `feat(isbn): add chulabook as 4th ISBN metadata provider`.

## Task 2: Detection service `chulabook_service.py`

**Interfaces (exact):**
- Module `core/library/services/chulabook_service.py`, `__all__ = ["detect_chulabook_books"]`.
- `detect_chulabook_books(conn: sqlite3.Connection, timeout: float = 5.0, workers: int = 8) -> Result[List[Dict[str, object]], str]`
- Row dict: `{"book_id": int, "isbn": str(normalized), "title": str, "author": str}` (`title`/`author` `""` when NULL).
- Rule per spec §3: flag row iff `_fetch_chulabook(isbn)` truthy AND `isbn not in isbn_cache` AND `_fetch_primo`/`_fetch_seed`/`_fetch_openlibrary` all falsy.
- `is_valid_isbn`-rejected rows: skipped silently (not flagged, no provider call).
- Concurrency: `concurrent.futures.ThreadPoolExecutor(max_workers=workers)` over rows (house pattern); per-row exceptions inside the worker → row skipped, not raised.
- `Err` only when the `books` table is missing (`sqlite3.OperationalError`).
- `isbn_cache` table absent ⇒ treat as empty (do not fail).

**Tests (`tests/test_chulabook_service.py`):** in-memory conn + `apply_migrations`; seed books via `book_repo.add_book` (pattern: `tests/test_repositories.py`); providers monkeypatched at `core.library.services.chulabook_service.<name>` (the service imports the four `_fetch_*` names into its own namespace, so patch there).
- `test_flags_chulabook_only_book` — 1 book; chulabook→meta, others→None ⇒ flagged, `isbn` normalized.
- `test_cached_isbn_never_flagged` — chulabook→meta AND isbn row inserted directly into `isbn_cache` ⇒ NOT flagged (Review Focus 7).
- `test_standard_db_hit_not_flagged` — chulabook→meta, `_fetch_primo`→meta ⇒ NOT flagged.
- `test_chulabook_miss_not_flagged` — chulabook→None ⇒ NOT flagged.
- `test_invalid_isbn_skipped` — `isbn="SMTE-00001-01"` ⇒ `Ok`, not flagged, no provider called for it (assert via call log).
- `test_dashed_db_isbn_normalized_and_flagged` — book seeded with `isbn="978-616-9444-54-1"` (dashes as stored in DB), chulabook→meta for normalized form ⇒ flagged with `isbn == "9786169444541"` (Review Focus 1).
- `test_thai_digit_isbn_skipped_no_crash` — `isbn="๙๗๘๖๑๖๙๔๔๔๕๔๑"` ⇒ `Ok`, not flagged.
- `test_duplicate_isbn_each_row_flagged` — 2 books, same chulabook-only ISBN ⇒ 2 flagged rows, distinct `book_id`.
- `test_missing_books_table_returns_err` — fresh conn without migrations ⇒ `res.ok is False`.
- `test_worker_exception_skips_row` — `_fetch_chulabook` raises for exactly one ISBN ⇒ that book unflagged, others fine.

**Steps:**
- [ ] Write the failing tests in `tests/test_chulabook_service.py`.
- [ ] Run `.venv/bin/pytest tests/test_chulabook_service.py -q` — confirm failures (`ModuleNotFoundError`).
- [ ] Implement `core/library/services/chulabook_service.py`.
- [ ] Run `.venv/bin/pytest tests/test_chulabook_service.py tests/test_chulabook_provider.py -q` — pass.
- [ ] Commit: `feat(chulabook): detect chulabook-exclusive books in catalog`.

## Task 3: Adapter slot `detectChulabookBooks`

**Interfaces (exact):** in `apps/librarian_management_app/adapters/librarian_admin_adapter.py`
- Signals (declared with the existing `isbnLookupStarted`/`isbnLookupCompleted` pair): `chulabookCheckStarted = Signal()` and `chulabookCheckCompleted = Signal(str)`.
- `@Slot() def detectChulabookBooks(self) -> str` — emits `chulabookCheckStarted`, calls `detect_chulabook_books(self.conn, timeout=5.0)`, builds
  `payload = json.dumps({"ok": res.ok, "error": res.error, "count": len(res.data) if res.ok else 0, "books": _sanitize_for_qml(res.data) if res.ok else []})`,
  emits `chulabookCheckCompleted(payload)`, returns `payload`. Synchronous (house pattern of `fetchIsbnMetadata`).
- Import `detect_chulabook_books` next to the existing `IsbnLookupService` import.

**Tests (append to `tests/test_adapters.py`, house pattern):**
- `test_detect_chulabook_books_payload_shape` — temp DB + migrations; monkeypatch `detect_chulabook_books` in the adapter's namespace to return `Ok([{"book_id": 1, "isbn": "9786160000001", "title": "ท", "author": None}])`; call `adapter.detectChulabookBooks()`; `json.loads` ⇒ `ok True`, `count 1`, `books[0]["title"] == "ท"` and `books[0]["author"] == ""` (`_sanitize_for_qml` None→`""` contract, `core/shared/mock_qt.py`), and `chulabookCheckCompleted` emitted with the same payload string (connect the signal and capture).
- `test_detect_chulabook_books_err_payload` — service returns `Err("boom")` ⇒ `ok False`, `error "boom"`, `count 0`, `books []`.

**Steps:**
- [ ] Write the two failing tests (attribute missing on adapter).
- [ ] Run `.venv/bin/pytest tests/test_adapters.py -q` — confirm failures.
- [ ] Add signals + slot + import.
- [ ] Run `.venv/bin/pytest tests/test_adapters.py -q` — pass.
- [ ] Commit: `feat(librarian): expose detectChulabookBooks adapter slot`.

## Task 4: QML UI — button, status, results dialog

**Interfaces (exact):**
- `BookCatalogView.qml` additions:
  - `signal detectChulabookRequested()`
  - `property string chulabookStatus: ""`
  - `property bool chulabookDialogOpen: false`
  - `property var chulabookBooks: []`
  - `StyledButton` in the existing header `RowLayout` (before `btnOpenGeneratorPage`): `id: btnDetectChulabook`, `objectName: "btnDetectChulabook"`, `text: "📕 ตรวจ Chulabook"`, `variant: StyledButton.Primary`, `onClicked: root.detectChulabookRequested()`.
  - Status `Text` `objectName: "chulabookStatusText"` bound to `chulabookStatus` under the search row; `visible: chulabookStatus !== ""`; `font.pixelSize: Math.max(11, Math.round(13 * (window.fontScale || 1.0)))`; `Component.onCompleted: Typography.applyToItem(this)`.
  - Results `Dialog` `objectName: "chulabookDialog"`: `visible: chulabookDialogOpen`; header `Text` "พบหนังสือที่พบเฉพาะใน Chulabook — N เล่ม" (N from `chulabookBooks.length`); `ListView` `objectName: "chulabookResultsList"` with `model: ListModel { id: chulabookResultsModel }`; delegate: `Item` with `implicitHeight: Math.max(34, Math.round(titleText.implicitHeight + 16))` containing title `Text` (`elide: ElideRight`, font reactive to `window.fontScale`) + sub `Text` "ISBN: " + model.isbn; footer `StyledButton` `objectName: "btnCloseChulabookDialog"` text "ปิด" `onClicked: root.chulabookDialogOpen = false`.
- `Main.qml` additions:
  - `onDetectChulabookRequested: window.detectChulabook()` on the `bookCatalogView` instance (mirrors `onSearchRequested`).
  - `function detectChulabook()`: sets `bookCatalogView.chulabookStatus = "กำลังตรวจสอบ..."`, `var res = JSON.parse(librarianAdmin.detectChulabookBooks())`; on `!res.ok` → status `"✗ " + (res.error || "cannot detect")`, return; else `bookCatalogView.chulabookBooks = res.books`, status `res.count ? "พบ " + res.count + " เล่มที่พบเฉพาะใน Chulabook" : "ไม่พบหนังสือที่พบเฉพาะใน Chulabook"`, and when `res.count > 0`: populate `chulabookResultsModel` from `res.books` and set `chulabookDialogOpen = true`.
- Layout/alignment: obey Global Constraints (no hardcoded pixel heights on the button/delegates; reactive fonts; `Typography.applyToItem` on the status + delegate texts).

**Tests (`tests/test_ui_chulabook_detection.py`, house pattern from `tests/test_ui_isbn_scanning.py`):** offscreen engine loading `Main.qml`, temp DB + migrations, seed 3 books: ISBN `9786160000001` (chulabook-only), `9786160000002` (inserted into `isbn_cache`), `9786160000003` (NLT hit). Monkeypatch `core.library.services.isbn_providers._fetch_chulabook` → meta only for `...001`; `_fetch_primo` → meta only for `...003`; `_fetch_seed`/`_fetch_openlibrary` → None.
- `test_button_exists` — `find_child(window, "btnDetectChulabook")` not None.
- `test_detect_flow_flags_one_book` — `btn.click()`; assert `bookCatalogView.chulabookStatus === "พบ 1 เล่มที่พบเฉพาะใน Chulabook"` (property read via `window.findChild`), `chulabookDialogOpen is True`, `chulabookResultsModel.count === 1`, model row `isbn === "9786160000001"`.
- `test_close_dialog` — `btnCloseChulabookDialog.click()` ⇒ `chulabookDialogOpen is False`.
- `test_error_status_on_service_failure` — additionally monkeypatch the adapter's `detect_chulabook_books` to `Err("boom")` ⇒ status starts with `"✗"`, dialog stays closed.

**Steps:**
- [ ] Write the failing tests in `tests/test_ui_chulabook_detection.py`.
- [ ] Run `.venv/bin/pytest tests/test_ui_chulabook_detection.py -q` — confirm failures (missing objectNames).
- [ ] Implement the `BookCatalogView.qml` + `Main.qml` additions.
- [ ] Run `.venv/bin/pytest tests/test_ui_chulabook_detection.py -q` — pass.
- [ ] Commit: `feat(librarian-ui): chulabook detection button and results dialog`.

## Task 5: Wiki, log, full verification

**Steps:**
- [ ] Update `wiki/services/library-services.md`: add a "Chulabook Detection & Fetching" subsection (API endpoints, detection rule, provider order, adapter slot, UI entry points) — match existing page style.
- [ ] Append a `wiki/log.md` entry dated `2026-11-10`: `feat | Chulabook 4th ISBN provider + catalog detection + Librarian UI` with the three file areas touched.
- [ ] Run `.venv/bin/pytest tests/ -q` — full suite green (100% coverage target per AGENTS.md §5).
- [ ] Commit: `docs: wiki + log for chulabook detection & fetching`.
- [ ] Push `dev` (branch invariant — never `main`).
