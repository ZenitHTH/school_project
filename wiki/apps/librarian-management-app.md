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
        ├── BookActionDialogs.qml     # addBook, addCopies, barcodeConfirm, editBook, deleteBook
        └── CategoryActionDialogs.qml # renameCategory, reassignCategory, simpleDeleteCategory
```

---

## 2. Key Modules & Workflows

### 2.1 Book Catalog & Copies
- Books are classified under categories. Each book can have multiple copies (`SMTE-00001-01`, `SMTE-00001-02`).
- Deleting a book checks if copies have active loans; if so, deletion is blocked.

### 2.2 Circulation Desk (`CirculationDeskView.qml`)
- Streamlines librarian checkout and returns.
- Prevents checkout if:
  1. Student status is not `'active'` (e.g., `'transferred_out'`).
  2. Student has unpaid overdue fines exceeding policy threshold.
  3. Student has reached max concurrent book limit.

### 2.3 Book Registration & Grouping Split View (`BarcodeGeneratorView.qml`, Tab 6)
- 2-column split screen:
  - **Left Card (Book Registration)**: Register new book or add copies to an existing book. Immediately commits deterministic `SMTE-xxxxx-xx` barcodes to `book_copies` in SQLite upon save.
  - **Right Card (Grouping Management)**: Add, edit, or delete classification categories. Changes instantly refresh `genCategoryCombo` on the left card without losing typed input.

### 2.4 Dedicated Barcode Printout Generator (`CategoryManagementView.qml`, Tab 7)
- Staff can search books, select specific books via checkboxes, and export their active barcodes (`exportSelectedBooksPdf`).
- Or print all active barcodes across the library (`exportAllBooksPdf` / `btnExportPdfSheet`) to standard A4 sticker sheets (3 columns x 8 rows = 24 labels/sheet).
- Automatically excludes retired and disposed copies (`status NOT IN ('retired', 'disposed')`).

### 2.5 Student Snapshot Sync (`StudentSyncView.qml`)
- Imports `snapshot.sqlite` exported from the Student Management App.
- Computes additions, promotions, and status changes, displaying a preview before applying updates to `library.sqlite`.
