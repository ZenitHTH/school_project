# Fix Barcode Printout Multi-Copy Export & Locked Code128 Row UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the Librarian Management UI so books with multiple copies (e.g. 5 copies) reliably register/update all copy barcodes (`SMTE-xxxxx-01` .. `SMTE-xxxxx-05`), export all 5 barcodes to the A4 PDF sheet (instead of only 1 `SMTE-00001-01` barcode), and replace the locked-looking grey `Code128` row text on the Barcode Printout page with interactive copy controls.

**Architecture:** Fix QML state/layout bugs in `BarcodeGeneratorView.qml` (Page 6), `BookActionDialogs.qml`, and `BookCatalogView.qml` (Page 0) that prevented adding/updating copies to 5 (`genExistingBookCombo` resetting `currentIndex` to `-1` and collapsing to 16px height, `+5` button adding `1+5=6`, `editBookDialog` lacking a total-copies field, and dialogs not refreshing `loadPrintableBooks`). Update `CategoryManagementView.qml` (Page 7) to remove the static grey `"Code128"` text on each row, display all copy barcodes clearly, provide a direct `+ เพิ่มเล่ม` action per row, and verify that PDF exports contain every barcode of a 5-copy book.

**Tech Stack:** Python 3.14, PySide6 (Qt Quick / QML), SQLite3, pytest

**Spec:** `doc/book_barcode_generation.md`

## Global Constraints

- Barcodes follow `{PREFIX}-{book_id:05d}-{copy_seq:02d}` with `PREFIX = "SMTE"` (`doc/book_barcode_generation.md` §2).
- `copy_seq` increments from `book_repo.count_copies_ever(conn, book_id) + 1` and is never reused (`doc/book_barcode_generation.md` §3).
- Label sheets export to A4 3×8 PDF via `core.library.services.label_service.export_label_sheet_pdf` (`doc/book_barcode_generation.md` §8).
- Sanitize all database dicts via `_sanitize_for_qml` before JSON serialization (`AGENTS.md` §3.2).
- Maintain 100% pytest pass rate across `tests/` and update `wiki/` + `wiki/log.md` (`AGENTS.md` §3.5, §4).

## Review Focus

- Switching to Mode 1 (`➕ เพิ่มเล่มหนังสือเดิม`) on Page 6 after adding a book must auto-select the first book (`currentIndex = 0`) instead of leaving `genExistingBookCombo.currentIndex` at `-1` with empty `displayText`.
- Clicking `+5` when `genCopyCountInput` is at default `"1"` must set `"5"` (not `"6"`), and re-saving the same title/ISBN in Mode 0 with a higher copy count (`5` when `1` exists) must top up the existing book's copies to `5` instead of leaving 1 copy or creating a duplicate title.
- Editing a book via `✏️ แก้ไข` (`editBookDialog`) and increasing total copies from `1` to `5` must generate the 4 additional barcodes (`-02` .. `-05`) and refresh Page 7 (`loadPrintableBooks`) immediately.
- Adding copies from Catalog (`+ เพิ่มเล่ม`) or from Page 7 (`🏷️ พิมพ์สติกเกอร์บาร์โค้ด`) must refresh `genBarcodesModel` so exporting PDF immediately after produces all 5 barcodes (`SMTE-xxxxx-01` .. `SMTE-xxxxx-05`) in the PDF file.
- Every `ComboBox` (`genCategoryCombo`, `genExistingBookCombo`, `editBookCategoryCombo`) and `ScrollView` form on Page 6 must have explicit `implicitHeight: 36` and `availableWidth` binding so controls never collapse to 16px height or 254px width.

---

### Task 1: Fix Multi-Copy Registration, Existing-Book ComboBox, and Edit/Add-Copies Sync

**Files:**
- Modify: `apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml:101-425`
- Modify: `apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml:38-353`
- Modify: `apps/librarian_management_app/qml/views/BookCatalogView.qml:18-95`
- Modify: `apps/librarian_management_app/qml/Main.qml:97-116,293-302,556-625`
- Test: `tests/test_ui_librarian.py`

**Interfaces:**
- Consumes: `LibrarianAdminAdapter.addBook(...) -> str`, `LibrarianAdminAdapter.addCopies(book_id: int, copies_or_barcodes: Any) -> str`, `LibrarianAdminAdapter.getBooksWithBarcodes(query: str = "") -> str`
- Produces:
  - `BarcodeGeneratorView.loadBooksForExistingSelector()` sets `genExistingBookCombo.currentIndex = 0` (or preserves selected `book_id`) when `genExistingBooksModel.count > 0`
  - `BarcodeGeneratorView.executeGenerateAndSave()` tops up copies if the same active book (`title` + `isbn`) already exists with fewer copies, or creates a new book with `count` copies
  - `BookActionDialogs.openEditBookDialog(bookId, title, author, isbn, categoryId, shelf, totalCopies)` & `editBookCopiesInput` (`objectName: "editBookCopiesInput"`)
  - `Main.qml` `openAddCopiesDialog(bookId, title)` forwarding function

- [ ] **Step 1: Write failing tests in `tests/test_ui_librarian.py` for Mode 1 auto-selection, `+5` / top-up to 5 copies, and `editBookDialog` copy count increase**

```python
def test_existing_book_selector_auto_selects_and_adds_copies_to_five(lib_ui):
    window = lib_ui["window"]
    find(window, "navBtnGenerator").clicked.emit()
    process(lib_ui["app"])

    # 1. Add book with 1 copy initially
    find(window, "genBookTitle").setProperty("text", "หัวใจคณิตศาสตร์ ม.ต้น")
    find(window, "genBookIsbn").setProperty("text", "9786164408500")
    find(window, "genBookAuthor").setProperty("text", "ณัฐอุดมพาณิชย์")
    find(window, "genCopyCountInput").setProperty("text", "1")
    find(window, "btnExecuteGenerate").clicked.emit()
    process(lib_ui["app"])

    # 2. Switch to Mode 1 (Add Copies to Existing) -> combo must auto-select (>= 0), height >= 32
    find(window, "btnModeAddCopies").clicked.emit()
    process(lib_ui["app"])
    combo = find(window, "genExistingBookCombo")
    assert combo.property("currentIndex") >= 0
    assert combo.property("displayText") != ""
    assert combo.property("height") >= 32

    # 3. Select the newly added book and add 4 copies -> total 5 barcodes in PDF
    model = find(window, "genExistingBooksModel")
    target_idx = 0
    for i in range(model.property("count")):
        if model.get(i).property("title").toString() == "หัวใจคณิตศาสตร์ ม.ต้น":
            target_idx = i
            break
    combo.setProperty("currentIndex", target_idx)
    find(window, "genCopyCountInput").setProperty("text", "4")
    find(window, "btnExecuteGenerate").clicked.emit()
    process(lib_ui["app"])

    books = json.loads(lib_ui["adapter"].getBooksWithBarcodes("หัวใจคณิตศาสตร์"))
    assert len(books) == 1
    assert len(books[0]["barcodes"]) == 5
    assert books[0]["barcodes"][0].endswith("-01")
    assert books[0]["barcodes"][4].endswith("-05")


def test_edit_book_dialog_increases_total_copies_and_syncs_printout(lib_ui):
    window = lib_ui["window"]
    res = json.loads(lib_ui["adapter"].addBook("ฟิสิกส์ ม.ต้น", "9786160001112", "อ.นิวตัน", "", "", "B-1", "1"))
    book_id = res["data"]["book_id"]

    invoke(
        window,
        "openEditBookDialog",
        Q_ARG("QVariant", book_id),
        Q_ARG("QVariant", "ฟิสิกส์ ม.ต้น"),
        Q_ARG("QVariant", "อ.นิวตัน"),
        Q_ARG("QVariant", "9786160001112"),
        Q_ARG("QVariant", 0),
        Q_ARG("QVariant", "B-1"),
        Q_ARG("QVariant", 1),
    )
    process(lib_ui["app"])

    copies_input = find(window, "editBookCopiesInput")
    assert copies_input is not None
    assert copies_input.property("text") == "1"
    copies_input.setProperty("text", "5")
    invoke(window, "submitEditBook")
    process(lib_ui["app"])

    books = json.loads(lib_ui["adapter"].getBooksWithBarcodes("ฟิสิกส์ ม.ต้น"))
    assert len(books) == 1
    assert len(books[0]["barcodes"]) == 5
```

- [ ] **Step 2: Run pytest to verify the new tests fail**

Run: `.venv/bin/pytest tests/test_ui_librarian.py -k "test_existing_book_selector_auto_selects_and_adds_copies_to_five or test_edit_book_dialog_increases_total_copies_and_syncs_printout" -v`
Expected: FAIL (`combo.property("currentIndex") == -1` and `editBookCopiesInput is None`).

- [ ] **Step 3: Update `BarcodeGeneratorView.qml`, `BookActionDialogs.qml`, `BookCatalogView.qml`, and `Main.qml`**

In `apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml`:
- Give `ScrollView` `id: leftFormScroll` and set child `ColumnLayout { width: leftFormScroll.availableWidth; spacing: 12 }`.
- Give `genCategoryCombo` and `genExistingBookCombo` `implicitHeight: 36` and a right-aligned `▼` indicator in `background: Rectangle { implicitHeight: 36; ... }`.
- In `loadBooksForExistingSelector(preferredBookId)`: preserve `preferredBookId` or previous `book_id`, defaulting `genExistingBookCombo.currentIndex = 0` when `genExistingBooksModel.count > 0`, and update `existingBookInfoText`.
- In `+5` button: `var cur = parseInt(genCopyCountInput.text) || 1; var c = (cur === 1) ? 5 : Math.min(99, cur + 5); genCopyCountInput.text = c.toString();`.
- In `executeGenerateAndSave()` Mode 0: check if an active book with the same `title` (and `isbn`) already exists in `librarianAdmin.searchBooks(title)`. If found and `existing.total_copies < count`, call `librarianAdmin.addCopies(existing.book_id, (count - existing.total_copies).toString())` so increasing copy count from `1` to `5` and clicking save tops up the book to 5 copies; otherwise call `librarianAdmin.addBook(...)` and select the newly created book in `loadBooksForExistingSelector(res.data.book_id)`.

In `apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml`, `BookCatalogView.qml`, and `Main.qml`:
- Add `property alias editBookCopiesInput: editBookCopiesInput` to `BookActionDialogs.qml` and `Main.qml`.
- Update `openEditBookDialog(bookId, title, author, isbn, categoryId, shelf, totalCopies)` to set `editBookDialog.currentTotalCopies = totalCopies || 1` and `editBookCopiesInput.text = (totalCopies || 1).toString()`.
- In `submitEditBook()`: after `librarianAdmin.updateBook(...)` succeeds, if `parseInt(editBookCopiesInput.text) > editBookDialog.currentTotalCopies`, call `librarianAdmin.addCopies(editBookDialog.targetBookId, (newTotal - editBookDialog.currentTotalCopies).toString())`. Always call `rootWindow.searchBooks()`, `rootWindow.loadBooksForExistingSelector()`, and `rootWindow.loadPrintableBooks("")`.
- Style `addCopiesDialog` with custom Thai buttons (`ยกเลิก` / `💾 เพิ่มเล่มและสร้างบาร์โค้ด`), `onAccepted` on `addCopiesCountInput`, and refresh `rootWindow.searchBooks()`, `rootWindow.loadBooksForExistingSelector()`, and `rootWindow.loadPrintableBooks("")`.
- In `Main.qml`: add `function openAddCopiesDialog(bookId, title)` forwarding to `bookDialogs.openAddCopiesDialog(bookId, title)` and update `openEditBookDialog` to forward `totalCopies`.

- [ ] **Step 4: Run pytest to verify Task 1 tests pass**

Run: `.venv/bin/pytest tests/test_ui_librarian.py -v`
Expected: PASS

- [ ] **Step 5: Commit Task 1**

```bash
git add apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml apps/librarian_management_app/qml/views/BookCatalogView.qml apps/librarian_management_app/qml/Main.qml tests/test_ui_librarian.py
git commit -m "fix(librarian_ui): fix multi-copy registration, existing book selector, and edit copy sync"
```

---

### Task 2: Replace Locked `Code128` Row Label with Copy Action on Barcode Printout Page & Verify 5-Barcode PDF Export

**Files:**
- Modify: `apps/librarian_management_app/qml/views/CategoryManagementView.qml:20-135,290-380`
- Modify: `apps/librarian_management_app/qml/Main.qml:356-360`
- Modify: `tests/test_ui_librarian.py`
- Modify: `wiki/apps/librarian-management-app.md`
- Modify: `wiki/log.md`

**Interfaces:**
- Consumes: `BookActionDialogs.openAddCopiesDialog(bookId, title)`, `LibrarianAdminAdapter.getBooksWithBarcodes(query)`, `LibrarianAdminAdapter.exportLabelsPdf(barcodes_json, output_path)`
- Produces:
  - `CategoryManagementView.addCopiesRequested(int bookId, string title)` signal wired in `Main.qml` to `bookDialogs.openAddCopiesDialog(bookId, title)`
  - `CategoryManagementView.loadPrintableBooks(query)` formats `barcode_preview` to list all barcodes (up to 5 inline, e.g. `SMTE-00001-01, SMTE-00001-02, SMTE-00001-03, SMTE-00001-04, SMTE-00001-05`) and replaces the static grey `Code128` text on each row with a `+ เพิ่มเล่ม` button

- [ ] **Step 1: Write failing test in `tests/test_ui_librarian.py` verifying 5-copy PDF output and removal of locked `Code128` row text**

```python
def test_barcode_printout_exports_all_five_barcodes_to_pdf(lib_ui):
    import re
    window = lib_ui["window"]
    lib_ui["adapter"].addBook("เคมีคำนวณ ม.ต้น", "9786169990001", "อ.เคมี", "", "", "C-1", "5")

    find(window, "navBtnCategories").clicked.emit()
    process(lib_ui["app"])

    search_box = find(window, "barcodePrintSearchInput")
    search_box.setProperty("text", "เคมีคำนวณ")
    process(lib_ui["app"])

    model = find(window, "genBarcodesModel")
    assert model.property("count") == 1
    row0 = model.get(0)
    assert row0.property("copy_count").toInt() == 5
    preview_str = row0.property("barcode_preview").toString()
    assert "-01" in preview_str and "-05" in preview_str

    find(window, "btnPrintSelectedPdf").clicked.emit()
    process(lib_ui["app"])

    cat_screen = find(window, "categoryScreen")
    pdf_path = cat_screen.property("lastPdfExported")
    assert os.path.exists(pdf_path)
    pdf_bytes = open(pdf_path, "rb").read()
    barcodes_in_pdf = re.findall(rb"\((SMTE-\d{5}-\d{2})\)", pdf_bytes)
    assert len(barcodes_in_pdf) == 5
    assert barcodes_in_pdf[0].endswith(b"-01")
    assert barcodes_in_pdf[4].endswith(b"-05")
```

- [ ] **Step 2: Run pytest to verify the new test fails on `barcode_preview` / row UI check**

Run: `.venv/bin/pytest tests/test_ui_librarian.py -k "test_barcode_printout_exports_all_five_barcodes_to_pdf" -v`
Expected: PASS/FAIL depending on `barcode_preview` format and row controls; inspect and update `CategoryManagementView.qml`.

- [ ] **Step 3: Update `CategoryManagementView.qml` and `Main.qml`, and update `wiki/` docs**

In `apps/librarian_management_app/qml/views/CategoryManagementView.qml`:
- Add `signal addCopiesRequested(int bookId, string title)`.
- In `loadPrintableBooks(query)`: format `barcode_preview` so books with `<= 5` copies display all barcodes separated by `, ` (`b.barcodes.join(", ")`), and books with `> 5` copies display `b.barcodes.slice(0, 3).join(", ") + " ... " + b.barcodes[b.barcodes.length - 1]`.
- In `genBarcodesList` delegate: remove `Text { text: "Code128"; ... }` and replace it with `Button { text: "+ เพิ่มเล่ม"; flat: true; font.pixelSize: 12; onClicked: barcodePrintScreen.addCopiesRequested(model.book_id, model.title) }`.
- In `Main.qml`: wire `CategoryManagementView { id: categoryView; onAddCopiesRequested: function(bookId, title) { bookDialogs.openAddCopiesDialog(bookId, title) } }`.
- Update `wiki/apps/librarian-management-app.md` and append summary to `wiki/log.md`.

- [ ] **Step 4: Run full pytest suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: 100% PASS across all test files.

- [ ] **Step 5: Commit Task 2**

```bash
git add apps/librarian_management_app/qml/views/CategoryManagementView.qml apps/librarian_management_app/qml/Main.qml tests/test_ui_librarian.py wiki/apps/librarian-management-app.md wiki/log.md
git commit -m "fix(librarian_ui): replace locked Code128 row label with add-copies action and show all copy barcodes"
```
