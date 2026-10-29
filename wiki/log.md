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
## [2026-10-15] fix | Pure-Stdlib Code128 PDF Generator & Barcode Lookup
- Replaced external `python-barcode`/`reportlab` dependencies in `label_service.py` with pure-stdlib ISO/IEC 15417 Code128-B + PDF 1.4 vector generator.
- Escaped PDF text delimiters `(`, `)`, `\` and mapped out-of-range non-ASCII chars without crash.
- Defaulted empty `barcodes_csv` to 1 copy in `LibrarianAdminAdapter.addBook` and supported int/str in `addCopies`.
- Implemented case/dash-insensitive barcode lookup and ISBN fallback in `book_repo.get_copy_by_barcode`.
- Fixed argument binding order in `BarcodeGeneratorView.qml`.

## [2026-10-15] chore | Repo Cleanup: Removed Dead Files, Duplicate Docs & Unused Specs
- Removed 4 duplicate root docs (`application_layer_design.md`, `database_layer_design.md`, `design_doc.md`, `ui_layer_design.md`).
- Removed 2 unused root scripts (`query_lm_studio.py`, `seed_sample_students.py`).
- Removed 3 unused `packaging/*_windows.spec` files superseded by unified cross-platform specs.
- Removed zero-import dead modules `core/library/models.py` and `core/shared/errors.py`.
- Added exclusion regression test in `tests/test_spec_exclusions.py`.

## [2026-10-15] refactor | Centralized QML Sanitizer & File URL Normalizer
- Extracted shared `NUMERIC_KEYS`, `_sanitize_for_qml`, and `normalize_file_path` into `core/shared/mock_qt.py`.
- Fixed boolean preservation in `_sanitize_for_qml` to prevent `bool` values being coerced to integers.
- Supported percent-encoded Thai `file://` URLs in `normalize_file_path`.
- Cleaned up duplicate implementations across `StudentAdminAdapter`, `LibrarianAdminAdapter`, and `BoothAdapter`.

## [2026-10-15] perf | Single-Pass Student Search Join & FTS5 Query Optimization
- Replaced correlated per-row `max(e2.id)` enrollment subqueries in `student_repo.py` with single-pass `latest_e` join.
- Replaced triple FTS5 `MATCH` queries per student row with single `LEFT JOIN` on `students_fts`.
- Fixed parameter alignment when combining search query with `grade_level` and `room` filters.
- Guaranteed only latest semester enrollment is matched during student search.

## [2026-10-15] perf | Batched Snapshot Sync & Composite Book Copy Index
- Added migration `0009_copies_book_status_idx.sql` creating composite index `idx_copies_book_status` on `book_copies(book_id, status)`.
- Batched student and enrollment upserts in `apply_sync` using `local_cur.executemany` instead of row-by-row loops.
- Sorted `student_id_changes` by `id ASC` to preserve chronological renumbering order during snapshot synchronization with active loans.

## [2026-10-15] fix | Post-Review Path Normalization, QML Slots & Search DRY
- Fixed DB path resolution in `booth_app/main.py` to target canonical `SMTE-LibrarianManagement` without creating misspelled ghost directories.
- Normalized `file://` URLs in `LibrarianAdminAdapter.exportLabelsPdf` and added fallback to system temp dir when `/tmp` is missing.
- Aligned `BookActionDialogs.qml` slot calls and explicit `@Slot(int, str)` / `@Slot(int, int)` overloads in `LibrarianAdminAdapter.addCopies`.
- Deduplicated student search and count SQL query construction into shared `_build_student_search_clauses` in `data/repositories/student_repo.py`.

## [2026-10-16] ci | Standard CI & Tag-Driven Release Pipeline
- Replaced monolithic push-to-main `build.yml` with fast test-only `ci.yml` (on main pushes/PRs) and tag-driven `release.yml` (`v*.*.*` and `workflow_dispatch`).
- Added test gate requiring pytest suite pass before triggering 4-OS installer builds.
- Dynamically propagates semantic version from tag (`${GITHUB_REF_NAME#v}`) to all installer scripts.
- Preserved macOS `.app` framework symlinks via `ditto -c -k --sequesterRsrc --keepParent`.
- Isolated Windows Inno Setup `AppId` per application name to prevent uninstall key overwriting.
- Sanitized RPM pre-release version hyphens with tildes (`${VERSION//-/\~}`).
- Automated generation of `SHA256SUMS.txt` and GitHub Releases with release notes.

## [2026-10-16] feat | Book Registration Split View & Dedicated Barcode Printout Page
- Repurposed Tab 6 (`BarcodeGeneratorView.qml`) into 2-column split view combining book registration (auto-saving deterministic barcodes to SQLite) and category grouping management with live combo sync.
- Repurposed Tab 7 (`CategoryManagementView.qml`) into dedicated Barcode Printout Generator supporting search, individual book selection, and Print All A4 PDF export.
- Added `book_repo.list_books_with_barcodes` and `LibrarianAdminAdapter.getBooksWithBarcodes` excluding retired/disposed copies.
- Maintained 100% test coverage with automated UI verification for split view and selectable printing.

## [2026-10-16] fix | Multi-Copy Barcode Registration, Edit Copy Sync & Printout Row Action
- Resolved Mode 1 existing book combo index reset and size collapse on Page 6 by preserving selection and adding implicitHeight constraints.
- Enabled top-up copy count adjustment in Mode 0 and added `+5` stepper smart increment (`1 -> 5`).
- Added `editBookCopiesInput` to `editBookDialog` in `BookActionDialogs.qml` allowing total copies adjustment directly from Catalog Edit.
- Replaced static grey `Code128` text on printout rows with direct `+ เพิ่มเล่ม` button and multi-barcode list display.
- Verified 5-copy book PDF export produces all 5 physical barcodes in output PDF.

## [2026-10-16] ci | Dev vs Main Branch CI/CD Separation
- Configured `.github/workflows/ci.yml` to run fast test suite only on `dev` pushes and PRs (`main`, `dev`) without building desktop packages.
- Configured `.github/workflows/release.yml` to build and publish all desktop packages (`.exe`, `Setup.exe`, `.dmg`, `.deb`, `.rpm`, `.tar.gz`, `SHA256SUMS.txt`) when pushing/merging to `main`, pushing `v*.*.*` tags, or via `workflow_dispatch`.
- Organized git branches with dedicated `dev` branch for active development and `main` for release builds.

## [2026-10-23] fix | Audit Critical Bug Fixes & Code Quality Hardening
- Fixed offset-naive vs offset-aware return timestamp comparison crash in `LoanService.return_book`.
- Added `("active", "graduated")` transition in `core/student/models.py` and updated `EnrollmentService.promote_students` to graduate Grade 6 seniors.
- Added LIKE fallback for <3 char search terms in `book_repo.search_books` to bypass FTS5 trigram 0-result bug.
- Ensured deterministic `out_conn.close()` in `data/sync/export.py` on export failures.
- Closed OpenPyXL workbooks with `try...finally: wb.close()` across XLSX importers.
- Sanitized dictionary returns across all UI adapters (`BoothAdapter`, `LibrarianAdminAdapter`, `StudentAdminAdapter`) using `_sanitize_for_qml` to prevent QML null property crashes.
- Centralized `format_barcode` in `core/library/policy.py` and eliminated N+1 query in `book_repo.list_books_with_barcodes` with single batched `IN (...)` query.
- Timestamped backup salt file to match backup DB filename in `data/db.py:backup_database`.
- Cleaned up SQLite connection fixtures and open file handles across test suite to eliminate all `ResourceWarning` leaks under Python 3.14.

## [2026-10-29] ci | Canonical Setup Version (1.1.0) & Clean Versioned GitHub Releases
- Added canonical `VERSION` (`1.1.0`) and `core/shared/version.py` (`APP_VERSION`), wired into `installer.iss`, `build_deb.sh`, `build_rpm.sh`, `create_dmg.sh`, PyInstaller `.spec` files, and `QGuiApplication.setApplicationVersion`.
- Refactored `.github/workflows/release.yml` to resolve `version` and `tag` (`v<VERSION>`) once in the `test` job, publish only clean native OS installers (`Setup.exe`, `.dmg`, `.deb`, `.rpm` + `SHA256SUMS.txt`), delete stale `latest` pre-release clutter, and generate a structured Markdown download table.
