# Modular & Shared QML Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deconstruct monolithic QML code across all applications (`student_management_app`, `librarian_management_app`, `booth_app`) into a shared reusable component library (`apps/common_qml/`) and dedicated per-app modular screens/dialogs (`views/`, `dialogs/`), shrinking `Main.qml` files from ~4,300 lines down to clean coordinators (<150 lines each), while maintaining 100% test compatibility and packaging support.

**Architecture:** 
1. `apps/common_qml/`: Shared cross-application UI building blocks (`PaginationBar.qml`, `StyledSearchField.qml`, `ActionFeedbackBanner.qml`, `AuditLogView.qml`, `FirstLaunchDialog.qml`).
2. Per-app `views/` and `dialogs/`: Self-contained screens and modal dialogs.
3. Thin root `Main.qml`: Holds navigation state, registers models, and delegates to views.
4. Python runners & PyInstaller specs: Configured with `engine.addImportPath` and shared QML asset collection.

**Tech Stack:** PySide6 (Qt Quick Controls 2, QML), Python 3.14, openpyxl, pytest.

**Spec Reference:** Shared design analysis across `apps/student_management_app/qml/Main.qml`, `apps/librarian_management_app/qml/Main.qml`, and `apps/booth_app/qml/Main.qml`.

## Global Constraints
- **Zero test regressions**: All `objectName` identifiers (`mainStack`, `searchInput`, `studentList`, `searchResultsModel`, `btnViewDetail`, `logList`, `logModel`, `firstLaunchDialog`, etc.) must remain unchanged so Qt test discovery (`findChild(QObject, "<name>")`) works identically.
- **Cross-platform safe**: Text inputs must include explicit palettes/backgrounds to prevent macOS native dark rendering bugs.
- **Packaging integrity**: All packaging `.spec` files (Linux & Windows) must bundle `apps/common_qml/*.qml` in `datas`.
- **Runtime portability**: `main.py` in all 3 apps must register `apps/common_qml` via `engine.addImportPath` supporting both dev and frozen `sys._MEIPASS` modes.

## Review Focus
1. **QObject `findChild` traversing modular components**: Ensure components created inside `StackLayout` or imported files expose their internal `objectName` to root `engine.rootObjects()[0].findChild(QObject, ...)`.
2. **QML Context Property Scoping**: Ensure subcomponents can access adapter properties (`studentAdmin`, `librarianAdmin`, `boothAdapter`) either directly from rootContext or via clear property bindings.
3. **FileDialog and Popup parenting**: Modal dialogs must be centered and scoped to `parent` or `ApplicationWindow`.
4. **Packaging build consistency**: Check that `.spec` files bundle the new directory structures without missing dependencies.
5. **No behavioral side-effects**: Test all 175 tests pass with `pytest tests/` after each task.

---

### Task 1: Create `apps/common_qml/` Shared Library and Wire Python Runners

**Files:**
- Create: `apps/common_qml/StyledSearchField.qml`
- Create: `apps/common_qml/PaginationBar.qml`
- Create: `apps/common_qml/ActionFeedbackBanner.qml`
- Create: `apps/common_qml/AuditLogView.qml`
- Create: `apps/common_qml/FirstLaunchDialog.qml`
- Modify: `apps/student_management_app/main.py:85-95`
- Modify: `apps/librarian_management_app/main.py:85-95`
- Modify: `apps/booth_app/main.py:40-50`
- Modify: `packaging/student_management.spec:8-12`
- Modify: `packaging/librarian_management.spec:8-12`
- Modify: `packaging/booth_app.spec:8-12`
- Modify: `packaging/student_management_windows.spec:8-12`
- Modify: `packaging/librarian_management_windows.spec:8-12`
- Modify: `packaging/booth_app_windows.spec:8-12`
- Test: `tests/test_qml_loads.py`

**Interfaces:**
- Consumes: Qt 6 Quick / Quick Controls 2.
- Produces: Importable QML module `common_qml` providing `StyledSearchField`, `PaginationBar`, `ActionFeedbackBanner`, `AuditLogView`, `FirstLaunchDialog`.

- [ ] **Step 1: Write `StyledSearchField.qml`**
Reusable text field with explicit white background, `#cbd5e1` border, blue focus ring, dark text `#0f172a`, and clean placeholder styling.

- [ ] **Step 2: Write `PaginationBar.qml`**
Reusable pagination bar exposing `currentPage`, `totalPages`, `totalCount`, and signals `pageRequested(int page)`.

- [ ] **Step 3: Write `ActionFeedbackBanner.qml`**
Reusable feedback rectangle exposing `text`, `isError`, and auto-hide/visible semantics.

- [ ] **Step 4: Write `AuditLogView.qml`**
Reusable audit trail table with `logList` ListView, `logModel` ListModel, and formatted columns (timestamp, action, detail).

- [ ] **Step 5: Write `FirstLaunchDialog.qml`**
Reusable setup wizard popup with welcome banner, file import button (`firstLaunchImportBtn`), blank db button (`firstLaunchBlankBtn`), and status text (`firstLaunchStatusText`).

- [ ] **Step 6: Update `main.py` across all 3 apps and all 6 `.spec` files**
Add `engine.addImportPath(...)` in `apps/*/main.py` pointing to `apps/common_qml`. Add `('../apps/common_qml/*.qml', 'apps/common_qml')` to `datas` in packaging spec files.

- [ ] **Step 7: Run test suite to verify loading and runtime configuration**
Run: `.venv/bin/pytest tests/test_qml_loads.py`
Expected: PASS.

- [ ] **Step 8: Commit**
```bash
git add apps/common_qml/ apps/*/main.py packaging/*.spec
git commit -m "feat(qml): create apps/common_qml shared library and wire import paths"
```

---

### Task 2: Student Management App - Modularize into Views and Dialogs

**Files:**
- Create: `apps/student_management_app/qml/dialogs/StudentActionDialogs.qml`
- Create: `apps/student_management_app/qml/views/StudentSearchView.qml`
- Create: `apps/student_management_app/qml/views/StudentDetailView.qml`
- Create: `apps/student_management_app/qml/views/BulkPromotionView.qml`
- Create: `apps/student_management_app/qml/views/LineSyncExportView.qml`
- Create: `apps/student_management_app/qml/views/ExcelImportView.qml`
- Modify: `apps/student_management_app/qml/Main.qml`
- Test: `tests/test_ui_student.py`

**Interfaces:**
- Consumes: `apps/common_qml` components (`StyledSearchField`, `PaginationBar`, `ActionFeedbackBanner`, `AuditLogView`, `FirstLaunchDialog`), `studentAdmin`.
- Produces: Slim `Main.qml` (~120 lines). Preserves all `objectName` identifiers: `mainStack`, `searchInput`, `searchButton`, `studentList`, `searchResultsModel`, `btnViewDetail`, `btnChangeRoom`, `btnChangeStatus`, `btnEditName`, `btnChangeId`, `actionFeedback`, `btnPromote`, `promoteResultText`, `btnExportSnapshot`, `exportStatusText`, `logList`, `logModel`, `selectFileButton`, `selectedFilePath`, `btnPreviewDiff`, `importButton`, `importStatusText`, badges, `diffListView`, `diffModel`, all dialog inputs and buttons.

- [ ] **Step 1: Extract dialogs into `apps/student_management_app/qml/dialogs/StudentActionDialogs.qml`**
Move `roomDialog`, `statusDialog`, `nameDialog`, `idDialog`, and `confirmImportDialog`.

- [ ] **Step 2: Extract views into `apps/student_management_app/qml/views/`**
- `StudentSearchView.qml`: Tab 0 table and search using `StyledSearchField` and `PaginationBar`.
- `StudentDetailView.qml`: Tab 1 individual student detail and action buttons.
- `BulkPromotionView.qml`: Tab 2 promotion.
- `LineSyncExportView.qml`: Tab 3 snapshot export.
- Tab 4: Instantiate shared `AuditLogView`.
- `ExcelImportView.qml`: Tab 5 Excel diff preview & import.

- [ ] **Step 3: Refactor `apps/student_management_app/qml/Main.qml` to orchestrate views**
Replace the 1,775 lines with clean component instantiations inside `stackLayout`.

- [ ] **Step 4: Run student UI test suite**
Run: `.venv/bin/pytest tests/test_ui_student.py -v`
Expected: PASS (all 38 tests pass).

- [ ] **Step 5: Commit**
```bash
git add apps/student_management_app/qml/
git commit -m "refactor(student_app): modularize Main.qml using shared and local views"
```

---

### Task 3: Librarian Management App - Modularize into Views and Dialogs

**Files:**
- Create: `apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml`
- Create: `apps/librarian_management_app/qml/dialogs/CategoryActionDialogs.qml`
- Create: `apps/librarian_management_app/qml/views/BookCatalogView.qml`
- Create: `apps/librarian_management_app/qml/views/CirculationDeskView.qml`
- Create: `apps/librarian_management_app/qml/views/StudentSyncView.qml`
- Create: `apps/librarian_management_app/qml/views/FinesManagementView.qml`
- Create: `apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml`
- Create: `apps/librarian_management_app/qml/views/CategoryManagementView.qml`
- Modify: `apps/librarian_management_app/qml/Main.qml`
- Test: `tests/test_ui_librarian.py`

**Interfaces:**
- Consumes: `apps/common_qml` components (`StyledSearchField`, `PaginationBar`, `ActionFeedbackBanner`, `AuditLogView`, `FirstLaunchDialog`), `librarianAdmin`.
- Produces: Slim `Main.qml` (~150 lines). Preserves all `objectName` identifiers across book catalog, circulation desk, student sync, fines, audit log, barcode generator, category manager, and dialogs.

- [ ] **Step 1: Extract dialogs into `dialogs/BookActionDialogs.qml` and `dialogs/CategoryActionDialogs.qml`**
Move all book edit/delete/copies modals and category rename/reassign modals.

- [ ] **Step 2: Extract views into `apps/librarian_management_app/qml/views/`**
- `BookCatalogView.qml`: Catalog list, search, add copies.
- `CirculationDeskView.qml`: Loan and return operations with student card lookup.
- `StudentSyncView.qml`: Sync diff preview and application.
- `FinesManagementView.qml`: Fine ledger and settlement.
- Tab 5: Instantiate shared `AuditLogView`.
- `BarcodeGeneratorView.qml`: Barcode generation and PDF sheet export.
- `CategoryManagementView.qml`: Category tree and books count.

- [ ] **Step 3: Refactor `apps/librarian_management_app/qml/Main.qml` to orchestrate views**
Replace the 2,314 lines with clean component instantiations inside `stackLayout`.

- [ ] **Step 4: Run librarian UI test suite**
Run: `.venv/bin/pytest tests/test_ui_librarian.py -v`
Expected: PASS (all 21 tests pass).

- [ ] **Step 5: Commit**
```bash
git add apps/librarian_management_app/qml/
git commit -m "refactor(librarian_app): modularize Main.qml using shared and local views"
```

---

### Task 4: Booth App - Use Shared Components and Verify All Applications

**Files:**
- Modify: `apps/booth_app/qml/Main.qml`
- Test: `tests/test_ui_booth.py`
- Test: Full test suite (`pytest tests/`)

**Interfaces:**
- Consumes: `apps/common_qml` components (`StyledSearchField`, `ActionFeedbackBanner`).
- Produces: Consistent styling and layout matching Student and Librarian apps. Preserves all `objectName` fields (`emptyDbWarningBanner`, `studentIdInput`, `btnIdentify`, `studentStatusMsg`, `bookBarcodeInput`, `btnCheckout`, `btnReturn`, `feedbackBanner`, `btnLogout`).

- [x] **Step 1: Refactor `apps/booth_app/qml/Main.qml` to use shared components**
Use `StyledSearchField` for barcode/ID inputs and `ActionFeedbackBanner` for feedback banner.

- [x] **Step 2: Run booth UI tests**
Run: `.venv/bin/pytest tests/test_ui_booth.py -v`
Expected: PASS (all 13 tests pass).

- [x] **Step 3: Run entire project test suite**
Run: `.venv/bin/pytest tests/`
Expected: All 175 tests pass.

- [x] **Step 4: Visual offscreen verification**
Render offscreen snapshots of all 3 applications to verify zero layout or visual regressions.

- [x] **Step 5: Commit**
```bash
git add apps/booth_app/qml/
git commit -m "refactor(booth_app): adopt common QML components and finalize clean restructure"
```
