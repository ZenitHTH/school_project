# Cross-Platform Desktop Packaging (`packaging/` & `.github/workflows/`)

## 1. Overview
The project distributes standalone desktop executables across four platforms:
1. **Windows**: `.exe` built on `windows-latest`.
2. **macOS**: `.app` bundle built on `macos-latest`.
3. **Ubuntu Linux**: Executable built with PySide6 bundled plugins on `ubuntu-24.04`.
4. **Fedora Linux**: Containerized build for RPM-based distributions.

---

## 2. PyInstaller Spec Files
Each app has dedicated spec files:
- `packaging/student_management.spec` & `packaging/student_management_windows.spec`
- `packaging/librarian_management.spec` & `packaging/librarian_management_windows.spec`
- `packaging/booth_app.spec` & `packaging/booth_app_windows.spec`

### Bundled Asset Requirements:
1. **Common QML library**: `('../apps/common_qml/*.qml', 'apps/common_qml')`.
2. **Local views & dialogs**: E.g. `('../apps/student_management_app/qml/views/*.qml', 'apps/student_management_app/qml/views')`.
3. **Database migrations**: `('../data/migrations/*.sql', 'data/migrations')`.

---

## 3. Runtime Environment Fixes (`apps/common_linux_env.py`)
To prevent Qt QML font crashes or missing Wayland/X11 platform plugins on Linux Mint and Ubuntu:
- Automatically sets `QT_QPA_PLATFORM="xcb;wayland"` with fallback.
- Overrides `QML_IMPORT_PATH` and ensures `Fusion` style is applied for consistent cross-platform controls.
