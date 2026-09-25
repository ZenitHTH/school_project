-- Migration 0008: Add 'disposed' status to book_copies and migrate books_fts to trigram
PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS book_copies_new (
    copy_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL REFERENCES books(book_id),
    barcode     TEXT UNIQUE,
    status      TEXT NOT NULL DEFAULT 'available'
                CHECK (status IN ('available','on_loan','lost','damaged','retired','disposed'))
);

INSERT INTO book_copies_new (copy_id, book_id, barcode, status)
SELECT copy_id, book_id, barcode, status FROM book_copies;

DROP TABLE book_copies;

ALTER TABLE book_copies_new RENAME TO book_copies;

CREATE INDEX IF NOT EXISTS idx_copies_book ON book_copies(book_id);

PRAGMA foreign_keys = ON;

-- Recreate books_fts with trigram tokenizer
DROP TRIGGER IF EXISTS books_ai;
DROP TRIGGER IF EXISTS books_ad;
DROP TRIGGER IF EXISTS books_au;
DROP TABLE IF EXISTS books_fts;

CREATE VIRTUAL TABLE books_fts USING fts5(
    title, author, isbn,
    content='books',
    content_rowid='book_id',
    tokenize='trigram'
);

CREATE TRIGGER books_ai AFTER INSERT ON books BEGIN
    INSERT INTO books_fts(rowid, title, author, isbn)
    VALUES (new.book_id, new.title, new.author, new.isbn);
END;

CREATE TRIGGER books_ad AFTER DELETE ON books BEGIN
    INSERT INTO books_fts(books_fts, rowid, title, author, isbn)
    VALUES ('delete', old.book_id, old.title, old.author, old.isbn);
END;

CREATE TRIGGER books_au AFTER UPDATE ON books BEGIN
    INSERT INTO books_fts(books_fts, rowid, title, author, isbn)
    VALUES ('delete', old.book_id, old.title, old.author, old.isbn);
    INSERT INTO books_fts(rowid, title, author, isbn)
    VALUES (new.book_id, new.title, new.author, new.isbn);
END;

INSERT INTO books_fts(rowid, title, author, isbn)
SELECT book_id, title, author, isbn FROM books;
