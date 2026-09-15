import sqlite3
from typing import List, Optional
from core.shared.log_service import record_activity


def create_fine(
    conn: sqlite3.Connection,
    loan_id: int,
    amount: float,
    reason: str,
    actor: Optional[str] = None,
) -> int:
    """Assess a fine on a loan."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO fines (loan_id, amount, reason, paid)
            VALUES (?, ?, ?, 0)
            """,
            (loan_id, amount, reason),
        )
        fine_id = cur.lastrowid

        record_activity(
            conn,
            action="fine.create",
            entity_type="fine",
            entity_id=fine_id,
            detail=f"Assessed {amount:.2f} THB fine for {reason} on loan {loan_id}",
            actor=actor,
        )
        return fine_id


def record_payment(
    conn: sqlite3.Connection,
    fine_id: int,
    paid_at: str,
    actor: Optional[str] = None,
) -> None:
    """Record that a fine has been paid."""
    with conn:
        conn.execute(
            "UPDATE fines SET paid = 1, paid_at = ? WHERE fine_id = ?",
            (paid_at, fine_id),
        )
        record_activity(
            conn,
            action="fine.pay",
            entity_type="fine",
            entity_id=fine_id,
            detail=f"Recorded payment for fine {fine_id}",
            actor=actor,
        )


def get_unpaid_fines_total(conn: sqlite3.Connection, student_id: int) -> float:
    """Calculate total unpaid fine amount for a student."""
    sql = """
        SELECT coalesce(sum(f.amount), 0.0)
        FROM fines f
        JOIN loans l ON l.loan_id = f.loan_id
        WHERE l.student_id = ? AND f.paid = 0
    """
    cur = conn.cursor()
    cur.execute(sql, (student_id,))
    row = cur.fetchone()
    return float(row[0]) if row else 0.0


def list_fines(conn: sqlite3.Connection, paid: Optional[bool] = None) -> List[sqlite3.Row]:
    """List fines with student and book titles."""
    conditions = []
    params = []
    if paid is not None:
        conditions.append("f.paid = ?")
        params.append(1 if paid else 0)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""
        SELECT f.*, l.student_id, s.full_name, b.title
        FROM fines f
        JOIN loans l ON l.loan_id = f.loan_id
        JOIN students s ON s.student_id = l.student_id
        JOIN book_copies bc ON bc.copy_id = l.copy_id
        JOIN books b ON b.book_id = bc.book_id
        {where}
        ORDER BY f.fine_id DESC
    """
    return conn.execute(sql, params).fetchall()
