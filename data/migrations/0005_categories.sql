-- Migration 0005: Categories normalization
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE
);

-- Add category_id column if not already present
-- SQLite allows ADD COLUMN
ALTER TABLE books ADD COLUMN category_id INTEGER REFERENCES categories(category_id);

-- Migrate existing textual categories if present
INSERT OR IGNORE INTO categories (name)
SELECT DISTINCT category FROM books WHERE category IS NOT NULL AND category != '';

UPDATE books
SET category_id = (SELECT c.category_id FROM categories c WHERE c.name = books.category)
WHERE category IS NOT NULL AND category != '';
