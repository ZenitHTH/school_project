-- Migration 0004: FTS5 Virtual Tables and triggers
CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
    title, author, isbn, content='books', content_rowid='book_id'
);

CREATE TRIGGER IF NOT EXISTS books_ai AFTER INSERT ON books BEGIN
    INSERT INTO books_fts(rowid, title, author, isbn)
    VALUES (new.book_id, new.title, new.author, new.isbn);
END;

CREATE TRIGGER IF NOT EXISTS books_ad AFTER DELETE ON books BEGIN
    INSERT INTO books_fts(books_fts, rowid, title, author, isbn)
    VALUES ('delete', old.book_id, old.title, old.author, old.isbn);
END;

CREATE TRIGGER IF NOT EXISTS books_au AFTER UPDATE ON books BEGIN
    INSERT INTO books_fts(books_fts, rowid, title, author, isbn)
    VALUES ('delete', old.book_id, old.title, old.author, old.isbn);
    INSERT INTO books_fts(rowid, title, author, isbn)
    VALUES (new.book_id, new.title, new.author, new.isbn);
END;

CREATE VIRTUAL TABLE IF NOT EXISTS students_fts USING fts5(
    full_name, first_name, last_name, national_id, content='students', content_rowid='student_id'
);

CREATE TRIGGER IF NOT EXISTS students_ai AFTER INSERT ON students BEGIN
    INSERT INTO students_fts(rowid, full_name, first_name, last_name, national_id)
    VALUES (new.student_id, new.full_name, new.first_name, new.last_name, new.national_id);
END;

CREATE TRIGGER IF NOT EXISTS students_ad AFTER DELETE ON students BEGIN
    INSERT INTO students_fts(students_fts, rowid, full_name, first_name, last_name, national_id)
    VALUES ('delete', old.student_id, old.full_name, old.first_name, old.last_name, old.national_id);
END;

CREATE TRIGGER IF NOT EXISTS students_au AFTER UPDATE ON students BEGIN
    INSERT INTO students_fts(students_fts, rowid, full_name, first_name, last_name, national_id)
    VALUES ('delete', old.student_id, old.full_name, old.first_name, old.last_name, old.national_id);
    INSERT INTO students_fts(rowid, full_name, first_name, last_name, national_id)
    VALUES (new.student_id, new.full_name, new.first_name, new.last_name, new.national_id);
END;

-- Sync any existing rows
INSERT INTO books_fts(rowid, title, author, isbn) SELECT book_id, title, author, isbn FROM books;
INSERT INTO students_fts(rowid, full_name, first_name, last_name, national_id)
SELECT student_id, full_name, first_name, last_name, national_id FROM students;
