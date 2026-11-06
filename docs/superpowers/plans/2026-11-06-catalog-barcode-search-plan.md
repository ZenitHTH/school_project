# Catalog Barcode Search + Category Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The catalog search on the first page of Librarian Management finds books by scanning/pasting a barcode sticker, and a shared `StyledComboBox` filters results by category.

**Architecture:** `search_books` FTS/non-FTS SQL gains one normalized `OR` barcode condition; the adapter slot gains an optional `category_id: int = 0`; `BookCatalogView` gains a shared combo between search field and button. No new adapter methods, no new QML components.

**Tech Stack:** Python 3.14, SQLite FTS5, PySide6 (QML), `Result[T,E]`, shared `common_qml/` components.

**Spec:** `docs/superpowers/specs/2026-11-06-catalog-barcode-search-design.md`

## Global Constraints

- All service/repo changes return `Result`/`Ok`/`Err` from `core.shared.result`; never raise across boundaries.
- Dictionaries passed to QML go through `_sanitize_for_qml` (already in the adapter `searchBooks` path).
- Never hardcode pixel heights on buttons/badges/headers; dynamic `implicitHeight` pattern (AGENTS rule 6). The new combo is a `StyledComboBox` (shared, already compliant).
- Inputs and `ComboBox` must left-align text and vertically center with ≥12px left padding; apply the alignment rule to combo button contentItem AND popup delegate (AGENTS rule 7).
- Run `.venv/bin/pytest tests/` after each task; must pass before committing.
- Commit exclusively to `dev` (AGENTS rule 8). Do not touch `main`.
- Barcode normalization = `REPLACE(LOWER(value), '-', '')`, identical to `get_copy_by_barcode`.
- Thai copy strings exactly as in the spec (placeholder and `-- ทุกหมวดหมู่ --`).

## Review Focus

1. **Legacy zero-arg `searchBooks` invocation** — existing tests (`test_ui_librarian.py::test_catalog_search_filtering`, `test_repro_catalog_edge_cases.py`) invoke `searchBooks` with no arguments via `QMetaObject.invokeMethod`; the QML function body must treat an absent/invalid second arg as `0` (Task 3).
2. **Barcode + category filter compose** — a barcode outside the selected category yields an empty list (spec behavior); Task 1 test asserts this.
3. **Barcode normalization** — lowercase and dash-insensitive matching; Task 1 tests.
4. **FTS-branch regression** — adding the `OR` clause to the FTS query must not break existing title/author/ISBN/trigram search; Task 1 test asserts a normal title query still hits with the new JOIN present.
5. **Strict Qt slot arg types** — the QML call must pass exactly `(string, int)` to `searchBooks`; Task 2 test covers the Python side, Task 3 UI test covers the QML side.

## File Map

| File | Change |
|---|---|
| `data/repositories/book_repo.py` | `search_books`: barcode OR-clause in both SQL branches; add `LEFT JOIN` to non-FTS branch |
| `tests/test_repositories.py` | new `test_book_barcode_search` |
| `apps/librarian_management_app/adapters/librarian_admin_adapter.py` | `searchBooks` slot: `category_id: int = 0` param |
| `tests/test_adapters.py` | new `test_librarian_search_books_barcode_and_category` |
| `apps/librarian_management_app/qml/views/BookCatalogView.qml` | `catalogCategoryModel` + `catalogCategoryCombo`, placeholder, `Component.onCompleted` loader |
| `apps/librarian_management_app/qml/Main.qml` | `searchBooks` passes selected category with guard |
| `tests/test_ui_librarian.py` | new `test_catalog_barcode_and_category_filter`; structural objectName list |
| `wiki/apps/librarian-management-app.md`, `wiki/log.md` | doc updates (Task 4) |


## Task 1 — Repo: barcode condition in `search_books`

**Files:**
- Modify: `data/repositories/book_repo.py` (`search_books`, ~line 285)
- Test: `tests/test_repositories.py` (new function, uses existing `repo_db` fixture)

**Interfaces:**
- Produces: `book_repo.search_books(conn, query, category_id=None)` unchanged signature; now also matches `query` against normalized `book_copies.barcode`.
- Consumes: existing `book_copies(barcode)` table; `categories` table (column `category_id`).

**Steps:**

- [ ] Write the failing test — append to `tests/test_repositories.py`:

```python
def test_book_barcode_search(repo_db):
    import data.repositories.book_repo as book_repo
    cat_a = repo_db.execute("INSERT INTO categories (name) VALUES ('หมวด A')").lastrowid
    cat_b = repo_db.execute("INSERT INTO categories (name) VALUES ('หมวด B')").lastrowid
    book_a = book_repo.add_book(repo_db, title="ฟิสิกส์", author="จอห์น ดี", category_id=cat_a)
    book_repo.add_copies(repo_db, book_a, barcodes=["SCI-100", "SCI-101"])
    book_b = book_repo.add_book(repo_db, title="เคมีย์", category_id=cat_b)
    book_repo.add_copies(repo_db, book_b, barcodes=["SCI-102"])
    repo_db.commit()

    # exact barcode
    r = book_repo.search_books(repo_db, "SCI-100")
    assert r.ok and len(r.data) == 1 and r.data[0]["book_id"] == book_a

    # normalization: lowercase + dash-insensitive
    r = book_repo.search_books(repo_db, "sci100")
    assert r.ok and len(r.data) == 1 and r.data[0]["book_id"] == book_a

    # barcode + category filter compose (book_a is in cat A; filter cat B -> empty)
    r = book_repo.search_books(repo_db, "SCI-100", category_id=cat_b)
    assert r.ok and len(r.data) == 0

    # FTS branch regression: normal title search still works with new JOIN
    r = book_repo.search_books(repo_db, "ฟิสิกส์")
    assert r.ok and len(r.data) == 1 and r.data[0]["book_id"] == book_a
```

- [ ] Run it, expect failure (barcode query returns 0 rows): `.venv/bin/pytest tests/test_repositories.py::test_book_barcode_search -v`
- [ ] Implement — in `book_repo.search_books`:
  - FTS branch `WHERE`: append `OR REPLACE(LOWER(bc.barcode), '-', '') = ?` and append the normalized query value (`query.strip().lower().replace("-", "")`) to the existing params tuple.
  - Non-FTS branch: add `LEFT JOIN book_copies bc ON bc.book_id = b.book_id AND bc.status = 'active'` and append the same `OR` clause + param (keep the existing category `AND` condition; the new `OR` must be the last standalone condition so it binds correctly).
  - Add `# shortcut:` comment on the barcode branch: full scan of `book_copies`; upgrade to trigram index if ~10k+ copies.
- [ ] Run the new test → pass.
- [ ] Run full suite `.venv/bin/pytest tests/` → all pass.
- [ ] Commit to `dev`: `feat(repo): search_books matches barcode stickers`

## Task 2 — Adapter: `searchBooks` category param

**Files:**
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py` (`searchBooks` slot, ~line 107)
- Test: `tests/test_adapters.py` (new function, uses existing `librarian_adapter` fixture)

**Interfaces:**
- Produces: `LibrarianAdminAdapter.searchBooks(query: str = "", category_id: int = 0) -> str` (JSON `Result`). `category_id=0` (or falsy) → no category filter.
- Consumes: `catalog_service.search_books(conn, query, category_id=...)` — existing `catalog_service.search_books` already accepts `category_id` (verify exact name/param at implementation; if the service param is `None`-only, pass `category_id or None`).

**Steps:**

- [ ] Write the failing test — append to `tests/test_adapters.py`:

```python
def test_librarian_search_books_barcode_and_category(librarian_adapter):
    adapter, conn = librarian_adapter
    res = json.loads(adapter.addBook("ฟิสิกส์ ม.ปลาย", "", "ผุ้แต่ง", "", "1", "", "PHYS-01"))
    book_id = res["data"]["book_id"]
    cat_a = json.loads(adapter.addCategory("หมวดฟิสิกส์"))["data"]["category_id"]
    cat_b = json.loads(adapter.addCategory("หมวดคณิตศาสตร์"))["data"]["category_id"]
    conn.execute("UPDATE books SET category_id = ? WHERE book_id = ?", (cat_a, book_id))
    conn.commit()
    adapter.addBook("คณิตศาสตร์", "", "ผุ้แต่ง 2", "", str(cat_b), "", "MATH-01")

    # barcode search (default category_id=0)
    books = json.loads(adapter.searchBooks("PHYS-01"))
    assert any(b["book_id"] == book_id for b in books)

    # category filter only (empty query)
    books = json.loads(adapter.searchBooks("", cat_a))
    assert [b["book_id"] for b in books] == [book_id]

    # barcode + non-matching category -> empty
    books = json.loads(adapter.searchBooks("PHYS-01", cat_b))
    assert books == []
```

- [ ] Run it, expect failure (TypeError: unexpected arg `category_id`, or no category filter): `.venv/bin/pytest tests/test_adapters.py::test_librarian_search_books_barcode_and_category -v`
- [ ] Implement — `searchBooks` signature becomes `searchBooks(self, query: str = "", category_id: int = 0) -> str`; body passes `category_id=category_id if category_id else None` into the existing service/repo call it already makes.
- [ ] Run the new test → pass.
- [ ] Run full suite `.venv/bin/pytest tests/` → all pass (especially existing `test_librarian_add_and_search_book`, which calls `searchBooks(q)` with one arg).
- [ ] Commit to `dev`: `feat(adapter): searchBooks accepts category_id filter`


## Task 3 — QML: category combo + barcode-aware search field

**Files:**
- Modify: `apps/librarian_management_app/qml/views/BookCatalogView.qml` (Tab 0 row ~line 370-395; models block ~line 90)
- Modify: `apps/librarian_management_app/qml/Main.qml` (`searchBooks` function, ~line 451)
- Test: `tests/test_ui_librarian.py` (new function + structural objectName list ~line 354)

**Interfaces:**
- Consumes: `librarianAdmin.listCategories()` (existing, returns JSON list of `{category_id, name}`), `librarianAdmin.searchBooks(query: string, category_id: int)` (Task 2), `StyledComboBox` (shared, from `apps/common_qml/`).
- Produces: objectNames `catalogCategoryModel` (ListModel) and `catalogCategoryCombo` (StyledComboBox); `searchBooks(q, catId)` where absent/invalid `catId` → `0` (all categories).

**Steps:**

- [ ] Write the failing UI test — append to `tests/test_ui_librarian.py`:

```python
def test_catalog_barcode_and_category_filter(lib_ui):
    window, app = lib_ui["window"], lib_ui["app"]
    adapter = lib_ui["adapter"]
    cat_a = json.loads(adapter.addCategory("หมวดฟิสิกส์"))["data"]["category_id"]
    adapter.addBook("ฟิสิกส์ 101", "", "ผุ้แต่ง", "", str(cat_a), "", "FIS-01")
    cat_b = json.loads(adapter.addCategory("หมวดคณิศาสตร"))["data"]["category_id"]
    adapter.addBook("คณิศาสตร 101", "", "ผุ้แต่ง 2", "", str(cat_b), "", "MATH-01")
    process(app)

    combo = find(window, "catalogCategoryCombo")
    assert combo is not None
    model = find(window, "catalogModel")

    # 1) barcode sticker typed/scanned into the existing search field (all categories)
    find(window, "catalogSearchInput").setProperty("text", "SCI-01")
    invoke(window, "searchBooks")  # zero-arg legacy call path (Review Focus #1)
    process(app)
    assert model.property("count") >= 1

    # 2) category filter narrows to the single book in cat_a
    cat_model = find(window, "catalogCategoryModel")
    idx = next(i for i in range(cat_model.property("count"))
               if cat_model.get(i).get("category_id") == cat_a)
    combo.setProperty("currentIndex", idx)
    process(app)
    find(window, "catalogSearchInput").setProperty("text", "")
    invoke(window, "searchBooks")
    process(app)
    assert model.property("count") == 1
```

- Also update the structural objectName list in `test_ui_librarian.py` (~line 354) to include `"catalogCategoryCombo"` and `"catalogCategoryModel"`.
- [ ] Run it, expect failure (`catalogCategoryCombo` is None): `.venv/bin/pytest tests/test_ui_librarian.py::test_catalog_barcode_and_category_filter -v`
- [ ] Implement in `BookCatalogView.qml`:
  - Add `ListModel { id: catalogCategoryModel }` next to the other models (~line 90).
  - In the Tab 0 row, insert `StyledComboBox { id: catalogCategoryCombo; model: catalogCategoryModel }` between `catalogSearchInput` and the search `Button`. Layout via `Layout.fillWidth`/`Layout.preferredWidth` consistent with the row; no hardcoded heights.
  - Placeholder on `catalogSearchInput` → `placeholderText: "Search title, author, ISBN, or barcode"`.
  - `Component.onCompleted` on the Tab 0 container (or the view root), mirroring `BarcodeGeneratorView.reloadCategories()`:
    ```qml
    Component.onCompleted: {
        catalogCategoryModel.append({ "category_id": 0, "name": "-- All Categories --" })
        try {
            var cats = JSON.parse(librarianAdmin.listCategories())
            for (var i = 0; i < cats.length; i++) {
                catalogCategoryModel.append(cats[i])
            }
        } catch (e) {}
    }
    ```
  - Verify `StyledComboBox` satisfies the alignment rule (left-aligned, vertically centered content in button AND popup delegate — AGENTS rule 7); existing `tests/test_ui_text_and_dropdown_alignment.py` guards this. Only fix if that test fails.
- [ ] Implement in `Main.qml` — `searchBooks` becomes:
  ```qml
  function searchBooks(q, catId) {
      var c = (catId === undefined || catId === null) ? 0 : Number(catId)
      if (isNaN(c) || c < 0) c = 0
      // ...existing clear/JSON.parse logic, then:
      var raw = librarianAdmin.searchBooks(q, c)
      // ...existing row appends unchanged
  }
  ```
- [ ] Run the new UI test → pass.
- [ ] Run full suite `.venv/bin/pytest tests/` → all pass (guards: `test_catalog_search_filtering` zero-arg invocation, `test_qml_loads.py`, `test_ui_text_and_dropdown_alignment.py`, `test_repro_catalog_edge_cases.py`).
- [ ] Commit to `dev`: `feat(qml): catalog barcode search + category filter combo`


## Task 4 — Docs

**Files:**
- Modify: `wiki/apps/librarian-management-app.md` (catalog page section)
- Modify: `wiki/log.md` (append entry)

**Steps:**

- [ ] In `wiki/apps/librarian-management-app.md`: note that the catalog search field matches barcode stickers (normalized `LOWER`/dash-insensitive, `# shortcut` full-scan of `book_copies`), and that the category `StyledComboBox` (`catalogCategoryCombo`, option `-- ทุกหมวดหมู่ --`) filters results via `searchBooks(query, category_id)`.
- [ ] Append a `wiki/log.md` entry: date, one line — "Catalog search now matches barcode stickers; category filter combo added (shared StyledComboBox); spec + plan in docs/superpowers/."
- [ ] Run `.venv/bin/pytest tests/` (final gate) → all pass.
- [ ] Commit to `dev`: `docs: catalog barcode search + category filter`

## Execution Notes

- Branch: work on `dev` only (AGENTS rule 8).
- One commit per task; task order 1 → 4 (2 depends on 1's SQL, 3 depends on 2's signature).
- Verify exact current line numbers before editing — the plan's line references are approximate.
- If `catalog_service.search_books` has a different `category_id` param name, adapt the adapter call in Task 2 to match the real signature; the QML-visible contract (`searchBooks(string, int)`) does not change.

