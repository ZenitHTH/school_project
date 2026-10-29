import datetime
import sqlite3
from typing import Any, Dict, List, Optional
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


def rename_category(conn: sqlite3.Connection, category_id: int, new_name: str) -> None:
    """Rename category and update books table textual column."""
    clean = new_name.strip()
    with conn:
        conn.execute("UPDATE categories SET name = ? WHERE category_id = ?", (clean, category_id))
        conn.execute("UPDATE books SET category = ? WHERE category_id = ?", (clean, category_id))


def get_books_by_category(conn: sqlite3.Connection, category_id: int) -> List[sqlite3.Row]:
    """Retrieve all books assigned to a category."""
    return conn.execute(
        "SELECT book_id, title, author, isbn FROM books WHERE category_id = ?",
        (category_id,),
    ).fetchall()


def delete_category(conn: sqlite3.Connection, category_id: int, reassign_to_id: Optional[int] = None) -> None:
    """Delete category, reassigning existing books or setting them to NULL."""
    with conn:
        if reassign_to_id is not None:
            row = conn.execute("SELECT name FROM categories WHERE category_id = ?", (reassign_to_id,)).fetchone()
            new_name = row[0] if row else None
            conn.execute(
                "UPDATE books SET category_id = ?, category = ? WHERE category_id = ?",
                (reassign_to_id, new_name, category_id),
            )
        else:
            conn.execute(
                "UPDATE books SET category_id = NULL, category = NULL WHERE category_id = ?",
                (category_id,),
            )
        conn.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))


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

    clean_query = query.strip()
    if clean_query:
        if len(clean_query) < 3:
            conditions.append("(b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?)")
            like_param = f"%{clean_query}%"
            params.extend([like_param, like_param, like_param])
        else:
            escaped = clean_query.replace('"', '""')
            fts_query = f'"{escaped}"*' if " " not in escaped else f'"{escaped}"'
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


def get_book_copy_breakdown(conn: sqlite3.Connection, book_id: int) -> Dict[str, Any]:
    """Return count breakdown and copy details for a book."""
    sql = """
        SELECT c.copy_id, c.barcode, c.status,
               (SELECT count(*) FROM loans l WHERE l.copy_id = c.copy_id) AS loan_count
        FROM book_copies c
        WHERE c.book_id = ?
        ORDER BY c.copy_id ASC
    """
    rows = conn.execute(sql, (book_id,)).fetchall()
    copies = []
    available = sum(1 for r in rows if r["status"] == "available")
    on_loan = sum(1 for r in rows if r["status"] == "on_loan")
    for r in rows:
        st = r["status"]
        copies.append({
            "copy_id": r["copy_id"],
            "barcode": r["barcode"],
            "status": st,
            "loan_count": r["loan_count"],
            "can_remove": (st == "available" and r["loan_count"] == 0),
        })
    return {
        "book_id": book_id,
        "total_copies": len(rows),
        "available_copies": available,
        "on_loan_copies": on_loan,
        "other_copies": len(rows) - available - on_loan,
        "copies": copies,
    }


def remove_excess_copies(
    conn: sqlite3.Connection,
    book_id: int,
    count_to_remove: int,
    actor: Optional[str] = None,
) -> List[str]:
    """Safely remove unloaned available copies for a book (e.g. entered by mistake)."""
    if count_to_remove <= 0:
        return []
    sql = """
        SELECT c.copy_id, c.barcode
        FROM book_copies c
        WHERE c.book_id = ? AND c.status = 'available'
          AND NOT EXISTS (SELECT 1 FROM loans l WHERE l.copy_id = c.copy_id)
        ORDER BY c.copy_id DESC
        LIMIT ?
    """
    candidates = conn.execute(sql, (book_id, count_to_remove)).fetchall()
    if len(candidates) < count_to_remove:
        raise ValueError(
            f"Cannot remove {count_to_remove} copies; only {len(candidates)} unloaned available copies found."
        )
    removed_barcodes = []
    with conn:
        for row in candidates:
            cid = row["copy_id"]
            conn.execute("DELETE FROM book_copy_status_log WHERE copy_id = ?", (cid,))
            conn.execute("DELETE FROM book_copies WHERE copy_id = ?", (cid,))
            removed_barcodes.append(row["barcode"])
        conn.execute(
            "UPDATE books SET total_copies = (SELECT count(*) FROM book_copies WHERE book_id = ?) WHERE book_id = ?",
            (book_id, book_id),
        )
        record_activity(
            conn,
            action="catalog.remove_copies",
            entity_type="book",
            entity_id=book_id,
            detail=f"Removed {len(removed_barcodes)} cop(ies): {', '.join(removed_barcodes)}",
            actor=actor,
        )
    return removed_barcodes



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
    """Lookup copy and parent book by barcode (case/dash-insensitive + ISBN fallback)."""
    clean = barcode.strip()
    if not clean:
        return None

    # 1. Exact match
    sql_exact = """
        SELECT bc.*, b.title, b.author, b.isbn, b.active
        FROM book_copies bc
        JOIN books b ON b.book_id = bc.book_id
        WHERE bc.barcode = ?
    """
    row = conn.execute(sql_exact, (clean,)).fetchone()
    if row:
        return row

    norm = clean.lower().replace("-", "")
    # 2. Case and dash-insensitive barcode match
    sql_norm = """
        SELECT bc.*, b.title, b.author, b.isbn, b.active
        FROM book_copies bc
        JOIN books b ON b.book_id = bc.book_id
        WHERE REPLACE(LOWER(bc.barcode), '-', '') = ?
        LIMIT 1
    """
    row = conn.execute(sql_norm, (norm,)).fetchone()
    if row:
        return row

    # 3. ISBN fallback (find available copy first, or first copy)
    sql_isbn = """
        SELECT bc.*, b.title, b.author, b.isbn, b.active
        FROM book_copies bc
        JOIN books b ON b.book_id = bc.book_id
        WHERE REPLACE(LOWER(b.isbn), '-', '') = ?
        ORDER BY CASE WHEN bc.status = 'available' THEN 0 ELSE 1 END, bc.copy_id ASC
        LIMIT 1
    """
    return conn.execute(sql_isbn, (norm,)).fetchone()


def get_copies_for_book(conn: sqlite3.Connection, book_id: int) -> List[sqlite3.Row]:
    """List all physical copies for a book."""
    return conn.execute("SELECT * FROM book_copies WHERE book_id = ? ORDER BY copy_id ASC", (book_id,)).fetchall()


def count_copies_ever(conn: sqlite3.Connection, book_id: int) -> int:
    """Count all copies ever registered for this book (including lost, damaged, retired, disposed)."""
    row = conn.execute("SELECT count(*) FROM book_copies WHERE book_id = ?", (book_id,)).fetchone()
    return row[0] if row else 0


def insert_copy(conn: sqlite3.Connection, book_id: int, barcode: str, status: str = "available") -> int:
    """Insert a single copy and update book total_copies."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO book_copies (book_id, barcode, status) VALUES (?, ?, ?)",
            (book_id, barcode.strip(), status),
        )
        copy_id = cur.lastrowid
        cur.execute(
            "UPDATE books SET total_copies = (SELECT count(*) FROM book_copies WHERE book_id = ?) WHERE book_id = ?",
            (book_id, book_id),
        )
        return copy_id


def list_books_with_barcodes(conn: sqlite3.Connection, query: str = "") -> List[Dict[str, Any]]:
    """List active books with their active non-disposed barcodes in a single batched query."""
    books = search_books(conn, query=query, limit=500, offset=0)
    if not books:
        return []
    book_ids = [b["book_id"] for b in books]
    placeholders = ",".join("?" for _ in book_ids)
    sql = f"""
        SELECT book_id, barcode
        FROM book_copies
        WHERE book_id IN ({placeholders}) AND status NOT IN ('retired', 'disposed')
        ORDER BY copy_id ASC
    """
    rows = conn.execute(sql, book_ids).fetchall()
    barcode_map: Dict[int, List[str]] = {}
    for r in rows:
        barcode_map.setdefault(r["book_id"], []).append(r["barcode"])

    result = []
    for b in books:
        item = dict(b)
        item["barcodes"] = barcode_map.get(b["book_id"], [])
        result.append(item)
    return result
