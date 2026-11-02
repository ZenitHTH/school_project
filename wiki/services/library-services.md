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
- **Auto-Incremented Barcode Generation**:
  - Generates barcodes with prefix `SMTE` and zero-padded sequence (e.g. `SMTE000001`).
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
- **Safe Overwrite Policy & Re-entrancy Protection**: QML autofill never overwrites existing non-blank `Title` or `Author` text entered by the librarian. Input and generation actions are disabled during event-loop pump (`ExcludeUserInputEvents`) to prevent re-entrant submissions.
- **Error Handling**: Network timeouts, non-book tables, redirects, or malformed inputs return `Err("cannot fetch data")` safely trapped in a Rust-style `Result[Dict[str, str], str]`.

