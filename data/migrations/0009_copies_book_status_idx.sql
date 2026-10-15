-- Migration 0009: Composite index on book_copies(book_id, status) for fast copy availability checks
CREATE INDEX IF NOT EXISTS idx_copies_book_status ON book_copies(book_id, status);
