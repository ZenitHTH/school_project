-- Migration 0001: Initial student schema
CREATE TABLE IF NOT EXISTS students (
    student_id   INTEGER PRIMARY KEY,
    national_id  TEXT,
    prefix       TEXT,
    first_name   TEXT,
    last_name    TEXT,
    full_name    TEXT NOT NULL,
    gender       TEXT CHECK (gender IN ('M','F') OR gender IS NULL),
    status       TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS enrollments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(student_id),
    academic_year INTEGER,
    semester      INTEGER,
    grade_level   TEXT NOT NULL,
    room          INTEGER NOT NULL,
    track         TEXT,
    seq_no        INTEGER,
    UNIQUE (student_id, academic_year, semester, grade_level, room)
);

CREATE TABLE IF NOT EXISTS room_changes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(student_id),
    old_room    TEXT,
    new_room    TEXT,
    change_date TEXT,
    note        TEXT
);

CREATE TABLE IF NOT EXISTS transfers_out (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id          INTEGER NOT NULL REFERENCES students(student_id),
    room_at_transfer    TEXT,
    destination_school  TEXT,
    transfer_date       TEXT,
    note                TEXT,
    source_sheet        TEXT
);

CREATE TABLE IF NOT EXISTS transfers_in (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id       INTEGER NOT NULL REFERENCES students(student_id),
    old_student_id   INTEGER,
    previous_school  TEXT,
    transfer_date    TEXT,
    room             TEXT,
    note             TEXT
);

CREATE TABLE IF NOT EXISTS leave_of_absence (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id            INTEGER NOT NULL REFERENCES students(student_id),
    grade_room_at_leave   TEXT,
    leave_date            TEXT,
    expected_return_date  TEXT,
    note                  TEXT
);

CREATE TABLE IF NOT EXISTS retentions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     INTEGER NOT NULL REFERENCES students(student_id),
    academic_year  INTEGER,
    old_class      TEXT,
    new_class      TEXT,
    entry_date     TEXT,
    note           TEXT
);

CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_grade_room ON enrollments(academic_year, semester, grade_level, room);
CREATE INDEX IF NOT EXISTS idx_transfers_out_student ON transfers_out(student_id);
CREATE INDEX IF NOT EXISTS idx_transfers_in_student ON transfers_in(student_id);
CREATE INDEX IF NOT EXISTS idx_room_changes_student ON room_changes(student_id);
CREATE INDEX IF NOT EXISTS idx_leave_student ON leave_of_absence(student_id);
CREATE INDEX IF NOT EXISTS idx_retentions_student ON retentions(student_id);

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
