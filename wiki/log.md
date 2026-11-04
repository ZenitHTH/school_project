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
## [2026-11-04] fix | UI Invariants & Typography Double-Scaling Resolution (Audit Remediation)
- **Typography Double-Scaling Elimination**:
  - `apps/common_qml/Typography.js`: Added baseline normalization (`extractBaselineSize` & `recordBaseHeight`) to divide active scale factor (`obj.font.pixelSize / currentFactor`) upon recording defaults for lazily created QML delegate items. Prevents double-multiplication (1.5 * 1.5 = 2.25x) and ensures exact restoration on 100% reset.
- **Rule 6 Responsive QML Heights & Delegate Lifecycle**:
  - `StudentSearchView.qml`: Converted hardcoded table header and delegate heights to dynamic `implicitHeight` with `height: implicitHeight`, bound font sizes to `window.fontScale`, added `Component.onCompleted: Typography.applyToItem(this)`.
  - `ActiveLoansView.qml`: Replaced hardcoded height with dynamic `implicitHeight: Math.max(54, Math.round(rowContent.implicitHeight + 16))`, added text elision and delegate lifecycle hook.
  - `FinesManagementView.qml`: Replaced hardcoded height with dynamic `implicitHeight: Math.max(54, Math.round(rowContent.implicitHeight + 16))`, added Typography lifecycle hook.
  - `AuditLogView.qml`: Converted delegate to dynamic `implicitHeight: Math.max(48, Math.round(rowContent.implicitHeight + 14))`, added Typography hook.
  - `BookActionDialogs.qml`: Converted barcode confirmation delegate to dynamic `implicitHeight: Math.max(30, Math.round(row.implicitHeight + 8))`.
  - `ExcelImportView.qml`: Converted diff items delegate to dynamic `implicitHeight: Math.max(36, Math.round(diffRowContent.implicitHeight + 10))`.
  - `BookInventoryRightPane.qml`: Set category item minimum touch targets to ≥ 24x24 px, made `incomingBookPreviewCard` dynamic height (`Math.max(185, previewCol.implicitHeight + 24)`), and updated `inventorySummaryBadge` to dynamic implicitHeight.
- **Accessibility & Contrast**:
  - `EditBookDialog.qml`: Updated strikethrough/delete tag text color on `#fee2e2` background from `#ef4444` to `#991b1b` (WCAG AA > 6:1 contrast ratio) and removed fixed button height.
- **Layout Overflow Resiliency**:
  - `CirculationDeskView.qml`: Added `wrapMode: Text.Wrap` and `Layout.fillWidth: true` to `deskStatusText`.
  - `CategoryManagementView.qml`: Replaced fixed heights on metric cards, toolbar, and PDF banner with dynamic `implicitHeight` bound to content; widened filter combo for high font scales.
  - `StudentManagement Main.qml`: Bound sidebar width reactively to `(settingsView ? (settingsView.currentFontSize / 14.0) * settingsView.currentUiScale : 1.0)`.
  - `SettingsView.qml`: Converted status preview badge to dynamic `implicitHeight: Math.max(28, Math.round(badgeTxt.implicitHeight + 8))`.
- **Testing**: Added `tests/test_ui_responsive_delegates.py`. 100% test pass rate (291/291 passed).

## [2026-11-04] fix | Reactive Table & Delegate Typography Scaling (Lazy Delegate Lifecycle Fix)
- Resolved issue where inventory and printable books tables remained at default tiny sizes (10-12px font, 44-48px rows) when fonts were scaled to 18-24px:
  - Root Cause: Qt Quick `ListView` instantiates delegate instances lazily/asynchronously upon model population (`model.append(...)`), which bypassed initial tree traversal.
  - `apps/librarian_management_app/qml/Main.qml` & `apps/student_management_app/qml/Main.qml`:
    - Exposed reactive typography properties on root window: `fontScale`, `appFontFamily`, `appFontSize`.
  - `apps/common_qml/Typography.js`:
    - Added module-level `currentConfig` caching and exported `applyToItem(item)` and `scale(basePx)` functions for live delegate lifecycle attachment.
  - `BookInventoryRightPane.qml`:
    - Re-anchored table header to dynamic line-height: `implicitHeight: Math.max(28, Math.round(invHeaderRow.implicitHeight + 8))` and bound header text sizes to `window.fontScale`.
    - Added `Component.onCompleted: Typography.applyToItem(this)` and dynamic `implicitHeight: Math.max(48, Math.round(invRowContent.implicitHeight + 14))` to row delegate.
    - Added `onCountChanged` synchronization hook to `inventoryBooksList`.
  - `CategoryManagementView.qml`:
    - Re-anchored table header to dynamic line-height: `implicitHeight: Math.max(32, Math.round(catHeaderRow.implicitHeight + 8))` and bound header texts to `window.fontScale`.
    - Added `Component.onCompleted: Typography.applyToItem(this)` and dynamic `implicitHeight: Math.max(50, Math.round(barcodesRow.implicitHeight + 14))` to row delegate.
    - Added `onCountChanged` synchronization hook to `genBarcodesList`.
  - `BookCatalogView.qml`:
    - Converted row delegate to dynamic `implicitHeight: Math.max(64, Math.round(catalogRowLayout.implicitHeight + 20))` with `Component.onCompleted: Typography.applyToItem(this)` and `window.fontScale` bindings.
    - Added `onCountChanged` synchronization hook to `catalogList`.
  - `tests/test_ui_overlap_and_layout.py`:
    - Added automated unit tests `test_inventory_books_list_delegate_scales_with_font_size` and `test_category_management_delegate_scales_with_font_size`.
- All 287 tests passing across the workspace.

## [2026-11-04] fix | Typography Scaling Layout Bounds & Text Elision Across Navigation and Tables
- Resolved text and button/pill overflow and collisions under dynamic typography scaling (18-24px, 125%-150% UI scale):
  - `apps/librarian_management_app/qml/Main.qml`:
    - Responsive sidebar width: `Layout.preferredWidth: Math.max(260, Math.min(340, Math.round(260 * Math.max(1.0, (settingsView ? (settingsView.currentFontSize / 14.0) * settingsView.currentUiScale : 1.0)))))`.
    - `NavBtn`: Added `rightPadding: 12`, `elide: Text.ElideRight`, and `clip: true` to prevent labels spilling out of button pill borders.
  - `apps/student_management_app/qml/Main.qml`:
    - Responsive sidebar width: `Layout.preferredWidth: Math.max(260, Math.min(340, Math.round(260 * Math.max(1.0, (baseFontSize / 14.0) * (settingsView ? settingsView.currentUiScale : 1.0)))))`.
    - Navigation Repeater delegate: Added `elide: Text.ElideRight`, `clip: true`, and `Layout.fillWidth: true`.
  - `apps/librarian_management_app/qml/views/BookInventoryRightPane.qml`:
    - Re-anchored header row with `Layout.fillWidth: true`, `elide: Text.ElideRight` on title, and `Layout.alignment: Qt.AlignRight` on `btnGoToPrintPage` to keep the button inside card boundaries.
    - Staged book copy count badge: dynamic `implicitHeight: Math.max(22, Math.round(incomingCopyCountText.implicitHeight + 4))` and `implicitWidth: Math.round(incomingCopyCountText.implicitWidth + 12)` with `Layout.preferred*` bindings.
    - Category tag delegate: dynamic `implicitHeight: Math.max(28, Math.round(catRow.implicitHeight + 6))` and `implicitWidth: Math.round(catRow.implicitWidth + 12)`.
  - `apps/librarian_management_app/qml/views/CategoryManagementView.qml`:
    - Category & copy count pills: dynamic `implicitHeight: Math.max(24, Math.round(pillText.implicitHeight + 6))` with explicit parent width bounds (`width: parent.width - 8`), `horizontalAlignment: Text.AlignHCenter`, and `elide: Text.ElideRight`.
    - `+ เล่ม` button: dynamic `implicitHeight: Math.max(28, Math.round(font.pixelSize + 14))` replacing hardcoded 26px height.
  - `tests/test_ui_overlap_and_layout.py`:
    - Expanded test suite to 8 tests covering sidebar width expansion, text elision, right-pane print button card bounding, category/copy count pill heights, and student sidebar bounds.
- All 285 tests passing across the workspace.

## [2026-11-04] fix | Sidebar NavBtn Height Bounding & Active Border Pill Clipping
- Fixed layout collapse in `apps/librarian_management_app/qml/Main.qml` where sidebar `NavBtn` components were rendered with an 8px tall active border pill clipping through button text:
  - Re-anchored `component NavBtn` with `implicitHeight: Math.max(38, Math.round(navText.implicitHeight + 18))` and `Layout.preferredHeight: implicitHeight`, ensuring Qt Quick `ColumnLayout` properly allocates vertical bounds (>= 38px) rather than collapsing to default 8px padding.
  - Linked `background: Rectangle` to `implicitHeight: navBtnRoot.implicitHeight` to bound the rounded pill border around the entire label.
  - Adjusted sidebar `ColumnLayout` spacing from 12 to 8 to maintain balanced vertical rhythm.
  - Added automated layout regression test `test_librarian_sidebar_nav_btn_height_and_bounds` to `tests/test_ui_overlap_and_layout.py` (5/5 passing).
- All 282 tests passing across the workspace.

## [2026-11-04] fix | High-Scale Typography Layout Resiliency & Text-Button Overlap Prevention
- Resolved text and button/textbox collision issues occurring at higher font sizes (18-24px) or UI scaling factors (125%-150%):
  - `BookInventoryRightPane.qml`: Re-architected inventory header area into a 2-row layout separating the title/badge row from the search textbox and refresh button row, guaranteeing zero horizontal collisions regardless of title text length.
  - `CirculationDeskView.qml`: Moved `checkoutStudentName` to its own dedicated row below `studentLookupInput` and `btnLookupStudent`, and replaced fixed 120px/140px card heights with dynamic `implicitHeight` to prevent text pushing into and overlapping the input box and buttons.
  - `EditBookDialog.qml`: Decomposed copy adjustment stepper into a 2-row column separating the label from stepper `-`/`+` and quick delta chips with responsive `preferredHeight` and `preferredWidth`. Made feedback banner dynamically adapt to text content height with `wrapMode: Text.Wrap`.
  - `StyledSearchField.qml`: Replaced hardcoded 38px height with dynamic `Math.max(38, Math.round((font.pixelSize || 14) * 2.2))` ensuring text glyphs never clip borders.
  - `SettingsView.qml`: Replaced rigid 200px label widths with responsive `minimumWidth: 160`, `preferredWidth: Math.max(180, implicitWidth)`, and `wrapMode: Text.Wrap` preventing labels from spilling over dropdowns and sliders.
  - `Typography.js`: Added safe control height scaling (`applyHeightScale`) that adjusts `implicitHeight` proportionally for buttons and text inputs during live tree traversal.
- Added regression test suite `tests/test_ui_overlap_and_layout.py` (4/4 passing). All 281 tests passing.

## [2026-11-04] feat | Built-in Font Assets Bundling & Runtime Registration
- Bundled full font binary assets into `apps/common_qml/fonts/`:
  - `NotoSansThai-Regular.ttf` & `NotoSansThai-Bold.ttf`
  - `THSarabunNew.ttf` & `THSarabunNew-Bold.ttf`
  - `THSarabun.ttf` & `THSarabun-Bold.ttf`
  - `Tahoma.ttf` & `Tahoma-Bold.ttf`
  - `SukhumvitSet.ttc`
- Implemented `get_bundled_fonts_dir()` and `register_bundled_fonts()` in `core/shared/mock_qt.py`:
  - Dynamically registers font files via `QFontDatabase.addApplicationFont`.
  - Configures `QFont.insertSubstitution` so `"Noto Sans"` automatically aliases to `"Noto Sans Thai"` and `"Sarabun"` to `"TH Sarabun New"`.
  - Integrated into application entry points (`apps/librarian_management_app/main.py`, `apps/student_management_app/main.py`, `apps/booth_app/main.py`) and `apply_qt_app_font`.
- Created `apps/common_qml/BundledFonts.qml` with `FontLoader` declarations and registered in `apps/common_qml/qmldir`.
- Updated PyInstaller spec files (`packaging/librarian_management.spec`, `packaging/student_management.spec`, `packaging/booth_app.spec`) to include `apps/common_qml/fonts/*` and `apps/common_qml/*.js`.
- Added test suite `tests/test_bundled_fonts.py` (4/4 passing) and verified all 277 tests pass.

## [2026-11-04] feat | Visual System Settings Menu & Global Typography Traversal (Noto Sans)
- Created shared `SettingsView.qml` in `apps/common_qml/` providing runtime UI customization:
  - Added `"Noto Sans"` along with Thai & system font presets (`System Default`, `Noto Sans`, `Sarabun`, `TH Sarabun New`, `Segoe UI`, `Sukhumvit Set`, `Tahoma`).
  - Font size adjustment slider and steppers constrained between 10px and 24px (default 14px).
  - UI scaling sliding bar restricted to 50% - 150% (0.5x - 1.5x) with preset chips (75%, 100%, 125%, 150%).
  - Live preview card rendering sample headings, paragraph, metadata, and badge tags reacting immediately to slider/combo adjustments.
  - Reset to factory defaults button (`resetToDefaults()`).
- Created `apps/common_qml/Typography.js` (.pragma library) to record baseline fonts and recursively traverse QML component trees, dynamically applying user-selected font family and scale factors to all labels, inputs, and buttons while preserving monospace elements.
- Implemented `setAppFont` slots in `LibrarianAdminAdapter` and `StudentAdminAdapter` via `core.shared.mock_qt.apply_qt_app_font` to propagate active typography to `QGuiApplication.instance().setFont(...)` so newly instantiated delegates inherit active styles.
- Wired `targetWindow: window` and `onCurrentIndexChanged` synchronization hooks in both Librarian and Student `Main.qml`.
- Followed Robert C. Martin's Clean Code principles: all files strictly under 200 lines (`Typography.js` 77 lines, `SettingsView.qml` 189 lines, `student_admin_adapter.py` 196 lines, `test_ui_settings_view.py` 192 lines), all functions under 20 lines, max 3 arguments, max 2 levels of nesting, and zero unhandled exceptions.
- Authored test suite `tests/test_ui_settings_view.py` (7/7 passing) and verified entire test suite (273/273 passing).

## [2026-11-03] feat | ISBN Duplicate Detection & Registration Form Auto-Clear
- Added `CatalogService.get_active_book_by_isbn` and `LibrarianAdminAdapter.checkBookByIsbn` to query existing active books by normalized ISBN.
- Implemented real-time duplicate ISBN detection in `BarcodeGeneratorView.qml` and `BookActionDialogs.qml` to prevent unique constraint failures and warn librarians before duplicate book creation.
- Enhanced `BarcodeGeneratorView.qml` to auto-clear registration fields (`clearRegistrationForm`) and refocus the ISBN scanner input on save, enabling continuous barcode gun scanning.
- Modularized QML preview and execution logic into small, single-responsibility functions adhering to Robert C. Martin's Clean Code principles.
- Added comprehensive unit and UI tests in `tests/test_isbn_duplicate_and_form_clear.py` and `tests/test_ui_isbn_scanning.py` (266/266 passing).

## [2026-11-03] fix | Catalog Layout Truncation, Row Factory Resiliency & Add Copies Debounce
- Fixed delegate text horizontal layout explosion in `BookCatalogView.qml` with responsive width (`fillWidth: true`, min: 280, pref: 380), `elide: Text.ElideRight`, and `maximumLineCount: 1`.
- Made `book_repo.get_book_copy_breakdown` resilient to arbitrary row factories (supporting both `sqlite3.Row`/dict and standard `tuple` rows) via `_extract_copy_item`.
- Added `isSubmitting` debounce flag and disabled state to `addCopiesDialog` in `BookActionDialogs.qml` to prevent duplicate submissions on rapid Enter key dispatch.
- Added regression test suite in `tests/test_repro_catalog_edge_cases.py` (248/248 passing).

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

## [2026-10-29] feat | Live Book Entry Preview, Inventory Grid Table & Dedicated Barcode Print Studio
- Modularized Tab 6 right pane into `BookInventoryRightPane.qml`:
  - Added live preview card (`incomingBookPreviewCard`) dynamically updating title, author, ISBN, category, shelf, copy count, and preview barcodes (`SMTE-xxxxx-01`...) as user types on the left pane.
  - Added bordered inventory stock grid table (`inventoryBooksList` / `inventoryBooksModel`) displaying current library books with search filtering and direct inline actions (`+ เพิ่มเล่ม`, `✏️ แก้ไข`, `🗑️ ลบ`).
  - Added direct navigation button `btnGoToPrintPage` to jump to dedicated barcode print studio.
- Upgraded Tab 7 (`CategoryManagementView.qml`) into Dedicated Barcode Print Studio:
  - Added live print queue summary cards (`selectedBooksCountText`, `selectedStickersCountText`, and `estimatedPagesText` calculating required A4 3x8 sheets).
  - Added category filter combobox (`barcodeCategoryFilterCombo`) and selection checkboxes per row.
  - Added catalog navigation button `btnOpenPrintPage` from Tab 0.
- Maintained 100% test coverage with automated UI verification in `tests/test_ui_librarian.py` (213/213 passed, 0 warnings).

## [2026-10-29] feat | Modern Edit Book Studio & Copy Count Corrections
- Extracted and redesigned `EditBookDialog.qml` with high-aesthetic styling:
  - Two structured visual cards for bibliographic metadata and copy inventory adjustments.
  - Added live copy status pills (Available, On Loan, Total).
  - Added interactive steppers (`[-]`, `[+]`, `+1`, `+5`, `-1`) and dynamic feedback banners for increasing or reducing copies.
  - Added live barcode tray with real-time deletion strikethrough previews.
- Implemented copy reduction and inventory adjustment in backend:
  - Added `book_repo.get_book_copy_breakdown` and `book_repo.remove_excess_copies` to safely prune unloaned available copies when entered by mistake.
  - Added `CatalogService.adjust_total_copies` with guardrails preventing reductions below active on-loan counts.
  - Exposed `LibrarianAdminAdapter.adjustBookCopies` and `LibrarianAdminAdapter.getBookCopiesDetail` with QML sanitization.
- Maintained 100% test coverage with 217 passing unit and UI tests.

## [2026-10-29] ci | Release v1.1.1 & Single-Command Version Bump CLI
- Bumped project version to `1.1.1` via single-command workflow (`python scripts/bump_version.py patch`).
- Introduced `scripts/bump_version.py` and `python -m core.shared.version`:
  - Added duplicate tag collision check querying `git tag --list` to strictly prevent releasing existing tags (e.g. `v1.1.0`).
  - Added automatic SemVer calculations (`patch`, `minor`, `major`) and explicit version targets.
  - Automatically synchronizes `VERSION` and `packaging/installers/windows/installer.iss` (`#define AppVersion`).
- Decoupled packaging shell scripts (`build_deb.sh`, `build_rpm.sh`, `create_dmg.sh`) and PyInstaller `.spec` files from hardcoded version literals.
- Maintained 100% test coverage with 224 unit and UI tests.

## [2026-11-02] feat | ISBN Metadata Lookup & Non-Overwriting Auto-fill
- Implemented `IsbnLookupService` (`core/library/services/isbn_service.py`) supporting ISBN-10/13 normalization, validation, SQLite cache (`isbn_cache` and `books` table fallback), and National Library of Thailand (NLT) web scraping using pure standard library (`urllib.request` + `html.parser`).
- Exposed `LibrarianAdminAdapter.fetchIsbnMetadata` slot returning sanitized JSON results.
- Added `[🔍 ดึงข้อมูล]` action buttons in `BarcodeGeneratorView.qml` (Tab 6) and `BookActionDialogs.qml` (`addBookDialog`) with non-overwriting autofill (preserves existing user-typed Title/Author).
- Added comprehensive unit tests in `tests/test_isbn_service.py` and UI tests in `tests/test_ui_librarian.py`.

## [2026-11-02] feat | ISBN Autofill Overwrite on Match & Auto-Fetch on Scan
- Updated autofill policy in `BarcodeGeneratorView.qml` and `BookActionDialogs.qml` to overwrite existing Title/Author when matching database metadata is retrieved, while safely preserving existing text on lookup failure.
- Added "ค้นหาอัตโนมัติเมื่อสแกน (Auto-fetch on scan)" toggle checkbox (`chkAutoFetchIsbn` and `chkDialogAutoFetchIsbn`, checked by default).
- Added barcode scanner enter (`onAccepted`) trigger and 13-digit debounce timer (300ms) while retaining manual `[🔍 ดึงข้อมูล]` action buttons.
- Updated UI test assertions in `tests/test_ui_librarian.py` covering match overwrite, failure text preservation, and auto-fetch controls.
- Maintained 100% test coverage across all services and adapters.

## [2026-11-02] ci | Release v1.2.0 & ISBN Lookup Integration
- Bumped project version to `1.2.0` via `scripts/bump_version.py minor`.
- Synchronized `VERSION` and Inno Setup Windows installer (`installer.iss`).
- Shipped 3-provider ISBN lookup pipeline (NLT Primo VE -> SE-ED Web-BFF -> Open Library), auto-fetch on scan, and match overwrite into release build.
- Maintained 100% test coverage across 238 unit and UI tests.

## [2026-11-02] ci | Restrict Builds to Main & Fix Linux Runner Exit Code 134
- Removed `.github/workflows/ci.yml` so GitHub Actions never trigger on `dev` branch pushes, reserving packaging and CI strictly for `main`.
- Upgraded `release.yml` runner Python version from 3.11 to 3.12 across all jobs (`test`, `build-windows`, `build-macos`, `build-ubuntu`). This prevents upstream Shiboken6 / PySide6 refcount leaks on `None` (`none_dealloc: deallocating None`, exit code 134) via Python 3.12 PEP 683 immortal objects.
- Guarded `QCoreApplication.instance() is not None` in `isbn_service.py` before pumping events.
- Added timer stop guards in `BarcodeGeneratorView.qml` and `BookActionDialogs.qml` (`Component.onDestruction` and `fetch*` invocations) to prevent stray timer executions during test teardown.
- Flushed `qapp.processEvents()` in UI test fixtures before and after `engine.deleteLater()`.
- Updated `tests/test_spec_exclusions.py` verifying `ci.yml` absence and `release.yml` triggers and Python 3.12 configuration.
- 100% test pass (238/238 passed).

## [2026-11-03] feat | Arabic Digit Filtering & "ลืมเปลี่ยนภาษา" Warning for ISBN Lookup
- Added `is_arabic_isbn` validator in `core/library/services/isbn_providers.py` to ensure only Arabic digits (0-9, hyphens/spaces, and ISBN-10 check digit X) trigger ISBN searches.
- Extracted `core/library/services/seed_detail_parser.py` helper module adhering to Clean Code file length standard (< 200 lines).
- Added early guard clause in `IsbnLookupService.lookup` returning `Err("ลืมเปลี่ยนภาษา")` when non-Arabic/Thai characters or Thai numerals (`๑-๙`) are supplied.
- Updated `BarcodeGeneratorView.qml` and `BookActionDialogs.qml` with `isArabicIsbn` validation:
  - On `onTextChanged`, immediately shows `"✗ ลืมเปลี่ยนภาษา"` when Thai keyboard layout input is detected without firing debounce fetch timers.
  - On `fetchIsbnAndAutofill` / `fetchDialogIsbnAndAutofill`, skips remote fetch and retains `"✗ ลืมเปลี่ยนภาษา"`.
  - Clears warning automatically when text is cleared or corrected.
- Added comprehensive unit and UI tests in `tests/test_isbn_service.py` and `tests/test_ui_librarian.py`.
- 100% test pass across full test suite (242/242 passed).

## [2026-11-03] fix | Duplicate ISBN Rejection, Accidental Book Purge & Sequence Recycling
- Added `get_book_by_isbn` and `get_active_book_by_isbn` in `data/repositories/book_repo.py` with hyphen/whitespace normalization and enforced active ISBN uniqueness check in `add_book` (`ValueError("Active book with this ISBN already exists")`).
- Enforced duplicate active ISBN check in `CatalogService.add_book` returning `Result.fail("Active book with this ISBN already exists")`.
- Updated `retire_book` in `data/repositories/book_repo.py` to check for loans AND reservations (`_book_has_history`):
  - Books with zero history (accidental entries) are hard-deleted along with their copies and status logs, and `sqlite_sequence` is rewound to the maximum remaining IDs for `books` and `book_copies`, eliminating barcode skips and ID jumps.
  - Books with loan or reservation history remain soft-deleted (`active = 0`), preserving foreign key integrity and audit logs.
- Extracted `_record_copy_retirement_logs` in `book_repo.py` ensuring functions remain strictly under 20 lines.
- Updated `remove_excess_copies` in `data/repositories/book_repo.py` to rewind `book_copies` sequence upon copy deletion.
- Updated `LibrarianAdminAdapter.previewBarcodes` to resolve next `book_id` by querying `sqlite_sequence` with fallback to `MAX(book_id)`, ensuring preview barcodes match SQLite allocation.
- Updated `BarcodeGeneratorView.qml` to prioritize matching existing books by normalized ISBN and title, routing double-scanned books to `addCopies` instead of creating duplicate book records.
- Added comprehensive unit and regression tests in `tests/test_id_jump_repro.py` covering sequence rewind, reservation soft-delete preservation, and real adapter double-scan behavior.
- 100% test pass across all 253 tests.


## [2026-11-04] ci(release) | Release v1.2.3: Dynamic Typography, Responsive QML Layouts & Accessibility
- Bumped version to 1.2.3 across `VERSION` and `packaging/installers/windows/installer.iss`.
- Normalized `Typography.js` baseline size extraction to prevent double-scaling during asynchronous delegate creation.
- Converted hardcoded heights on buttons, badges, table headers, and ListView delegates across Student and Librarian apps to dynamic `implicitHeight` (Rule 6).
- Fixed WCAG AA contrast ratio (> 6:1) in `EditBookDialog.qml` and expanded touch targets in `BookInventoryRightPane.qml`.
- Added automated and adversarial test suites: `tests/test_ui_responsive_delegates.py` and `tests/test_ui_adversarial_scaling.py`.
- 100% test pass across full test suite (301/301 passed).

## [2026-11-04] feat | Settings Persistence & Dialog Placeholder Sizing Invariants
- **Settings Persistence**:
  - Implemented `core/shared/settings_service.py` (`SettingsService`) persisting `font_family`, `font_size`, `ui_scale` to `~/.school_project/settings.json` with fallback defaults using `Result[T, E]`.
  - Exposed `@Slot` methods `saveSettings`, `loadSettings`, and `resetSettings` in `StudentAdminAdapter` and `LibrarianAdminAdapter`.
  - Updated `SettingsView.qml` to auto-load persisted settings on `Component.onCompleted` and added "💾 บันทึกการตั้งค่า (Save Settings)" (`btnSaveSettings`).
  - Extracted `apps/common_qml/SettingsPreviewCard.qml` to keep `SettingsView.qml` modular and strictly under 200 lines.
- **Placeholder & Input Sizing Invariants**:
  - Updated `apps/common_qml/StyledSearchField.qml` with minimum dimensions (`implicitWidth >= 180`, `implicitHeight >= 38`), padding (12px), and vertical alignment to prevent placeholder text truncation under extreme downscaling.
  - Enforced `Layout.fillWidth: true` and `implicitHeight: Math.max(36, Math.round(font.pixelSize * 2.2 || 36))` across all input fields in `StudentActionDialogs.qml` and `BookActionDialogs.qml`.
- Extracted `apps/student_management_app/adapters/roster_import_helper.py` to keep `StudentAdminAdapter` under 200 lines and all functions under 20 lines.
- 100% test pass across full test suite (309/309 passed).

## [2026-11-04] fix | NLT Primo Parallel Title Cleaning & Series Title Prepending
- Extracted `core/library/services/primo_title_cleaner.py` (`compose_primo_title`, `clean_parallel_title`, `clean_series_title`) to keep all files under 200 lines and functions under 20 lines.
- Updated `parse_nlt_primo_json` in `core/library/services/isbn_providers.py`:
  - Strips parallel / English titles matching `\s*=\s*.*$`.
  - Extracts series title from `addata.seriestitle` and `display.series`.
  - Cleans MARC subfield identifiers (`$$Q...`) and prepends series title when not already present at start of title.
- Verified ISBN 9786160443536 resolves to `"เก่งวิทย์ด้วยตัวเองจนคุณครูตกใจ แรงโน้มถ่วง"`.
- 100% test pass across all 320 tests.


## [2026-11-04] ci(release) | Release v1.2.4: Settings Persistence, Dialog Sizing & ISBN Title Series Extraction
- Bumped version to 1.2.4 across `VERSION` and `packaging/installers/windows/installer.iss`.
- Shipped persistent visual settings (`SettingsService`, `SettingsAdapterMixin`, and modular `SettingsView`).
- Shipped WCAG AA contrast `#64748b` in `StyledSearchField` and responsive dialog layout bounds.
- Shipped NLT Primo series title prepending and parallel title cleaning (`primo_title_cleaner.py`).
- 100% test pass across full test suite (323/323 passed).
