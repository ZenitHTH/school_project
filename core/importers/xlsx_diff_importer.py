import re
import sqlite3
from typing import Any, Dict, List, Optional
import openpyxl
from core.importers.build_db import GRADE_SHEETS, clean, split_name, to_int, TITLE_RE, YEAR_RE, SEM_RE
from core.shared.log_service import record_activity
from core.shared.result import Result


def parse_roster_sheets(file_path: str) -> List[Dict[str, Any]]:
    """Parse roster workbook sheets into structured row dictionaries with fast read-only streaming."""
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    rows: List[Dict[str, Any]] = []

    try:
        for sheet_name in wb.sheetnames:
            if sheet_name not in GRADE_SHEETS:
                continue
            ws = wb[sheet_name]
            grade, room, year, semester, track = None, None, None, None, None
            in_block = False

            for row in ws.iter_rows(values_only=True):
                a = clean(row[0]) if len(row) > 0 else None
                b = row[1] if len(row) > 1 else None
                c = clean(row[2]) if len(row) > 2 else None
                d = row[3] if len(row) > 3 else None

                title_match = TITLE_RE.search(str(a)) if a else None
                if title_match:
                    grade, room = int(title_match.group(1)), int(title_match.group(2))
                    ym = YEAR_RE.search(a)
                    sm = SEM_RE.search(a)
                    year = int(ym.group(1)) if ym else None
                    if year and year > 2400:
                        year -= 543
                    semester = int(sm.group(1)) if sm else None
                    track = TITLE_RE.sub("", a)
                    track = YEAR_RE.sub("", track)
                    track = SEM_RE.sub("", track)
                    track = clean(track.replace("ภาคเรียนที่", "")) or None
                    in_block = False
                    continue

                if a == "ที่":
                    in_block = True
                    continue

                if in_block and isinstance(b, (int, float)) and c:
                    seq = to_int(a)
                    student_id = to_int(b)
                    if not student_id:
                        continue
                    prefix, first, last, full, gender = split_name(c)
                    rows.append({
                        "student_id": student_id,
                        "national_id": clean(str(d)) if d is not None else None,
                        "prefix": prefix,
                        "first_name": first,
                        "last_name": last,
                        "full_name": full,
                        "gender": gender,
                        "grade_level": f"ม.{grade}" if grade else None,
                        "room": room,
                        "track": track,
                        "seq_no": seq,
                        "academic_year": year,
                        "semester": semester,
                    })
                elif in_block and a is None and b is None:
                    in_block = False
    finally:
        wb.close()

    return rows


def calculate_xlsx_diff(
    conn: sqlite3.Connection,
    file_path: str,
    academic_year: Optional[int] = None,
    semester: Optional[int] = None,
) -> Result:
    """
    Diff parsed xlsx roster against current database per design_doc §6a.
    Returns categorized diff:
      - new_students
      - grade_room_changes
      - missing_students
      - identity_conflicts
    """
    try:
        parsed_rows = parse_roster_sheets(file_path)
    except Exception as e:
        return Result.fail(f"Failed to read roster file: {e}")

    # Fetch current active students and their latest enrollment
    curr_rows = conn.execute("""
        SELECT
            s.student_id,
            s.national_id,
            s.full_name,
            s.status,
            e.grade_level,
            e.room,
            e.academic_year,
            e.semester
        FROM students s
        LEFT JOIN enrollments e ON e.student_id = s.student_id
            AND e.id = (
                SELECT max(e2.id) FROM enrollments e2 WHERE e2.student_id = s.student_id
            )
    """).fetchall()

    db_students: Dict[int, sqlite3.Row] = {row["student_id"]: row for row in curr_rows}
    file_student_ids = {row["student_id"] for row in parsed_rows}

    new_students: List[Dict[str, Any]] = []
    grade_room_changes: List[Dict[str, Any]] = []
    identity_conflicts: List[Dict[str, Any]] = []
    missing_students: List[Dict[str, Any]] = []

    for f_row in parsed_rows:
        sid = f_row["student_id"]
        if sid not in db_students:
            new_students.append(f_row)
        else:
            db_s = db_students[sid]
            # Check name or status conflict
            if f_row["full_name"] and db_s["full_name"] and f_row["full_name"] != db_s["full_name"]:
                identity_conflicts.append({
                    "student_id": sid,
                    "db_name": db_s["full_name"],
                    "file_name": f_row["full_name"],
                })

            # Check grade/room change
            f_grade = f_row.get("grade_level")
            f_room = f_row.get("room")
            if (f_grade and f_grade != db_s["grade_level"]) or (f_room is not None and f_room != db_s["room"]):
                grade_room_changes.append({
                    "student_id": sid,
                    "old_grade": db_s["grade_level"],
                    "old_room": db_s["room"],
                    "new_grade": f_grade,
                    "new_room": f_room,
                    "track": f_row.get("track"),
                    "seq_no": f_row.get("seq_no"),
                })

    for sid, db_s in db_students.items():
        if sid not in file_student_ids and db_s["status"] == "active":
            missing_students.append({
                "student_id": sid,
                "full_name": db_s["full_name"],
                "grade_level": db_s["grade_level"],
                "room": db_s["room"],
            })

    detected_year = None
    detected_semester = None
    for r in parsed_rows:
        if r.get("academic_year"):
            detected_year = r["academic_year"]
            detected_semester = r.get("semester") or 1
            break

    diff_data = {
        "new_students": new_students,
        "grade_room_changes": grade_room_changes,
        "missing_students": missing_students,
        "identity_conflicts": identity_conflicts,
        "total_in_file": len(parsed_rows),
        "detected_year": detected_year,
        "detected_semester": detected_semester,
    }
    return Result.success(diff_data)


def apply_xlsx_diff(
    conn: sqlite3.Connection,
    diff: Dict[str, Any],
    academic_year: int,
    semester: int,
    actor: Optional[str] = None,
) -> Result:
    """
    Apply diff changes atomically in a single transaction.
    Adds new students and appends new enrollment periods for promotions.
    """
    try:
        with conn:
            # 1. Insert new students and their initial enrollments
            for s in diff.get("new_students", []):
                raw_g = s.get("gender")
                gender = "M" if raw_g in ("M", "ชาย") else ("F" if raw_g in ("F", "หญิง") else None)
                conn.execute(
                    """
                    INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, gender, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                    ON CONFLICT(student_id) DO UPDATE SET
                        full_name = excluded.full_name,
                        gender = excluded.gender
                    """,
                    (
                        s["student_id"],
                        s.get("national_id"),
                        s.get("prefix"),
                        s.get("first_name"),
                        s.get("last_name"),
                        s["full_name"],
                        gender,
                    ),
                )
                if s.get("grade_level") and s.get("room") is not None:
                    conn.execute(
                        """
                        INSERT INTO enrollments (student_id, academic_year, semester, grade_level, room, track, seq_no)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(student_id, academic_year, semester, grade_level, room)
                        DO UPDATE SET track = excluded.track, seq_no = excluded.seq_no
                        """,
                        (
                            s["student_id"],
                            academic_year,
                            semester,
                            s["grade_level"],
                            s["room"],
                            s.get("track"),
                            s.get("seq_no"),
                        ),
                    )

            # 2. Append new enrollments for grade/room promotions
            for c in diff.get("grade_room_changes", []):
                conn.execute(
                    """
                    INSERT INTO enrollments (student_id, academic_year, semester, grade_level, room, track, seq_no)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(student_id, academic_year, semester, grade_level, room)
                    DO UPDATE SET track = excluded.track, seq_no = excluded.seq_no
                    """,
                    (
                        c["student_id"],
                        academic_year,
                        semester,
                        c["new_grade"],
                        c["new_room"],
                        c.get("track"),
                        c.get("seq_no"),
                    ),
                )

            # Log activity
            summary = (
                f"Applied xlsx promotion import: {len(diff.get('new_students', []))} added, "
                f"{len(diff.get('grade_room_changes', []))} promoted for Year {academic_year} Sem {semester}"
            )
            record_activity(
                conn,
                action="xlsx_diff_import",
                entity_type="enrollment",
                entity_id="bulk",
                detail=summary,
                actor=actor,
            )

        return Result.success({
            "new_added": len(diff.get("new_students", [])),
            "promoted": len(diff.get("grade_room_changes", [])),
        })
    except Exception as e:
        return Result.fail(f"Failed to apply xlsx diff: {e}")
