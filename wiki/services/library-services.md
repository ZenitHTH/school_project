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
- **Renew (`renew_loan`)**:
  - Validates remaining renewals < `max_renewals`.
  - Extends due date by `loan_duration_days`.
- **Internal structure** (clean-code refactor, 2026-11-09): `checkout` is a thin orchestration calling `_check_student_eligibility` (steps 1–3; returns a failure `Result` or `None`) and `_resolve_checkout_copy` (step 4; `Result.success(copy)` or a failure `Result`). `return_book` delegates overdue-fine assessment to `_assess_overdue_fine` (keeps the same internal error-swallow + `[WARN]` stderr behavior). Public behavior, `Result` shapes, and error messages are unchanged.

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

## 6. Barcode Label Generator (`core.library.services.label_service`)
Generates printable A4 PDF sheets with barcode labels and dashed cut lines.
- **Pure-Stdlib Vector Engine**: Zero external dependencies (no `python-barcode`, `Pillow`, or `reportlab`). Emits direct vector PDF 1.4 rectangles (`re f`) and dashed cut guides (`[3 3] 0 d`).
- **Grid Layout**: Configurable 3 columns × 8 rows (24 labels per A4 page).
- **Format**: ISO/IEC 15417 Code128-B barcodes with human-readable text labels and PDF delimiter escaping.
- **Structure** (clean-code refactor, 2026-11-09): `export_label_sheet_pdf` is the orchestrator; `_prepare_barcode_items` (input normalization), `_render_label_cell` (per-cell drawing: dashed guide + Code128 bars + readable text), `_assemble_pdf_document` (PDF 1.4 objects / xref / trailer). Output PDFs are byte-identical to the pre-refactor versions for identical inputs (verified by SHA-256).

---

## 7. ISBN Lookup Service (`core.library.services.isbn_service` & `isbn_providers`)
Provides ISBN validation and metadata retrieval for book registration.
- **3-Provider JSON Pipeline (`isbn_providers.py`)**:
  1. **NLT Primo VE REST API** (`nlt.primo.exlibrisgroup.com`): Primary authoritative endpoint for books deposited with the National Library of Thailand. Extracts `title`, `author` (stripped of MARC `$$` subfields and trailing `.`), and `publisher`.
  2. **SE-ED Web-BFF REST API** (`mp-api.se-ed.com/web-bff`): Secondary endpoint for commercial Thai exam-prep, tutor, and publisher books. Verifies SKU in `physicalProduct.variants`, extracts title, and parses the Lexical JSON AST to extract author and publisher.
  3. **Open Library Books API** (`openlibrary.org`): Tertiary endpoint for international and English literature/textbooks.
- **Two-Tier Authoritative Local Lookup**:
  1. Authoritative local `books` table checked first (`ORDER BY active DESC, book_id DESC`), ensuring active copies take precedence and edits in the catalog are never shadowed by stale cache entries.
  2. Persistent SQLite `isbn_cache` table queried on local catalog miss.
  3. Queries chained remote providers on local miss and populates `isbn_cache` upon successful retrieval.
- **Autofill Overwrite Policy & Re-entrancy Protection**:
  - **Match Found**: When matching metadata is retrieved from local cache or remote providers, QML autofill overwrites any existing `Title` and `Author` fields to ensure newly scanned books receive authoritative catalog metadata.
  - **Error Preservation**: When lookup fails (`cannot fetch data`), user-entered text is preserved intact without deletion or corruption.
  - **Auto-Fetch on Scan Option**: Supported via toggle checkbox (`chkAutoFetchIsbn` in `BarcodeGeneratorView`, `chkDialogAutoFetchIsbn` in `BookActionDialogs`, checked by default). Triggers autofill automatically on scanner enter (`onAccepted`) or when 13 digits are scanned (300ms debounce), while keeping manual `[🔍 ดึงข้อมูล]` buttons accessible.
  - Input and generation actions are disabled during event-loop pump (`ExcludeUserInputEvents`) to prevent re-entrant submissions.
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
  - Chain position: **last** — `NLT Primo → SE-ED → Open Library → Chulabook`. The existing `fetchIsbnMetadata` autofill therefore resolves Chulabook-only ISBNs with no UI change, and successful lookups persist to `isbn_cache`.
- **Detection rule (`detect_chulabook_books(conn, timeout=5.0, workers=8) -> Result[list[dict], str]`)**: a book row is flagged iff `_fetch_chulabook(isbn)` hits **and** the normalized ISBN is absent from `isbn_cache` **and** all three standard providers miss. Invalid/Thai-digit ISBNs are skipped silently; per-row exceptions skip that row; `Err` only when the `books` table is missing. Rows: `{book_id, isbn (normalized), title, author}`.
- **Librarian UI**: `LibrarianAdminAdapter.detectChulabookBooks()` slot (`chulabookCheckStarted`/`chulabookCheckCompleted` signals, `_sanitize_for_qml` on `books[]`) drives the `📕 ตรวจ Chulabook` button in `BookCatalogView.qml` (Tab 0) — status line `chulabookStatusText` + results `Dialog` (`chulabookResultsModel`) listing flagged books. Wired via `window.detectChulabook()` in `Main.qml`. Synchronous slot (house pattern); ~30–60 s for a 200-book catalog.

