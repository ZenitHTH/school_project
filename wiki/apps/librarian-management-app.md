# Librarian Management App Architecture (`apps/librarian_management_app/`)

## 1. Directory Structure
```
apps/librarian_management_app/
├── main.py
├── adapters/
│   └── librarian_admin_adapter.py
└── qml/
    ├── Main.qml
    ├── views/
    │   ├── BookCatalogView.qml       # Tab 0: Book Catalog & Copy Status
    │   ├── CirculationDeskView.qml   # Tab 1: Checkouts & Returns
    │   ├── ActiveLoansView.qml       # Tab 2: Currently Loaned Out Books
    │   ├── StudentSyncView.qml       # Tab 3: Snapshot Diff & Apply
    │   ├── FinesManagementView.qml   # Tab 4: Unpaid / Paid Fines Ledger
    │   ├── BarcodeGeneratorView.qml  # Tab 6: Book Registration (left) + Grouping Management (right)
    │   └── CategoryManagementView.qml# Tab 7: Dedicated Barcode Printout Generator (Selectable / Print All A4 PDF)
    └── dialogs/
        ├── BookActionDialogs.qml     # addBook, addCopies, barcodeConfirm, deleteBook
        ├── EditBookDialog.qml        # Dedicated modern edit dialog with copy count corrections
        └── CategoryActionDialogs.qml # renameCategory, reassignCategory, simpleDeleteCategory
```

---

## 2. Key Modules & Workflows

### 2.1 Book Catalog & Copies (`BookCatalogView.qml` & `EditBookDialog.qml`)
- Books are classified under categories. Each book can have multiple copies (`SMTE-00001-01`, `SMTE-00001-02`).
- **Catalog Search (Tab 0)**: The single search field (`catalogSearchInput`) matches title/author/ISBN (FTS5 trigram, LIKE fallback <3 chars) **and** barcode stickers — the query is also compared against normalized `book_copies.barcode` (lowercase, dash-insensitive, via `EXISTS` subquery in `book_repo.search_books`; full scan, `# shortcut` — upgrade to trigram index at ~10k+ copies). Dash-less ISBN input (raw scanned/pasted digits) matches via normalized substring against `books.isbn` (same `search_books` path, so the add-book page's right-pane inventory search bar (`inventorySearchInput`) supports it too). The category `StyledComboBox` (`catalogCategoryCombo`, first option `-- ทุกหมวดหมู่ --`) filters results via `LibrarianAdminAdapter.searchBooks(query, category_id)` (Qt slot `@Slot(str, int)`; `0` = all categories). All QML call sites pass both args (strict Qt arity).
- **Book Metadata & Copy Correction Studio (`EditBookDialog.qml`)**:
  - Modal card supporting simultaneous metadata updates (Title, Author, ISBN, Category, Shelf) and copy adjustments.
  - **Copy Count Corrections ("เมื่อกรอกผิด")**:
    - Supports adjusting total copies upward (automatically generating subsequent barcodes) or downward (safely removing unloaned available copies).
    - Blocks reductions below current on-loan copy count with visual error prevention.
    - Interactive steppers (`[-]`, `[+]`, `+1`, `+5`, `-1`) and real-time barcode tray preview with deletion strikethrough badges.
- Deleting a book checks if copies have active loans; if so, deletion is blocked.

### 2.2 Circulation Desk (`CirculationDeskView.qml`)
- Streamlines librarian checkout and returns.
- Prevents checkout if:
  1. Student status is not `'active'` (e.g., `'transferred_out'`).
  2. Student has unpaid overdue fines exceeding policy threshold.
  3. Student has reached max concurrent book limit.

### 2.3 Book Registration, Live Preview & Inventory Grid (`BarcodeGeneratorView.qml` & `BookInventoryRightPane.qml`, Tab 6)
- 2-column split screen:
  - **Left Card (Book Registration)**: Register new book or add copies to an existing book. Immediately commits deterministic `SMTE-xxxxx-xx` barcodes to `book_copies` in SQLite upon save. Auto-selects existing books upon switching to mode 1 and supports topping up copies to a target count.
  - **Duplicate ISBN Detection (`checkBookByIsbn`)**: Scans/inputs trigger duplicate checks against active catalog. If a matching book exists, alerts librarian with existing copy count and routes save operation to append copies to the existing title rather than failing database unique constraints.
  - **Form Auto-Clear & Continuous Scanning**: Clearing of input fields upon successful save (`clearRegistrationForm`), immediately returning focus to the ISBN input field for rapid barcode gun scanning.
  - **Right Card (Live Incoming Preview & Inventory Grid Table)**:
    - **Top Bordered Table Box**: Displays real-time live preview of the book currently being entered/modified (`incomingBookPreviewCard`), including Title, Author, ISBN, Category, Shelf Location, Copy Count, and deterministic barcode sequence preview (`SMTE-xxxxx-01` ...).
    - **Middle Bordered Table Box**: Structured inventory table (`inventoryBooksList` / `inventoryBooksModel`) showing all books currently in library stock with search filter, copy count badges, and inline actions (`+ เพิ่มเล่ม`, `✏️ แก้ไข`, `🗑️ ลบ`).
    - **Bottom Compact Category Strip**: Quick addition, editing, and deletion of classification categories.
    - **Direct Navigation Button**: `btnGoToPrintPage` to jump directly to the Dedicated Barcode Print Studio (Tab 7).

### 2.4 Dedicated Barcode Print Studio (`CategoryManagementView.qml`, Tab 7)
- Staff can search books and filter by category (`barcodeCategoryFilterCombo`).
- Live Print Queue Metrics display:
  - Selected books count (`selectedBooksCountText`)
  - Total barcode stickers count (`selectedStickersCountText`)
  - Estimated A4 sticker sheets (`estimatedPagesText`, 24 stickers/sheet at 3 columns x 8 rows).
- Clickable bordered table rows with checkboxes for selective printing (`exportSelectedBooksPdf`) or full printout (`exportAllBooksPdf` / `btnExportPdfSheet`).
- Includes direct per-row `+ เล่ม` action button to top up physical copies without leaving the page.
- Automatically excludes retired and disposed copies (`status NOT IN ('retired', 'disposed')`).

### 2.5 Student Snapshot Sync (`StudentSyncView.qml`)
- Imports `snapshot.sqlite` exported from the Student Management App.
- Computes additions, promotions, and status changes, displaying a preview before applying updates to `library.sqlite`.

### 2.6 System Settings & Sidebar Navigation (`Main.qml` & `SettingsView.qml`)
- Left sidebar navigation uses dynamic `implicitHeight: Math.max(38, Math.round(navText.implicitHeight + 18))` and `Layout.preferredHeight` on `NavBtn` to ensure active highlight pills cleanly encase text labels across all system font sizes and UI scaling factors.
- Tab 8 embeds the shared `SettingsView.qml` for real-time font family, font size (10–24px), and UI scaling (50%–150%) adjustment.

### 2.7 Books without ISBN (No-ISBN checkbox)
- A book may exist without an ISBN: `books.isbn` is nullable (migration `0002`) and an empty ISBN stores as `NULL` — never a sentinel like `-` (repo write paths store the ISBN exactly as submitted, with no normalization on write).
- All three ISBN inputs — add-book dialog `newBookIsbn`, edit dialog `editBookIsbnInput`, barcode generator `genBookIsbn` — carry a `ไม่มี ISBN (No ISBN)` checkbox (`chkNoIsbnAdd` / `chkNoIsbnEdit` / `chkNoIsbnGen`).
- Checked → the ISBN field disables (`enabled: !chk.checked`) and shows `-`; unchecked → editable and the `-` is cleared (only when the field text is exactly `-`).
- Every submit path sends `''` when the box is checked (`chk.checked ? "" : field.text`), so `books.isbn` becomes `NULL`; the database never stores the hyphen.
- Opening the edit dialog on a `NULL`-ISBN book auto-checks the box and shows `-` (`openEditBookDialog` in `BookActionDialogs.qml`).
- Catalog lists already render `model.isbn || '-'` for missing ISBNs (`BookCatalogView.qml:136`); ISBN auto-fetch and duplicate checks run only for non-empty ISBNs; lending keys off the copy barcode (`SMTE-{book_id:05d}-{seq:02d}`), never the ISBN.
- Contract pinned in `tests/test_book_without_isbn.py`; checkbox lock behavior in `tests/test_ui_barcode_generator_fields.py::test_no_isbn_checkbox_locks_field`.

