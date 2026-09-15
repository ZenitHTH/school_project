import datetime
import os
import sqlite3
from typing import Optional
from core.shared.result import Result
from core.shared.log_service import record_activity


def export_snapshot(
    conn: sqlite3.Connection,
    output_path: str,
    actor: Optional[str] = None,
) -> Result:
    """
    Export minimal student snapshot file (students, active enrollments, id changes)
    from Student Management to be shared via LINE chat.
    """
    try:
        if os.path.exists(output_path):
            os.remove(output_path)

        out_conn = sqlite3.connect(output_path)
        out_cur = out_conn.cursor()

        # Create destination tables
        out_cur.execute(
            """
            CREATE TABLE students (
                student_id   INTEGER PRIMARY KEY,
                national_id  TEXT,
                prefix       TEXT,
                first_name   TEXT,
                last_name    TEXT,
                full_name    TEXT NOT NULL,
                gender       TEXT,
                status       TEXT NOT NULL
            );
            """
        )
        out_cur.execute(
            """
            CREATE TABLE enrollments (
                id            INTEGER PRIMARY KEY,
                student_id    INTEGER NOT NULL,
                academic_year INTEGER,
                semester      INTEGER,
                grade_level   TEXT NOT NULL,
                room          INTEGER NOT NULL,
                track         TEXT
            );
            """
        )
        out_cur.execute(
            """
            CREATE TABLE student_id_changes (
                id          INTEGER PRIMARY KEY,
                old_id      INTEGER NOT NULL,
                new_id      INTEGER NOT NULL,
                reason      TEXT,
                changed_at  TEXT NOT NULL
            );
            """
        )
        out_cur.execute(
            """
            CREATE TABLE snapshot_meta (
                exported_at TEXT NOT NULL,
                student_count INTEGER NOT NULL,
                enrollment_count INTEGER NOT NULL
            );
            """
        )

        # Copy students
        src_cur = conn.cursor()
        src_cur.execute(
            "SELECT student_id, national_id, prefix, first_name, last_name, full_name, gender, status FROM students"
        )
        students = src_cur.fetchall()
        out_cur.executemany(
            "INSERT INTO students VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [tuple(s) for s in students],
        )

        # Copy current enrollments
        src_cur.execute(
            """
            SELECT id, student_id, academic_year, semester, grade_level, room, track
            FROM enrollments
            WHERE id IN (SELECT max(id) FROM enrollments GROUP BY student_id)
            """
        )
        enrollments = src_cur.fetchall()
        out_cur.executemany(
            "INSERT INTO enrollments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tuple(e) for e in enrollments],
        )

        # Copy id changes
        src_cur.execute("SELECT id, old_id, new_id, reason, changed_at FROM student_id_changes")
        id_changes = src_cur.fetchall()
        out_cur.executemany(
            "INSERT INTO student_id_changes VALUES (?, ?, ?, ?, ?)",
            [tuple(c) for c in id_changes],
        )

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        out_cur.execute(
            "INSERT INTO snapshot_meta VALUES (?, ?, ?)",
            (now_iso, len(students), len(enrollments)),
        )

        out_conn.commit()
        out_conn.close()

        record_activity(
            conn,
            action="sync.export",
            entity_type="system",
            entity_id=0,
            detail=f"Exported student snapshot with {len(students)} students to {os.path.basename(output_path)}",
            actor=actor,
        )

        return Result.success({
            "output_path": output_path,
            "student_count": len(students),
            "enrollment_count": len(enrollments),
            "exported_at": now_iso,
        })
    except Exception as e:
        return Result.fail(f"Snapshot export failed: {e}")
