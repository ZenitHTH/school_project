# Audit Critical Bugs & Quality Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all 4 critical bugs and 5 high-priority quality defects identified during the repository audit (naive datetime return crash, missing Grade 6 graduation status transition, FTS5 trigram short-query failure, snapshot export connection leak, openpyxl workbook descriptor leaks, QML null sanitization, barcode DRY & N+1 query optimization, timestamped salt backups, and test fixture resource leaks).

**Architecture:** Harden `LoanService.return_book` to normalize return timestamps to UTC before comparison; update `LEGAL_STATUS_TRANSITIONS` and `EnrollmentService.promote_students` to transition non-promotable seniors to `graduated`; add `< 3` character `LIKE` fallback to `book_repo.search_books`; introduce safe `try...finally` connection and workbook cleanup in `export_snapshot`, `xlsx_validator`, and `build_db`; enforce `_sanitize_for_qml` across all adapter query and barcode lookup slots; centralize `format_barcode` in `core/library/policy.py` and replace N+1 queries in `book_repo.list_books_with_barcodes`; timestamp backup salt files in `data/db.py`; and convert pytest fixtures from `return conn` to `yield conn; conn.close()`.

**Tech Stack:** Python 3.14, PySide6 (Qt Quick/QML), SQLite3 with FTS5 trigram, OpenPyXL, pytest.

**Spec:** `wiki/index.md`, `wiki/services/student-service.md`, `wiki/services/library-services.md`, `wiki/database/student-search-fts5.md`, `wiki/architecture/result-type.md`

## Global Constraints

- **Architecture Rules & Invariants:** Use `Result[T, E]`, `Ok`, and `Err` from `core.shared.result`; never raise unhandled exceptions across service boundaries (`wiki/architecture/result-type.md`).
- **QML Sanitization:** All dictionary structures returned to QML via adapters must pass through `_sanitize_for_qml()` (`core/shared/mock_qt.py`).
- **Clean Code & Line Cap:** Keep files under 200 lines where practical; functions under 20 lines; no boolean flag arguments.
- **Zero New Dependencies:** Maintain strict stdlib + existing `requirements.txt` policy (`ponytail` ladder).
- **100% Test Pass Rate:** Every task must pass `.venv/bin/pytest tests/` with zero warnings under `-W default`.

## Review Focus

1. **`return_book` called with an ISO string missing timezone offset (e.g. `"2026-10-25T14:30:00"`):** Must not raise `TypeError: can't compare offset-naive and offset-aware datetimes`; must calculate overdue days accurately against UTC due dates.
2. **`promote_students` run on Grade 6 (ม.6) students:** Must transition student status in `students` table to `"graduated"` and record `student.update_status` in `activity_log`, blocking future library checkouts.
3. **`search_books` query with 1 or 2 characters (e.g. `"AI"`, `"C"`, `"เค"`):** Must return matching titles via `LIKE` fallback rather than 0 results from FTS5 trigram.
4. **Snapshot export encountering mid-stream disk or SQL errors:** Must close destination SQLite connection in `finally:`, preventing locked file handles.
5. **Printable barcode list loaded for 500 catalog titles:** Must execute a single batched query with `GROUP_CONCAT` instead of 501 separate SQL statements.

---

### Task 1: Fix Offset-Naive Return Datetime in LoanService

**Files:**
- Modify: `core/library/services/loan_service.py:130-145`
- Test: `tests/test_loan_service.py`

**Interfaces:**
- Consumes: `core.library.services.loan_service.LoanService.return_book(loan_id: int, returned_at: Optional[str] = None, actor: Optional[str] = None) -> Result`
- Produces: Normalized UTC datetime comparison preventing `TypeError` on naive ISO timestamp inputs.

- [ ] **Step 1: Write the failing test in `tests/test_loan_service.py`**

```python
def test_return_book_with_naive_iso_timestamp_calculates_overdue_fine(service_conn):
    from core.library.services.loan_service import LoanService
    from core.library.services.fine_service import FineService
    import datetime

    fine_svc = FineService(service_conn)
    loan_svc = LoanService(service_conn, fine_service=fine_svc)

    # Setup student and book copy
    service_conn.execute("INSERT INTO students (student_id, full_name, status) VALUES (501, 'นักเรียน ยืมหนังสือ', 'active')")
    service_conn.execute("INSERT INTO books (book_id, title) VALUES (10, 'หนังสือฟิสิกส์')")
    service_conn.execute("INSERT INTO book_copies (copy_id, book_id, barcode, status) VALUES (101, 10, 'PHY-01', 'available')")
    service_conn.commit()

    # Checkout 10 days ago (due 3 days ago with 7-day duration)
    now = datetime.datetime.now(datetime.timezone.utc)
    borrowed_at = (now - datetime.timedelta(days=10)).isoformat()
    due_at = (now - datetime.timedelta(days=3)).isoformat()
    
    cur = service_conn.cursor()
    cur.execute(
        "INSERT INTO loans (copy_id, student_id, borrowed_at, due_at, status) VALUES (101, 501, ?, ?, 'active')",
        (borrowed_at, due_at)
    )
    loan_id = cur.lastrowid
    cur.execute("UPDATE book_copies SET status = 'on_loan' WHERE copy_id = 101")
    service_conn.commit()

    # Pass an offset-naive string
    naive_return_time = "2026-10-25T15:00:00"
    res = loan_svc.return_book(loan_id=loan_id, returned_at=naive_return_time)
    assert res.ok is True
    # Verify fine was assessed and not swallowed by exception
    unpaid = fine_svc.get_unpaid_total(501)
    assert unpaid > 0, "Fine must be assessed for late return with naive timestamp"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_loan_service.py::test_return_book_with_naive_iso_timestamp_calculates_overdue_fine -v`
Expected: FAIL with `AssertionError: Fine must be assessed for late return with naive timestamp` (due to swallowed `TypeError`).

- [ ] **Step 3: Implement UTC normalization in `core/library/services/loan_service.py`**

In `return_book()`, before comparing `ret_dt > due_dt`:
```python
due_dt = datetime.datetime.fromisoformat(loan["due_at"])
ret_dt = datetime.datetime.fromisoformat(return_time)
if due_dt.tzinfo is not None and ret_dt.tzinfo is None:
    ret_dt = ret_dt.replace(tzinfo=datetime.timezone.utc)
elif due_dt.tzinfo is None and ret_dt.tzinfo is not None:
    due_dt = due_dt.replace(tzinfo=datetime.timezone.utc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_loan_service.py::test_return_book_with_naive_iso_timestamp_calculates_overdue_fine -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/library/services/loan_service.py tests/test_loan_service.py
git commit -m "fix(library): normalize return timestamps to UTC in loan return fine check"
```

---

### Task 2: Implement Grade 6 Graduation Status Transition

**Files:**
- Modify: `core/student/models.py:35-41`
- Modify: `core/student/services/enrollment_service.py:160-164`
- Test: `tests/test_student_service.py`

**Interfaces:**
- Consumes: `core.student.models.LEGAL_STATUS_TRANSITIONS`
- Produces: Legal transition from `"active"` to `"graduated"` and automatic status update during `promote_students()`.

- [ ] **Step 1: Write the failing test in `tests/test_student_service.py`**

```python
def test_promote_students_sets_grade_6_status_to_graduated(service_conn):
    from core.student.services.enrollment_service import EnrollmentService
    from core.student.services.student_service import StudentService

    e_svc = EnrollmentService(service_conn)
    s_svc = StudentService(service_conn)

    service_conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES (601, 'นักเรียน จบการศึกษา', 'active')"
    )
    service_conn.commit()

    e_svc.enroll_next_period(601, 2567, 1, "ม.6", 1)

    res = e_svc.promote_students(source_year=2567, source_semester=1, target_year=2568, target_semester=1)
    assert res.ok is True
    assert res.data["graduated_count"] == 1

    # Student must now be graduated
    assert s_svc.get_status(601) == "graduated"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_student_service.py::test_promote_students_sets_grade_6_status_to_graduated -v`
Expected: FAIL with `AssertionError: assert 'active' == 'graduated'`.

- [ ] **Step 3: Update `core/student/models.py` and `core/student/services/enrollment_service.py`**

1. In `core/student/models.py`, add `("active", "graduated")` to `LEGAL_STATUS_TRANSITIONS`.
2. In `core/student/services/enrollment_service.py`, in `promote_students()`, when `curr_grade not in GRADE_MAP`:
```python
else:
    # ม.6 graduates
    student_repo.update_status(
        self.conn,
        student_id=s["student_id"],
        new_status="graduated",
        reason=f"Graduated from ม.6 at end of {source_year}/{source_semester}",
        actor=actor,
    )
    graduated_count += 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_student_service.py::test_promote_students_sets_grade_6_status_to_graduated -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/student/models.py core/student/services/enrollment_service.py tests/test_student_service.py
git commit -m "fix(student): support graduated status transition and update grade 6 cohort upon promotion"
```

---

### Task 3: Add Short-Query Fallback to Catalog Book Search

**Files:**
- Modify: `data/repositories/book_repo.py:170-185`
- Test: `tests/test_search_algorithm.py`

**Interfaces:**
- Consumes: `data.repositories.book_repo.search_books(conn, query: str, ...)`
- Produces: Accurate substring search matches for queries shorter than 3 characters (`len < 3`).

- [ ] **Step 1: Write the failing test in `tests/test_search_algorithm.py`**

```python
def test_book_search_short_query_fallback(conn):
    from data.repositories import book_repo
    book_repo.add_book(conn, title="AI and Machine Learning", author="John Doe", isbn="978-001")
    book_repo.add_book(conn, title="เคมีพื้นฐาน", author="สมศักดิ์", isbn="978-002")

    # Short query < 3 characters
    res_ai = book_repo.search_books(conn, query="AI")
    assert len(res_ai) == 1
    assert res_ai[0]["title"] == "AI and Machine Learning"

    res_chem = book_repo.search_books(conn, query="เค")
    assert len(res_chem) == 1
    assert res_chem[0]["title"] == "เคมีพื้นฐาน"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_search_algorithm.py::test_book_search_short_query_fallback -v`
Expected: FAIL with `AssertionError: assert 0 == 1` (FTS5 trigram returns empty results for < 3 characters).

- [ ] **Step 3: Implement short-query check in `data/repositories/book_repo.py`**

In `search_books()`:
```python
clean_query = query.strip()
if clean_query:
    if len(clean_query) < 3:
        conditions.append("(b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?)")
        like_param = f"%{clean_query}%"
        params.extend([like_param, like_param, like_param])
    else:
        escaped = clean_query.replace('"', '""')
        fts_query = f'"{escaped}"*' if " " not in escaped else f'"{escaped}"'
        conditions.append("b.book_id IN (SELECT rowid FROM books_fts WHERE books_fts MATCH ?)")
        params.append(fts_query)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_search_algorithm.py::test_book_search_short_query_fallback -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/repositories/book_repo.py tests/test_search_algorithm.py
git commit -m "fix(catalog): add LIKE fallback for book searches under 3 characters"
```

---

### Task 4: Ensure Exception-Safe Connection Cleanup in Snapshot Export

**Files:**
- Modify: `data/sync/export.py:20-132`
- Test: `tests/test_sync_edge_cases.py`

**Interfaces:**
- Consumes: `data.sync.export.export_snapshot(conn, output_path, actor)`
- Produces: Safe `try...finally` closure ensuring `out_conn` is closed on both success and error.

- [ ] **Step 1: Write the failing test in `tests/test_sync_edge_cases.py`**

```python
def test_export_snapshot_closes_connection_on_error(conn, tmp_path, monkeypatch):
    from data.sync.export import export_snapshot
    out_file = str(tmp_path / "failing_snapshot.sqlite")

    # Force a failure during student copying
    def broken_fetchall():
        raise sqlite3.OperationalError("Simulated disk error during export")

    cur = conn.cursor()
    monkeypatch.setattr(cur, "fetchall", broken_fetchall)
    monkeypatch.setattr(conn, "cursor", lambda: cur)

    res = export_snapshot(conn, out_file)
    assert res.ok is False
    assert "Simulated disk error" in res.error

    # Verify that file handle is not held open: file can be deleted immediately
    import os
    if os.path.exists(out_file):
        os.remove(out_file)  # Would fail on Windows if out_conn remains unclosed
```

- [ ] **Step 2: Run test to verify current behavior**

Run: `.venv/bin/pytest tests/test_sync_edge_cases.py::test_export_snapshot_closes_connection_on_error -v`

- [ ] **Step 3: Refactor connection lifecycle in `data/sync/export.py`**

Restructure `export_snapshot()`:
```python
out_conn = sqlite3.connect(output_path)
try:
    # table creation, copy students, enrollments, id_changes, meta...
    out_conn.commit()
finally:
    out_conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_sync_edge_cases.py::test_export_snapshot_closes_connection_on_error -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/sync/export.py tests/test_sync_edge_cases.py
git commit -m "fix(sync): guarantee out_conn close in snapshot export via finally block"
```

---

### Task 5: Fix OpenPyXL Workbook Descriptor Leaks

**Files:**
- Modify: `core/importers/xlsx_validator.py:64-70`
- Modify: `core/importers/build_db.py:286-330`
- Test: `tests/test_importers.py`

**Interfaces:**
- Consumes: `core.importers.xlsx_validator.validate_xlsx_structure`, `core.importers.build_db.import_roster`
- Produces: Zero leaked open file handles on Excel workbook inspection.

- [ ] **Step 1: Write test verifying no unclosed workbook resource warnings**

Run: `.venv/bin/pytest tests/test_importers.py -W "error::ResourceWarning"`
Expected: Note any warnings or verify existing tests.

- [ ] **Step 2: Implement safe workbook closure in `xlsx_validator.py` and `build_db.py`**

1. In `core/importers/xlsx_validator.py:64-68`:
```python
if _openpyxl_ok:
    try:
        with openpyxl.load_workbook(file_path, read_only=True) as wb:
            sheet_names = list(wb.sheetnames)
    except Exception as e:
        return Result.fail(f"Cannot read file as Excel: {e}")
```

2. In `core/importers/build_db.py:287`:
```python
wb = openpyxl.load_workbook(xlsx_path, data_only=True)
try:
    # parsing grade sheets...
finally:
    wb.close()
```

- [ ] **Step 3: Run test to verify clean execution**

Run: `.venv/bin/pytest tests/test_importers.py tests/test_xlsx_diff_importer.py -W "error::ResourceWarning"`
Expected: PASS with 0 resource warnings.

- [ ] **Step 4: Commit**

```bash
git add core/importers/xlsx_validator.py core/importers/build_db.py
git commit -m "fix(importers): close openpyxl workbooks deterministically to prevent descriptor leaks"
```

---

### Task 6: Apply QML Null Sanitization Across All UI Adapter Endpoints

**Files:**
- Modify: `apps/booth_app/adapters/booth_adapter.py:48-56`
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py:253-298, 354-358`
- Modify: `apps/student_management_app/adapters/student_admin_adapter.py:129-134, 206-210`
- Test: `tests/test_adapters.py`

**Interfaces:**
- Consumes: `core.shared.mock_qt._sanitize_for_qml`
- Produces: Strictly sanitized JSON dictionaries preventing QML null role exceptions.

- [ ] **Step 1: Write failing test in `tests/test_adapters.py`**

```python
def test_adapter_endpoints_sanitize_null_values(conn):
    from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
    from apps.booth_app.adapters.booth_adapter import BoothAdapter
    import json

    lib_adapter = LibrarianAdminAdapter(conn)
    booth_adapter = BoothAdapter(conn)

    # Insert book with NULL author, isbn, publisher, shelf_location
    cur = conn.cursor()
    cur.execute("INSERT INTO books (book_id, title) VALUES (99, 'Test Null Book')")
    cur.execute("INSERT INTO book_copies (copy_id, book_id, barcode, status) VALUES (991, 99, 'NULL-01', 'available')")
    conn.commit()

    raw_lib = json.loads(lib_adapter.getCopyByBarcode("NULL-01"))
    assert raw_lib["ok"] is True
    assert raw_lib["data"]["author"] == ""
    assert raw_lib["data"]["isbn"] == ""

    raw_booth = json.loads(booth_adapter.getCopyByBarcode("NULL-01"))
    assert raw_booth["ok"] is True
    assert raw_booth["data"]["author"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_adapters.py::test_adapter_endpoints_sanitize_null_values -v`
Expected: FAIL with `AssertionError: assert None == ''`.

- [ ] **Step 3: Add `_sanitize_for_qml` calls in adapters**

1. In `apps/booth_app/adapters/booth_adapter.py`:
- In `getCopyByBarcode`: `data = _sanitize_for_qml(res.data) if res.ok else {}`
- In `checkout`: `data = _sanitize_for_qml(res.data) if res.ok else {}`

2. In `apps/librarian_management_app/adapters/librarian_admin_adapter.py`:
- In `getCopyByBarcode`: `data = _sanitize_for_qml(res.data) if res.ok else {}`
- In `getActiveLoans`, `getStudentBorrowHistory`, `getCopyBorrowHistory`, `listFines`, `getActivityLogs`: sanitize row lists with `_sanitize_for_qml()`.

3. In `apps/student_management_app/adapters/student_admin_adapter.py`:
- In `getHistory`, `getActivityLogs`: wrap with `_sanitize_for_qml()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_adapters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/booth_app/adapters/booth_adapter.py apps/librarian_management_app/adapters/librarian_admin_adapter.py apps/student_management_app/adapters/student_admin_adapter.py tests/test_adapters.py
git commit -m "fix(adapters): sanitize all dictionary returns for QML null safety"
```

---

### Task 7: Unify Barcode Formatting & Eliminate N+1 Query in `list_books_with_barcodes`

**Files:**
- Modify: `core/library/policy.py:1-25`
- Modify: `core/library/services/catalog_service.py:84-90, 150-155`
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py:215-234`
- Modify: `data/repositories/book_repo.py:345-357`
- Test: `tests/test_barcode_and_disposed.py`

**Interfaces:**
- Consumes: `core.library.policy.format_barcode(book_id: int, seq: int) -> str`
- Produces: Single reusable barcode generator and single batched SQL query for printable barcode listings.

- [ ] **Step 1: Write test for unified barcode formatting and batched barcode retrieval**

In `tests/test_barcode_and_disposed.py`:
```python
def test_format_barcode_and_batched_list(conn):
    from core.library.policy import format_barcode
    from data.repositories import book_repo

    assert format_barcode(12, 3) == "LIB-00012-03"
    assert format_barcode(1, 100) == "LIB-00001-100"

    b_id = book_repo.add_book(conn, title="รวมเล่มบาร์โค้ด")
    book_repo.add_copies(conn, b_id, barcodes=[format_barcode(b_id, 1), format_barcode(b_id, 2)])

    results = book_repo.list_books_with_barcodes(conn, query="รวมเล่ม")
    assert len(results) == 1
    assert results[0]["barcodes"] == ["LIB-00001-01", "LIB-00001-02"]
```

- [ ] **Step 2: Run test to verify failure**

Run: `.venv/bin/pytest tests/test_barcode_and_disposed.py::test_format_barcode_and_batched_list -v`
Expected: FAIL with `ImportError: cannot import name 'format_barcode' from 'core.library.policy'`.

- [ ] **Step 3: Implement `format_barcode` and batched query**

1. In `core/library/policy.py`:
```python
def format_barcode(book_id: int, seq: int) -> str:
    """Format standardized library barcode."""
    return f"{BARCODE_PREFIX}-{book_id:05d}-{seq:02d}"
```

2. Replace format strings in `core/library/services/catalog_service.py` (`add_book`, `add_copies`) and `apps/librarian_management_app/adapters/librarian_admin_adapter.py` (`previewBarcodes`) with `format_barcode(...)`.

3. In `data/repositories/book_repo.py`, rewrite `list_books_with_barcodes`:
```python
def list_books_with_barcodes(conn: sqlite3.Connection, query: str = "") -> List[Dict[str, Any]]:
    """List active books with their active non-disposed barcodes in a single batched query."""
    books = search_books(conn, query=query, limit=500, offset=0)
    if not books:
        return []
    book_ids = [b["book_id"] for b in books]
    placeholders = ",".join("?" for _ in book_ids)
    sql = f"""
        SELECT book_id, barcode
        FROM book_copies
        WHERE book_id IN ({placeholders}) AND status NOT IN ('retired', 'disposed')
        ORDER BY copy_id ASC
    """
    rows = conn.execute(sql, book_ids).fetchall()
    barcode_map: Dict[int, List[str]] = {}
    for r in rows:
        barcode_map.setdefault(r["book_id"], []).append(r["barcode"])

    result = []
    for b in books:
        item = dict(b)
        item["barcodes"] = barcode_map.get(b["book_id"], [])
        result.append(item)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_barcode_and_disposed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/library/policy.py core/library/services/catalog_service.py apps/librarian_management_app/adapters/librarian_admin_adapter.py data/repositories/book_repo.py tests/test_barcode_and_disposed.py
git commit -m "refactor(catalog): unify barcode formatting and eliminate N+1 query in barcode listing"
```

---

### Task 8: Save Timestamped Salt File in Database Backups

**Files:**
- Modify: `data/db.py:178-183`
- Test: `tests/test_clean_and_memory_launch.py`

**Interfaces:**
- Consumes: `data.db.backup_database(conn, db_path, backup_dest_dir)`
- Produces: Timestamped salt backup matching the timestamped database file.

- [ ] **Step 1: Write test in `tests/test_clean_and_memory_launch.py`**

```python
def test_backup_database_creates_matching_timestamped_salt(tmp_path):
    from data.db import backup_database
    import sqlite3

    db_path = str(tmp_path / "school.sqlite")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INT);")
    conn.commit()

    # Create dummy salt file
    salt_file = tmp_path / "school.sqlite.salt"
    salt_file.write_bytes(b"1234567890abcdef")

    backup_path = backup_database(conn, db_path)
    conn.close()

    assert backup_path != ":memory:"
    from pathlib import Path
    bp = Path(backup_path)
    salt_backup = bp.parent / f"{bp.name}.salt"
    assert salt_backup.exists()
    assert salt_backup.read_bytes() == b"1234567890abcdef"
```

- [ ] **Step 2: Run test to verify failure**

Run: `.venv/bin/pytest tests/test_clean_and_memory_launch.py::test_backup_database_creates_matching_timestamped_salt -v`
Expected: FAIL with `AssertionError: assert False (salt_backup.exists())`.

- [ ] **Step 3: Update `backup_database` in `data/db.py`**

In `data/db.py:178-183`:
```python
salt_file = Path(f"{db_path}.salt")
if salt_file.exists():
    shutil.copy2(salt_file, dest_dir / f"{backup_db_path.name}.salt")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_clean_and_memory_launch.py::test_backup_database_creates_matching_timestamped_salt -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/db.py tests/test_clean_and_memory_launch.py
git commit -m "fix(db): timestamp backup salt file to match backup database file"
```

---

### Task 9: Clean Up Test Fixture Connection Leaks

**Files:**
- Modify: `tests/test_all_services_comprehensive.py:14-25`
- Modify: `tests/test_barcode_and_disposed.py:13-18`
- Modify: `tests/test_search_algorithm.py:8-31`
- Test: Run whole pytest suite with `-W "error::ResourceWarning"`

**Interfaces:**
- Consumes: Pytest fixture lifecycle (`yield conn; conn.close()`)
- Produces: Zero unclosed database connection warnings across entire test suite.

- [ ] **Step 1: Run pytest to see unclosed connection warnings**

Run: `.venv/bin/pytest -k "test_student_service or test_barcode_and_disposed" -W "error::ResourceWarning"`
Expected: FAIL with `ResourceWarning: unclosed database in <sqlite3.Connection...>`.

- [ ] **Step 2: Update fixtures to close connections on teardown**

1. In `tests/test_all_services_comprehensive.py:14-25`:
```python
@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    apply_migrations(c)
    c.execute(
        "INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, gender, status) "
        "VALUES (1001, '1234567890123', 'นาย', 'กิตติ', 'มีสุข', 'นายกิตติ มีสุข', 'M', 'active')"
    )
    c.commit()
    yield c
    c.close()
```

2. In `tests/test_barcode_and_disposed.py:13-18`:
```python
@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    apply_migrations(c)
    yield c
    c.close()
```

3. In `tests/test_search_algorithm.py:8-31`:
```python
@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    apply_migrations(c)
    # ... insert seed records ...
    c.commit()
    yield c
    c.close()
```

- [ ] **Step 3: Run full test suite with ResourceWarning error gating**

Run: `.venv/bin/pytest tests/ -W "error::ResourceWarning"`
Expected: PASS with 0 warnings.

- [ ] **Step 4: Commit**

```bash
git add tests/test_all_services_comprehensive.py tests/test_barcode_and_disposed.py tests/test_search_algorithm.py
git commit -m "test: close sqlite connection fixtures on teardown to eliminate resource warnings"
```

---

### Task 10: Run Full System Verification & Update Documentation

**Files:**
- Modify: `wiki/services/student-service.md`
- Modify: `wiki/log.md`

- [ ] **Step 1: Run full pytest suite with coverage**

Run: `.venv/bin/pytest --cov=core --cov=data --cov=apps tests/`
Expected: 200+ tests pass with zero errors.

- [ ] **Step 2: Update `wiki/services/student-service.md` and `wiki/log.md`**

Document the `("active", "graduated")` status transition and audit improvements.

- [ ] **Step 3: Final Commit**

```bash
git add wiki/services/student-service.md wiki/log.md
git commit -m "docs(wiki): document graduated status transition and audit bug fixes"
```
