# Common QML Components Library (`apps/common_qml/`)

The `apps/common_qml/` folder contains shared, production-tested QML components reusable across Student Management, Librarian Management, and Booth Kiosk apps.

---

## 1. Components Reference

### 1.1 `StyledSearchField.qml`
- Standardized text input with crisp white background, `#cbd5e1` border, blue focus ring, dark text `#0f172a`, and placeholder text.
- Replaces unstyled native `TextField` controls that render invisibly on certain Linux desktop themes or dark modes.
- **Signals**: `onAccepted`.

### 1.2 `PaginationBar.qml`
- Reusable pagination toolbar supporting first, previous, numbered pages, next, last, and summary info text (`หน้า X จาก Y (N รายการ)`).
- **Properties**:
  - `currentPage: int`
  - `totalPages: int`
  - `totalCount: int`
  - `countUnit: string` (e.g. `"รายการ"`, `"เล่ม"`)
- **Signals**: `pageRequested(int page)`.

### 1.3 `ActionFeedbackBanner.qml`
- Toast/notification banner providing visual confirmation of database actions.
- Automatically handles success (green background `#ecfdf5`) and error (red background `#fef2f2`) states.
- **Properties**: `text`, `isError`, `duration`.

### 1.4 `AuditLogView.qml`
- Standardized audit log viewer component displaying timestamp, actor, entity, action, and detail.
- **Properties**: `logList`, `logModel`.

### 1.5 `FirstLaunchDialog.qml`
- First-time wizard dialog greeting the user when database is empty.
- Provides choice between selecting an Excel roster file for initial import or creating a blank standard schema database.
- **ObjectNames**: `firstLaunchDialog`, `firstLaunchStatusText`, `firstLaunchImportBtn`, `firstLaunchBlankBtn`.

---

## 2. QML Engine Integration
All application entry points (`apps/*/main.py`) configure the import path for `apps/common_qml` both in development and PyInstaller frozen modes:

```python
common_qml_dir = os.path.join(sys._MEIPASS, "apps", "common_qml") \
    if getattr(sys, "frozen", False) else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common_qml"))
engine.addImportPath(common_qml_dir)
engine.addImportPath(os.path.dirname(common_qml_dir))
```

And in QML files:
```qml
import "../../common_qml"
```
