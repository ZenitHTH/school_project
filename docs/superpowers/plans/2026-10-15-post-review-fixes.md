# Post-Review Barcode Path, QML Dialog & Search DRY Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 3 remaining post-review bugs in `539c105..cc6f046` (`SMTE-LibraryManagement` typo in `booth_app/main.py`, unpatched `BookActionDialogs.qml` / `exportLabelsPdf` path handling, and duplicated SQL query builder in `student_repo.py`).

**Architecture:** Fix `apps/booth_app/main.py` to resolve `SMTE-LibrarianManagement/library.sqlite` without creating ghost directories, update `BookActionDialogs.qml` and `LibrarianAdminAdapter.exportLabelsPdf` for cross-platform path normalization and typed `@Slot(int, str)` / `@Slot(int, int)` overloads, and extract `_build_student_search_clauses` in `data/repositories/student_repo.py` shared by `search_students` and `count_students`.

**Tech Stack:** Python 3.10–3.15, PySide6 (Qt Quick / QML), SQLite3 (FTS5 trigram), pytest.

**Spec:** `wiki/index.md`, `doc/book_barcode_generation.md`, `doc/file_locations_design.md`

## Global Constraints

- **Canonical App Directory Names:** `SMTE-StudentManagement`, `SMTE-LibrarianManagement`, `SMTE-Booth` (`doc/file_locations_design.md` §2). Never create `SMTE-LibraryManagement`.
- **Service & Adapter Contract:** Return JSON-serialized `Result` dicts (`{"ok": bool, ...}`); normalize `file://` URLs via `normalize_file_path` (`core/shared/mock_qt.py`).
- **Zero New Dependencies:** Stdlib + existing `requirements.txt` only (`ponytail` ladder).

## Review Focus

1. **`booth_app/main.py` DB path fallback when `SMTE-LibrarianManagement/library.sqlite` exists:** Must resolve `get_default_db_path("SMTE-LibrarianManagement", "library.sqlite")` (not `"SMTE-LibraryManagement"`) and must not create an empty `SMTE-LibraryManagement` directory on disk.
2. **`exportLabelsPdf` called with a `file://` URL or `/tmp/...` path when `/tmp` is missing:** `LibrarianAdminAdapter.exportLabelsPdf` must strip `file://` via `normalize_file_path` and fall back to `tempfile.gettempdir()` when `/tmp` does not exist.
3. **`BookActionDialogs.qml` `addBookDialog` and `addCopiesDialog` slot calls:** `newBookBarcodes` must default to `"1"` and `addCopiesDialog` must pass a string (`raw || "1"`) while `LibrarianAdminAdapter.addCopies` exposes explicit `@Slot(int, str, result=str)` and `@Slot(int, int, result=str)` signatures.
4. **Boolean values in `NUMERIC_KEYS` fields during `_sanitize_for_qml`:** If a dict ever carries a `bool` under any key, `isinstance(True, int)` in Python must not coerce it or skip nested sanitization.
5. **Parity between `search_students` and `count_students` in `student_repo.py`:** Both functions must use the exact same `JOIN` and `WHERE` clauses from `_build_student_search_clauses` so pagination counts never diverge from returned rows.

---

### Task 1: Fix Booth App `SMTE-LibrarianManagement` Shared DB Path Resolution

**Files:**
- Modify: `apps/booth_app/main.py:24-34`
- Test: `tests/test_file_locations.py`

**Interfaces:**
- Consumes: `data.paths.get_default_db_path(app_name: str, db_filename: str) -> Path`
- Produces: `resolve_booth_db_path() -> str` in `apps/booth_app/main.py`

- [ ] **Step 1: Write the failing test in `tests/test_file_locations.py`**

```python
def test_booth_resolves_librarian_management_db_path(tmp_path, monkeypatch):
    import data.paths as dp
    import apps.booth_app.main as booth_main

    monkeypatch.setattr(dp, "get_app_data_dir", lambda app_name: tmp_path / app_name)
    monkeypatch.delenv("BOOTH_DB_PATH", raising=False)

    lib_dir = tmp_path / "SMTE-LibrarianManagement"
    lib_dir.mkdir(parents=True, exist_ok=True)
    lib_db = lib_dir / "library.sqlite"
    lib_db.write_bytes(b"sqlite")

    resolved = booth_main.resolve_booth_db_path()
    assert resolved == str(lib_db)
    assert not (tmp_path / "SMTE-LibraryManagement").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_file_locations.py::test_booth_resolves_librarian_management_db_path -v`
Expected: FAIL with `AttributeError: module 'apps.booth_app.main' has no attribute 'resolve_booth_db_path'` (and typo `SMTE-LibraryManagement` in `main.py`).

- [ ] **Step 3: Implement `resolve_booth_db_path() -> str` in `apps/booth_app/main.py`**

```python
def resolve_booth_db_path() -> str:
    if os.environ.get("BOOTH_DB_PATH"):
        return os.environ["BOOTH_DB_PATH"]
    lib_path = str(get_default_db_path("SMTE-LibrarianManagement", "library.sqlite"))
    booth_path = str(get_default_db_path("SMTE-Booth", "library.sqlite"))
    if os.path.exists(lib_path) and not os.path.exists(booth_path):
        return lib_path
    return booth_path
```
Call `db_path = resolve_booth_db_path()` inside `main()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_file_locations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/booth_app/main.py tests/test_file_locations.py
git commit -m "fix(booth): resolve SMTE-LibrarianManagement db path instead of typo"
```

---

### Task 2: Fix `exportLabelsPdf` Path Normalization & `BookActionDialogs.qml` Slot Bindings

**Files:**
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py:160-210`
- Modify: `apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml:125-190`
- Test: `tests/test_barcode_and_disposed.py`

**Interfaces:**
- Consumes: `core.shared.mock_qt.normalize_file_path(file_path: str) -> str`
- Produces:
  - `LibrarianAdminAdapter.addCopies(self, book_id: int, copies_or_barcodes: Any = "1") -> str` with `@Slot(int, str, result=str)` and `@Slot(int, int, result=str)`
  - `LibrarianAdminAdapter.exportLabelsPdf(self, barcodes_json: str, output_path: str) -> str` normalizing `file://` URLs and falling back to `tempfile.gettempdir()` when `/tmp` is missing

- [ ] **Step 1: Write the failing test in `tests/test_barcode_and_disposed.py`**

```python
def test_export_labels_pdf_normalizes_file_url(conn, tmp_path):
    adapter = LibrarianAdminAdapter(conn)
    pdf_path = tmp_path / "url_labels.pdf"
    file_url = "file://" + str(pdf_path)

    resp = json.loads(adapter.exportLabelsPdf(json.dumps(["SMTE-00001-01"]), file_url))
    assert resp["ok"] is True
    assert resp["data"]["output_path"] == str(pdf_path)
    assert pdf_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_barcode_and_disposed.py::test_export_labels_pdf_normalizes_file_url -v`
Expected: FAIL because `exportLabelsPdf` passes raw `"file:///..."` to `open(output_path, "wb")`.

- [ ] **Step 3: Update `exportLabelsPdf` and `addCopies` in `librarian_admin_adapter.py` and `BookActionDialogs.qml`**

In `apps/librarian_management_app/adapters/librarian_admin_adapter.py`:
- Decorate `addCopies` with `@Slot(int, str, result=str)`, `@Slot(int, int, result=str)`, and `@Slot(int, result=str)`.
- In `exportLabelsPdf`:
  ```python
  output_path = normalize_file_path(output_path)
  if output_path.startswith("/tmp/") and not os.path.exists("/tmp"):
      import tempfile
      output_path = os.path.join(tempfile.gettempdir(), os.path.basename(output_path))
  ```
In `apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml`:
- Set `text: "1"` on `newBookBarcodes` (`L132`).
- In `addCopiesDialog.onAccepted` (`L165-174`), replace the `if (count > 0 ...)` branch with:
  ```javascript
  var raw = addCopiesCountInput.text.trim() || "1"
  var bookId = rootWindow ? rootWindow.selectedBookId : 0
  var res = JSON.parse(librarianAdmin.addCopies(bookId, raw))
  ```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_barcode_and_disposed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/librarian_management_app/adapters/librarian_admin_adapter.py apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml tests/test_barcode_and_disposed.py
git commit -m "fix(librarian): normalize exportLabelsPdf file URLs and align dialog slots"
```

---

### Task 3: Deduplicate Student Search Query Builder in `data/repositories/student_repo.py`

**Files:**
- Modify: `data/repositories/student_repo.py:7-165`
- Test: `tests/test_search_algorithm.py`

**Interfaces:**
- Consumes: `query: str`, `grade_level: Optional[str]`, `room: Optional[int]`, `status: Optional[str]`
- Produces: `_build_student_search_clauses(query: str, grade_level: Optional[str], room: Optional[int], status: Optional[str]) -> Tuple[str, str, str, List[Any]]` returning `(joins_sql, where_sql, order_sql, params)` used by both `search_students` and `count_students`

- [ ] **Step 1: Write the failing test in `tests/test_search_algorithm.py`**

```python
def test_search_and_count_share_clause_builder_and_match_counts(conn):
    from data.repositories import student_repo

    assert hasattr(student_repo, "_build_student_search_clauses")
    for q in ["", "4321", "สม", "เข็ม"]:
        rows = student_repo.search_students(conn, query=q, grade_level="ม.1")
        total = student_repo.count_students(conn, query=q, grade_level="ม.1")
        assert len(rows) == total
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_search_algorithm.py::test_search_and_count_share_clause_builder_and_match_counts -v`
Expected: FAIL with `AssertionError` (`_build_student_search_clauses` not defined).

- [ ] **Step 3: Extract `_build_student_search_clauses` in `data/repositories/student_repo.py`**

Move the shared `join_clauses`, `where_conditions`, `order_clause`, and `params` construction into `_build_student_search_clauses(query, grade_level, room, status)` and call it from both `search_students` and `count_students` (`shrink: -45 lines`).

- [ ] **Step 4: Run search and repository tests to verify they pass**

Run: `pytest tests/test_search_algorithm.py tests/test_repositories.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/repositories/student_repo.py tests/test_search_algorithm.py docs/superpowers/plans/2026-10-15-post-review-fixes.md
git commit -m "refactor(student_repo): deduplicate search and count SQL clause builder"
```
