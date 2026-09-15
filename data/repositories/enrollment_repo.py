import datetime
import sqlite3
from typing import Any, List, Optional
from core.shared.log_service import record_activity


def get_current_enrollment(conn: sqlite3.Connection, student_id: int) -> Optional[sqlite3.Row]:
    """Return the most recent enrollment for a student."""
    sql = """
        SELECT * FROM enrollments
        WHERE student_id = ?
        ORDER BY academic_year DESC, semester DESC, id DESC
        LIMIT 1
    """
    return conn.execute(sql, (student_id,)).fetchone()


def change_classroom(
    conn: sqlite3.Connection,
    student_id: int,
    new_room: int,
    reason: Optional[str] = None,
    actor: Optional[str] = None,
) -> None:
    """Move student to another room within the active period and record to room_changes."""
    now_date = datetime.date.today().isoformat()
    with conn:
        cur = conn.cursor()
        current = get_current_enrollment(conn, student_id)
        if not current:
            raise ValueError(f"No current enrollment found for student {student_id}")

        old_room = str(current["room"])
        new_room_str = str(new_room)

        # Update enrollment row
        cur.execute(
            "UPDATE enrollments SET room = ? WHERE id = ?",
            (new_room, current["id"]),
        )

        # Log to room_changes
        cur.execute(
            """
            INSERT INTO room_changes (student_id, old_room, new_room, change_date, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, old_room, new_room_str, now_date, reason),
        )

        record_activity(
            conn,
            action="enrollment.change_classroom",
            entity_type="student",
            entity_id=student_id,
            detail=f"Room: {old_room} -> {new_room_str}" + (f" ({reason})" if reason else ""),
            actor=actor,
        )


def enroll_next_period(
    conn: sqlite3.Connection,
    student_id: int,
    academic_year: int,
    semester: int,
    grade_level: str,
    room: int,
    track: Optional[str] = None,
    seq_no: Optional[int] = None,
    actor: Optional[str] = None,
) -> int:
    """Create a new enrollment row for a new academic period."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO enrollments (student_id, academic_year, semester, grade_level, room, track, seq_no)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, academic_year, semester, grade_level, room, track, seq_no),
        )
        enr_id = cur.lastrowid

        record_activity(
            conn,
            action="enrollment.enroll_period",
            entity_type="student",
            entity_id=student_id,
            detail=f"Enrolled {grade_level}/{room} year={academic_year} sem={semester}",
            actor=actor,
        )
        return enr_id


def get_class_roster(
    conn: sqlite3.Connection,
    academic_year: int,
    semester: int,
    grade_level: str,
    room: int,
) -> List[sqlite3.Row]:
    """Get all students enrolled in a specific class."""
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
            e.track,
            e.seq_no
        FROM enrollments e
        JOIN students s ON s.student_id = e.student_id
        WHERE e.academic_year = ? AND e.semester = ? AND e.grade_level = ? AND e.room = ?
        ORDER BY e.seq_no ASC, s.student_id ASC
    """
    return conn.execute(sql, (academic_year, semester, grade_level, room)).fetchall()


def get_class_statistics(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Fetch live computed statistics from view v_class_statistics."""
    sql = """
        SELECT * FROM v_class_statistics
        ORDER BY academic_year DESC, semester DESC, grade_level ASC, room ASC
    """
    return conn.execute(sql).fetchall()
