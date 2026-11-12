# Books Without ISBN — Checkbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give librarians an explicit 'No ISBN' checkbox in every book dialog. Checked → the ISBN field locks and shows '-'; saving writes an empty ISBN → `books.isbn` NULL.

**Architecture:** Backend already stores blank ISBN as NULL (`books.isbn` nullable, migration `0002`; `CatalogService.add_book`/`update_book` coerce `""` → `None`) and the catalog list already renders `model.isbn || "-"` (`BookCatalogView.qml:136`, `BookInventoryRightPane.qml:121,339`). Task 1 pins that backend contract with regression tests. Task 2 adds the checkbox + field lock + `-` display to the three ISBN inputs; submit paths send `''` when the box is checked. Task 3 updates the wiki. No schema migration, no data change.

**Why save `''` not `'-'`:** both write paths store the ISBN as typed — `_insert_book_row` and repo `update_book` (`SET isbn = ?`), no normalization on write — so `'-'` would persist in the row. `''` → NULL; lookups already treat `'-'` as empty (`_normalize_isbn`, `book_repo.py:57-61`), and the UI draws '-' for NULL.

**Tech Stack:** Python 3.14, PySide6 QML (offscreen tests), SQLite (schema frozen), pytest.

**Spec:** No separate spec file. Requirements (2026-11-11 design decision, revised):
1. A book may exist without an ISBN — blank must insert, update, search, and lend without error.
2. Fake/placeholder ISBN numbers are rejected as a workaround.
3. UI provides a "No ISBN" checkbox: checked → ISBN input disabled and shows `-`; unchecked → normal editing.
4. Submit with the box checked sends `''` (→ NULL), never `'-'`.
5. UI must make optionality visible in every ISBN input (add, edit, barcode generator).

## Global Constraints

- Run `.venv/bin/pytest tests/` after every change; 100% test coverage is mandatory (AGENTS.md rule 5).
- Service layer returns `Result[T, E]` from `core.shared.result`; no unhandled exceptions cross boundaries (rule 1).
- DB dicts to QML always pass `_sanitize_for_qml` (`core/shared/mock_qt.py:15`): a `None` ISBN arrives in QML as `''` (rule 2).
- No new schema migration. `books.isbn TEXT` stays nullable (`data/migrations/0002_library_tables.sql:4`). No data migration — no existing row stores '-'.
- QML edits stay inside the existing dialogs; no hardcoded pixel heights (house rules 6–7); reuse existing `CheckBox` styling as `chkDialogAutoFetchIsbn` (`BookActionDialogs.qml:299-305`).
- UI copy is Thai, matching existing style.
- New Python test code uses single-quoted string literals; QML snippets keep double quotes to match the existing files.
- No new dependencies.
- Commit and push to `dev` only, never `main` (rule 8).
- After code lands: update the relevant `wiki/` page and append a `wiki/log.md` entry (AGENTS.md §4).

## Review Focus

- Checked → ISBN input `enabled === false`, text is `-`; unchecked → editable and the `-` is cleared.
- Submit with the box checked sends `''` (not `'-'`) → `books.isbn IS NULL`.
- Edit dialog opened on a NULL-ISBN book auto-checks the box and shows `-`.
- Two books with NULL ISBN coexist; `checkBookByIsbn('')` never triggers the duplicate guard.
- FTS/LIKE title search returns a book whose `isbn` is NULL.
- Adapter JSON payloads contain `isbn: ''`, never `null` (QML role stability).
- Lending a no-ISBN book by copy barcode still works (existing coverage: `tests/test_adapters.py:289`).
- Checkbox edits don't break `tests/test_ui_barcode_generator_fields.py` / `tests/test_ui_librarian.py` — they locate inputs by `objectName`, not text (verified).

## File Structure

| File | Change |
|---|---|
| `tests/test_book_without_isbn.py` (new) | Contract tests for NULL-ISBN books (service, repo, adapter JSON, search) |
| `tests/test_ui_barcode_generator_fields.py` | Checkbox presence + field-lock assertions |
| `apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml` | Add-book checkbox + lock + submit + open-reset; edit-dialog submit + auto-check |
| `apps/librarian_management_app/qml/dialogs/EditBookDialog.qml` | Edit checkbox + lock + alias |
| `apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml` | Generator checkbox + lock + both submit paths + reset |
| `wiki/apps/librarian-management-app.md` | Document no-ISBN checkbox behavior |
| `wiki/log.md` | Append change entry |

## Task 1: Pin the no-ISBN contract (regression tests)

**Interfaces:** self-contained.

- [ ] Create `tests/test_book_without_isbn.py`. Define a local fixture mirroring `tests/test_adapters.py:38-48`: temp `library.sqlite` via `get_connection(path, pin="123456")`, `apply_migrations(conn)`, `LibrarianAdminAdapter(conn)`, yield `(adapter, conn)`, close on teardown.
- [ ] Write `test_add_book_empty_isbn_stores_null`: `svc = CatalogService(conn)`; `res = svc.add_book(title='หนังสือไม่มี ISBN', isbn='', copy_count=1)`; assert `res.is_ok()`; `SELECT isbn FROM books WHERE title = ?` → `row["isbn"] is None`; `SELECT COUNT(*) FROM book_copies` for the new `book_id` → 1, and its barcode matches `SMTE-\d{5}-\d{2}` (`core/library/policy.py:20`).
- [ ] Write `test_two_null_isbn_books_coexist`: `svc.add_book(title='A ไม่มี ISBN', isbn=None, copy_count=1)` and `svc.add_book(title='B ไม่มี ISBN', isbn=None, copy_count=1)` → both `is_ok()`; `json.loads(adapter.checkBookByIsbn(''))` → `ok` true (guard only runs for non-empty ISBN, `catalog_service.py:67`; `_normalize_isbn` returns `None` for empty, `book_repo.py:57-61`).
- [ ] Write `test_null_isbn_roundtrip_adapter_json`: `add_res = json.loads(adapter.addBook('หนังสือไม่มี ISBN 2', '', '', '', '', '', 'NOISBN-01'))` (7 positional args, pattern from `tests/test_adapters.py:205`); `book_id = add_res['data']['book_id']`; assert `json.loads(adapter.getBook(book_id))['data']['isbn'] == ''` and `json.loads(adapter.searchBooks('หนังสือไม่มี ISBN 2'))['data'][0]['isbn'] == ''`.
- [ ] Write `test_update_book_empty_isbn_stays_null`: add via `json.loads(adapter.addBook('ISBN เดิม', '9786100000001', '', '', '', '', 'OLD-01'))`; then `json.loads(adapter.updateBook(book_id=book_id, title='ISBN เดิม', isbn='', author='', category_id_str='', shelf_location=''))` → `ok` true; `SELECT isbn FROM books WHERE book_id = ?` → `is None`.
- [ ] Run `.venv/bin/pytest tests/test_book_without_isbn.py -v`. Expect PASS — behavior already exists, this pins it. If an assertion fails, fix the root cause in `core/library/services/catalog_service.py` or the adapter, never the test.
- [ ] Run full suite `.venv/bin/pytest tests/` — green.
- [ ] Commit: `test: pin contract for books without ISBN`.

## Task 2: "No ISBN" checkbox with locked field (QML)

**Interfaces (objectNames, new):** `chkNoIsbnAdd` / `newBookIsbn` (`BookActionDialogs.qml` add dialog), `chkNoIsbnEdit` / `editBookIsbnInput` (`EditBookDialog.qml` + `BookActionDialogs.qml` edit path), `chkNoIsbnGen` / `genBookIsbn` (`BarcodeGeneratorView.qml`). Checkbox text: `ไม่มี ISBN (No ISBN)`. Locked-field text: `-`.

**Binding pattern (same in all three):** checkbox `onClicked`/`onCheckedChanged` → if checked: `field.text = "-"`; if unchecked: `field.text = ""`. Field: `enabled: !chkNoIsbn.checked`. Submit: `chkNoIsbn.checked ? "" : field.text.trim()`.

TDD:

- [ ] In `tests/test_ui_barcode_generator_fields.py`, add `test_no_isbn_checkbox_locks_field` using the file's existing offscreen-QML fixture (load pattern from `tests/test_ui_librarian.py:908` — librarian `Main.qml` + `librarianAdmin` context property). For each of the three pairs (`chkNoIsbnAdd`/`newBookIsbn`, `chkNoIsbnEdit`/`editBookIsbnInput`, `chkNoIsbnGen`/`genBookIsbn`): `win.findChild(QObject, chk).setProperty('checked', true)` → assert `win.findChild(QObject, field).property('enabled') is False` and `.property('text') == '-'`; set `checked` back to `false` → assert `enabled is True` and `text == ""`.
- [ ] Run `.venv/bin/pytest tests/test_ui_barcode_generator_fields.py -v` — new test FAILS (checkboxes don't exist yet).
- [ ] `BookActionDialogs.qml` — add-book dialog:
  - Inside the ISBN `RowLayout` (lines 257–298), after `btnDialogFetchIsbn`, add `CheckBox { id: chkNoIsbn; objectName: "chkNoIsbnAdd"; text: "ไม่มี ISBN (No ISBN)"; font.pixelSize: 12 }` with the `onCheckedChanged` lock/clear behavior and `newBookIsbn.enabled: !chkNoIsbn.checked`.
  - `onAccepted` (line 330–332): replace `newBookIsbn.text` with `chkNoIsbn.checked ? "" : newBookIsbn.text.trim()` in the `librarianAdmin.addBook(...)` call.
  - `onAboutToShow` (line 236–246): add `chkNoIsbn.checked = false`.
- [ ] `EditBookDialog.qml` — edit dialog:
  - In the ISBN `ColumnLayout` (lines 224–235), after `isbnInput`, add `CheckBox { id: chkNoIsbn; objectName: "chkNoIsbnEdit"; text: "ไม่มี ISBN (No ISBN)"; font.pixelSize: 12 }`; `isbnInput.enabled: !chkNoIsbn.checked`; same lock/clear behavior (checked → `isbnInput.text = "-"`, unchecked → `""`).
  - Add `property alias chkNoIsbnEdit: chkNoIsbn` (mirror of the existing `property alias editBookIsbnInput: isbnInput`, line 23).
- [ ] `BookActionDialogs.qml` — edit path:
  - `openEditBookDialog` (lines 56–60): after `editBookIsbnInput.text = isbn`, set `editBookDialog.chkNoIsbnEdit.checked = (isbn === "")` (this both locks and displays `-` via the handler).
  - `submitEditBook` (~line 95): replace `editBookIsbnInput.text.trim()` with `editBookDialog.chkNoIsbnEdit.checked ? "" : editBookIsbnInput.text.trim()`.
- [ ] `BarcodeGeneratorView.qml` — generator view:
  - Near the `genBookIsbn` field (~lines 545–560), add `CheckBox { id: chkNoIsbnGen; objectName: "chkNoIsbnGen"; text: "ไม่มี ISBN (No ISBN)"; font.pixelSize: 12 }`; `genBookIsbn.enabled: !chkNoIsbnGen.checked`; same lock/clear behavior.
  - New-book submit (~line 197) and add-copies selector path (~line 391): `var isbn = chkNoIsbnGen.checked ? "" : genBookIsbn.text.trim()`.
  - After-save reset (~line 323): add `chkNoIsbnGen.checked = false` next to `genBookIsbn.text = ""`.
- [ ] Run `.venv/bin/pytest tests/test_ui_barcode_generator_fields.py -v` — PASS.
- [ ] Run `.venv/bin/pytest tests/test_ui_librarian.py tests/test_qml_loads.py tests/test_ui_barcode_generator_fields.py -v` — green (QML loads, auto-fetch and duplicate-check flows unregressed).
- [ ] Commit: `ui: add No-ISBN checkbox with locked ISBN field in add, edit, and barcode-generator views`.

## Task 3: Update wiki (house rule)

- [ ] `wiki/apps/librarian-management-app.md`: add a short "Books without ISBN" section — checkbox `ไม่มี ISBN (No ISBN)` in add/edit/generator dialogs; checked → field locks and shows `-`; submit sends empty ISBN → `books.isbn` NULL; UI renders `-` for missing ISBN (`BookCatalogView.qml:136`); auto-fetch ISBN only runs for non-empty valid ISBN; lending keys off the copy barcode, never the ISBN; the DB stores NULL for no-ISBN books.
- [ ] Append `wiki/log.md`: date 2026-11-11, one-line summary, link to this plan.
- [ ] Run `.venv/bin/pytest tests/` — green.
- [ ] Commit: `docs: wiki — books without ISBN checkbox`.

## Out of scope (deliberate)

- Storing '-' in books.isbn — rejected: both write paths store the ISBN as typed (no normalization on write), so the hyphen would persist in the row. '' → NULL, and lookups already treat '-' as empty.
- Fake-ISBN sanitization or data migration — rejected: no row stores a fake value to repair; leaving the field blank is the correct operator behavior.
- `has_isbn` column — rejected: derivable from `isbn IS NULL`; a flag duplicates state.
- Catalog filter "show books without ISBN" — not requested; revisit if asked.
- Barcode handling — unchanged: barcodes are auto-generated per copy (`SMTE-{book_id:05d}-{seq:02d}`) and are independent of ISBN.
