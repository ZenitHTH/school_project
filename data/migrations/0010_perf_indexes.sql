-- Migration 0010: Performance indexes for loans, fines, reservations, books, and normalized ISBN/barcode lookups
CREATE INDEX IF NOT EXISTS idx_loans_status_due ON loans(status, due_at);
CREATE INDEX IF NOT EXISTS idx_fines_paid_id ON fines(paid, fine_id DESC);
CREATE INDEX IF NOT EXISTS idx_reservations_book_status ON reservations(book_id, status, reserved_at, reservation_id);
CREATE INDEX IF NOT EXISTS idx_reservations_status_reserved ON reservations(status, reserved_at);
CREATE INDEX IF NOT EXISTS idx_books_active_cat_id ON books(active, category_id, book_id DESC);
CREATE INDEX IF NOT EXISTS idx_books_norm_isbn ON books(UPPER(REPLACE(REPLACE(isbn, '-', ''), ' ', '')));
CREATE INDEX IF NOT EXISTS idx_copies_norm_barcode ON book_copies(REPLACE(LOWER(barcode), '-', ''));
