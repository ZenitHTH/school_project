-- Migration 0002: Library domain tables
CREATE TABLE IF NOT EXISTS books (
    book_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn           TEXT,
    title          TEXT NOT NULL,
    author         TEXT,
    publisher      TEXT,
    category       TEXT,
    shelf_location TEXT,
    total_copies   INTEGER NOT NULL DEFAULT 1,
    active         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS book_copies (
    copy_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL REFERENCES books(book_id),
    barcode     TEXT UNIQUE,
    status      TEXT NOT NULL DEFAULT 'available'
                CHECK (status IN ('available','on_loan','lost','damaged','retired'))
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    copy_id      INTEGER NOT NULL REFERENCES book_copies(copy_id),
    student_id   INTEGER NOT NULL REFERENCES students(student_id),
    borrowed_at  TEXT NOT NULL,
    due_at       TEXT NOT NULL,
    returned_at  TEXT,
    status       TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','returned','overdue','lost'))
);

CREATE TABLE IF NOT EXISTS reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id        INTEGER NOT NULL REFERENCES books(book_id),
    student_id     INTEGER NOT NULL REFERENCES students(student_id),
    reserved_at    TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'waiting'
                CHECK (status IN ('waiting','ready','fulfilled','cancelled','expired'))
);

CREATE TABLE IF NOT EXISTS fines (
    fine_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id     INTEGER NOT NULL REFERENCES loans(loan_id),
    amount      REAL NOT NULL,
    reason      TEXT NOT NULL,
    paid        INTEGER NOT NULL DEFAULT 0,
    paid_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_copies_book ON book_copies(book_id);
CREATE INDEX IF NOT EXISTS idx_loans_student ON loans(student_id);
CREATE INDEX IF NOT EXISTS idx_loans_copy ON loans(copy_id);
CREATE INDEX IF NOT EXISTS idx_reservations_book ON reservations(book_id);
CREATE INDEX IF NOT EXISTS idx_fines_loan ON fines(loan_id);
