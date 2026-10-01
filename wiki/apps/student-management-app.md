# Student Management App Architecture (`apps/student_management_app/`)

## 1. Directory Structure
```
apps/student_management_app/
├── main.py
├── adapters/
│   └── student_admin_adapter.py
└── qml/
    ├── Main.qml
    ├── views/
    │   ├── StudentSearchView.qml   # Tab 0: FTS5 Search & List View
    │   ├── StudentDetailView.qml   # Tab 1: View/Edit Student & Actions
    │   ├── BulkPromotionView.qml   # Tab 2: Bulk Yearly Promotion
    │   ├── LineSyncExportView.qml  # Tab 3: Air-Gapped Snapshot Export
    │   └── ExcelImportView.qml     # Tab 5: Excel Diff Roster Import
    └── dialogs/
        └── StudentActionDialogs.qml # roomDialog, statusDialog, nameDialog, idDialog, confirmImportDialog
```

---

## 2. Views Breakdown

| View Component | Purpose | Key ObjectNames & Controls |
|---|---|---|
| `StudentSearchView.qml` | Interactive student search table with pagination | `searchInput`, `searchButton`, `studentList`, `searchResultsModel`, `btnViewDetail` |
| `StudentDetailView.qml` | Student profile card, history, and status change buttons | `btnChangeRoom`, `btnChangeStatus`, `btnEditName`, `btnChangeId`, `actionFeedback` |
| `BulkPromotionView.qml` | One-click term-to-term student promotion | `btnPromote`, `promoteResultText` |
| `LineSyncExportView.qml` | Exports `snapshot.sqlite` for transfer to Library | `btnExportSnapshot`, `exportStatusText` |
| `ExcelImportView.qml` | Excel roster selection, diff preview, and import trigger | `selectFileButton`, `selectedFilePath`, `btnPreviewDiff`, `importButton`, `diffListView` |

---

## 3. Action Dialogs (`StudentActionDialogs.qml`)
All modal action dialogs are isolated into `StudentActionDialogs.qml` with explicit objectNames:
- `roomDialog`: Move student to another room (`newRoomInput`, `roomReasonInput`).
- `statusDialog`: Transition student between `active`, `on_leave`, and `transferred_out` (`statusCombo`, `statusReasonInput`).
- `nameDialog`: Edit prefix, first name, and last name (`editPrefixInput`, `editFirstNameInput`, `editLastNameInput`, `nameReasonInput`).
- `idDialog`: Change student ID with foreign key cascade across enrollments, loans, and audit logs (`newIdInput`, `idReasonInput`).
- `confirmImportDialog`: Modal preview showing additions, promotions, and spelling conflicts before writing to the database.

---

## 4. UI Adapter Safeguards (`StudentAdminAdapter`)
- All database payloads sent to QML are passed through `_sanitize_for_qml` to convert `None` values into typed defaults (e.g. `""` for strings, `0` for numeric IDs) to prevent QML engine type errors.
- Method returns use `Result.to_dict()` or `json.dumps({"ok": bool, "data": ..., "error": ..., "warnings": [...]})`.
