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
    │   ├── StudentSyncView.qml       # Tab 2: Snapshot Diff & Apply
    │   ├── FinesManagementView.qml   # Tab 3: Unpaid / Paid Fines Ledger
    │   ├── BarcodeGeneratorView.qml  # Tab 5: Barcode & PDF Label Generator
    │   └── CategoryManagementView.qml# Tab 6: Classification Category Editor
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

### 2.3 Barcode Label Generator (`BarcodeGeneratorView.qml`)
- Generates Code128 barcodes using standard label sizes.
- Exports printable A4 PDF sheets (3 columns x 8 rows) via ReportLab directly to the user's `Documents` or `Downloads` folder.

### 2.4 Student Snapshot Sync (`StudentSyncView.qml`)
- Imports `snapshot.sqlite` exported from the Student Management App.
- Computes additions, promotions, and status changes, displaying a preview before applying updates to `library.sqlite`.
