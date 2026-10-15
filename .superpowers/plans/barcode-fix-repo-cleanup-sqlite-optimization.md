# Barcode Fix, Repo Cleanup & SQLite Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate external barcode/PDF runtime dependencies (`No module named 'barcode'`), remove 2,064 lines of dead files/duplication across root, `packaging/`, `core/`, and `apps/`, and optimize the three SQLite bottlenecks in student search, snapshot sync, and catalog lookup.

**Architecture:** Replace third-party `python-barcode`/`Pillow`/`reportlab` calls in `core/library/services/label_service.py` with a pure-stdlib ISO/IEC 15417 Code128-B + PDF 1.4 vector generator and fix QML/adapter barcode argument bindings. Delete superseded root design docs, unused `*_windows.spec` files, and zero-import modules, centralizing `_sanitize_for_qml` and `normalize_file_path` in `core/shared/mock_qt.py`. Replace correlated per-row SQLite subqueries and Python row-by-row loops in `student_repo.py`, `apply.py`, and `book_copies` with single-pass joins, `executemany`, and a composite `(book_id, status)` index.

**Tech Stack:** Python 3.10–3.15 (stdlib `sqlite3`, `urllib.parse`), PySide6 (Qt Quick / QML), SQLite3 with FTS5 `trigram`, pytest.

**Spec:** `wiki/index.md`, `doc/book_barcode_generation.md`, `doc/student_search_algorithm.md`, `doc/database_layer_design.md`

## Global Constraints

- **Python & Dependencies:** Python >= 3.10 stdlib first (`ponytail` ladder); zero new third-party packages added to `requirements.txt`.
- **Service Return Contract:** Use `Result[T, E]`, `Ok`, and `Err` from `core.shared.result`; never raise unhandled exceptions across service or adapter boundaries (`AGENTS.md` §3.1).
- **QML Sanitization:** Always run database dictionaries through `_sanitize_for_qml` before serializing to JSON for QML (`AGENTS.md` §3.2), converting `None` to `0` for `NUMERIC_KEYS` and `""` for text keys while preserving `bool`.
- **Barcode Format & Sequence Invariant:** Format `{BARCODE_PREFIX}-{book_id:05d}-{copy_seq:02d}` (`BARCODE_PREFIX = "SMTE"`), where `copy_seq` is `count_copies_ever(conn, book_id) + 1` and never reuses retired or disposed sequence numbers (`doc/book_barcode_generation.md` §2–§3).
- **Search Privacy Invariant:** `student_repo.search_students` must never match `national_id` (`doc/student_search_algorithm.md`).
- **Wiki Maintenance:** Update relevant `wiki/` pages and append a summary entry to `wiki/log.md` (`AGENTS.md` §4).

## Review Focus

1. **Barcode strings containing PDF delimiters `(`, `)`, `\` or non-ASCII characters in `export_label_sheet_pdf`:** PDF text stream must escape `\`, `(`, `)` and Code128-B encoder must map out-of-range characters (`ord(ch) < 32` or `ord(ch) > 126`) to `?` without raising `IndexError` or producing a corrupt PDF.
2. **Stale imports or re-creation of deleted dead modules (`core/library/models.py`, `core/shared/errors.py`, `packaging/*_windows.spec`, duplicate root `.md` files):** Codebase must have zero references to deleted files while keeping `core.student.models` intact.
3. **Percent-encoded Thai `file://` URLs and boolean values in shared adapter utilities:** `normalize_file_path("file:///tmp/%E0%B8%99%E0%B8%A3.xlsx")` must decode to `"/tmp/นร.xlsx"`, and `_sanitize_for_qml({"ok": True, "student_id": None})` must keep `True` as `bool` (not `1`) even though `isinstance(True, int)` is `True` in Python.
4. **Student search with embedded double quotes (`สม"ชาย`) or historical enrollments from prior semesters:** FTS5 query construction must escape `"` as `""` without raising `sqlite3.OperationalError`, and room/grade filters must match only each student's latest enrollment (`MAX(id)`), never an older semester's room.
5. **Chained student ID renumbering (`1001 -> 8001 -> 9001`) during batch `apply_sync` with active library loans:** `student_id_changes` must apply in chronological `id ASC` order before `executemany` upserts so `ON UPDATE CASCADE` preserves `loans.student_id` without `FOREIGN KEY constraint failed`.

---

### Task 1: Pure-Stdlib Code128 PDF Label Generator & Barcode Lookup

**Files:**
- Modify: `core/library/services/label_service.py`
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py:137-220`
- Modify: `apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml:110-140`
- Modify: `apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml:120-190`
- Modify: `data/repositories/book_repo.py:235-265`
- Modify: `apps/booth_app/main.py:20-35`
- Test: `tests/test_barcode_and_disposed.py`

**Interfaces:**
- Consumes: `core.library.policy.BARCODE_PREFIX` (`"SMTE"`), `data.paths.get_default_db_path(app_name: str, db_filename: str) -> Path`
- Produces:
  - `export_label_sheet_pdf(copies: List[Union[Tuple[int, str], str]], output_path: str, cols: int = 3, rows: int = 8) -> None` in `core/library/services/label_service.py`
  - `LibrarianAdminAdapter.addBook(title, isbn="", author="", publisher="", category_id="", shelf_location="", barcodes_csv="") -> str` (defaults blank `barcodes_csv` to `copy_count = 1`)
  - `LibrarianAdminAdapter.addCopies(book_id: int, copies_or_barcodes: Any = "1") -> str` (accepts `int` or `str`)
  - `book_repo.get_copy_by_barcode(conn: sqlite3.Connection, barcode: str) -> Optional[sqlite3.Row]` (case/dash-insensitive + ISBN fallback)

- [ ] **Step 1: Write the failing tests in `tests/test_barcode_and_disposed.py`**
- [ ] **Step 2: Run test to verify it passes with stdlib PDF generator**
- [ ] **Step 3: Implement stdlib `export_label_sheet_pdf` in `core/library/services/label_service.py` and fix QML/adapter/repo bindings**
- [ ] **Step 4: Commit**

---

### Task 2: Dead File, Duplicate Doc & Unused Spec Removal (`ponytail-audit`)

**Files:**
- Delete: `application_layer_design.md`
- Delete: `database_layer_design.md`
- Delete: `design_doc.md`
- Delete: `ui_layer_design.md`
- Delete: `query_lm_studio.py`
- Delete: `seed_sample_students.py`
- Delete: `packaging/booth_app_windows.spec`
- Delete: `packaging/librarian_management_windows.spec`
- Delete: `packaging/student_management_windows.spec`
- Delete: `core/library/models.py`
- Delete: `core/shared/errors.py`
- Modify: `tests/test_spec_exclusions.py`

**Interfaces:**
- Consumes: `os.path` in `tests/test_spec_exclusions.py`
- Produces: Clean repo tree (`-2,014 lines`) with canonical docs in `doc/` and `wiki/`, canonical specs in `packaging/{librarian_management,student_management,booth_app}.spec`, and canonical error/result handling in `core/shared/result.py`.

- [ ] **Step 1: Write the failing test in `tests/test_spec_exclusions.py`**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Delete the 11 dead/duplicate files**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 3: Shared QML Sanitizer & `file://` URL Normalizer

**Files:**
- Modify: `core/shared/mock_qt.py`
- Modify: `apps/student_management_app/adapters/student_admin_adapter.py:1-55`
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py:1-40`
- Modify: `apps/booth_app/adapters/booth_adapter.py:1-35`
- Test: `tests/test_adapters.py`

**Interfaces:**
- Consumes: `urllib.parse.unquote`, `urllib.parse.urlparse`, `typing.Any`, `typing.Set`
- Produces:
  - `NUMERIC_KEYS: Set[str]` in `core/shared/mock_qt.py`
  - `_sanitize_for_qml(obj: Any) -> Any` in `core/shared/mock_qt.py` (re-exported in adapters for backward compatibility with existing test imports)
  - `normalize_file_path(file_path: str) -> str` in `core/shared/mock_qt.py`

- [ ] **Step 1: Write the failing test in `tests/test_adapters.py`**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `NUMERIC_KEYS`, `_sanitize_for_qml(obj: Any) -> Any`, and `normalize_file_path(file_path: str) -> str` in `core/shared/mock_qt.py` and import in all 3 adapters**
- [ ] **Step 4: Run adapter tests to verify they pass**
- [ ] **Step 5: Commit**

---

### Task 4: Student Search Single-Pass Enrollment & FTS5 Join

**Files:**
- Modify: `data/repositories/student_repo.py:7-160`
- Test: `tests/test_search_algorithm.py`

**Interfaces:**
- Consumes: `students`, `enrollments`, `students_fts` tables in SQLite
- Produces:
  - `search_students(conn, query, grade_level=None, room=None, status=None, limit=50, offset=0) -> List[sqlite3.Row]`
  - `count_students(conn, query, grade_level=None, room=None, status=None) -> int`
  - `get_student(conn, student_id: int) -> Optional[sqlite3.Row]`

- [ ] **Step 1: Write the failing/edge-case test in `tests/test_search_algorithm.py`**
- [ ] **Step 2: Run test to verify current behavior and query plan**
- [ ] **Step 3: Replace correlated `max(e2.id)` and triple `students_fts` subqueries in `data/repositories/student_repo.py`**
- [ ] **Step 4: Run search and repository test suites**
- [ ] **Step 5: Commit**

---

### Task 5: Batch Snapshot Sync (`executemany`) & Composite Copy Status Index

**Files:**
- Create: `data/migrations/0009_copies_book_status_idx.sql`
- Modify: `data/sync/apply.py:30-95`
- Modify: `wiki/database/schema.md`
- Modify: `wiki/log.md`
- Test: `tests/test_sync_edge_cases.py`

**Interfaces:**
- Consumes: `data.migrate.apply_migrations`, `data.sync.diff.compute_diff`
- Produces:
  - Migration `0009_copies_book_status_idx.sql` creating `idx_copies_book_status ON book_copies(book_id, status)`
  - Batched `apply_sync(snapshot_path: str, local_conn: sqlite3.Connection, actor: Optional[str] = None) -> Result` using `local_cur.executemany` and `ORDER BY id ASC` on `student_id_changes`

- [ ] **Step 1: Write the failing test in `tests/test_sync_edge_cases.py`**
- [ ] **Step 2: Run test to verify it fails before `0009_copies_book_status_idx.sql`**
- [ ] **Step 3: Create `data/migrations/0009_copies_book_status_idx.sql` and batch `data/sync/apply.py` with `executemany`**
- [ ] **Step 4: Run sync and migration tests to verify they pass**
- [ ] **Step 5: Commit**
