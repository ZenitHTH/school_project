# Book Catalog Barcode Search — Design

- Date: 2026-11-06
- Status: draft (awaiting approval)
- Scope: small change

## Intent & why

The first page of the Librarian Management app (Tab 0, `BookCatalogView.qml`)
cannot find a book by its barcode sticker. Its search field matches
title/author/ISBN only (FTS5). Librians who scan a sticker at the desk have no
way to locate the book on the catalog page. Additionally, the catalog page has
no way to narrow the list by category. Goal: (1) scanning or typing a barcode
sticker into the existing search field finds the book, and (2) a category
filter dropdown narrows the list on the same search row.

## Approach (user-selected: A — one field, barcode-aware)

1. `data/repositories/book_repo.py::search_books` (line ~275): in the FTS branch
   (query length >= 3), OR an extra normalized exact-match barcode condition:

   ```sql
   OR b.book_id IN (
       SELECT bc.book_id FROM book_copies bc
       WHERE REPLACE(LOWER(bc.barcode), '-', '') = ?
   )
   ```

   Parameter: `query.strip().lower().replace("-", "")`.
   The short-query LIKE branch (query < 3 chars) is untouched — a barcode is
   always 9+ characters.
2. `apps/librarian_management_app/qml/views/BookCatalogView.qml`: update
   `catalogSearchInput.placeholderText` to mention barcode, in the file's
   existing text style.
3. Barcode lookup reuses the existing query pipeline — no new adapter method.

### Category filter dropdown (user request, 2026-11-06)

4. `apps/librarian_management_app/qml/views/BookCatalogView.qml`: add a
   shared `StyledComboBox` (objectName `catalogCategoryCombo`, model
   `catalogCategoryModel`) between the search field and the search button on
   the search row. First option is `{category_id: 0, name: "-- ทุกหมวดหมู่ --"}`
   (the `id 0 = all` pattern already used by `BarcodeGeneratorView`). Loaded
   in `Component.onCompleted` via the existing `librarianAdmin.listCategories()`
   call, same as `BarcodeGeneratorView.loadCategoriesList`.
5. `apps/librarian_management_app/adapters/librarian_admin_adapter.py`:
   `searchBooks` becomes `@Slot(str, int, result=str)
   def searchBooks(self, query: str, category_id: int = 0)`, passing
   `category_id or None` to `catalog_svc.search`. `0` (the dropdown's "all"
   option) means no filter. Repository and service layers are untouched —
   `search_books` already implements the `category_id` filter.
6. `apps/librarian_management_app/qml/Main.qml`: the `searchBooks()` QML
   function passes the selected id:
   `librarianAdmin.searchBooks(catalogSearchInput.text,
   catalogCategoryCombo.currentIndex <= 0 ? 0 : catalogCategoryModel.get(catalogCategoryCombo.currentIndex).category_id)`.

## Goals

- Scanning/typing `SMTE-00001-01` (any case, dashes optional) into the existing
  Tab 0 search field narrows the list to that book.
- Existing title/author/ISBN search behavior unchanged.
- A category filter dropdown on the Tab 0 search row narrows the list by
  category, combinable with the text/barcode query (e.g. a barcode query
  outside the selected category returns no rows).

## Non-goals

- No highlight/scroll-to-row on hit (default: the list filters, same as any
  other search).
- No dedicated scan field on Tab 0.
- No FTS index on `book_copies.barcode`.
- No live refresh of the category filter options after categories are added,
  renamed, or deleted (options reload on app start; same staleness as the
  other views' category lists).
- No changes to the booth app or the barcode print studio.

## Anti-goals

- No new adapter methods. No new shared QML component.

## Constraints

- AGENTS rules: reuse `common_qml` components (no new ones needed here),
  maintain 100% test coverage, run `.venv/bin/pytest tests/` after the change,
  update the relevant `wiki/` page and append `wiki/log.md`.
- Service layer unchanged; the change is at the repository layer.

## Decisions

- Approach A (single unified field) selected by the user, 2026-11-06.
- Post-hit behavior is filter-only (builder's call, minimal).
- Normalization mirrors `book_repo.get_copy_by_barcode` (lowercase, dashes
  stripped), without its ISBN fallback — that fallback serves checkout, not
  catalog search.
- Category filter: shared `StyledComboBox` (AGENTS rule 3/7), `id 0 = all`
  option pattern copied from `BarcodeGeneratorView`, loaded once in
  `Component.onCompleted` (builder's call; keeps the diff inside the view).
- `searchBooks` slot gains an optional `category_id` (default `0`) so existing
  one-argument Python callers keep working; QML always passes both.

## Known-limit shortcut

`REPLACE(LOWER(bc.barcode))` scans all `book_copies` rows per search. Fine at
school-library scale (hundreds–thousands of copies). Upgrade to an indexed
exact-match lookup if copy counts exceed ~10k. Carried as a one-line
`shortcut:` comment in the code.

## Test plan

- `tests/test_search_algorithm.py` / `tests/test_repositories.py`:
  - exact barcode with dashes returns the book;
  - lowercase / dash-less variants return the same book;
  - unknown barcode returns an empty result set;
  - title/author/ISBN searches still behave identically (regression).
- `tests/test_adapters.py`:
  - `searchBooks(query, category_id)` returns only books in that category;
  - `category_id=0` (and the one-argument default call) returns unfiltered
    results, matching previous behavior.
- QML: existing UI tests load `BookCatalogView`; placeholder assertion (if any)
  updated in `tests/test_adversarial_settings_and_placeholders.py`. A UI test
  asserts `catalogCategoryCombo` exists and `Main.qml`'s `searchBooks()` calls
  the adapter with the selected category id (per the existing
  `test_ui_librarian.py` / `test_qml_loads.py` patterns).

## Wiki

- `wiki/apps/librarian-management-app.md`: note Tab 0 search is barcode-aware.
- `wiki/log.md`: append entry.

## Left to the builder

- ~10-line diff in `book_repo.search_books`, 1-line QML placeholder,
  ~15-line `StyledComboBox` block in `BookCatalogView.qml`, 3-line adapter
  slot change, 1-line `Main.qml` call-site change, tests per the plan above,
  wiki updates. Run the full test suite before committing.
- If the real PySide6 `@Slot` rejects one-argument Python calls on the new
  two-arg signature (unlikely — Python defaults should apply), update the
  existing test call sites to pass `0` explicitly.
- Git: commit/push exclusively to `dev` per AGENTS branch invariant.
