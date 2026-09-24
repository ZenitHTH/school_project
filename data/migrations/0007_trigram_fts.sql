-- Migration 0005: Recreate students_fts with trigram tokenizer on full_name only
DROP TRIGGER IF EXISTS students_ai;
DROP TRIGGER IF EXISTS students_ad;
DROP TRIGGER IF EXISTS students_au;
DROP TABLE IF EXISTS students_fts;

CREATE VIRTUAL TABLE students_fts USING fts5(
    full_name,
    content='students',
    content_rowid='student_id',
    tokenize='trigram'
);

CREATE TRIGGER students_ai AFTER INSERT ON students BEGIN
    INSERT INTO students_fts(rowid, full_name)
    VALUES (new.student_id, new.full_name);
END;

CREATE TRIGGER students_ad AFTER DELETE ON students BEGIN
    INSERT INTO students_fts(students_fts, rowid, full_name)
    VALUES ('delete', old.student_id, old.full_name);
END;

CREATE TRIGGER students_au AFTER UPDATE ON students BEGIN
    INSERT INTO students_fts(students_fts, rowid, full_name)
    VALUES ('delete', old.student_id, old.full_name);
    INSERT INTO students_fts(rowid, full_name)
    VALUES (new.student_id, new.full_name);
END;

INSERT INTO students_fts(rowid, full_name)
SELECT student_id, full_name FROM students;
