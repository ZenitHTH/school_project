import datetime
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from core.shared.log_service import record_activity


def search_students(
    conn: sqlite3.Connection,
    query: str,
    grade_level: Optional[str] = None,
    room: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[sqlite3.Row]:
    """Search students using FTS5 with optional grade, room, and status filters."""
    conditions = []
    params: List[Any] = []

    clean_query = query.strip()
    if clean_query:
        like_term = f"%{clean_query}%"
        if clean_query.isdigit():
            conditions.append("(s.student_id = ? OR s.national_id LIKE ? OR s.full_name LIKE ?)")
            params.extend([int(clean_query), like_term, like_term])
        else:
            clean_fts = clean_query.replace('"', '""')
            fts_query = f'"{clean_fts}"*' if " " not in clean_fts else f'"{clean_fts}"'
            conditions.append(
                "(s.student_id IN (SELECT rowid FROM students_fts WHERE students_fts MATCH ?) "
                "OR s.full_name LIKE ? OR s.first_name LIKE ? OR s.last_name LIKE ?)"
            )
            params.extend([fts_query, like_term, like_term, like_term])

    if grade_level is not None:
        conditions.append("e.grade_level = ?")
        params.append(grade_level)

    if room is not None:
        conditions.append("e.room = ?")
        params.append(room)

    if status is not None:
        conditions.append("s.status = ?")
        params.append(status)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT
            s.student_id,
            s.national_id,
            s.prefix,
            s.first_name,
            s.last_name,
            s.full_name,
            s.gender,
            s.status,
            e.grade_level,
            e.room,
            e.track,
            e.academic_year,
            e.semester
        FROM students s
        LEFT JOIN enrollments e ON e.student_id = s.student_id
            AND e.id = (
                SELECT max(e2.id) FROM enrollments e2 WHERE e2.student_id = s.student_id
            )
        {where_clause}
        ORDER BY s.student_id ASC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    return conn.execute(sql, params).fetchall()


def get_student(conn: sqlite3.Connection, student_id: int) -> Optional[sqlite3.Row]:
    """Fetch single student with current enrollment info."""
    sql = """
        SELECT
            s.student_id,
            s.national_id,
            s.prefix,
            s.first_name,
            s.last_name,
            s.full_name,
            s.gender,
            s.status,
            e.grade_level,
            e.room,
            e.track,
            e.academic_year,
            e.semester
        FROM students s
        LEFT JOIN enrollments e ON e.student_id = s.student_id
            AND e.id = (
                SELECT max(e2.id) FROM enrollments e2 WHERE e2.student_id = s.student_id
            )
        WHERE s.student_id = ?
    """
    return conn.execute(sql, (student_id,)).fetchone()


def update_status(
    conn: sqlite3.Connection,
    student_id: int,
    new_status: str,
    reason: Optional[str] = None,
    actor: Optional[str] = None,
) -> None:
    """Update student status and write to the corresponding audit table inside a transaction."""
    now_date = datetime.date.today().isoformat()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with conn:
        # Check current status
        cur = conn.cursor()
        cur.execute("SELECT status FROM students WHERE student_id = ?", (student_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Student {student_id} not found")
        old_status = row["status"]

        # Update students
        cur.execute("UPDATE students SET status = ? WHERE student_id = ?", (new_status, student_id))

        # Write to specific history tables
        if old_status == "active" and new_status == "on_leave":
            cur.execute(
                """
                INSERT INTO leave_of_absence (student_id, leave_date, note)
                VALUES (?, ?, ?)
                """,
                (student_id, now_date, reason),
            )
        elif old_status == "on_leave" and new_status == "active":
            cur.execute(
                """
                UPDATE leave_of_absence
                SET expected_return_date = ?
                WHERE id = (
                    SELECT max(id) FROM leave_of_absence WHERE student_id = ?
                )
                """,
                (now_date, student_id),
            )
        elif new_status == "transferred_out":
            cur.execute(
                """
                INSERT INTO transfers_out (student_id, transfer_date, note)
                VALUES (?, ?, ?)
                """,
                (student_id, now_date, reason),
            )
        elif old_status == "transferred_out" and new_status == "active":
            cur.execute(
                """
                INSERT INTO transfers_in (student_id, transfer_date, note)
                VALUES (?, ?, ?)
                """,
                (student_id, now_date, reason),
            )

        # Write activity_log
        record_activity(
            conn,
            action="student.update_status",
            entity_type="student",
            entity_id=student_id,
            detail=f"status: {old_status} -> {new_status}" + (f" ({reason})" if reason else ""),
            actor=actor,
        )


def change_student_id(
    conn: sqlite3.Connection,
    old_id: int,
    new_id: int,
    reason: Optional[str] = None,
    actor: Optional[str] = None,
) -> None:
    """Safely change primary key student_id, cascading to all tables and logging audit."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with conn:
        # Check uniqueness of new_id
        cur = conn.cursor()
        cur.execute("SELECT student_id FROM students WHERE student_id = ?", (new_id,))
        if cur.fetchone():
            raise ValueError(f"Student ID {new_id} is already in use")

        # Update students table (cascades via ON UPDATE CASCADE)
        cur.execute("UPDATE students SET student_id = ? WHERE student_id = ?", (new_id, old_id))

        # Insert audit trail
        cur.execute(
            """
            INSERT INTO student_id_changes (old_id, new_id, reason, changed_at)
            VALUES (?, ?, ?, ?)
            """,
            (old_id, new_id, reason, now_iso),
        )

        record_activity(
            conn,
            action="student.change_id",
            entity_type="student",
            entity_id=new_id,
            detail=f"ID changed: {old_id} -> {new_id}" + (f" ({reason})" if reason else ""),
            actor=actor,
        )


def update_name(
    conn: sqlite3.Connection,
    student_id: int,
    prefix: Optional[str],
    first_name: str,
    last_name: str,
    reason: Optional[str] = None,
    actor: Optional[str] = None,
) -> None:
    """Update name fields, recompute full_name, and log to student_name_changes."""
    full_name = f"{prefix or ''}{first_name} {last_name}".strip()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with conn:
        cur = conn.cursor()
        cur.execute("SELECT full_name FROM students WHERE student_id = ?", (student_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Student {student_id} not found")
        old_full_name = row["full_name"]

        cur.execute(
            """
            UPDATE students
            SET prefix = ?, first_name = ?, last_name = ?, full_name = ?
            WHERE student_id = ?
            """,
            (prefix, first_name, last_name, full_name, student_id),
        )

        cur.execute(
            """
            INSERT INTO student_name_changes (student_id, old_full_name, new_full_name, reason, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, old_full_name, full_name, reason, now_iso),
        )

        record_activity(
            conn,
            action="student.update_name",
            entity_type="student",
            entity_id=student_id,
            detail=f"Name: {old_full_name} -> {full_name}" + (f" ({reason})" if reason else ""),
            actor=actor,
        )


def get_student_history(conn: sqlite3.Connection, student_id: int) -> Dict[str, List[sqlite3.Row]]:
    """Retrieve full history across all audit tables for a given student."""
    cur = conn.cursor()
    return {
        "room_changes": cur.execute(
            "SELECT * FROM room_changes WHERE student_id = ? ORDER BY id DESC", (student_id,)
        ).fetchall(),
        "transfers_out": cur.execute(
            "SELECT * FROM transfers_out WHERE student_id = ? ORDER BY id DESC", (student_id,)
        ).fetchall(),
        "transfers_in": cur.execute(
            "SELECT * FROM transfers_in WHERE student_id = ? ORDER BY id DESC", (student_id,)
        ).fetchall(),
        "leave_of_absence": cur.execute(
            "SELECT * FROM leave_of_absence WHERE student_id = ? ORDER BY id DESC", (student_id,)
        ).fetchall(),
        "retentions": cur.execute(
            "SELECT * FROM retentions WHERE student_id = ? ORDER BY id DESC", (student_id,)
        ).fetchall(),
        "name_changes": cur.execute(
            "SELECT * FROM student_name_changes WHERE student_id = ? ORDER BY id DESC", (student_id,)
        ).fetchall(),
        "id_changes": cur.execute(
            "SELECT * FROM student_id_changes WHERE old_id = ? OR new_id = ? ORDER BY id DESC",
            (student_id, student_id),
        ).fetchall(),
    }
