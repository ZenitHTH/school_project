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
- **Grid Layout**: Configurable 3 columns × 8 rows (24 labels per A4 page).
- **Format**: Code128 barcodes rendered via ReportLab with human-readable text labels.
