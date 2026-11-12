"""
build_db.py — converts raw school-roster xlsx into SQLite tables.
Can be run standalone or imported as a service module.
"""
import sqlite3
import sys
from typing import Optional

from core.importers.roster_parser import (
    FEMALE_PREFIXES,
    GRADE_SHEETS,
    MALE_PREFIXES,
    PREFIXES,
    SEM_RE,
    TITLE_RE,
    YEAR_RE,
    clean,
    col as _col,
    iter_grade_rows,
    normalize_date,
    split_name,
    to_int,
)
from core.shared.result import Result

__all__ = [
    "GRADE_SHEETS", "PREFIXES", "MALE_PREFIXES", "FEMALE_PREFIXES",
    "TITLE_RE", "YEAR_RE", "SEM_RE", "clean", "split_name",
    "normalize_date", "to_int", "upsert_student", "parse_grade_sheet",
    "parse_transfers_out", "parse_transfers_in", "parse_room_changes",
    "parse_leave", "parse_retentions_69", "parse_retentions_68",
    "parse_repeat_room", "import_roster",
]


def upsert_student(cur, student_id, national_id, raw_name):
    if student_id is None or not raw_name:
        return
    prefix, first, last, full, gender = split_name(raw_name)
    cur.execute(
        """
        INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, gender)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(student_id) DO UPDATE SET
            national_id=COALESCE(excluded.national_id, students.national_id),
            prefix=excluded.prefix, first_name=excluded.first_name,
            last_name=excluded.last_name, full_name=excluded.full_name,
            gender=excluded.gender
        """,
        (student_id, clean(str(national_id)) if national_id is not None else None,
         prefix, first, last, full, gender),
    )


def parse_grade_sheet(ws, cur):
    for r in iter_grade_rows(ws):
        upsert_student(cur, r["student_id"], r["national_id"], r["full_name"])
        if r["student_id"] and r["grade_level"] and r["room"]:
            cur.execute(
                """INSERT OR IGNORE INTO enrollments
                   (student_id, academic_year, semester, grade_level, room, track, seq_no)
                   VALUES (?,?,?,?,?,?,?)""",
                (r["student_id"], r["academic_year"], r["semester"],
                 r["grade_level"], r["room"], r["track"], r["seq_no"]),
            )


def parse_transfers_out(ws, cur, source_sheet, header_rows):
    for row in ws.iter_rows(min_row=header_rows + 1, values_only=True):
        student_id, name = to_int(_col(row, 1)), _col(row, 2)
        if not student_id or not name:
            continue
        upsert_student(cur, student_id, _col(row, 3), name)
        cur.execute(
            """INSERT INTO transfers_out (student_id, room_at_transfer, destination_school, transfer_date, note, source_sheet)
               VALUES (?,?,?,?,?,?)""",
            (student_id, clean(_col(row, 4)), clean(_col(row, 5)),
             normalize_date(_col(row, 6)), clean(_col(row, 7)), source_sheet),
        )
        cur.execute("UPDATE students SET status='transferred_out' WHERE student_id=?", (student_id,))


def parse_transfers_in(ws, cur):
    for row in ws.iter_rows(min_row=4, values_only=True):
        old_id, new_id, name = to_int(_col(row, 1)), to_int(_col(row, 2)), _col(row, 3)
        student_id = new_id or old_id
        if not student_id or not name:
            continue
        upsert_student(cur, student_id, None, name)
        cur.execute(
            """INSERT INTO transfers_in (student_id, old_student_id, previous_school, transfer_date, room, note)
               VALUES (?,?,?,?,?,?)""",
            (student_id, old_id, clean(_col(row, 4)), normalize_date(_col(row, 5)),
             clean(_col(row, 6)), clean(_col(row, 7))),
        )


def parse_room_changes(ws, cur):
    for row in ws.iter_rows(min_row=5, values_only=True):
        student_id, name = to_int(_col(row, 1)), _col(row, 2)
        if not student_id or not name:
            continue
        upsert_student(cur, student_id, None, name)
        cur.execute(
            """INSERT INTO room_changes (student_id, old_room, new_room, change_date, note)
               VALUES (?,?,?,?,?)""",
            (student_id, clean(_col(row, 3)), clean(_col(row, 4)),
             normalize_date(_col(row, 5)), clean(_col(row, 6))),
        )


def parse_leave(ws, cur):
    for row in ws.iter_rows(min_row=4, values_only=True):
        student_id, name = to_int(_col(row, 1)), _col(row, 2)
        if not student_id or not name:
            continue
        upsert_student(cur, student_id, _col(row, 3), name)
        cur.execute(
            """INSERT INTO leave_of_absence (student_id, grade_room_at_leave, leave_date, expected_return_date, note)
               VALUES (?,?,?,?,?)""",
            (student_id, clean(_col(row, 4)), normalize_date(_col(row, 5)),
             normalize_date(_col(row, 7)), clean(_col(row, 6))),
        )
        cur.execute("UPDATE students SET status='on_leave' WHERE student_id=?", (student_id,))


def parse_retentions_69(ws, cur, year):
    for row in ws.iter_rows(min_row=2, values_only=True):
        student_id, name = to_int(_col(row, 1)), _col(row, 2)
        if not student_id or not name:
            continue
        upsert_student(cur, student_id, None, name)
        cur.execute(
            """INSERT INTO retentions (student_id, academic_year, new_class, entry_date, note)
               VALUES (?,?,?,?,?)""",
            (student_id, year, clean(_col(row, 3)), normalize_date(_col(row, 4)), clean(_col(row, 5))),
        )


def parse_retentions_68(ws, cur, year):
    for row in ws.iter_rows(min_row=3, values_only=True):
        student_id, name = to_int(_col(row, 1)), _col(row, 2)
        if not student_id or not name:
            continue
        upsert_student(cur, student_id, None, name)
        cur.execute(
            """INSERT INTO retentions (student_id, academic_year, old_class, new_class, note)
               VALUES (?,?,?,?,?)""",
            (student_id, year, clean(_col(row, 4)), clean(_col(row, 5)), clean(_col(row, 6))),
        )


def parse_repeat_room(ws, cur):
    for row in ws.iter_rows(min_row=2, values_only=True):
        student_id, name = to_int(_col(row, 1)), _col(row, 2)
        if not student_id or not name:
            continue
        upsert_student(cur, student_id, None, name)
        cur.execute(
            """INSERT INTO retentions (student_id, new_class, entry_date, note)
               VALUES (?,?,?,?)""",
            (student_id, clean(_col(row, 4)), normalize_date(_col(row, 3)), clean(_col(row, 5))),
        )


def _parse_all_sheets(wb, cur):
    sheets = set(wb.sheetnames)
    for name in GRADE_SHEETS:
        if name in sheets:
            parse_grade_sheet(wb[name], cur)
    for sheet, hdr in [("ย้ายออก", 1), ("ย้ายออกส่งเขต1", 3), ("ย้ายออกส่งเขต (2)", 3)]:
        if sheet in sheets:
            parse_transfers_out(wb[sheet], cur, sheet, header_rows=hdr)
    if "ย้ายเข้า" in sheets:
        parse_transfers_in(wb["ย้ายเข้า"], cur)
    if "ย้ายห้อง" in sheets:
        parse_room_changes(wb["ย้ายห้อง"], cur)
    if "รายชื่อพักการเรียน" in sheets:
        parse_leave(wb["รายชื่อพักการเรียน"], cur)
    if "รายชื่อไม่ได้เลื่อนชั้นปี69" in sheets:
        parse_retentions_69(wb["รายชื่อไม่ได้เลื่อนชั้นปี69"], cur, 2026)
    if "รายชื่อไม่ได้เลื่อนชั้นปี68" in sheets:
        parse_retentions_68(wb["รายชื่อไม่ได้เลื่อนชั้นปี68"], cur, 2025)
    if "นักเรียนม.3ชั้น" in sheets:
        parse_repeat_room(wb["นักเรียนม.3ชั้น"], cur)


def _run_import_transaction(wb, conn) -> Result:
    cur = conn.cursor()
    conn.execute("PRAGMA foreign_keys = OFF;")
    try:
        with conn:
            for t in ("retentions", "leave_of_absence", "transfers_in", "transfers_out", "room_changes", "enrollments", "students"):
                cur.execute(f"DELETE FROM {t};")
            _parse_all_sheets(wb, cur)
        tables = ("students", "enrollments", "room_changes", "transfers_out", "transfers_in", "leave_of_absence", "retentions")
        counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
        return Result.success(counts)
    except Exception as e:
        return Result.fail(f"Failed to import roster: {e}")
    finally:
        conn.execute("PRAGMA foreign_keys = ON;")


def import_roster(xlsx_path: str, conn: Optional[sqlite3.Connection] = None, db_path: Optional[str] = None) -> Result:
    """Import roster data from xlsx into open connection or db_path."""
    try:
        import openpyxl
    except ImportError:
        return Result.fail("openpyxl library is required for importing xlsx rosters")
    if conn is None and not db_path:
        return Result.fail("Must provide either an active database connection or db_path")
    close_after = conn is None
    active_conn = sqlite3.connect(db_path) if close_after else conn
    try:
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        try:
            return _run_import_transaction(wb, active_conn)
        finally:
            wb.close()
    finally:
        if close_after:
            active_conn.close()


if __name__ == "__main__":
    x_path = sys.argv[1] if len(sys.argv) > 1 else "default.profraw.xlsx"
    d_path = sys.argv[2] if len(sys.argv) > 2 else "school.sqlite"
    res = import_roster(x_path, db_path=d_path)
    if res.ok:
        print("Import successful:")
        for tbl, count in res.data.items():
            print(f"  {tbl}: {count} rows")
    else:
        print(f"Import failed: {res.error}")
