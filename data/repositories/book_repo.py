import datetime
import sqlite3
from typing import Any, List, Optional
from core.shared.log_service import record_activity


def list_categories(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Return all categories sorted alphabetically."""
    return conn.execute("SELECT * FROM categories ORDER BY name ASC").fetchall()


def add_category(conn: sqlite3.Connection, name: str) -> int:
    """Create a new category if not already existing."""
    clean_name = name.strip()
    with conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (clean_name,))
        cur.execute("SELECT category_id FROM categories WHERE name = ?", (clean_name,))
        row = cur.fetchone()
        return row[0]


def add_book(
    conn: sqlite3.Connection,
    title: str,
    isbn: Optional[str] = None,
    author: Optional[str] = None,
    publisher: Optional[str] = None,
    category_id: Optional[int] = None,
    shelf_location: Optional[str] = None,
    actor: Optional[str] = None,
) -> int:
    """Insert a new book record into books table."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO books (title, isbn, author, publisher, category_id, shelf_location, total_copies, active)
            VALUES (?, ?, ?, ?, ?, ?, 0, 1)
            """,
            (title, isbn, author, publisher, category_id, shelf_location),
        )
        book_id = cur.lastrowid

        record_activity(
            conn,
            action="catalog.add_book",
            entity_type="book",
            entity_id=book_id,
            detail=f"Added book: '{title}'",
            actor=actor,
        )
        return book_id


def update_book(
    conn: sqlite3.Connection,
    book_id: int,
    title: str,
    isbn: Optional[str] = None,
    author: Optional[str] = None,
    publisher: Optional[str] = None,
    category_id: Optional[int] = None,
    shelf_location: Optional[str] = None,
    actor: Optional[str] = None,
) -> None:
    """Update metadata for an existing book."""
    with conn:
        conn.execute(
            """
            UPDATE books
            SET title = ?, isbn = ?, author = ?, publisher = ?, category_id = ?, shelf_location = ?
            WHERE book_id = ?
            """,
            (title, isbn, author, publisher, category_id, shelf_location, book_id),
        )
        record_activity(
            conn,
            action="catalog.update_book",
            entity_type="book",
            entity_id=book_id,
            detail=f"Updated book: '{title}'",
            actor=actor,
        )


def retire_book(conn: sqlite3.Connection, book_id: int, actor: Optional[str] = None) -> None:
    """Soft-delete a book (active = 0) and mark all its copies retired."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with conn:
        cur = conn.cursor()
        cur.execute("UPDATE books SET active = 0 WHERE book_id = ?", (book_id,))

        cur.execute("SELECT copy_id, status FROM book_copies WHERE book_id = ?", (book_id,))
        copies = cur.fetchall()

        for c in copies:
            if c["status"] != "retired":
                cur.execute("UPDATE book_copies SET status = 'retired' WHERE copy_id = ?", (c["copy_id"],))
                cur.execute(
                    """
                    INSERT INTO book_copy_status_log (copy_id, old_status, new_status, reason, changed_at)
                    VALUES (?, ?, 'retired', 'Book retired', ?)
                    """,
                    (c["copy_id"], c["status"], now_iso),
                )

        record_activity(
            conn,
            action="catalog.retire_book",
            entity_type="book",
            entity_id=book_id,
            detail="Book retired (soft delete)",
            actor=actor,
        )


def get_book(conn: sqlite3.Connection, book_id: int) -> Optional[sqlite3.Row]:
    """Retrieve book details joined with category."""
    sql = """
        SELECT b.*, c.name as category_name
        FROM books b
        LEFT JOIN categories c ON c.category_id = b.category_id
        WHERE b.book_id = ?
    """
    return conn.execute(sql, (book_id,)).fetchone()


def search_books(
    conn: sqlite3.Connection,
    query: str,
    category_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[sqlite3.Row]:
    """Search active books using FTS5 with optional category filter."""
    conditions = ["b.active = 1"]
    params: List[Any] = []

    clean_query = query.strip().replace('"', '""')
    if clean_query:
        fts_query = f'"{clean_query}"*' if " " not in clean_query else f'"{clean_query}"'
        conditions.append("b.book_id IN (SELECT rowid FROM books_fts WHERE books_fts MATCH ?)")
        params.append(fts_query)

    if category_id is not None:
        conditions.append("b.category_id = ?")
        params.append(category_id)

    where_clause = " WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT b.*, c.name as category_name,
               (SELECT count(*) FROM book_copies bc WHERE bc.book_id = b.book_id AND bc.status = 'available') as available_copies
        FROM books b
        LEFT JOIN categories c ON c.category_id = b.category_id
        {where_clause}
        ORDER BY b.book_id DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    return conn.execute(sql, params).fetchall()


def add_copies(
    conn: sqlite3.Connection,
    book_id: int,
    barcodes: List[str],
    actor: Optional[str] = None,
) -> List[int]:
    """Add new copies with unique barcodes for a book."""
    inserted_ids = []
    with conn:
        cur = conn.cursor()
        for b in barcodes:
            cur.execute(
                "INSERT INTO book_copies (book_id, barcode, status) VALUES (?, ?, 'available')",
                (book_id, b.strip()),
            )
            inserted_ids.append(cur.lastrowid)

        # Update total_copies count
        cur.execute(
            "UPDATE books SET total_copies = (SELECT count(*) FROM book_copies WHERE book_id = ?) WHERE book_id = ?",
            (book_id, book_id),
        )

        record_activity(
            conn,
            action="catalog.add_copies",
            entity_type="book",
            entity_id=book_id,
            detail=f"Added {len(barcodes)} cop(ies)",
            actor=actor,
        )
    return inserted_ids


def mark_copy(
    conn: sqlite3.Connection,
    copy_id: int,
    new_status: str,
    reason: Optional[str] = None,
    actor: Optional[str] = None,
) -> None:
    """Change status of a copy (available, on_loan, lost, damaged, retired) and log to book_copy_status_log."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT status, book_id FROM book_copies WHERE copy_id = ?", (copy_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Copy {copy_id} not found")
        old_status = row["status"]

        cur.execute("UPDATE book_copies SET status = ? WHERE copy_id = ?", (new_status, copy_id))

        cur.execute(
            """
            INSERT INTO book_copy_status_log (copy_id, old_status, new_status, reason, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (copy_id, old_status, new_status, reason, now_iso),
        )

        record_activity(
            conn,
            action="catalog.mark_copy",
            entity_type="copy",
            entity_id=copy_id,
            detail=f"Copy status: {old_status} -> {new_status}" + (f" ({reason})" if reason else ""),
            actor=actor,
        )


def get_available_copy(conn: sqlite3.Connection, book_id: int) -> Optional[sqlite3.Row]:
    """Find first available copy for a book."""
    sql = "SELECT * FROM book_copies WHERE book_id = ? AND status = 'available' LIMIT 1"
    return conn.execute(sql, (book_id,)).fetchone()


def get_copy_by_barcode(conn: sqlite3.Connection, barcode: str) -> Optional[sqlite3.Row]:
    """Lookup copy and parent book by barcode."""
    sql = """
        SELECT bc.*, b.title, b.author, b.isbn, b.active
        FROM book_copies bc
        JOIN books b ON b.book_id = bc.book_id
        WHERE bc.barcode = ?
    """
    return conn.execute(sql, (barcode.strip(),)).fetchone()


def get_copies_for_book(conn: sqlite3.Connection, book_id: int) -> List[sqlite3.Row]:
    """List all physical copies for a book."""
    return conn.execute("SELECT * FROM book_copies WHERE book_id = ? ORDER BY copy_id ASC", (book_id,)).fetchall()
