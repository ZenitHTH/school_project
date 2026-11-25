# Plain-Paper Barcode Book Titles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finalize plain-paper A4 barcode label sheets with book titles by aligning the ASCII-only PDF layout with the Qt Thai renderer (fixed barcode size, vertically centered 1–4 line title zone), bundling `pythainlp` in PyInstaller packaging, and updating wiki documentation.

**Architecture:** `core/library/services/label_service.py` handles pure-stdlib ASCII PDF 1.4 output and routes non-ASCII (Thai) titles to `core/library/services/label_qt_renderer.py` (Qt `QPdfWriter` + `PyThaiNLP` `newmm` word-boundary wrapping). `LibrarianAdminAdapter.exportLabelsPdf` enriches bare barcode lists with book titles from SQLite automatically.

**Tech Stack:** Python 3.14, PySide6 (`QPdfWriter`, `QPainter`), `pythainlp>=5.0.0` (`newmm`), PyInstaller, pytest.

**Spec:** User requirements in current session (plain-paper A4 barcode with book title, Thai word-boundary wrapping via `pythainlp`, up to 4 wrapped lines, fixed barcode size across all cells, short titles vertically centered in the title zone).

## Global Constraints

- Keep `export_label_sheet_pdf` backward-compatible with bare `str`, `(copy_id, barcode)` 2-tuples, `(copy_id, barcode, title)` 3-tuples, and `{"barcode", "title"}` dicts.
- Keep `test_export_label_sheet_pdf_escapes_special_and_non_ascii_chars` passing (pure-stdlib PDF 1.4 bytes for ASCII/no-title inputs).
- All cells on a sheet must render Code128-B bars at the exact same vertical position and height.
- Commit and push exclusively to `dev` branch.

## Review Focus

- Very long ASCII titles (150+ chars) with no spaces: must wrap up to 4 lines and elide line 4 with `...` without overflowing the cell width.
- Very long Thai titles with no spaces: must wrap on `pythainlp` `newmm` word boundaries up to 4 lines and elide line 4 with `…`.
- Empty or whitespace-only title: must still render the barcode at the uniform fixed position without crashing.
- Frozen PyInstaller build: `pythainlp` corpus data must be bundled in `packaging/librarian_management.spec` so `word_tokenize(..., engine="newmm")` does not silently fall back to char wrapping.
- Full test suite regression: all existing tests under `tests/` must pass under `QT_QPA_PLATFORM=offscreen`.

---

### Task 1: Align ASCII PDF Renderer to Fixed Barcode Size & 4-Line Centered Title Zone

**Files:**
- Modify: `core/library/services/label_service.py`
- Test: `tests/test_barcode_and_disposed.py`

**Interfaces:**
- Consumes: `_escape_pdf_literal(text: str) -> Tuple[str, float]`, `_truncate_ascii_title(title: str, max_width_pt: float, font_size: float) -> Tuple[str, float]`
- Produces: `_wrap_ascii_title(title: str, max_width_pt: float, max_lines: int = 4) -> Tuple[List[Tuple[str, float]], float]`

- [ ] **Step 1: Write the failing test**

Add assertion in `tests/test_barcode_and_disposed.py::test_export_label_sheet_pdf_with_ascii_and_thai_titles` verifying a 200-char ASCII title wraps to 4 lines at `5.5 Tf` and ends with `...)`, and a no-title label renders without error.

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_barcode_and_disposed.py::test_export_label_sheet_pdf_with_ascii_and_thai_titles -v`
Expected: FAIL (`5.5 Tf` not found because current `_wrap_ascii_title` caps at 2 lines / `6.5 Tf`).

- [ ] **Step 3: Update `_wrap_ascii_title` and `_render_label_cell` in `core/library/services/label_service.py`**

Step font sizes `(7.5, 1)`, `(6.5, 2)`, `(6.0, 3)`, `(5.5, 4)` in `_wrap_ascii_title`. In `_render_label_cell`, reserve a fixed `32.0 pt` top title zone (when `title` is present, vertically center the `1..4` lines inside it) and keep Code128 bars at a fixed `bc_y` and `bc_h` when titles are used.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_barcode_and_disposed.py tests/test_adapters.py -q`
Expected: PASS (55 passed).

- [ ] **Step 5: Commit**

```bash
git add core/library/services/label_service.py core/library/services/label_qt_renderer.py apps/librarian_management_app/adapters/librarian_admin_adapter.py tests/test_barcode_and_disposed.py requirements.txt
git commit -m "feat(library): add book titles with 4-line Thai word wrap to plain-paper barcode PDFs"
```

---

### Task 2: Bundle PyThaiNLP Data in PyInstaller Spec

**Files:**
- Modify: `packaging/librarian_management.spec:25-29`

**Interfaces:**
- Consumes: `PyInstaller.utils.hooks.collect_all`
- Produces: `datas`, `binaries`, `hiddenimports` including `pythainlp` corpus data in `LibrarianManagement` executable/bundle.

- [ ] **Step 1: Add `pythainlp` to `collect_all` loop in `packaging/librarian_management.spec`**

Update `for pkg in ['core', 'data', 'apps']:` to `for pkg in ['core', 'data', 'apps', 'pythainlp']:`.

- [ ] **Step 2: Verify spec syntax**

Run: `.venv/bin/python -m py_compile packaging/librarian_management.spec`
Expected: Exit code 0.

- [ ] **Step 3: Commit**

```bash
git add packaging/librarian_management.spec
git commit -m "build(packaging): bundle pythainlp data files in librarian management spec"
```

---

### Task 3: Update Wiki Documentation & Run Full Test Suite

**Files:**
- Modify: `wiki/services/library-services.md`
- Modify: `wiki/log.md`

**Interfaces:**
- None (documentation & full verification).

- [ ] **Step 1: Update `wiki/services/library-services.md` and append entry to `wiki/log.md`**

Document `label_qt_renderer.py` (Qt `QPdfWriter` + `PyThaiNLP` `newmm` 1–4 line word-boundary wrapping, fixed barcode height, centered title zone) and `LibrarianAdminAdapter._attach_book_titles`.

- [ ] **Step 2: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add wiki/services/library-services.md wiki/log.md
git commit -m "docs(wiki): document barcode label book titles and Thai word-wrap renderer"
```
