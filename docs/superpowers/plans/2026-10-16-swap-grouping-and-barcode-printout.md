# Swap Book/Grouping Split View & Dedicated Barcode Printout Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the Librarian Management workflow so Page 6 combines Adding Books (left) with Grouping/Category Management (right) while automatically generating and saving new book barcodes into SQLite, and repurpose Page 7 (formerly Category Management) into the dedicated Barcode Printout Generator where staff can select specific books or print all saved barcodes to A4 PDF.

**Architecture:** Add `LibrarianAdminAdapter.getBooksWithBarcodes(query: str = "") -> str` backed by `book_repo.list_books_with_barcodes` to fetch active books with their persisted `book_copies.barcode` lists from SQLite. Update `apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml` (Page 6) into a 2-column split view: Left Card = Add Book / Add Copies form (which immediately generates and commits `SMTE-xxxxx-xx` barcodes to `book_copies` on save), Right Card = Category/Grouping Management (`categoryNameInput`, `btnAddCategory`, `categoryListView`, Edit/Delete actions) with live sync into `genCategoryCombo`. Repurpose `apps/librarian_management_app/qml/views/CategoryManagementView.qml` (Page 7) into the Barcode Printout Page where staff filter/select one or more books (or click Print All) to export their persisted barcodes via `librarianAdmin.exportLabelsPdf`.

**Tech Stack:** Python 3.10–3.15, PySide6 (Qt Quick / QML), SQLite3, pytest.

**Spec:** `wiki/apps/librarian-management-app.md`, `doc/book_barcode_generation.md`

## Global Constraints

- **Immediate DB Barcode Persistence on Book Save:** Adding a new book (`addBook`) or adding copies (`addCopies`) on the Left Card must immediately generate deterministic `SMTE-{book_id:05d}-{seq:02d}` barcodes and persist them into `book_copies` in SQLite.
- **Live Category Sync on Split Page:** Adding, renaming, or deleting a category on the Right Card (Grouping Management) must immediately refresh `genCategoryCombo` on the Left Card without leaving the page.
- **Print Selected vs. Print All:** The dedicated Barcode Printout page (Page 7) must allow selecting individual books via checkboxes to print only their barcodes (`exportSelectedBooksPdf`) OR printing all barcodes across all active books (`exportAllBooksPdf`).
- **QML `objectName` Continuity:** Preserve required `objectName` identifiers (`genBookTitle`, `genCopyCountInput`, `btnExecuteGenerate`, `genStatusMessage`, `categoryNameInput`, `btnAddCategory`, `categoryStatusText`, `categoryListView`, `categoryListModel`, `genBarcodesList`, `genBarcodesModel`, `btnExportPdfSheet`, `genPdfStatusText`) so existing and new UI tests can inspect every control deterministically.

## Review Focus

1. **Adding a book when `genCopyCountInput` is empty or invalid (`0` or non-numeric):** Must default to `1` copy so every newly added book always generates and persists at least `SMTE-{book_id:05d}-01` in `book_copies`.
2. **Creating, renaming, or deleting a category on the Right Card while filling out a new book on the Left Card:** Refreshing `genCategoryCombo` must preserve the user's typed `genBookTitle`, `genBookAuthor`, `genBookIsbn`, and `genShelfLocation` fields and select or reset the category index safely.
3. **Printing selected books when zero books are checked on the Barcode Printout Page:** Clicking `btnPrintSelectedPdf` with no book selected must display a clear Thai validation message in `genPdfStatusText` (`"✗ กรุณาเลือกหนังสืออย่างน้อย 1 รายการเพื่อพิมพ์บาร์โค้ด"`) instead of calling `exportLabelsPdf("[]", ...)`.
4. **Excluding retired/disposed copies from Print All / Print Selected barcode sheets:** `list_books_with_barcodes` must only include active printable copies (`bc.status NOT IN ('retired', 'disposed')`) so staff do not waste paper printing stickers for disposed books.
5. **Newly added book immediately appearing on the Barcode Printout Page:** Saving a book on Page 6 (`bookSaved()` signal) must refresh the Barcode Printout Page model (`loadPrintableBooks()`) so switching to Page 7 shows the new book and its saved barcodes immediately.

---

### Task 1: Backend Repository & Adapter Slot for Books with Persisted Barcodes

**Files:**
- Modify: `data/repositories/book_repo.py`
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py`
- Test: `tests/test_barcode_and_disposed.py`

**Interfaces:**
- Consumes: `books`, `book_copies`, `categories` tables in SQLite
- Produces:
  - `book_repo.list_books_with_barcodes(conn: sqlite3.Connection, query: str = "") -> List[Dict[str, Any]]` returning each active book with `book_id`, `title`, `author`, `isbn`, `category_name`, `total_copies`, `available_copies`, and `barcodes: List[str]` (active non-retired/non-disposed copy barcodes ordered by `copy_id ASC`)
  - `LibrarianAdminAdapter.getBooksWithBarcodes(self, query: str = "") -> str` (`@Slot(str, result=str)` and `@Slot(result=str)`)

- [ ] **Step 1: Write the failing test in `tests/test_barcode_and_disposed.py`**

```python
def test_get_books_with_barcodes_returns_saved_active_barcodes(conn):
    adapter = LibrarianAdminAdapter(conn)
    res1 = json.loads(adapter.addBook(title="ดาราศาสตร์ ม.3", author="อ.วิชัย", barcodes_csv="2"))
    assert res1["ok"] is True
    b1_id = res1["data"]["book_id"]

    # Mark second copy disposed — only active copy should be listed for printing
    copies = book_repo.get_copies_for_book(conn, b1_id)
    adapter.markCopy(copies[1]["copy_id"], "disposed", "ชำรุด")

    books = json.loads(adapter.getBooksWithBarcodes(""))
    assert len(books) == 1
    assert books[0]["book_id"] == b1_id
    assert books[0]["barcodes"] == [f"SMTE-{b1_id:05d}-01"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_barcode_and_disposed.py::test_get_books_with_barcodes_returns_saved_active_barcodes -v`
Expected: FAIL with `AttributeError: 'LibrarianAdminAdapter' object has no attribute 'getBooksWithBarcodes'`

- [ ] **Step 3: Implement `list_books_with_barcodes` in `data/repositories/book_repo.py` and `getBooksWithBarcodes` in `LibrarianAdminAdapter`**

In `data/repositories/book_repo.py`:
- Query active books via `search_books(conn, query=query, limit=500, offset=0)` and attach `"barcodes": [r["barcode"] for r in conn.execute("SELECT barcode FROM book_copies WHERE book_id = ? AND status NOT IN ('retired', 'disposed') ORDER BY copy_id ASC", (b["book_id"],)).fetchall()]`.
In `apps/librarian_management_app/adapters/librarian_admin_adapter.py`:
- Add `@Slot(str, result=str)` / `@Slot(result=str)` `def getBooksWithBarcodes(self, query: str = "") -> str:` returning `json.dumps(_sanitize_for_qml(rows))`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_barcode_and_disposed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/repositories/book_repo.py apps/librarian_management_app/adapters/librarian_admin_adapter.py tests/test_barcode_and_disposed.py
git commit -m "feat(library): add getBooksWithBarcodes slot for barcode printout selection"
```

---

### Task 2: Split Page 6 into Add Book (Left) + Grouping Management (Right) with Auto-Saved DB Barcodes

**Files:**
- Modify: `apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml`
- Modify: `apps/librarian_management_app/qml/Main.qml`
- Test: `tests/test_ui_librarian.py`

**Interfaces:**
- Consumes: `librarianAdmin.addBook`, `librarianAdmin.addCopies`, `librarianAdmin.listCategories`, `librarianAdmin.addCategory`, `editCategoryRequested(int catId, string catName)`, `deleteCategoryRequested(int catId, string catName)`
- Produces:
  - Left Card in `BarcodeGeneratorView.qml`: New Book / Add Copies form (`genBookTitle`, `genBookAuthor`, `genBookIsbn`, `genCategoryCombo`, `genShelfLocation`, `genExistingBookCombo`, `genCopyCountInput`, `btnExecuteGenerate`, `genStatusMessage`) that commits new books and their generated `SMTE-xxxxx-xx` barcodes directly to SQLite.
  - Right Card in `BarcodeGeneratorView.qml`: Grouping / Category Management (`categoryNameInput`, `btnAddCategory`, `categoryStatusText`, `categoryListView`, `categoryListModel`) with `loadCategoriesList()` and `addNewCategory()`, automatically refreshing `genCategoryCombo` on any category change.

- [ ] **Step 1: Write the failing UI test in `tests/test_ui_librarian.py`**

```python
def test_book_and_grouping_split_page_saves_barcodes_and_manages_categories(lib_ui):
    window = lib_ui["window"]
    find(window, "navBtnGenerator").clicked.emit()
    process(lib_ui["app"])

    # Right side: add category and verify Left side genCategoryModel updates immediately
    cat_input = find(window, "categoryNameInput")
    add_cat_btn = find(window, "btnAddCategory")
    cat_input.setProperty("text", "หมวดคอมพิวเตอร์")
    add_cat_btn.clicked.emit()
    process(lib_ui["app"])
    assert find(window, "categoryListModel").property("count") >= 1
    assert find(window, "genCategoryModel").property("count") >= 2

    # Left side: add book and verify barcodes are generated and saved in database
    find(window, "genBookTitle").setProperty("text", "Python เบื้องต้น")
    find(window, "genCopyCountInput").setProperty("text", "3")
    find(window, "btnExecuteGenerate").clicked.emit()
    process(lib_ui["app"])

    assert "✓" in find(window, "genStatusMessage").property("text")
    books = json.loads(lib_ui["adapter"].getBooksWithBarcodes("Python"))
    assert len(books) == 1
    assert len(books[0]["barcodes"]) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_librarian.py::test_book_and_grouping_split_page_saves_barcodes_and_manages_categories -v`
Expected: FAIL

- [ ] **Step 3: Update `BarcodeGeneratorView.qml` right column to Grouping Management and wire signals in `Main.qml`**

In `apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml`:
- Keep Left Card (`genBookTitle`, `genBookAuthor`, `genBookIsbn`, `genCategoryCombo`, `genShelfLocation`, `genExistingBookCombo`, `genCopyCountInput`, `btnExecuteGenerate`, `genStatusMessage`).
- Replace Right Card with Grouping / Category Management (`categoryNameInput`, `btnAddCategory`, `categoryStatusText`, `categoryListView`, `categoryListModel`, `editCategoryRequested`, `deleteCategoryRequested`).
- When `addNewCategory()` succeeds (or `initGeneratorPage()` runs), reload both `categoryListModel` and `genCategoryModel` while preserving the current form inputs.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_librarian.py -k "grouping_split_page or category" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml apps/librarian_management_app/qml/Main.qml tests/test_ui_librarian.py
git commit -m "feat(librarian_ui): combine book creation and grouping management in split view"
```

---

### Task 3: Repurpose Page 7 (`CategoryManagementView.qml`) into Dedicated Barcode Printout Generator (Select Books or Print All)

**Files:**
- Modify: `apps/librarian_management_app/qml/views/CategoryManagementView.qml`
- Modify: `apps/librarian_management_app/qml/Main.qml`
- Modify: `wiki/apps/librarian-management-app.md`
- Modify: `wiki/log.md`
- Test: `tests/test_ui_librarian.py`

**Interfaces:**
- Consumes: `librarianAdmin.getBooksWithBarcodes(query)`, `librarianAdmin.exportLabelsPdf(barcodes_json, output_path)`
- Produces:
  - Dedicated Barcode Printout Page on Page 7 (`stackLayout` index 7, `navBtnCategories`) with:
    - Search bar (`barcodePrintSearchInput`)
    - Book & barcode list (`genBarcodesList`, `genBarcodesModel`) showing each book's title, copy count, persisted barcode range (`SMTE-00001-01 .. SMTE-00001-03`), and selection checkbox (`selected: true/false`)
    - `"☑️ เลือกทั้งหมด / ยกเลิก"` (`btnSelectAllBooks`)
    - `"📄 พิมพ์เฉพาะหนังสือที่เลือก (PDF A4)"` (`btnPrintSelectedPdf`, calling `exportSelectedBooksPdf()`)
    - `"🖨️ พิมพ์บาร์โค้ดทั้งหมด (PDF A4)"` (`btnExportPdfSheet`, calling `exportGenPdf()` / `exportAllBooksPdf()`)
    - Status banner (`genPdfStatusText`) and open-file button

- [ ] **Step 1: Write the failing UI test in `tests/test_ui_librarian.py`**

```python
def test_barcode_printout_page_select_book_and_print_all(lib_ui):
    window = lib_ui["window"]
    # Add a second book so we can test printing selected vs printing all
    lib_ui["adapter"].addBook("เคมีอินทรีย์", "", "ดร.สมศรี", "", "", "", "2")

    # Navigate to Page 7 (Barcode Printout page)
    find(window, "navBtnCategories").clicked.emit()
    process(lib_ui["app"])

    model = find(window, "genBarcodesModel")
    assert model.property("count") >= 2

    # 1. Print Selected (select only first book)
    invoke(window, "deselectAllPrintableBooks")
    invoke(window, "setPrintableBookSelected", Q_ARG("QVariant", 0), Q_ARG("QVariant", True))
    find(window, "btnPrintSelectedPdf").clicked.emit()
    process(lib_ui["app"])
    assert "✓" in find(window, "genPdfStatusText").property("text")

    # 2. Print All
    find(window, "btnExportPdfSheet").clicked.emit()
    process(lib_ui["app"])
    assert "✓" in find(window, "genPdfStatusText").property("text")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_librarian.py::test_barcode_printout_page_select_book_and_print_all -v`
Expected: FAIL

- [ ] **Step 3: Implement Barcode Printout UI in `CategoryManagementView.qml` and wire in `Main.qml`**

In `apps/librarian_management_app/qml/views/CategoryManagementView.qml`:
- Load books and their persisted database barcodes via `librarianAdmin.getBooksWithBarcodes(barcodePrintSearchInput.text)`.
- Populate `genBarcodesModel` with `{ book_id, title, author, total_copies, barcodes_json, barcode_preview, barcode, selected: true }`.
- Implement `exportSelectedBooksPdf()` (collects barcodes from rows where `selected === true`; if empty, sets `genPdfStatusText.text = "✗ กรุณาเลือกหนังสืออย่างน้อย 1 รายการเพื่อพิมพ์บาร์โค้ด"`) and `exportGenPdf()` / `exportAllBooksPdf()` (collects barcodes from all rows in `genBarcodesModel` and calls `librarianAdmin.exportLabelsPdf`).
- Update `Main.qml` aliases and sidebar button labels (`navBtnGenerator`: `"📚 เพิ่มหนังสือ / หมวดหมู่"`, `navBtnCategories`: `"🏷️ พิมพ์สติกเกอร์บาร์โค้ด"`), and update existing UI tests in `tests/test_ui_librarian.py` (`test_barcode_generator_page_preview_and_save`, `test_category_management_screen`) to match the new page locations.
- Update `wiki/apps/librarian-management-app.md` and `wiki/log.md`.

- [ ] **Step 4: Run full UI and unit test suites**

Run: `pytest tests/test_ui_librarian.py tests/test_barcode_and_disposed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/librarian_management_app/ tests/test_ui_librarian.py wiki/ docs/superpowers/plans/2026-10-16-swap-grouping-and-barcode-printout.md
git commit -m "feat(librarian_ui): swap grouping to add-book split view and add selectable barcode printout page"
```
