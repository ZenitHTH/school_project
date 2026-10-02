# Wiki Revision Log

All architectural updates, refactorings, and knowledge ingestions are tracked here.

## [2026-10-01] init | Wiki created
- Scaffolding of LLM Wiki for School Project.
- Cataloged modular QML components (`apps/common_qml`).
- Documented Rust-style `Result[T, E]` type and warning propagation in core importers/adapters.
- Documented SQLite schema, FTS5 trigram search, and air-gapped snapshot sync.

## [2026-10-01] fix | QML Dialog Centering & Modal Bounds
- Fixed dialog centering in `apps/librarian_management_app/qml/dialogs/` (`BookActionDialogs.qml`, `CategoryActionDialogs.qml`) and `StudentActionDialogs.qml` by adding `anchors.fill: parent` to root items.
- Added `modal: true`, `closePolicy: Popup.CloseOnEscape`, and responsive width constraints across all modal dialogs.
- Verified 0 undefined-to-bool warnings across all apps.

## [2026-10-02] feat | Multi-Platform Setup Installers (.deb, .rpm, setup.exe, .dmg)
- Added Debian package generator (`packaging/installers/deb/build_deb.sh`) using native `dpkg-deb` with dynamic arch detection and desktop entry.
- Added RPM package generator (`packaging/installers/rpm/build_rpm.sh`) using `rpmbuild` with containerized build.
- Added Inno Setup Windows template (`packaging/installers/windows/installer.iss`) for `setup.exe` generation with Start Menu & Desktop shortcuts.
- Added macOS Apple disk image builder (`packaging/installers/macos/create_dmg.sh`) using native `hdiutil` UDZO compression.
- Verified `.deb` and `.rpm` build, install, launch, and uninstall across Ubuntu 22.04, Ubuntu 24.04, Ubuntu Devel (26.04), and Fedora 44 in Podman containers.
- Updated `.github/workflows/build.yml` to package and publish installers alongside portable distributions.

## [2026-10-02] audit | Wiki Health Audit & Gap Resolution
- Ran full link verification audit across `wiki/index.md`.
- Authored missing documentation pages:
  - `wiki/database/encryption-and-security.md`: PBKDF2 PIN hashing, 16-byte salt, lockout threshold, and SQLCipher fallback.
  - `wiki/services/student-service.md`: StudentService, EnrollmentService, search parser, and legal status state transitions.
  - `wiki/services/library-services.md`: CatalogService, LoanService, FineService, ReservationService, LibraryPolicy rules, and ReportLab A4 barcode generator.
- 100% of wiki index link targets are now valid and reachable.

## [2026-10-02] fix | Linux Software Rendering Fallback for Legacy Intel iGPUs
- Updated `apps/common_linux_env.py` to auto-configure `LIBGL_ALWAYS_SOFTWARE="1"`, `QT_QUICK_BACKEND="software"`, and `QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)`.
- Guarantees immediate launch on Linux machines with legacy Intel iGPUs lacking modern OpenGL/GLX drivers without manual terminal exports.
- Verified test suite passes 185/185 tests in `tests/test_linux_env.py`.

## [2026-10-02] fix | RPM Packaging Script Path Resolution
- Resolved `rpmbuild` failure in Fedora container where `%install` could not resolve relative `dist/LibrarianManagement`.
- Updated `packaging/installers/rpm/build_rpm.sh` to resolve and inject absolute binary path (`ABS_DIST_BIN_PATH`).
- Added unit test in `tests/test_spec_exclusions.py`.

## [2026-10-02] fix | Windows Inno Setup Installer Path Resolution
- Fixed Inno Setup build failure in `.github/workflows/build.yml` where relative `dist/StudentManagement.exe` was evaluated relative to `packaging/installers/windows/`.
- Injected absolute `${{ github.workspace }}` path for `/DSourceExe` and `/DOutputDir`.
- Updated default relative fallbacks in `packaging/installers/windows/installer.iss` to point to `..\..\..\dist\`.



