# SQLite Database Schema & Migrations

All SQLite database connections use `get_connection(...)` from `data/db.py`, which supports PIN-based encryption and automatic schema migrations.

---

## 1. Tables Overview

### Students & Enrollments
- **`students`**: Master student record.
  - `student_id` (INTEGER PRIMARY KEY): School student ID (e.g. 36582).
  - `national_id` (TEXT): 13-digit Thai national ID (strictly excluded from text search algorithms for privacy).
  - `prefix`, `first_name`, `last_name`, `full_name` (TEXT).
  - `gender` (TEXT: 'M' or 'F').
  - `status` (TEXT: `'active'`, `'on_leave'`, `'transferred_out'`).
- **`students_fts`**: FTS5 Virtual Table using trigram tokenizer on `full_name`.
- **`enrollments`**: Historical record of student classroom assignments per term.
  - `student_id` (INTEGER REFERENCES students(student_id)).
  - `academic_year` (INTEGER, e.g. 2568).
  - `semester` (INTEGER: 1 or 2).
  - `grade_level` (TEXT: e.g. `'ม.1'`).
  - `room` (INTEGER).
  - `track` (TEXT: e.g. `'วิทย์-คณิต'`).
  - `seq_no` (INTEGER).

### Library Catalog & Circulation
- **`books`**: Title-level book catalog.
  - `book_id` (INTEGER PRIMARY KEY AUTOINCREMENT).
  - `title`, `author`, `publisher`, `isbn`, `shelf_location` (TEXT).
  - `category_id` (INTEGER REFERENCES categories(category_id)).
- **`book_copies`**: Individual physical copies.
  - `copy_id` (INTEGER PRIMARY KEY AUTOINCREMENT).
  - `book_id` (INTEGER REFERENCES books(book_id)).
  - `barcode` (TEXT UNIQUE): E.g. `SMTE-00001-01`.
  - `status` (TEXT: `'available'`, `'borrowed'`, `'reserved'`, `'lost'`, `'disposed'`).
- **`loans`**: Borrow / return transactions.
  - `loan_id` (INTEGER PRIMARY KEY AUTOINCREMENT).
  - `copy_id`, `student_id`.
  - `borrowed_at`, `due_date`, `returned_at`.
- **`fines`**: Overdue fines ledger.
  - `fine_id` (INTEGER PRIMARY KEY AUTOINCREMENT).
  - `loan_id`, `student_id`, `amount`, `status` (`'unpaid'`, `'paid'`).
- **`categories`**: Book classifications.
- **`activity_logs`**: System audit trail.
- **`sync_state`**: Key-value store for sync versioning, hashes, and first-launch status.

---

## 2. Migrations System (`data/migrate.py`)
- Incremental migrations recorded in `schema_migrations` table (`version`, `applied_at`).
- Supports zero-downtime upgrades, index creation, and automatic FTS5 rebuilds.
