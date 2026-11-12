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

---

## 5. Typography & Responsive Layout (2026-11-12 modernization)
Aligned with the Librarian Management reference patterns (invariants #6/#7):
- `Main.qml` forces a light `palette.*` block (dark-mode guard for `StyledTextInput`/`StyledComboBox`) and exposes `fontScale`/`appFontFamily`/`appFontSize` bound to `SettingsView`.
- Sidebar nav delegates: dynamic `implicitHeight: Math.max(38, text.implicitHeight + 12)` (replaces fixed 42px) + scale-based fonts. Static sidebar controls (`sidebarTitleText`, `openWizardBtn`, status line) scale via `window.fontScale`.
- `StudentDetailView.qml`: empty-state / info cards use `implicitHeight: Math.max(min, content.implicitHeight + pad)`; status badge, feedback bar, and the three colored action-button backgrounds are dynamic (no fixed 140/26/44/42px). Fonts scale via `window.fontScale`; the info card gets a `Typography.applyToItem` pass (idempotent — baseline extraction divides out the current factor).
- `BulkPromotionView.qml` / `LineSyncExportView.qml` / `ExcelImportView.qml`: titles/body/badges scale with `window.fontScale`; the file-selection card and the four diff-summary badges use dynamic heights.
- `main.py` wires `setup_app_logging("SMTE-StudentManagement")` (rotating `app.log`, same as the librarian app).
- New objectNames for test discovery: `sidebarTitleText`, `sidebarNavRepeater`, `infoCard`, `detailStatusBadge`, `newBadgeBox`, `promoBadgeBox`, `missingBadgeBox`, `conflictBadgeBox`.
- Tests: `tests/test_ui_student_modernization.py` (6 tests: logging wiring, light-palette contract, dynamic nav-delegate height via standalone `QQmlComponent` instance, sidebar typography scaling, detail card/badge heights, import badges + font scaling).

