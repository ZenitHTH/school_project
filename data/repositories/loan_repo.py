import datetime
import sqlite3
from typing import List, Optional
from core.shared.log_service import record_activity


def create_loan(
    conn: sqlite3.Connection,
    copy_id: int,
    student_id: int,
    borrowed_at: str,
    due_at: str,
    actor: Optional[str] = None,
) -> int:
    """Create a new active loan and mark physical copy on_loan."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO loans (copy_id, student_id, borrowed_at, due_at, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (copy_id, student_id, borrowed_at, due_at),
        )
        loan_id = cur.lastrowid

        cur.execute("UPDATE book_copies SET status = 'on_loan' WHERE copy_id = ?", (copy_id,))

        record_activity(
            conn,
            action="loan.checkout",
            entity_type="loan",
            entity_id=loan_id,
            detail=f"Student {student_id} checked out copy {copy_id} (due {due_at})",
            actor=actor,
        )
        return loan_id


def return_loan(
    conn: sqlite3.Connection,
    loan_id: int,
    returned_at: str,
    actor: Optional[str] = None,
) -> None:
    """Close loan as returned and mark copy available."""
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT copy_id, student_id FROM loans WHERE loan_id = ?", (loan_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Loan {loan_id} not found")
        copy_id = row["copy_id"]
        student_id = row["student_id"]

        cur.execute(
            """
            UPDATE loans
            SET returned_at = ?, status = 'returned'
            WHERE loan_id = ?
            """,
            (returned_at, loan_id),
        )

        cur.execute("UPDATE book_copies SET status = 'available' WHERE copy_id = ?", (copy_id,))

        record_activity(
            conn,
            action="loan.return",
            entity_type="loan",
            entity_id=loan_id,
            detail=f"Student {student_id} returned copy {copy_id}",
            actor=actor,
        )


def renew_loan(
    conn: sqlite3.Connection,
    loan_id: int,
    new_due_at: str,
    actor: Optional[str] = None,
) -> None:
    """Extend loan due date."""
    with conn:
        conn.execute("UPDATE loans SET due_at = ? WHERE loan_id = ?", (new_due_at, loan_id))
        record_activity(
            conn,
            action="loan.renew",
            entity_type="loan",
            entity_id=loan_id,
            detail=f"Renewed loan {loan_id}, new due date: {new_due_at}",
            actor=actor,
        )


def get_loan(conn: sqlite3.Connection, loan_id: int) -> Optional[sqlite3.Row]:
    """Retrieve loan details joined with book and student info."""
    sql = """
        SELECT l.*, bc.barcode, bc.book_id, b.title, s.full_name, s.student_id
        FROM loans l
        JOIN book_copies bc ON bc.copy_id = l.copy_id
        JOIN books b ON b.book_id = bc.book_id
        JOIN students s ON s.student_id = l.student_id
        WHERE l.loan_id = ?
    """
    return conn.execute(sql, (loan_id,)).fetchone()


def get_active_loans_count(conn: sqlite3.Connection, student_id: int) -> int:
    """Return count of active or overdue loans for a student."""
    cur = conn.cursor()
    cur.execute(
        "SELECT count(*) FROM loans WHERE student_id = ? AND status IN ('active', 'overdue')",
        (student_id,),
    )
    return cur.fetchone()[0]


def get_active_loans(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Fetch all active/overdue loans for live monitoring."""
    sql = """
        SELECT l.*, bc.barcode, b.title, s.full_name, s.student_id
        FROM loans l
        JOIN book_copies bc ON bc.copy_id = l.copy_id
        JOIN books b ON b.book_id = bc.book_id
        JOIN students s ON s.student_id = l.student_id
        WHERE l.status IN ('active', 'overdue')
        ORDER BY l.due_at ASC
    """
    return conn.execute(sql).fetchall()


def get_overdue_loans(conn: sqlite3.Connection, current_iso_date: str) -> List[sqlite3.Row]:
    """Fetch all loans where due_at < current_date and status is active."""
    sql = """
        SELECT l.*, bc.barcode, b.title, s.full_name, s.student_id
        FROM loans l
        JOIN book_copies bc ON bc.copy_id = l.copy_id
        JOIN books b ON b.book_id = bc.book_id
        JOIN students s ON s.student_id = l.student_id
        WHERE l.status = 'active' AND l.due_at < ?
        ORDER BY l.due_at ASC
    """
    return conn.execute(sql, (current_iso_date,)).fetchall()


def get_student_loan_history(conn: sqlite3.Connection, student_id: int) -> List[sqlite3.Row]:
    """Complete loan history for a specific student."""
    sql = """
        SELECT l.*, bc.barcode, b.title, f.amount as fine_amount, f.paid as fine_paid
        FROM loans l
        JOIN book_copies bc ON bc.copy_id = l.copy_id
        JOIN books b ON b.book_id = bc.book_id
        LEFT JOIN fines f ON f.loan_id = l.loan_id
        WHERE l.student_id = ?
        ORDER BY l.loan_id DESC
    """
    return conn.execute(sql, (student_id,)).fetchall()


def get_book_copy_loan_history(conn: sqlite3.Connection, copy_id: int) -> List[sqlite3.Row]:
    """Lending trail for a specific copy for asset tracking."""
    sql = """
        SELECT l.*, s.full_name, s.student_id
        FROM loans l
        JOIN students s ON s.student_id = l.student_id
        WHERE l.copy_id = ?
        ORDER BY l.loan_id DESC
    """
    return conn.execute(sql, (copy_id,)).fetchall()
