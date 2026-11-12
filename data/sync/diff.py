import os
import sqlite3
from typing import Any, Dict, List
from core.shared.result import Result

_LOCAL_STUDENTS_SQL = """
    SELECT s.*, e.grade_level, e.room, e.track
    FROM students s
    LEFT JOIN enrollments e ON e.student_id = s.student_id
        AND e.id = (SELECT max(e2.id) FROM enrollments e2 WHERE e2.student_id = s.student_id)
"""


def _build_students_by_id(
    students: List[Dict[str, Any]], enrollments: List[Dict[str, Any]]
) -> Dict[int, Dict[str, Any]]:
    latest: Dict[int, Dict[str, Any]] = {}
    for enr in enrollments:
        sid = enr["student_id"]
        if sid not in latest or enr["id"] > latest[sid]["id"]:
            latest[sid] = enr
    result: Dict[int, Dict[str, Any]] = {}
    for stu in students:
        enr = latest.get(stu["student_id"], {})
        result[stu["student_id"]] = {
            **stu,
            "grade_level": enr.get("grade_level"),
            "room": enr.get("room"),
            "track": enr.get("track"),
        }
    return result


def load_snapshot_data(snapshot_path: str) -> Dict[str, Any]:
    """Load snapshot metadata, tables, and latest-enrollment student map in one open."""
    if not os.path.exists(snapshot_path):
        raise FileNotFoundError(f"Snapshot file not found: {snapshot_path}")
    snap_conn = sqlite3.connect(snapshot_path)
    snap_conn.row_factory = sqlite3.Row
    try:
        cur = snap_conn.cursor()
        meta = cur.execute("SELECT * FROM snapshot_meta LIMIT 1").fetchone()
        students = [dict(r) for r in cur.execute("SELECT * FROM students").fetchall()]
        enrollments = [dict(r) for r in cur.execute("SELECT * FROM enrollments").fetchall()]
        id_changes = [dict(r) for r in cur.execute("SELECT * FROM student_id_changes ORDER BY id ASC").fetchall()]
    finally:
        snap_conn.close()
    return {
        "exported_at": meta["exported_at"] if meta else "unknown",
        "students": students, "enrollments": enrollments, "id_changes": id_changes,
        "students_by_id": _build_students_by_id(students, enrollments),
    }


def _load_local_students(local_conn: sqlite3.Connection) -> Dict[int, Dict[str, Any]]:
    rows = local_conn.cursor().execute(_LOCAL_STUDENTS_SQL).fetchall()
    return {r["student_id"]: dict(r) for r in rows}


def _collect_id_renumbering(
    id_changes: List[Dict[str, Any]], local_students: Dict[int, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    renumbered: List[Dict[str, Any]] = []
    for idc in id_changes:
        old_id = idc["old_id"]
        if old_id in local_students:
            renumbered.append({
                "old_id": old_id,
                "new_id": idc["new_id"],
                "reason": idc["reason"],
                "changed_at": idc["changed_at"],
                "student_name": local_students[old_id]["full_name"],
            })
    return renumbered


def _diff_student_fields(s_data: Dict[str, Any], l_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        field: {"old": l_data.get(field), "new": s_data.get(field)}
        for field in ("full_name", "status", "grade_level", "room")
        if s_data.get(field) != l_data.get(field)
    }


def _collect_student_diffs(
    snap_students: Dict[int, Dict[str, Any]], local_students: Dict[int, Dict[str, Any]], id_renumbered: List[Dict[str, Any]]
):
    renum_new = {r["new_id"] for r in id_renumbered}
    renum_old = {r["old_id"] for r in id_renumbered}
    new_students = [s for sid, s in snap_students.items() if sid not in local_students and sid not in renum_new]
    missing_students = [l for lid, l in local_students.items() if lid not in snap_students and lid not in renum_old]
    changed_students: List[Dict[str, Any]] = []
    for sid, s_data in snap_students.items():
        if sid in local_students:
            diffs = _diff_student_fields(s_data, local_students[sid])
            if diffs:
                changed_students.append({
                    "student_id": sid, "student_name": s_data["full_name"],
                    "status_changed": "status" in diffs, "changes": diffs,
                })
    return new_students, changed_students, missing_students


def _build_diff_summary(new_s, changed_s, missing_s, id_renumbered) -> Dict[str, int]:
    return {
        "new_count": len(new_s),
        "changed_count": len(changed_s),
        "missing_count": len(missing_s),
        "id_renumbered_count": len(id_renumbered),
        "status_changes_count": sum(1 for c in changed_s if c["status_changed"]),
    }


def diff_snapshot_data(snap_data: Dict[str, Any], local_conn: sqlite3.Connection) -> Result:
    """Compute structured diff between preloaded snapshot data and local_conn mirror."""
    try:
        local_students = _load_local_students(local_conn)
        id_renumbered = _collect_id_renumbering(snap_data["id_changes"], local_students)
        new_s, changed_s, missing_s = _collect_student_diffs(
            snap_data["students_by_id"], local_students, id_renumbered
        )
        return Result.success({
            "exported_at": snap_data["exported_at"],
            "summary": _build_diff_summary(new_s, changed_s, missing_s, id_renumbered),
            "new": new_s, "changed": changed_s,
            "missing": missing_s, "id_renumbered": id_renumbered,
        })
    except Exception as e:
        return Result.fail(f"Failed to compute sync diff: {e}")


def compute_diff(snapshot_path: str, local_conn: sqlite3.Connection) -> Result:
    """Compare an incoming snapshot SQLite file with local_conn mirror tables."""
    if not os.path.exists(snapshot_path):
        return Result.fail(f"Snapshot file not found: {snapshot_path}")
    try:
        snap_data = load_snapshot_data(snapshot_path)
    except Exception as e:
        return Result.fail(f"Failed to compute sync diff: {e}")
    return diff_snapshot_data(snap_data, local_conn)
