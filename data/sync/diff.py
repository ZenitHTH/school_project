import os
import sqlite3
from typing import Any, Dict, List, Optional
from core.shared.result import Result


def compute_diff(snapshot_path: str, local_conn: sqlite3.Connection) -> Result:
    """
    Compare an incoming snapshot SQLite file with local_conn mirror tables.
    Returns structured diff preview. Pure read-only operation.
    """
    if not os.path.exists(snapshot_path):
        return Result.fail(f"Snapshot file not found: {snapshot_path}")

    try:
        try:
            snap_conn = sqlite3.connect(snapshot_path)
            snap_conn.row_factory = sqlite3.Row
            snap_cur = snap_conn.cursor()

            # Check metadata
            meta = snap_cur.execute("SELECT * FROM snapshot_meta LIMIT 1").fetchone()
            exported_at = meta["exported_at"] if meta else "unknown"

            # Load snapshot students
            snap_students_rows = snap_cur.execute(
                """
                SELECT s.*, e.grade_level, e.room, e.track
                FROM students s
                LEFT JOIN enrollments e ON e.student_id = s.student_id
                    AND e.id = (SELECT max(e2.id) FROM enrollments e2 WHERE e2.student_id = s.student_id)
                """
            ).fetchall()
            snap_students = {r["student_id"]: dict(r) for r in snap_students_rows}

            # Load snapshot ID changes
            snap_id_changes = snap_cur.execute(
                "SELECT * FROM student_id_changes ORDER BY id ASC"
            ).fetchall()
        finally:
            snap_conn.close()

        # Load local mirror students
        local_cur = local_conn.cursor()
        local_students_rows = local_cur.execute(
            """
            SELECT s.*, e.grade_level, e.room, e.track
            FROM students s
            LEFT JOIN enrollments e ON e.student_id = s.student_id
                AND e.id = (SELECT max(e2.id) FROM enrollments e2 WHERE e2.student_id = s.student_id)
            """
        ).fetchall()
        local_students = {r["student_id"]: dict(r) for r in local_students_rows}

        new_students: List[Dict[str, Any]] = []
        changed_students: List[Dict[str, Any]] = []
        missing_students: List[Dict[str, Any]] = []
        id_renumbered: List[Dict[str, Any]] = []

        # 1. Check ID renumbering
        for idc in snap_id_changes:
            old_id = idc["old_id"]
            new_id = idc["new_id"]
            if old_id in local_students:
                id_renumbered.append({
                    "old_id": old_id,
                    "new_id": new_id,
                    "reason": idc["reason"],
                    "changed_at": idc["changed_at"],
                    "student_name": local_students[old_id]["full_name"],
                })

        # 2. Check new and changed
        for s_id, s_data in snap_students.items():
            if s_id not in local_students:
                # Check if it was an old renumbered ID
                is_renumbered = any(r["new_id"] == s_id for r in id_renumbered)
                if not is_renumbered:
                    new_students.append(s_data)
            else:
                l_data = local_students[s_id]
                diffs = {}
                for field in ["full_name", "status", "grade_level", "room"]:
                    if s_data.get(field) != l_data.get(field):
                        diffs[field] = {"old": l_data.get(field), "new": s_data.get(field)}

                if diffs:
                    status_changed = "status" in diffs
                    changed_students.append({
                        "student_id": s_id,
                        "student_name": s_data["full_name"],
                        "status_changed": status_changed,
                        "changes": diffs,
                    })

        # 3. Check missing from snapshot
        for l_id, l_data in local_students.items():
            if l_id not in snap_students:
                is_renumbered = any(r["old_id"] == l_id for r in id_renumbered)
                if not is_renumbered:
                    missing_students.append(l_data)

        diff_result = {
            "exported_at": exported_at,
            "summary": {
                "new_count": len(new_students),
                "changed_count": len(changed_students),
                "missing_count": len(missing_students),
                "id_renumbered_count": len(id_renumbered),
                "status_changes_count": sum(1 for c in changed_students if c["status_changed"]),
            },
            "new": new_students,
            "changed": changed_students,
            "missing": missing_students,
            "id_renumbered": id_renumbered,
        }
        return Result.success(diff_result)
    except Exception as e:
        return Result.fail(f"Failed to compute sync diff: {e}")
