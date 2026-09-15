import datetime
import os
import sqlite3
from typing import Optional
from core.shared.result import Result
from core.shared.log_service import record_activity
from data.sync.diff import compute_diff


def apply_sync(
    snapshot_path: str,
    local_conn: sqlite3.Connection,
    actor: Optional[str] = None,
) -> Result:
    """
    Atomically apply student snapshot into local mirror database.
    Updates loans/reservations for renumbered IDs, refreshes mirror tables,
    updates sync_state, and records to activity_log.
    """
    diff_res = compute_diff(snapshot_path, local_conn)
    if not diff_res.ok:
        return diff_res

    diff_data = diff_res.data
    summary = diff_data["summary"]

    try:
        snap_conn = sqlite3.connect(snapshot_path)
        snap_conn.row_factory = sqlite3.Row
        snap_cur = snap_conn.cursor()

        try:
            students = snap_cur.execute("SELECT * FROM students").fetchall()
            enrollments = snap_cur.execute("SELECT * FROM enrollments").fetchall()
            id_changes = snap_cur.execute("SELECT * FROM student_id_changes").fetchall()
        finally:
            snap_conn.close()

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with local_conn:
            local_cur = local_conn.cursor()

            # 1. Update existing student IDs in students table, allowing ON UPDATE CASCADE
            # to propagate to loans and reservations automatically without FK violation
            for idc in id_changes:
                old_id = idc["old_id"]
                new_id = idc["new_id"]
                local_cur.execute(
                    "UPDATE students SET student_id = ? WHERE student_id = ?",
                    (new_id, old_id),
                )

            # 2. Upsert all students from snapshot
            for s in students:
                local_cur.execute(
                    """
                    INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, gender, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(student_id) DO UPDATE SET
                        national_id = excluded.national_id,
                        prefix = excluded.prefix,
                        first_name = excluded.first_name,
                        last_name = excluded.last_name,
                        full_name = excluded.full_name,
                        gender = excluded.gender,
                        status = excluded.status
                    """,
                    (s["student_id"], s["national_id"], s["prefix"], s["first_name"], s["last_name"], s["full_name"], s["gender"], s["status"]),
                )

            # 3. Refresh enrollments
            local_cur.execute("DELETE FROM enrollments;")
            for e in enrollments:
                local_cur.execute(
                    """
                    INSERT INTO enrollments (id, student_id, academic_year, semester, grade_level, room, track)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (e["id"], e["student_id"], e["academic_year"], e["semester"], e["grade_level"], e["room"], e["track"]),
                )

            # 3. Update sync_state
            local_cur.execute(
                """
                INSERT INTO sync_state (key, value, updated_at)
                VALUES ('last_synced_at', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (now_iso, now_iso),
            )
            local_cur.execute(
                """
                INSERT INTO sync_state (key, value, updated_at)
                VALUES ('snapshot_exported_at', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (diff_data["exported_at"], now_iso),
            )

            # 4. Activity log
            log_detail = (
                f"Sync applied: {summary['new_count']} new, {summary['changed_count']} updated "
                f"({summary['status_changes_count']} status changes), {summary['id_renumbered_count']} ID renumbered"
            )
            record_activity(
                local_conn,
                action="sync.import",
                entity_type="system",
                entity_id=0,
                detail=log_detail,
                actor=actor,
            )

        return Result.success({
            "applied_at": now_iso,
            "summary": summary,
        })
    except Exception as e:
        return Result.fail(f"Failed to apply sync: {e}")
