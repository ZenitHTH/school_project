# Book Entry Live Inventory Grid & Dedicated Barcode Print Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Book Entry page (`BarcodeGeneratorView.qml`) so the left pane handles book entry/management while the right pane displays bordered grid panels for (1) the book currently being entered with live barcode preview and (2) the current books in inventory, and enhance the dedicated Barcode Print page (`CategoryManagementView.qml`) for selecting books and printing A4 barcode sheets.

**Architecture:** Preserve the 2-column split layout in `BarcodeGeneratorView.qml` (Tab 6) while replacing the right pane with a structured, grid-bordered split panel containing a live incoming book preview card (`incomingBookPreviewCard` + `incomingBarcodesModel` powered by `librarianAdmin.previewBarcodes`) and a bordered inventory table (`inventoryGridTable` + `inventoryBooksModel` with inline edit/delete/+copies actions and compact category bar). Upgrade `CategoryManagementView.qml` (Tab 7) into a dedicated Barcode Print Studio with category filtering, selection summary metrics (selected books, total stickers, A4 page count), and direct navigation from both Catalog and Book Entry views.

**Tech Stack:** Python 3.14, PySide6 (QtQuick 2.15, QtQuick.Controls 2.15, QtQuick.Layouts 1.15), SQLite3, pytest.

**Spec:** User request (2026-10-29) & `wiki/apps/librarian-management-app.md`

## Global Constraints

- Maintain Clean Code rules: Python functions <= 20 lines, max 3 arguments, <= 2 indentation levels, files < 200 lines where applicable or split into modular QML components.
- Preserve all existing `objectName` aliases in `Main.qml`, `BarcodeGeneratorView.qml`, and `CategoryManagementView.qml` so existing 211 pytest tests continue to pass without regression.
- All database dictionary returns to QML must pass through `_sanitize_for_qml`.
- Run headless UI tests with `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_ui_librarian.py -v`.

## Review Focus

- Empty title / zero copy count in left form: live incoming preview must gracefully show placeholder state (`"กำลังรอการกรอกข้อมูลหนังสือ..."`) while still previewing next deterministic `SMTE-xxxxx-01` barcode.
- Switching between Mode 0 (New Book) and Mode 1 (Add Copies to Existing Book): live incoming preview must immediately switch from new book fields to the selected existing book's metadata and next sequence barcodes (`start_seq = count_copies_ever + 1`).
- Saving a book on the left pane: must immediately refresh the right-side "หนังสือที่อยู่ในคลังตอนนี้" (`inventoryBooksModel`) AND update the live incoming preview to reflect the newly saved state.
- Selecting/deselecting books and filtering by category on the Dedicated Barcode Print page: total selected book count, sticker count, and A4 sheet estimate (`ceil(stickers / 24)`) must stay accurate even when search/category filters change.
- Packaging spec inclusion: any new modular QML component in `apps/librarian_management_app/qml/views/` is automatically bundled via `('../apps/librarian_management_app/qml/views/*.qml', ...)` in `packaging/librarian_management.spec`.

---

### Task 1: Live Incoming Book Preview & Bordered Inventory Grid on Book Entry Page (`BarcodeGeneratorView.qml`)

**Files:**
- Create: `apps/librarian_management_app/qml/views/BookInventoryRightPane.qml`
- Modify: `apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml`
- Modify: `apps/librarian_management_app/qml/Main.qml`
- Test: `tests/test_ui_librarian.py`

**Interfaces:**
- Consumes:
  - `librarianAdmin.previewBarcodes(book_id: int, count: int) -> str` (JSON `{"ok": true, "target_book_id": int, "barcodes": [str]}`)
  - `librarianAdmin.searchBooks(query: str) -> str` (JSON list of book dicts)
- Produces (QML `objectName`s & functions on `BarcodeGeneratorView` / `Main.qml`):
  - `incomingBookPreviewCard` (`Rectangle`): bordered grid showing live book being entered (`incomingTitleText`, `incomingMetaText`, `incomingCopyCountText`, `incomingBarcodePreviewText`, `incomingBarcodesModel`).
  - `inventoryBooksList` (`ListView`) and `inventoryBooksModel` (`ListModel`): bordered table of books currently in stock with columns for ID, Title/Author, Category, Shelf, Copies, and action buttons (`+ เพิ่มเล่ม`, `✏️`, `🗑️`).
  - `btnGoToPrintPage` (`Button`): navigates directly from Book Entry (Tab 6) to Dedicated Barcode Print page (Tab 7).
  - `updateGenPreview()`: updates `incomingBookPreviewCard` and `incomingBarcodesModel` whenever left-side form inputs (`genBookTitle`, `genBookAuthor`, `genBookIsbn`, `genCategoryCombo`, `genShelfLocation`, `genCopyCountInput`, `genExistingBookCombo`, `currentGenMode`) change.

- [ ] **Step 1: Write the failing test in `tests/test_ui_librarian.py`**

```python
def test_book_entry_page_shows_live_incoming_preview_and_current_inventory_grid(lib_ui):
    window = lib_ui["window"]
    stack = find(window, "librarianStack")

    # Open Book Entry & Management page (Tab 6)
    find(window, "navBtnGenerator").clicked.emit()
    process(lib_ui["app"])
    assert stack.property("currentIndex") == 6

    # Verify right-side current inventory grid displays existing seeded book(s)
    inv_model = find(window, "inventoryBooksModel")
    assert inv_model is not None
    initial_inv_count = inv_model.property("count")
    assert initial_inv_count >= 1

    # Type new book on the left -> verify right-side incoming preview updates live
    find(window, "genBookTitle").setProperty("text", "ดาราศาสตร์และอวกาศ ม.ปลาย")
    find(window, "genBookAuthor").setProperty("text", "ดร.เอกภพ")
    find(window, "genBookIsbn").setProperty("text", "978-616-111-222-3")
    find(window, "genShelfLocation").setProperty("text", "A-09")
    find(window, "genCopyCountInput").setProperty("text", "3")
    process(lib_ui["app"])

    inc_title = find(window, "incomingTitleText")
    inc_barcodes = find(window, "incomingBarcodePreviewText")
    assert inc_title is not None
    assert "ดาราศาสตร์และอวกาศ ม.ปลาย" in inc_title.property("text")
    assert "SMTE-" in inc_barcodes.property("text")
    assert "-01" in inc_barcodes.property("text")
    assert "-03" in inc_barcodes.property("text")

    # Save book -> verify it immediately appears in right-side current inventory grid
    find(window, "btnExecuteGenerate").clicked.emit()
    process(lib_ui["app"])
    assert inv_model.property("count") == initial_inv_count + 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_ui_librarian.py::test_book_entry_page_shows_live_incoming_preview_and_current_inventory_grid -v`
Expected: FAIL with `AssertionError: assert None is not None` (`inventoryBooksModel` not found).

- [ ] **Step 3: Implement `BookInventoryRightPane.qml` and wire into `BarcodeGeneratorView.qml` & `Main.qml`**

Create `apps/librarian_management_app/qml/views/BookInventoryRightPane.qml` with:
1. **Top Bordered Table Box ("📥 หนังสือที่กำลังใส่เข้ามา — ข้อมูลจำลองก่อนบันทึก")**:
   - Grid table with bordered cells (`#cbd5e1` grid lines, `#f0f9ff` header accent) displaying:
     - ชื่อหนังสือ (`incomingTitleText`), ผู้แต่ง & ISBN (`incomingMetaText`), หมวดหมู่ & ชั้นวาง (`incomingLocationText`), จำนวนเล่ม (`incomingCopyCountText`), and รหัสบาร์โค้ดที่จะได้รับ (`incomingBarcodePreviewText`).
2. **Middle Bordered Table Box ("🏛️ หนังสือที่อยู่ในคลังตอนนี้ — คลังหนังสือปัจจุบัน")**:
   - Search filter bar (`inventorySearchInput`) + total books & copies counter badge.
   - Grid-bordered table header (`รหัส | ชื่อหนังสือ / ผู้แต่ง | หมวดหมู่ | ชั้นวาง | จำนวนเล่ม | จัดการ`) and `ListView` (`inventoryBooksList` / `inventoryBooksModel`) with cell borders (`Rectangle { width: 1; color: "#e2e8f0" }`) and quick action buttons (`+เล่ม`, `✏️`, `🗑️`).
3. **Bottom Compact Category Strip ("📁 จัดการหมวดหมู่หนังสือ")**:
   - Preserves `categoryNameInput`, `btnAddCategory`, `categoryStatusText`, `categoryListView`, and `categoryListModel` so librarians can still add/rename/delete categories on the same screen.

In `BarcodeGeneratorView.qml`:
- Wire `onTextChanged` / `onCurrentIndexChanged` of `genBookTitle`, `genBookAuthor`, `genBookIsbn`, `genCategoryCombo`, `genShelfLocation`, `genCopyCountInput`, `genExistingBookCombo`, and `onCurrentGenModeChanged` to `updateGenPreview()`.
- In `updateGenPreview()`, call `librarianAdmin.previewBarcodes(targetBookId, count)` and populate `incomingTitleText`, `incomingMetaText`, `incomingBarcodePreviewText`, and `incomingBarcodesModel`.
- In `initGeneratorPage()` and after `executeGenerateAndSave()`, call `loadInventoryGrid()` to refresh `inventoryBooksModel`.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_ui_librarian.py -v`
Expected: PASS (all existing + new UI tests pass).

- [ ] **Step 5: Commit**

```bash
git add apps/librarian_management_app/qml/views/BookInventoryRightPane.qml apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml apps/librarian_management_app/qml/Main.qml tests/test_ui_librarian.py
git commit -m "feat(librarian-ui): add live incoming book preview and bordered inventory grid on book entry page"
```

---

### Task 2: Dedicated Barcode Selection & Print Studio (`CategoryManagementView.qml`)

**Files:**
- Modify: `apps/librarian_management_app/qml/views/CategoryManagementView.qml`
- Modify: `apps/librarian_management_app/qml/views/BookCatalogView.qml`
- Modify: `apps/librarian_management_app/qml/Main.qml`
- Test: `tests/test_ui_librarian.py`

**Interfaces:**
- Consumes:
  - `librarianAdmin.getBooksWithBarcodes(query: str) -> str`
  - `librarianAdmin.listCategories() -> str`
  - `librarianAdmin.exportLabelsPdf(barcodes_json: str, output_path: str) -> str`
- Produces:
  - `barcodeCategoryFilterCombo` (`ComboBox`) & `barcodeCategoryFilterModel` (`ListModel`): filter printable books by category.
  - `selectedBooksCountText` (`Text`), `selectedStickersCountText` (`Text`), `estimatedPagesText` (`Text`): live print queue summary metrics (`24 ดวง/แผ่น A4`).
  - `btnGoToPrintPage` on `BarcodeGeneratorView.qml` and `btnOpenPrintPage` on `BookCatalogView.qml` to jump directly to Tab 7 (`categoryScreen`).
  - Bordered grid table on `CategoryManagementView.qml` (`เลือก | รหัส | ชื่อหนังสือ / ผู้แต่ง | หมวดหมู่ | จำนวนดวง | รหัสบาร์โค้ดประจำเล่ม | จัดการ`) where clicking a row or checkbox toggles selection for printing.

- [ ] **Step 1: Write the failing test in `tests/test_ui_librarian.py`**

```python
def test_dedicated_barcode_print_page_selection_metrics_and_navigation(lib_ui):
    window = lib_ui["window"]
    stack = find(window, "librarianStack")

    # Add two books in different categories
    cat_res = json.loads(lib_ui["adapter"].addCategory("วิทยาศาสตร์"))
    cat_id = str(cat_res["data"]["category_id"])
    lib_ui["adapter"].addBook("ฟิสิกส์นิวเคลียร์", "978111", "อ.สมชาย", "", cat_id, "S-1", "3")
    lib_ui["adapter"].addBook("ประวัติศาสตร์ไทย", "978222", "อ.สมหญิง", "", "", "H-1", "2")

    # Navigate from Book Entry page (Tab 6) to Dedicated Print page (Tab 7) via btnGoToPrintPage
    find(window, "navBtnGenerator").clicked.emit()
    process(lib_ui["app"])
    go_print_btn = find(window, "btnGoToPrintPage")
    assert go_print_btn is not None
    go_print_btn.clicked.emit()
    process(lib_ui["app"])
    assert stack.property("currentIndex") == 7

    # Verify live selection metrics (books selected & total barcode stickers)
    stickers_text = find(window, "selectedStickersCountText")
    assert stickers_text is not None
    assert "ดวง" in stickers_text.property("text")

    # Deselect all -> 0 stickers selected
    invoke(window, "deselectAllPrintableBooks")
    process(lib_ui["app"])
    assert "0" in stickers_text.property("text")

    # Select first book -> sticker count updates to match first book's copy_count
    invoke(window, "setPrintableBookSelected", Q_ARG("QVariant", 0), Q_ARG("QVariant", True))
    process(lib_ui["app"])
    row0_copies = find(window, "genBarcodesModel").get(0).property("copy_count").toInt()
    assert str(row0_copies) in stickers_text.property("text")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_ui_librarian.py::test_dedicated_barcode_print_page_selection_metrics_and_navigation -v`
Expected: FAIL with `AssertionError: assert None is not None` (`btnGoToPrintPage` / `selectedStickersCountText` not found).

- [ ] **Step 3: Implement enhanced Dedicated Barcode Print Studio in `CategoryManagementView.qml` and navigation hooks**

In `CategoryManagementView.qml`:
- Add `selectedBooksCount` and `selectedStickersCount` computed/updated properties via `recalculateSelectionStats()` called on load and selection change.
- Add summary metric badges (`selectedBooksCountText`, `selectedStickersCountText`, `estimatedPagesText`) showing:
  - จำนวนหนังสือที่เลือก (`X เรื่อง`)
  - จำนวนสติกเกอร์บาร์โค้ด (`Y ดวง`)
  - จำนวนกระดาษ A4 (`Math.ceil(Y / 24) แผ่น (3x8 ดวง/แผ่น)`)
- Add Category filter `ComboBox` (`barcodeCategoryFilterCombo`) alongside `barcodePrintSearchInput`.
- Upgrade the book list into a structured bordered table with clickable row selection, clear monospace barcode tags, and `+ เพิ่มเล่ม` button.
- Add `btnGoToPrintPage` in `BarcodeGeneratorView.qml` and `btnOpenPrintPage` in `BookCatalogView.qml` connected to navigate to `stackLayout.currentIndex = 7` and call `categoryView.loadPrintableBooks()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_ui_librarian.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/librarian_management_app/qml/views/CategoryManagementView.qml apps/librarian_management_app/qml/views/BookCatalogView.qml apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml apps/librarian_management_app/qml/Main.qml tests/test_ui_librarian.py
git commit -m "feat(librarian-ui): enhance dedicated barcode print studio with selection metrics and grid table"
```

---

### Task 3: Full Suite Verification & Wiki Documentation Update

**Files:**
- Modify: `wiki/apps/librarian-management-app.md`
- Modify: `wiki/log.md`

**Interfaces:**
- Consumes: Completed Tasks 1 & 2
- Produces: Updated architecture documentation and 100% passing test suite.

- [ ] **Step 1: Run full pytest suite with ResourceWarning error gate**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -W error::ResourceWarning -v`
Expected: 213+ passed, 0 warnings, 0 errors.

- [ ] **Step 2: Update `wiki/apps/librarian-management-app.md` and `wiki/log.md`**

Document `BookInventoryRightPane.qml` (live incoming book preview + bordered inventory grid) on Tab 6 and the enhanced Barcode Print Studio on Tab 7.

- [ ] **Step 3: Commit**

```bash
git add wiki/apps/librarian-management-app.md wiki/log.md docs/superpowers/plans/2026-10-29-book-entry-inventory-and-barcode-print-pages.md
git commit -m "docs(wiki): document live book entry preview grid and dedicated barcode print studio"
```
