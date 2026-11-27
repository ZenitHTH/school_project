# Library Services (`core/library/services/`)

## 1. Overview
The Library domain provides book cataloging, circulation desk operations (checkout, return, renew), fine enforcement, reservations, and printable barcode generation.

---

## 2. Library Policy Configuration (`core.library.policy.LibraryPolicy`)
Configurable rules governing borrowing behavior:
- `loan_duration_days`: 14 days
- `max_active_loans`: 3 books per student
- `max_renewals`: 1 renewal allowed per loan
- `overdue_fine_per_day`: 5.0 THB/day
- `max_overdue_fine`: 200.0 THB cap
- `unpaid_fines_threshold`: 50.0 THB (blocks new checkouts)
- `lost_book_fee`: 150.0 THB default replacement cost
- `BARCODE_PREFIX`: `"SMTE"`

---

## 3. Catalog Service (`core.library.services.catalog_service.CatalogService`)
Manages categories, book titles, and individual physical book copies.

### Key Workflows:
- **Category Hierarchy**:
  - `add_category(name)`, `rename_category(id, new_name)`, `delete_category(id, reassign_to_id)`
- **Auto-Incremented Barcode Generation & Sequence Sync**:
  - Generates barcodes with prefix `SMTE` and zero-padded sequence (e.g. `SMTE-00001-01`).
  - Barcode preview queries `sqlite_sequence` fallback to `MAX(book_id)` to deterministically match SQLite AUTOINCREMENT allocation.
- **Duplicate ISBN Rejection & Normalization**:
  - `add_book` prevents registering active duplicate books sharing the same ISBN (`Result.fail("Active book with this ISBN already exists")`).
  - ISBN lookup is normalized across whitespace and hyphens via `get_active_book_by_isbn`.
- **Accidental Entry Recovery & Sequence Recycling**:
  - `retire_book` checks if a book has any historical or active loans or reservations (`_book_has_history`).
  - Books with zero history (accidental creations) are hard-deleted along with their copies and status logs, and `sqlite_sequence` for `books` and `book_copies` is automatically rewound to prevent barcode/ID jumps.
  - Books with existing loan or reservation history retain soft-delete preservation (`active = 0`), preserving foreign key integrity and audit logs.
  - `remove_excess_copies` similarly rewinds `book_copies` sequence upon copy deletion.
- **Disposal & Copy Lifecycle**:
  - Tracks individual copy status (`available`, `borrowed`, `reserved`, `lost`, `disposed`).

---

## 4. Loan Service (`core.library.services.loan_service.LoanService`)
Handles circulation desk borrowing rules and validation pipeline.

### Checkout Validation Pipeline:
1. **Student Status Check**: Student must exist and be in `active` status.
2. **Unpaid Fines Threshold**: Blocks checkout if student has unpaid fines > `unpaid_fines_threshold` (50 THB).
3. **Active Loans Limit**: Blocks checkout if student already holds `max_active_loans` (3 loans).
4. **Copy Availability**: Verifies copy exists and is currently in `available` status.
5. **Atomic Loan Record**: Creates loan record with due date and transitions copy status to `borrowed`.

### Return & Renew Pipeline:
- **Return (`return_book`)**:
  - Calculates overdue days if returned after `due_date`.
  - Automatically assesses fine via `FineService` if overdue.
  - Updates copy status back to `available` (or `reserved` if pending reservations exist).
- **Renew (`renew`)**:
  - Validates remaining renewals < `max_renewals` via `loan_repo.get_renewal_count` (counted from `activity_log` `loan.renew` entries; preserves schema v9).
  - Extends due date by `loan_duration_days`.
- **Internal structure** (clean-code refactors, 2026-11-09 & 2026-11-12): `checkout` orchestrates `_check_student_eligibility`, `_resolve_checkout_copy`, `ReservationService.fulfill_ready_for_student`, and `_issue_loan` (zero raw `reservations` SQL in `LoanService`). `return_book` delegates overdue-fine assessment to `_assess_overdue_fine` (keeps the same internal error-swallow + `[WARN]` stderr behavior). Public behavior, `Result` shapes, and error messages are unchanged.

---

## 5. Fine Service & Reservation Service
- **Fine Service (`fine_service.py`)**:
  - Assesses overdue fines with `max_overdue_fine` ceiling.
  - Tracks `pending` vs `paid` status.
  - Supports partial or full fine payments and cancellation with audit logging.
- **Reservation Service (`reservation_service.py`)**:
  - Places book-level reservations for students when all copies are checked out.
  - Automatically alerts circulation desk when a reserved book is returned.

---

## 6. Barcode Label Generator (`core.library.services.label_service` & `label_qt_renderer`)
Generates printable A4 PDF sheets (`595.28 × 841.89 pt`) with Code128-B barcode labels, optional book titles, and dashed cut lines.
- **Grid Layout & Inputs**: Configurable 3 columns × 8 rows (24 labels per A4 page). `_prepare_barcode_items` accepts bare barcode strings, `(copy_id, barcode)` 2-tuples, `(copy_id, barcode, title)` 3-tuples, and `{"barcode", "title"}` dicts.
- **ASCII / No-Title Pure-Stdlib Vector Engine (`label_service.py`)**: Zero external dependencies (no `python-barcode`, `Pillow`, or `reportlab`). Emits direct vector PDF 1.4 rectangles (`re f`), dashed cut guides (`[3 3] 0 d`), ISO/IEC 15417 Code128-B bars, and human-readable text with PDF delimiter escaping (`_escape_pdf_literal`), assembled via `_assemble_pdf_document`. `_wrap_ascii_title` fits ASCII titles into 1–4 lines stepping `(7.5, 1)`, `(6.5, 2)`, `(6.0, 3)`, `(5.5, 4)` pt (eliding overflow with `...`), vertically centered inside a fixed `32.0 pt` top title zone in `_render_label_cell` with Code128 bars at a fixed vertical position and height across titled labels.
- **Unicode / Thai Qt Renderer (`label_qt_renderer.py`)**: When `_has_non_ascii_title` detects any non-ASCII character (`ord(ch) > 126`), `export_label_sheet_pdf` delegates to `export_label_sheet_qt_pdf` using Qt `QPdfWriter` (72 DPI A4) and `QPainter` (initializing an offscreen `QGuiApplication` via `_ensure_qt_app` when needed).
  - **Thai Word-Boundary Wrapping**: `_tokenize_title` segments text with `pythainlp.tokenize.word_tokenize(..., engine="newmm")` (character-list fallback if unavailable), and `_fit_title_lines` / `_wrap_tokens` pack tokens into 1–4 lines stepping `(7.5, 1)`, `(6.5, 2)`, `(6.0, 3)`, `(5.5, 4)` pt, eliding the 4th line via `QFontMetricsF.elidedText(..., Qt.ElideRight, max_w)`.
  - **Fixed Barcode Geometry & Centered Title Zone**: `_draw_qt_label_cell` reserves a fixed `32.0 pt` top title zone (`title_zone_h = 32.0`) with the 1–4 wrapped lines centered horizontally and vertically inside it, keeping `_draw_code128_bars` at a uniform `bc_y` and `bc_h` across every cell above the `8.5 pt` bold human-readable barcode label.
- **Librarian Adapter Title Enrichment (`LibrarianAdminAdapter._attach_book_titles`)**: `exportLabelsPdf(barcodes_json, output_path)` runs input items through `_attach_book_titles`, batch-querying `book_copies` joined with `books` for any bare barcode string or dict lacking a `title` while preserving caller-supplied titles.

---

## 7. ISBN Lookup Service (`core.library.services.isbn_service` & `isbn_providers`)
Provides ISBN validation and metadata retrieval for book registration.
- **5-Provider JSON Pipeline (`isbn_providers.py`)**:
  1. **NLT Primo VE REST API** (`nlt.primo.exlibrisgroup.com`): Primary authoritative endpoint for books deposited with the National Library of Thailand. Extracts `title`, `author` (stripped of MARC `$$` subfields and trailing `.`), and `publisher`.
  2. **SE-ED Web-BFF REST API** (`mp-api.se-ed.com/web-bff`): Secondary endpoint for commercial Thai exam-prep, tutor, and publisher books. Verifies SKU in `physicalProduct.variants`, extracts title, and parses the Lexical JSON AST to extract author and publisher.
  3. **Open Library Books API** (`openlibrary.org`): Tertiary endpoint for international and English literature/textbooks.
  4. **Chulabook Store API** (`api.chulabook.com`): 4th provider — exact-barcode search on `GET /products?search=<isbn>&limit=5`, then `GET /products/<id>` detail. See §8.
  5. **Nain Book Store (นายอินทร์, `www.naiin.com`)**: 5th provider (2026-11-12). The Vue SPA serves SSR pages (not blocked by Cloudflare for browser-like `User-Agent` + `Accept` + `Referer` headers):
     - Step 1: `GET /search-result?title=<isbn>` — the page embeds a product JSON array in `<product-list :items='[...]' :default-error='null'>` (HTML-entity-escaped; parsed by `parse_nain_search_items` after `html.unescape`). Rows carry `ProductID`/`ProductName`/`AuthorName`/`PublisherName`/prices — **no ISBN field**.
     - Step 2: `GET /product/detail/<ProductID>` for up to 3 candidates — the page carries a schema.org `Product`/`Book` JSON-LD block (`parse_nain_product_ld`) with `name`/`isbn`/`gtin13`/`sku`/`author`/`publisher`/`offers`; a hit requires the block's normalized ISBN to exactly match the queried ISBN.
     - Same timeout policy as Chulabook: 5 s per request (capped) + one automatic retry per request; fetches go through `_fetch_text` (HTML variant of `_fetch_json`, same logging trail).
- **Two-Tier Authoritative Local Lookup**:
  1. Authoritative local `books` table checked first (`ORDER BY active DESC, book_id DESC`), ensuring active copies take precedence and edits in the catalog are never shadowed by stale cache entries.
  2. Persistent SQLite `isbn_cache` table queried on local catalog miss.
  3. Queries chained remote providers on local miss and populates `isbn_cache` upon successful retrieval.
- **Autofill Overwrite Policy & Re-entrancy Protection**:
  - **Match Found**: When matching metadata is retrieved from local cache or remote providers, QML autofill overwrites any existing `Title` and `Author` fields to ensure newly scanned books receive authoritative catalog metadata.
  - **Error Preservation**: When lookup fails (`cannot fetch data`), user-entered text is preserved intact without deletion or corruption.
  - **Auto-Fetch on Scan Option**: Supported via toggle checkbox (`chkAutoFetchIsbn` in `BarcodeGeneratorView`, `chkDialogAutoFetchIsbn` in `BookActionDialogs`, checked by default). Triggers autofill automatically on scanner enter (`onAccepted`) or when 13 digits are scanned (300ms debounce), while keeping manual `[🔍 ดึงข้อมูล]` buttons accessible.
  - **Qt-Free Service Wait**: `IsbnLookupService._wait_for_future` uses pure-Python bounded polling (`future.result(timeout=...)` + `time.sleep(0.005)`) with zero `PySide6`/`QCoreApplication.processEvents()` calls, avoiding QML binding re-entrancy.
- **Arabic Digit Validation & "ลืมเปลี่ยนภาษา" Layout Protection**:
  - Barcode scanners or manual entry when typing under Thai keyboard layout (Kedmanee: `'1'` -> `'ๅ'`, `'7'` -> `'ึ'`, `'8'` -> `'ค'`, `'9'` -> `'ต'`, etc.) or Thai numerals (`๑-๙`) are detected by `is_arabic_isbn` in `isbn_providers.py`.
  - Non-Arabic characters immediately fail validation with `Err("ลืมเปลี่ยนภาษา")` before any local database or remote network requests are dispatched.
  - In QML views (`BarcodeGeneratorView.qml` and `BookActionDialogs.qml`), `onTextChanged` and fetch handlers display `"✗ ลืมเปลี่ยนภาษา"` to immediately guide librarians to toggle their keyboard layout without triggering remote fetch timeouts.
- **Error Handling**: Network timeouts, non-book tables, redirects, or malformed inputs return `Err("cannot fetch data")` (or `Err("ลืมเปลี่ยนภาษา")` for non-Arabic characters) safely trapped in a Rust-style `Result[Dict[str, str], str]`.

---

## 8. Chulabook Detection & Fetching (`core.library.services.chulabook_service`)
Detects catalog books that exist only in the Chulabook store (ศูนย์หนังสือจุฬาฯ) and auto-fills their metadata from the Chulabook API during registration.
- **Chulabook Store API (4th provider, `isbn_providers.py`)**: `api.chulabook.com` is the store's public REST API — no auth, no cookies, **not** behind the Sucuri JS challenge that blocks `www.chulabook.com` HTML pages.
  - Search: `GET /products?search=<isbn>&limit=5` → `{count, rows[]}`; match requires **exact normalized-barcode equality** (no fuzzy fallback).
  - Detail: `GET /products/<id>` → full record (`isbn`, `name`, `author`, `pub_year`, `edition`, `translator`, `price`, `cover_price`, `detail_th`, …). The API has **no publisher-name field** (only `pbls_code`), so `publisher` is reported as `""` — never fabricated.
  - Request headers: browser `User-Agent` + `Origin`/`Referer: https://www.chulabook.com` (sent via `_fetch_json(..., extra_headers=CHULABOOK_HEADERS)`).
  - Timeout policy: **5 s per request (capped) + one automatic retry per request**. The original 2.5 s step timed out on slow school networks (cold TLS handshake) and looked like "chulabook cannot fetch on Linux Mint". Persistent per-machine failures: run `scripts/diagnose_chulabook.py <ISBN>` there (stdlib-only) — it checks proxy env vars → DNS → TLS/CA store → HTTP, step by step.
- **Fetch logging**: every lookup/detection is traced to a rotating `app.log` (1 MB × 3) in the OS log dir — `~/Library/Logs/SMTE-LibrarianManagement/app.log` (macOS), `~/.local/state/SMTE-LibrarianManagement/logs/app.log` (Linux Mint), `%LOCALAPPDATA%\SMTE-LibrarianManagement\logs\app.log` (Windows). The file shows per-provider `miss`/`HIT` with elapsed times, every HTTP request (URL/status/elapsed), retry warnings with exception types, per-book detection skip reasons, and lookup rejections. Setup: `core/shared/app_logging.py` (`setup_app_logging`, called from Librarian `main.py`); module loggers use the `smte.isbn` namespace.
  - Chain position: **last two** — `NLT Primo → SE-ED → Open Library → Chulabook → Nain Book`. The existing `fetchIsbnMetadata` autofill therefore resolves Chulabook-only and Nain-only ISBNs with no UI change, and successful lookups persist to `isbn_cache`.
- **Detection rule (`detect_chulabook_books(conn, timeout=5.0, workers=8) -> Result[list[dict], str]`)**: a book row is flagged iff `_fetch_chulabook(isbn)` hits **and** the normalized ISBN is absent from `isbn_cache` **and** all three standard providers miss. Invalid/Thai-digit ISBNs are skipped silently; per-row exceptions skip that row; `Err` only when the `books` table is missing. Rows: `{book_id, isbn (normalized), title, author}`.
- **Librarian UI**: `LibrarianAdminAdapter.detectChulabookBooks()` slot (`chulabookCheckStarted`/`chulabookCheckCompleted` signals, `_sanitize_for_qml` on `books[]`) drives the `📕 ตรวจ Chulabook` button in `BookCatalogView.qml` (Tab 0) — status line `chulabookStatusText` + results `Dialog` (`chulabookResultsModel`) listing flagged books. Wired via `window.detectChulabook()` in `Main.qml`. Synchronous slot (house pattern); ~30–60 s for a 200-book catalog.

---

## 9. Book Database Export & Import (`core.shared.db_transfer` & `book_transfer_service`)
Provides checksummed `.sqlite` and `.xlsx` export, diff preview, and atomic `merge` / `replace` import for the library book catalog, with pre-import backups and active-circulation safety guards.

### Shared Bundle Primitives (`core/shared/db_transfer/`)
- **`manifest.py`**:
  - `compute_tables_checksum(tables)`: computes a canonical JSON (`sort_keys=True`, UTF-8) SHA-256 hex digest over sorted table rows.
  - `build_manifest(domain, schema_version, tables)`: generates `{domain, schema_version, checksum, row_counts, created_at}` metadata.
  - `verify_manifest(manifest, expected_domain, tables)`: verifies bundle domain (`"books"`) and SHA-256 checksum via `Result[dict[str, Any], str]`.
- **`sqlite_io.py`**:
  - `write_sqlite_bundle(output_path, manifest, schemas, rows_by_table)`: validates non-symlink/non-directory targets, normalizes `file://` URLs (`normalize_file_path`), writes `transfer_manifest` + parameterized domain tables into a temporary `.sqlite` file, and atomically swaps via `os.replace`.
  - `read_sqlite_bundle(input_path, expected_domain, required_tables)`: opens untrusted bundles read-only via `file:<abspath>?mode=ro` (`uri=True`), enforces `PRAGMA trusted_schema = OFF;`, rejects any `VIEW`, `TRIGGER`, or `CREATE VIRTUAL TABLE` in `sqlite_master`, verifies required tables, and validates the manifest domain & SHA-256 checksum.
- **`xlsx_io.py`**:
  - `write_xlsx_bundle(output_path, sheets)`: atomically writes multi-sheet `.xlsx` workbooks using `openpyxl.Workbook(write_only=True)` + `os.replace`.
  - `read_xlsx_bundle(input_path, required_sheets, max_rows_per_sheet=100_000)`: enforces zip-bomb bounds (`xl/workbook.xml` `<= 10 MB`), streams sheets with `openpyxl.load_workbook(..., read_only=True, data_only=True)`, and validates required sheets.
- **`backup.py`**:
  - `create_pre_import_backup(conn, db_path)`: creates a timestamped backup using SQLite's online `conn.backup()` API under `<db_dir>/backups/<stem>.pre_import_<ts>.sqlite` (copying `.salt` if present).

### Book Transfer Orchestrator (`core.library.services.book_transfer_service`)
- **`export_books_db(conn, output_path, fmt, include_circulation=False) -> Result[dict[str, Any], str]`**:
  - Exports `_CORE_TABLES` (`categories`, `books`, `book_copies`)—plus `_CIRC_TABLES` (`loans`, `reservations`, `fines`, `book_copy_status_log`) when `include_circulation=True`—to `.sqlite` (domain `"books"`, schema v10) or `.xlsx`. Rejects overwriting the active application DB (`PRAGMA database_list` + `os.path.realpath`).
- **`preview_books_import(conn, input_path, mode="merge") -> Result[dict[str, Any], str]`**:
  - Loads `.sqlite`/`.db` or `.xlsx` bundles read-only and computes non-mutating diff counts (`new_categories`, `new_books`, `updated_books`, `new_copies`, `skipped_copies`, `total_source_books`, `total_source_copies`, `can_apply`, `blocked_reason`, `format`).
  - Matches books by normalized ISBN (`_normalize_isbn`) or fallback `(title, author)` key, and matches copies by normalized barcode (`_norm_barcode`).
- **`apply_books_import(conn, input_path, mode="merge", db_path="", actor="ADMIN") -> Result[dict[str, Any], str]`**:
  - **`merge` mode**: Upserts categories, books, and copies inside a single `with conn:` transaction; preserves any copy whose local status is `on_loan` and recomputes `books.total_copies`.
  - **`replace` mode**: Blocked (`_check_replace_blockers`) if any active/overdue `loans`, unpaid `fines` (`paid = 0`), or `waiting`/`ready` `reservations` exist; otherwise clears library tables before importing.
  - Creates a pre-import backup via `create_pre_import_backup` when `db_path != ":memory:"` and logs `library.import_<mode>` via `record_activity`.

### Librarian Adapter & UI Integration
- **`LibrarianAdminAdapter`** (`apps/librarian_management_app/adapters/librarian_admin_adapter.py`):
  - Exposes `@Slot`s `exportBooksDatabase(output_path, fmt, include_circulation=False)`, `previewBooksImport(input_path, mode="merge")`, and `applyBooksImport(input_path, mode="merge", actor="LIBRARIAN")` returning `_sanitize_for_qml` JSON (`{"ok", "data", "error"}`) with path validation against active DB overwrites and symlinks.
- **`DatabaseTransferCard.qml`** (`apps/common_qml/DatabaseTransferCard.qml`):
  - Reusable card integrated into `SettingsView.qml` (`showBookTransferCard`, enabled in `apps/librarian_management_app/qml/Main.qml`) with format/mode `StyledComboBox` selectors, native `FileDialog` save/open pickers, preview-gated Apply button (`btnApplyImportDb`), diff summary box, and `ActionFeedbackBanner`.


