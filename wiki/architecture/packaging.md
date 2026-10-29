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

## 5. GitHub Actions Pipeline & Git Branch Strategy (`.github/workflows/`)
The repository separates active development (`dev`) from release packaging (`main`):
1. **Development CI (`.github/workflows/ci.yml`)**:
   - Triggers on `push` to `dev` and `pull_request` targeting `main` or `dev`.
   - Runs fast headless `pytest` (`QT_QPA_PLATFORM=offscreen`) with pip caching on `ubuntu-24.04` — **no desktop packaging** on `dev` pushes.
   - Uses concurrency cancellation (`${{ github.workflow }}-${{ github.ref }}`) to drop redundant builds on fast pushes.
2. **Main & Tag Release Pipeline (`.github/workflows/release.yml`)**:
   - Triggers on `push` to `main`, semantic version tags (`v*.*.*`), or manual `workflow_dispatch`.
   - Single version source of truth: `VERSION` file (`1.1.0`) and `core/shared/version.py` (`APP_VERSION`), synchronized across `installer.iss`, `build_deb.sh`, `build_rpm.sh`, `create_dmg.sh`, PyInstaller `.spec` bundles, and `QGuiApplication.setApplicationVersion`.
   - `test` job runs headless `pytest` and resolves `outputs.version` and `outputs.tag` (`v<VERSION>`) once for all downstream build jobs.
   - Builds native OS installers only (no duplicate raw binaries): Windows (`*-Setup-<ver>.exe`), macOS (`*-<ver>.dmg`), Debian/Ubuntu (`*_<ver>_amd64.deb`), and Fedora/RHEL (`*-<ver>-1.*.rpm`).
   - Cleans stale tags/releases before publishing versioned release `v<VERSION>` with structured download table (`RELEASE_NOTES.md`) and `SHA256SUMS.txt`.

