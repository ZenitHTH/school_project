# Cross-Platform Desktop Packaging (`packaging/` & `.github/workflows/`)

## 1. Overview
The project distributes standalone desktop executables and native OS installers across four platforms:
1. **Windows**: Portable `.exe` and Inno Setup `Setup.exe` built on `windows-latest`.
2. **macOS**: Portable `.app` bundle, `.zip`, and Apple `.dmg` disk image built via native `hdiutil` on `macos-latest`.
3. **Ubuntu / Debian Linux**: Portable `.tar.gz` and `.deb` package built via `dpkg-deb` on `ubuntu-24.04`.
4. **Fedora / RHEL Linux**: Portable `.tar.gz` and `.rpm` package built via containerized `rpmbuild` on `fedora:latest`.

---

## 2. PyInstaller Spec Files
Each app has a unified cross-platform spec file:
- `packaging/student_management.spec`
- `packaging/librarian_management.spec`
- `packaging/booth_app.spec`

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
  - Sanitizes pre-release versions containing hyphens (`RPM_VERSION="${VERSION//-/\~}"`) to conform to RPM spec version constraints.
- **Windows (`setup.exe`)**:
  - Script: `packaging/installers/windows/installer.iss`
  - Built with Inno Setup CLI (`iscc`). Provides Start Menu shortcut, Desktop icon toggle, and clean Windows uninstaller.
  - Generates unique per-application `AppId={{C78DFE32-0941-4E7B-BFA6-92AE8997321F}-{#AppName}` so multiple SMTE apps installed on the same machine do not overwrite each other's registry keys.
- **macOS (`.dmg`)**:
  - Script: `packaging/installers/macos/create_dmg.sh`
  - Built with native Apple `hdiutil` (UDZO compressed format) with drag-to-Applications folder symlink.

---

## 4. Runtime Environment Fixes (`apps/common_linux_env.py`)
To prevent Qt QML font crashes, missing Wayland/X11 platform plugins, or GLX/OpenGL failures on older Intel iGPUs:
- Automatically sets `LIBGL_ALWAYS_SOFTWARE="1"` and `QT_QUICK_BACKEND="software"` on Linux when not overridden.
- Configures `QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)` to ensure immediate software rasterization fallback.
- Clears `GIO_MODULE_DIR` in frozen bundles to avoid GLib/GIO symbol collisions with host libraries.

---

## 5. GitHub Actions Pipeline (`.github/workflows/`)
The deployment architecture is split into two distinct workflows:
1. **Continuous Integration (`.github/workflows/ci.yml`)**:
   - Triggers on `push` and `pull_request` targeting `main`.
   - Runs fast headless `pytest` (`QT_QPA_PLATFORM=offscreen`) with pip caching on `ubuntu-24.04`.
   - Uses concurrency cancellation (`${{ github.workflow }}-${{ github.ref }}`) to drop redundant builds on fast pushes.
2. **Tag-Driven Release Pipeline (`.github/workflows/release.yml`)**:
   - Triggers only on semantic version tags (`v*.*.*`) or manual `workflow_dispatch`.
   - Gated behind a required `test` job before starting any OS builds.
   - Matrix builds across 4 platforms: `windows-latest`, `macos-latest`, `ubuntu-24.04`, and `fedora:latest` container.
   - Dynamically derives `VERSION` from the Git tag (`${GITHUB_REF_NAME#v}`) or dispatch input, passing it into all installer scripts.
   - Archives macOS `.app` bundles using native `ditto -c -k --sequesterRsrc --keepParent` to preserve Qt framework symlinks.
   - Aggregates all artifacts, generates `SHA256SUMS.txt`, and publishes immutable releases with automated release notes via `softprops/action-gh-release@v2`.

