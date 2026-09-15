-- Migration 0003: Student FK ON UPDATE CASCADE and audit tables
PRAGMA foreign_keys = OFF;

-- Drop view referencing enrollments during rebuild
DROP VIEW IF EXISTS v_class_statistics;

-- 1. enrollments
CREATE TABLE IF NOT EXISTS enrollments_new (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    academic_year INTEGER,
    semester      INTEGER,
    grade_level   TEXT NOT NULL,
    room          INTEGER NOT NULL,
    track         TEXT,
    seq_no        INTEGER,
    UNIQUE (student_id, academic_year, semester, grade_level, room)
);
INSERT OR IGNORE INTO enrollments_new SELECT id, student_id, academic_year, semester, grade_level, room, track, seq_no FROM enrollments;
DROP TABLE enrollments;
ALTER TABLE enrollments_new RENAME TO enrollments;
CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_grade_room ON enrollments(academic_year, semester, grade_level, room);

-- 2. room_changes
CREATE TABLE IF NOT EXISTS room_changes_new (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    old_room    TEXT,
    new_room    TEXT,
    change_date TEXT,
    note        TEXT
);
INSERT OR IGNORE INTO room_changes_new SELECT id, student_id, old_room, new_room, change_date, note FROM room_changes;
DROP TABLE room_changes;
ALTER TABLE room_changes_new RENAME TO room_changes;
CREATE INDEX IF NOT EXISTS idx_room_changes_student ON room_changes(student_id);

-- 3. transfers_out
CREATE TABLE IF NOT EXISTS transfers_out_new (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id          INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    room_at_transfer    TEXT,
    destination_school  TEXT,
    transfer_date       TEXT,
    note                TEXT,
    source_sheet        TEXT
);
INSERT OR IGNORE INTO transfers_out_new SELECT id, student_id, room_at_transfer, destination_school, transfer_date, note, source_sheet FROM transfers_out;
DROP TABLE transfers_out;
ALTER TABLE transfers_out_new RENAME TO transfers_out;
CREATE INDEX IF NOT EXISTS idx_transfers_out_student ON transfers_out(student_id);

-- 4. transfers_in
CREATE TABLE IF NOT EXISTS transfers_in_new (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id       INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    old_student_id   INTEGER,
    previous_school  TEXT,
    transfer_date    TEXT,
    room             TEXT,
    note             TEXT
);
INSERT OR IGNORE INTO transfers_in_new SELECT id, student_id, old_student_id, previous_school, transfer_date, room, note FROM transfers_in;
DROP TABLE transfers_in;
ALTER TABLE transfers_in_new RENAME TO transfers_in;
CREATE INDEX IF NOT EXISTS idx_transfers_in_student ON transfers_in(student_id);

-- 5. leave_of_absence
CREATE TABLE IF NOT EXISTS leave_of_absence_new (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id            INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    grade_room_at_leave   TEXT,
    leave_date            TEXT,
    expected_return_date  TEXT,
    note                  TEXT
);
INSERT OR IGNORE INTO leave_of_absence_new SELECT id, student_id, grade_room_at_leave, leave_date, expected_return_date, note FROM leave_of_absence;
DROP TABLE leave_of_absence;
ALTER TABLE leave_of_absence_new RENAME TO leave_of_absence;
CREATE INDEX IF NOT EXISTS idx_leave_student ON leave_of_absence(student_id);

-- 6. retentions
CREATE TABLE IF NOT EXISTS retentions_new (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    academic_year  INTEGER,
    old_class      TEXT,
    new_class      TEXT,
    entry_date     TEXT,
    note           TEXT
);
INSERT OR IGNORE INTO retentions_new SELECT id, student_id, academic_year, old_class, new_class, entry_date, note FROM retentions;
DROP TABLE retentions;
ALTER TABLE retentions_new RENAME TO retentions;
CREATE INDEX IF NOT EXISTS idx_retentions_student ON retentions(student_id);

-- 7. loans
CREATE TABLE IF NOT EXISTS loans_new (
    loan_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    copy_id      INTEGER NOT NULL REFERENCES book_copies(copy_id),
    student_id   INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    borrowed_at  TEXT NOT NULL,
    due_at       TEXT NOT NULL,
    returned_at  TEXT,
    status       TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','returned','overdue','lost'))
);
INSERT OR IGNORE INTO loans_new SELECT loan_id, copy_id, student_id, borrowed_at, due_at, returned_at, status FROM loans;
DROP TABLE loans;
ALTER TABLE loans_new RENAME TO loans;
CREATE INDEX IF NOT EXISTS idx_loans_student ON loans(student_id);
CREATE INDEX IF NOT EXISTS idx_loans_copy ON loans(copy_id);

-- 8. reservations
CREATE TABLE IF NOT EXISTS reservations_new (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id        INTEGER NOT NULL REFERENCES books(book_id),
    student_id     INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    reserved_at    TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'waiting'
                CHECK (status IN ('waiting','ready','fulfilled','cancelled','expired'))
);
INSERT OR IGNORE INTO reservations_new SELECT reservation_id, book_id, student_id, reserved_at, status FROM reservations;
DROP TABLE reservations;
ALTER TABLE reservations_new RENAME TO reservations;
CREATE INDEX IF NOT EXISTS idx_reservations_book ON reservations(book_id);

-- Audit tables
CREATE TABLE IF NOT EXISTS student_id_changes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    old_id      INTEGER NOT NULL,
    new_id      INTEGER NOT NULL,
    reason      TEXT,
    changed_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS student_name_changes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    old_full_name TEXT NOT NULL,
    new_full_name TEXT NOT NULL,
    reason        TEXT,
    changed_at    TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS v_class_statistics AS
SELECT
    e.academic_year,
    e.semester,
    e.grade_level,
    e.room,
    e.track,
    SUM(CASE WHEN s.gender = 'M' THEN 1 ELSE 0 END) AS male_count,
    SUM(CASE WHEN s.gender = 'F' THEN 1 ELSE 0 END) AS female_count,
    COUNT(*) AS total
FROM enrollments e
JOIN students s ON s.student_id = e.student_id
GROUP BY e.academic_year, e.semester, e.grade_level, e.room, e.track;

PRAGMA foreign_keys = ON;
