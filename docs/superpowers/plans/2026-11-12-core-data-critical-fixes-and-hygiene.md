# Core & Data Critical Fixes and Boundary Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix verified correctness bugs and clean up leaky library boundaries across `core/` and `data/` while keeping all existing public signatures and the 404-test suite intact.

**Architecture:** Apply surgical, behavior-preserving fixes inside `data/repositories/`, `core/library/services/`, `core/importers/`, and `data/sync/` using small (<20-line) helper functions and existing `Result[T, E]` boundaries. Extract shared Excel roster parsing into `core/importers/roster_parser.py` and single-open snapshot loading into `data/sync/diff.py`, remove `PySide6` event-loop re-entrancy from `core/`, and keep schema version at `9`.

**Tech Stack:** Python 3.14, SQLite (FTS5 trigram), `openpyxl >= 3.1.0`, `platformdirs >= 3.0.0`, `pytest >= 7.0.0`.

**Spec:** Derived from the 2026-11-12 swarm and Context7 codebase audit on `dev` (`eaacaa9`), scoped per user selection to Plan 1 (Core & Data critical fixes + pragmatic Clean Code boundary cleanup).

## Global Constraints

- Python 3.14 runtime; dependencies pinned in `requirements.txt` (`PySide6>=6.5.0`, `openpyxl>=3.1.0`, `platformdirs>=3.0.0`, `pytest>=7.0.0`).
- Preserve existing public module/service signatures and `Result[T, E]` shapes used by the 404 existing tests (`tests/`).
- Keep database schema at `PRAGMA user_version = 9` (no new migration file; `tests/test_migrations.py` asserts `applied == 9`).
- Follow Clean Code rules: functions `<= 20` lines, guard clauses first, no new dead code or swallowed exceptions.
- Commit work exclusively to the `dev` branch; run `.venv/bin/pytest tests/` after each task and update `wiki/` + `wiki/log.md` at the end.

## Review Focus

- `book_repo.search_books` with `category_id` filter + book matching normalized `isbn` when query targets a different book's barcode -> must not bypass `bc.book_id = b.book_id` via unparenthesized `AND ... OR`.
- `book_repo._rewind_sequence` invoked with an unexpected `table_name` or `pk_col` -> must reject with `ValueError` instead of interpolating arbitrary SQL identifiers.
- `LoanService.renew` called more than `LibraryPolicy.max_renewals` times on an active loan with no waiting reservations -> must fail with a renewal-limit `Result` error.
- `IsbnLookupService.lookup` invoked while a `QCoreApplication` instance is active and the remote future raises or times out -> must wait without calling `QCoreApplication.processEvents()`.
- `build_db.import_roster` reading a workbook under `read_only=True` streaming when sheets have trailing `None` rows, missing optional sheets, or non-integer cells -> must parse identically without `ws.cell(...)` random access and always close the workbook.

---

### Task 1: Fix `book_repo` SQL Precedence Bug, Guard `_rewind_sequence`, and Remove Dead `get_book_by_isbn`

**Files:**
- Modify: `data/repositories/book_repo.py:57-89,175-184,308-316`
- Test: `tests/test_repositories.py`

**Interfaces:**
- Consumes: existing `books`, `book_copies`, `sqlite_sequence` tables.
- Produces: parenthesized `search_books(conn, query, category_id=None, limit=50, offset=0) -> List[sqlite3.Row]`, validated `_rewind_sequence(conn, table_name, pk_col) -> None`; removes unused `get_book_by_isbn`.

- [ ] **Step 1: Write failing tests for SQL precedence leak and `_rewind_sequence` identifier guard**

Add to `tests/test_repositories.py`:

```python
def test_search_books_barcode_isbn_precedence_with_category(repo_db):
    cat_a = book_repo.add_category(repo_db, "หมวด A")
    cat_b = book_repo.add_category(repo_db, "หมวด B")
    book_a = book_repo.add_book(repo_db, title="Alpha", isbn="978-0-11-000001-1", category_id=cat_a)
    book_repo.add_copies(repo_db, book_a, barcodes=["BAR-100"])
    book_b = book_repo.add_book(repo_db, title="Beta", isbn="978-0-22-000002-2", category_id=cat_b)
    book_repo.add_copies(repo_db, book_b, barcodes=["BAR-200"])
    repo_db.commit()

    # Searching a string that matches nothing as barcode, but book_a has 0 copies matching
    # another book's barcode: unparenthesized `AND barcode = ? OR isbn LIKE ?` leaks across books
    # whenever a book has any copy row at all.
    rows = book_repo.search_books(repo_db, "9780220000022", category_id=cat_a)
    assert rows == []


def test_rewind_sequence_rejects_unwhitelisted_table(repo_db):
    with pytest.raises(ValueError, match="Unsupported sequence target"):
        book_repo._rewind_sequence(repo_db, "students; DROP TABLE books;--", "student_id")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_repositories.py -k "test_search_books_barcode_isbn_precedence_with_category or test_rewind_sequence_rejects_unwhitelisted_table" -v`
Expected: FAIL (`_rewind_sequence` executes invalid SQL / `OperationalError`, and verify precedence assertion).

- [ ] **Step 3: Fix `search_books`, guard `_rewind_sequence`, and delete `get_book_by_isbn` in `data/repositories/book_repo.py`**

1. Delete `get_book_by_isbn` (`data/repositories/book_repo.py:64-74`).
2. Add constant `_ALLOWED_SEQUENCE_TARGETS = {"books": "book_id", "book_copies": "copy_id"}` above `_rewind_sequence`; raise `ValueError(f"Unsupported sequence target: {table_name}.{pk_col}")` if `_ALLOWED_SEQUENCE_TARGETS.get(table_name) != pk_col`.
3. In `search_books` (`data/repositories/book_repo.py:309-314`), parenthesize the OR inside `EXISTS`:

```python
        query_cond = (
            f"({query_cond} OR EXISTS (SELECT 1 FROM book_copies bc "
            "WHERE bc.book_id = b.book_id "
            "AND (REPLACE(LOWER(bc.barcode), '-', '') = ? "
            "OR REPLACE(LOWER(b.isbn), '-', '') LIKE ?)))"
        )
```

- [ ] **Step 4: Run repository and search tests to verify they pass**

Run: `.venv/bin/pytest tests/test_repositories.py tests/test_search_algorithm.py -v`
Expected: PASS (all tests green).

- [ ] **Step 5: Commit**

```bash
git add data/repositories/book_repo.py tests/test_repositories.py
git commit -m "fix(book_repo): parenthesize EXISTS OR clause, guard sequence rewind, drop dead lookup"
```

---

### Task 2: Enforce `LibraryPolicy.max_renewals` and Extract Ready-Reservation Query in `LoanService`

**Files:**
- Modify: `data/repositories/loan_repo.py:77-95`
- Modify: `data/repositories/reservation_repo.py:113-122`
- Modify: `core/library/services/reservation_service.py:54-65`
- Modify: `core/library/services/loan_service.py:1-12,119-128,188-207`
- Test: `tests/test_loan_service.py`

**Interfaces:**
- Consumes: `LibraryPolicy.max_renewals` (`core/library/policy.py:9`), `activity_log` (`action='loan.renew'`), `ReservationService.fulfill`.
- Produces:
  - `loan_repo.get_renewal_count(conn: sqlite3.Connection, loan_id: int) -> int`
  - `reservation_repo.get_ready_reservation_id(conn: sqlite3.Connection, book_id: int, student_id: int) -> Optional[int]`
  - `ReservationService.fulfill_ready_for_student(self, book_id: int, student_id: int, actor: Optional[str] = None) -> bool`

- [ ] **Step 1: Write failing test for `max_renewals` enforcement**

Add to `tests/test_loan_service.py`:

```python
def test_renew_enforces_max_renewals(library_env):
    loan_svc = library_env["loan"]
    cat_svc = library_env["catalog"]
    conn = library_env["conn"]

    conn.execute("INSERT INTO students (student_id, full_name, status) VALUES (60, 'ผู้ยืม ต่ออายุ', 'active')")
    conn.commit()
    cat_svc.add_book(title="หนังสือต่ออายุ", barcodes=["REN-01"])

    loan_id = loan_svc.checkout(student_id=60, barcode="REN-01").data["loan_id"]

    first = loan_svc.renew(loan_id, actor="Librarian")
    assert first.ok is True

    second = loan_svc.renew(loan_id, actor="Librarian")
    assert second.ok is False
    assert "renewal limit" in second.error.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_loan_service.py::test_renew_enforces_max_renewals -v`
Expected: FAIL (`second.ok` is `True` because `max_renewals` is ignored).

- [ ] **Step 3: Implement `get_renewal_count`, `get_ready_reservation_id`, and `LoanService` cleanup**

1. In `data/repositories/loan_repo.py`, add `get_renewal_count(conn: sqlite3.Connection, loan_id: int) -> int` querying `SELECT COUNT(*) FROM activity_log WHERE action = 'loan.renew' AND entity_type = 'loan' AND entity_id = ?`.
2. In `data/repositories/reservation_repo.py`, add `get_ready_reservation_id(conn: sqlite3.Connection, book_id: int, student_id: int) -> Optional[int]` querying `SELECT reservation_id FROM reservations WHERE book_id = ? AND student_id = ? AND status = 'ready' LIMIT 1`.
3. In `core/library/services/reservation_service.py`, add `fulfill_ready_for_student(self, book_id: int, student_id: int, actor: Optional[str] = None) -> bool` calling `reservation_repo.get_ready_reservation_id` and `self.fulfill`, and remove unused `List` import (`line 3`).
4. In `core/library/services/loan_service.py`:
   - Remove unused `List`, `reservation_repo`, `student_repo` imports (`lines 4, 10`).
   - Replace raw SQL in `checkout` (`lines 119-127`) with `self.reservation_service.fulfill_ready_for_student(copy["book_id"], student_id, actor=actor)`.
   - In `renew` (`lines 188-206`): remove unused `now` (`line 199`), check `if loan_repo.get_renewal_count(self.conn, loan_id) >= self.policy.max_renewals: return Result.fail(f"Renewal limit reached: maximum {self.policy.max_renewals} renewal(s) allowed")`.

- [ ] **Step 4: Run loan & comprehensive service tests to verify pass**

Run: `.venv/bin/pytest tests/test_loan_service.py tests/test_all_services_comprehensive.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data/repositories/loan_repo.py data/repositories/reservation_repo.py core/library/services/reservation_service.py core/library/services/loan_service.py tests/test_loan_service.py
git commit -m "fix(loan): enforce max_renewals policy and remove raw reservation SQL"
```

---

### Task 3: Remove `PySide6.QtCore` and `QCoreApplication.processEvents()` from `IsbnLookupService`

**Files:**
- Modify: `core/library/services/isbn_service.py:1-39,78-97`
- Test: `tests/test_isbn_service.py`

**Interfaces:**
- Consumes: `concurrent.futures.Future`, `fetch_remote_providers`.
- Produces: pure-Python `IsbnLookupService._wait_for_future(self, future: concurrent.futures.Future) -> Optional[Dict[str, str]]` with zero `PySide6` imports.

- [ ] **Step 1: Write failing test verifying `isbn_service` neither imports `PySide6` nor invokes `processEvents()`**

Add to `tests/test_isbn_service.py`:

```python
def test_isbn_service_does_not_call_qt_process_events(monkeypatch):
    import core.library.services.isbn_service as isbn_mod

    assert not hasattr(isbn_mod, "QCoreApplication")
    assert not hasattr(isbn_mod, "HAVE_QT")

    conn = sqlite3.connect(":memory:")
    svc = IsbnLookupService(conn, timeout=0.05)

    class SlowFuture:
        def result(self, timeout=None):
            raise TimeoutError()

    assert svc._wait_for_future(SlowFuture()) is None
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_isbn_service.py::test_isbn_service_does_not_call_qt_process_events -v`
Expected: FAIL (`AssertionError: assert not hasattr(isbn_mod, 'QCoreApplication')` / `'HAVE_QT'`).

- [ ] **Step 3: Remove Qt coupling from `core/library/services/isbn_service.py`**

1. Remove `from core.shared.mock_qt import HAVE_QT` and `if HAVE_QT: from PySide6.QtCore import QCoreApplication, QEventLoop` (`lines 22, 25-26`).
2. In `_wait_for_future` (`lines 78-86`), slice `timeout=min(0.02, max(0.0, deadline - time.monotonic()))` and `time.sleep(0.005)` on `TimeoutError` instead of `QCoreApplication.processEvents(...)`.
3. In `_fetch_remote` (`lines 93-94`), log `logger.warning("remote lookup failed for %s: %s", isbn, exc)` on exception before returning `None`.

- [ ] **Step 4: Run ISBN tests to verify pass**

Run: `.venv/bin/pytest tests/test_isbn_service.py tests/test_isbn_logging.py tests/test_isbn_series_title_cleaning.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/library/services/isbn_service.py tests/test_isbn_service.py
git commit -m "refactor(isbn): remove Qt processEvents re-entrancy from IsbnLookupService"
```

---

### Task 4: Extract Shared `roster_parser.py` and Switch `build_db.py` to `read_only=True` Streaming

**Files:**
- Create: `core/importers/roster_parser.py`
- Modify: `core/importers/build_db.py:1-338`
- Modify: `core/importers/xlsx_diff_importer.py:1-76`
- Test: `tests/test_importers.py`, `tests/test_xlsx_diff_importer.py`

**Interfaces:**
- Consumes: `openpyxl.load_workbook(..., read_only=True, data_only=True)`, `ws.iter_rows(values_only=True)`.
- Produces: `core/importers/roster_parser.py` exporting `GRADE_SHEETS`, `TITLE_RE`, `YEAR_RE`, `SEM_RE`, `clean`, `split_name`, `normalize_date`, `to_int`, `iter_grade_rows(ws) -> Iterator[Dict[str, Any]]`, `parse_grade_workbook(file_path: str) -> List[Dict[str, Any]]`.
- Preserves: `build_db.py` re-exports `GRADE_SHEETS`, `clean`, `split_name`, `normalize_date`, `to_int`, `TITLE_RE`, `YEAR_RE`, `SEM_RE`, `import_roster`.

- [ ] **Step 1: Write failing tests for streaming grade-sheet parsing with blank trailing rows and `read_only=True` enforcement**

Add to `tests/test_importers.py`:

```python
def test_import_roster_uses_read_only_streaming_and_closes_workbook(tmp_path, migrated_db, monkeypatch):
    import openpyxl

    path = str(tmp_path / "stream.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ม.1"
    ws.append(["ชั้นมัธยมศึกษาปีที่ 1 / 1 วิทย์-คณิต ปีการศึกษา 2568 ภาคเรียนที่ 1"])
    ws.append(["ที่", "รหัส", "ชื่อ-สกุล", "เลขประชาชน"])
    ws.append([1, 10001, "เด็กชายสมชาย ใจดี", "1100100100101"])
    ws.append([None, None, None, None])
    wb.save(path)

    seen = {}
    orig_load = openpyxl.load_workbook

    def spy_load(p, *args, **kwargs):
        seen["read_only"] = kwargs.get("read_only")
        seen["data_only"] = kwargs.get("data_only")
        return orig_load(p, *args, **kwargs)

    monkeypatch.setattr(openpyxl, "load_workbook", spy_load)
    res = import_roster(path, conn=migrated_db)
    assert res.ok is True
    assert seen == {"read_only": True, "data_only": True}
    row = migrated_db.execute("SELECT full_name FROM students WHERE student_id = 10001").fetchone()
    assert row["full_name"] == "เด็กชายสมชาย ใจดี"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_importers.py::test_import_roster_uses_read_only_streaming_and_closes_workbook -v`
Expected: FAIL (`seen["read_only"]` is `None`).

- [ ] **Step 3: Create `core/importers/roster_parser.py` and refactor `build_db.py` & `xlsx_diff_importer.py`**

1. Create `core/importers/roster_parser.py` (<150 lines, all functions `<20` lines) holding `GRADE_SHEETS`, `PREFIXES`, `MALE_PREFIXES`, `FEMALE_PREFIXES`, `TITLE_RE`, `YEAR_RE`, `SEM_RE`, `clean`, `split_name`, `normalize_date`, `to_int`, `_parse_header_meta(header: str)`, `iter_grade_rows(ws) -> Iterator[Dict[str, Any]]`, and `parse_grade_workbook(file_path: str) -> List[Dict[str, Any]]` (using `load_workbook(file_path, read_only=True, data_only=True)` + `try/finally: wb.close()`). Note: in `_parse_header_meta`, subtract `543` only when `year > 2400`.
2. In `core/importers/xlsx_diff_importer.py`, remove unused `import re` and replace `parse_roster_sheets` body with a thin wrapper delegating to `parse_grade_workbook(file_path)`.
3. In `core/importers/build_db.py`:
   - Re-export helpers from `core.importers.roster_parser`; remove unused `Dict, Any` (`line 9`) and duplicate `import sys` (`line 340`).
   - Refactor `parse_grade_sheet` to consume `iter_grade_rows(ws)` and rewrite `parse_transfers_out`, `parse_transfers_in`, `parse_room_changes`, `parse_leave`, `parse_retentions_69`, `parse_retentions_68`, `parse_repeat_room` to stream via `ws.iter_rows(min_row=..., values_only=True)` with safe tuple indexing (`def _col(row, idx)`).
   - In `import_roster`, load with `openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)` and close `wb` in `finally`.

- [ ] **Step 4: Run importer tests to verify pass**

Run: `.venv/bin/pytest tests/test_importers.py tests/test_xlsx_diff_importer.py tests/test_spec_exclusions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/importers/roster_parser.py core/importers/build_db.py core/importers/xlsx_diff_importer.py tests/test_importers.py
git commit -m "refactor(importers): extract shared roster_parser and stream build_db in read_only mode"
```

---

### Task 5: Eliminate Double Snapshot Open in `data/sync/` and Simplify `data/paths.py`

**Files:**
- Modify: `data/sync/diff.py:1-119`
- Modify: `data/sync/apply.py:1-143`
- Modify: `data/paths.py:1-83`
- Test: `tests/test_sync.py`, `tests/test_file_locations.py`

**Interfaces:**
- Consumes: `platformdirs` (`user_data_path`, `user_log_path`, `user_downloads_path`, `user_documents_path`).
- Produces:
  - `data/sync/diff.py`: `load_snapshot_data(snapshot_path: str) -> Dict[str, Any]` and `diff_snapshot_data(snap_data: Dict[str, Any], local_conn: sqlite3.Connection) -> Result`; keeps `compute_diff(snapshot_path, local_conn) -> Result` unchanged externally.
  - `data/sync/apply.py`: `apply_sync` opens `snapshot_path` once via `load_snapshot_data`.
  - `data/paths.py`: keeps exact public API (`get_app_data_dir`, `get_app_log_dir`, `get_default_db_path`, `get_default_download_dir`, `get_default_documents_dir`).

- [ ] **Step 1: Write failing test ensuring `apply_sync` opens `snapshot_path` only once**

Add to `tests/test_sync.py`:

```python
def test_apply_sync_opens_snapshot_once(sync_env, monkeypatch):
    import sqlite3
    s_conn = sync_env["s_conn"]
    l_conn = sync_env["l_conn"]
    snap_path = sync_env["snapshot_path"]

    s_conn.execute("INSERT INTO students (student_id, full_name, status) VALUES (2001, 'ทดสอบ ซิงค์', 'active')")
    s_conn.commit()
    assert export_snapshot(s_conn, snap_path).ok is True

    connect_calls = []
    real_connect = sqlite3.connect

    def spy_connect(target, *args, **kwargs):
        if str(target) == snap_path:
            connect_calls.append(str(target))
        return real_connect(target, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", spy_connect)
    res = apply_sync(snap_path, l_conn)
    assert res.ok is True
    assert len(connect_calls) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_sync.py::test_apply_sync_opens_snapshot_once -v`
Expected: FAIL (`len(connect_calls) == 2`).

- [ ] **Step 3: Refactor `data/sync/diff.py`, `data/sync/apply.py`, and `data/paths.py`**

1. In `data/sync/diff.py`:
   - Remove unused `Optional` import (`line 3`).
   - Extract `load_snapshot_data(snapshot_path: str) -> Dict[str, Any]` returning `{"exported_at", "students", "enrollments", "id_changes", "students_by_id"}` (opened and closed once in `try/finally`), and `diff_snapshot_data(snap_data, local_conn) -> Result` broken into `<20`-line helpers (`_load_local_students`, `_collect_id_renumbering`, `_collect_student_diffs`).
   - Implement `compute_diff(snapshot_path, local_conn)` using `load_snapshot_data` + `diff_snapshot_data`.
2. In `data/sync/apply.py`:
   - Remove unused `import os` (`line 2`), fix duplicate `# 3.` comment numbering, load snapshot once via `load_snapshot_data(snapshot_path)`, compute diff via `diff_snapshot_data(snap_data, local_conn)`, and split writes into `<20`-line helpers (`_apply_id_changes`, `_upsert_students`, `_refresh_enrollments`, `_update_sync_state`).
3. In `data/paths.py`:
   - Remove unused `Optional` (`line 4`), `os`, `sys`, and the duplicated 25-line manual OS fallback; use `platformdirs.user_data_path(..., appauthor=False, ensure_exists=True)`, `platformdirs.user_log_path(..., appauthor=False, ensure_exists=True)`, `platformdirs.user_downloads_path()`, `platformdirs.user_documents_path()`. Fix `get_default_db_path` docstring (`line 63`) to remove the false env-var override claim.

- [ ] **Step 4: Run sync, file location, and full test suite**

Run: `.venv/bin/pytest tests/test_sync.py tests/test_sync_edge_cases.py tests/test_file_locations.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data/sync/diff.py data/sync/apply.py data/paths.py tests/test_sync.py
git commit -m "refactor(data): single-open snapshot in apply_sync and simplify paths via platformdirs"
```

---

### Task 6: Sync Wiki Documentation and Run Full Test Suite

**Files:**
- Modify: `wiki/architecture/overview.md:50-70`
- Modify: `wiki/services/library-services.md`
- Modify: `wiki/services/excel-diff-importer.md`
- Modify: `wiki/log.md`

**Interfaces:**
- Consumes: `AGENTS.md` Section 4 (Ingest & Maintenance Workflow).
- Produces: accurate `wiki/` docs (`book_repo`, remote ISBN provider note, `roster_parser.py`, `max_renewals` enforcement) and appended `wiki/log.md` entry.

- [ ] **Step 1: Update `wiki/` pages for verified inaccuracies and Task 1–5 changes**

1. Fix `wiki/architecture/overview.md` (`catalog_repo` -> `book_repo`, clarify offline core + optional remote ISBN metadata lookup, mention `roster_parser.py`).
2. Note `max_renewals` enforcement and Qt-free `IsbnLookupService` in `wiki/services/library-services.md`, and shared `roster_parser.py` in `wiki/services/excel-diff-importer.md`.
3. Append chronological summary entry to `wiki/log.md`.

- [ ] **Step 2: Run full test suite**

Run: `.venv/bin/pytest tests/ -q`
Expected: All `404+` tests PASS with `0` failures.

- [ ] **Step 3: Commit**

```bash
git add wiki/architecture/overview.md wiki/services/library-services.md wiki/services/excel-diff-importer.md wiki/log.md
git commit -m "docs(wiki): sync architecture and service docs after core/data fixes"
```
