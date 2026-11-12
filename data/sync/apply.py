import datetime
import sqlite3
from typing import Any, Dict, List, Optional
from core.shared.result import Result
from core.shared.log_service import record_activity
from data.sync.diff import diff_snapshot_data, load_snapshot_data

_UPSERT_STUDENT_SQL = """
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
"""

_UPSERT_SYNC_STATE_SQL = """
    INSERT INTO sync_state (key, value, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
"""


def _apply_id_changes(local_cur: sqlite3.Cursor, id_changes: List[Dict[str, Any]]) -> None:
    # 1. Update existing student IDs so ON UPDATE CASCADE updates loans and reservations
    for idc in id_changes:
        local_cur.execute(
            "UPDATE students SET student_id = ? WHERE student_id = ?",
            (idc["new_id"], idc["old_id"]),
        )


def _upsert_students(local_cur: sqlite3.Cursor, students: List[Dict[str, Any]]) -> None:
    # 2. Batch upsert all students from snapshot
    rows = [
        (
            s["student_id"], s["national_id"], s["prefix"], s["first_name"],
            s["last_name"], s["full_name"], s["gender"], s["status"],
        )
        for s in students
    ]
    local_cur.executemany(_UPSERT_STUDENT_SQL, rows)


def _refresh_enrollments(local_cur: sqlite3.Cursor, enrollments: List[Dict[str, Any]]) -> None:
    # 3. Batch refresh enrollments
    local_cur.execute("DELETE FROM enrollments;")
    rows = [
        (
            e["id"], e["student_id"], e["academic_year"], e["semester"],
            e["grade_level"], e["room"], e["track"],
        )
        for e in enrollments
    ]
    local_cur.executemany(
        "INSERT INTO enrollments (id, student_id, academic_year, semester, grade_level, room, track) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def _update_sync_state(local_cur: sqlite3.Cursor, now_iso: str, exported_at: str) -> None:
    # 4. Update sync_state
    local_cur.execute(_UPSERT_SYNC_STATE_SQL, ("last_synced_at", now_iso, now_iso))
    local_cur.execute(_UPSERT_SYNC_STATE_SQL, ("snapshot_exported_at", exported_at, now_iso))


def _record_sync_activity(local_conn: sqlite3.Connection, summary: Dict[str, Any], actor: Optional[str]) -> None:
    # 5. Activity log
    detail = (
        f"Sync applied: {summary['new_count']} new, {summary['changed_count']} updated "
        f"({summary['status_changes_count']} status changes), {summary['id_renumbered_count']} ID renumbered"
    )
    record_activity(
        local_conn, action="sync.import", entity_type="system",
        entity_id=0, detail=detail, actor=actor,
    )


def apply_sync(snapshot_path: str, local_conn: sqlite3.Connection, actor: Optional[str] = None) -> Result:
    """Atomically apply student snapshot into local mirror database."""
    try:
        snap_data = load_snapshot_data(snapshot_path)
        diff_res = diff_snapshot_data(snap_data, local_conn)
        if not diff_res.ok:
            return diff_res
        summary = diff_res.data["summary"]
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with local_conn:
            cur = local_conn.cursor()
            _apply_id_changes(cur, snap_data["id_changes"])
            _upsert_students(cur, snap_data["students"])
            _refresh_enrollments(cur, snap_data["enrollments"])
            _update_sync_state(cur, now_iso, diff_res.data["exported_at"])
            _record_sync_activity(local_conn, summary, actor)
        return Result.success({"applied_at": now_iso, "summary": summary})
    except Exception as e:
        return Result.fail(f"Failed to apply sync: {e}")
