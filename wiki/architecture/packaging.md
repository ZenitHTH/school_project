# Cross-Platform Desktop Packaging (`packaging/` & `.github/workflows/`)

## 1. Overview
The project distributes standalone desktop executables and native OS installers across four platforms:
1. **Windows**: Portable `.exe` and Inno Setup `Setup.exe` built on `windows-latest`.
2. **macOS**: Portable `.app` bundle, `.zip`, and Apple `.dmg` disk image built via native `hdiutil` on `macos-latest`.
3. **Ubuntu / Debian Linux**: Portable `.tar.gz` and `.deb` package built via `dpkg-deb` on `ubuntu-24.04`.
4. **Fedora / RHEL Linux**: Portable `.tar.gz` and `.rpm` package built via containerized `rpmbuild` on `fedora:latest`.

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

## 3. Native Setup Installers (`packaging/installers/`)
- **Debian / Ubuntu (`.deb`)**:
  - Script: `packaging/installers/deb/build_deb.sh`
  - Installs to `/usr/lib/<app>`, creates symlink in `/usr/bin/<app>`, and installs desktop launcher in `/usr/share/applications/<app>.desktop`.
- **Fedora / RHEL (`.rpm`)**:
  - Script: `packaging/installers/rpm/build_rpm.sh`
  - Generates RPM spec and runs `rpmbuild` inside Fedora container. Installs to `/usr/lib/<app>`, symlinks to `/usr/bin/<app>`, and sets up `.desktop`.
- **Windows (`setup.exe`)**:
  - Script: `packaging/installers/windows/installer.iss`
  - Built with Inno Setup CLI (`iscc`). Provides Start Menu shortcut, Desktop icon toggle, and clean Windows uninstaller.
- **macOS (`.dmg`)**:
  - Script: `packaging/installers/macos/create_dmg.sh`
  - Built with native Apple `hdiutil` (UDZO compressed format) with drag-to-Applications folder symlink.

---

## 4. Runtime Environment Fixes (`apps/common_linux_env.py`)
To prevent Qt QML font crashes, missing Wayland/X11 platform plugins, or GLX/OpenGL failures on older Intel iGPUs:
- Automatically sets `LIBGL_ALWAYS_SOFTWARE="1"` and `QT_QUICK_BACKEND="software"` on Linux when not overridden.
- Configures `QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)` to ensure immediate software rasterization fallback.
- Clears `GIO_MODULE_DIR` in frozen bundles to avoid GLib/GIO symbol collisions with host libraries.
