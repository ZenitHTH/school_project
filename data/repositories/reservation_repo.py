import sqlite3
from typing import List, Optional
from core.shared.log_service import record_activity


def create_reservation(
    conn: sqlite3.Connection,
    book_id: int,
    student_id: int,
    reserved_at: str,
    actor: Optional[str] = None,
) -> int:
    """Add student to reservation queue for a book."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reservations (book_id, student_id, reserved_at, status)
            VALUES (?, ?, ?, 'waiting')
            """,
            (book_id, student_id, reserved_at),
        )
        res_id = cur.lastrowid

        record_activity(
            conn,
            action="reservation.create",
            entity_type="reservation",
            entity_id=res_id,
            detail=f"Student {student_id} reserved book {book_id}",
            actor=actor,
        )
        return res_id


def cancel_reservation(
    conn: sqlite3.Connection,
    reservation_id: int,
    actor: Optional[str] = None,
) -> None:
    """Cancel waiting or ready reservation."""
    with conn:
        conn.execute(
            "UPDATE reservations SET status = 'cancelled' WHERE reservation_id = ?",
            (reservation_id,),
        )
        record_activity(
            conn,
            action="reservation.cancel",
            entity_type="reservation",
            entity_id=reservation_id,
            detail=f"Cancelled reservation {reservation_id}",
            actor=actor,
        )


def promote_next_reservation(
    conn: sqlite3.Connection,
    book_id: int,
    actor: Optional[str] = None,
) -> Optional[int]:
    """Find oldest waiting reservation and mark it ready."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT reservation_id, student_id FROM reservations
            WHERE book_id = ? AND status = 'waiting'
            ORDER BY reserved_at ASC, reservation_id ASC
            LIMIT 1
            """,
            (book_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        res_id = row["reservation_id"]
        cur.execute("UPDATE reservations SET status = 'ready' WHERE reservation_id = ?", (res_id,))

        record_activity(
            conn,
            action="reservation.ready",
            entity_type="reservation",
            entity_id=res_id,
            detail=f"Reservation {res_id} marked ready for pickup by student {row['student_id']}",
            actor=actor,
        )
        return res_id


def fulfill_reservation(
    conn: sqlite3.Connection,
    reservation_id: int,
    actor: Optional[str] = None,
) -> None:
    """Mark reservation fulfilled upon checkout."""
    with conn:
        conn.execute(
            "UPDATE reservations SET status = 'fulfilled' WHERE reservation_id = ?",
            (reservation_id,),
        )
        record_activity(
            conn,
            action="reservation.fulfill",
            entity_type="reservation",
            entity_id=reservation_id,
            detail=f"Fulfilled reservation {reservation_id}",
            actor=actor,
        )


def has_waiting_reservation(conn: sqlite3.Connection, book_id: int) -> bool:
    """Check if book has pending reservations (used to block renewals)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM reservations WHERE book_id = ? AND status IN ('waiting', 'ready') LIMIT 1",
        (book_id,),
    )
    return cur.fetchone() is not None


def list_reservations(conn: sqlite3.Connection, status: Optional[str] = None) -> List[sqlite3.Row]:
    """List reservations with book and student names."""
    conditions = []
    params = []
    if status:
        conditions.append("r.status = ?")
        params.append(status)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""
        SELECT r.*, b.title, s.full_name, s.student_id
        FROM reservations r
        JOIN books b ON b.book_id = r.book_id
        JOIN students s ON s.student_id = r.student_id
        {where}
        ORDER BY r.reserved_at ASC
    """
    return conn.execute(sql, params).fetchall()
