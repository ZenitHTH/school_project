import os
import sqlite3
from typing import List, Optional, Tuple
from core.shared.result import Result

GRADE_SHEETS = ["ม.1", "ม.2", "ม.3", "ม.4", "ม.5", "ม.6"]


def validate_sqlite_file(file_path: str, conn: Optional[sqlite3.Connection] = None) -> Result:
    """Check if sqlite file has expected schema tables and key columns."""
    if not os.path.exists(file_path) and conn is None:
        return Result.fail(f"File not found: {file_path}")

    close_after = False
    if conn is None:
        try:
            conn = sqlite3.connect(file_path)
            close_after = True
        except Exception as e:
            return Result.fail(f"Could not open SQLite database: {e}")

    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cur.fetchall()}

        required_tables = [
            "students", "enrollments", "room_changes", "transfers_out",
            "transfers_in", "leave_of_absence", "retentions"
        ]
        missing_tables = [t for t in required_tables if t not in tables]
        if missing_tables:
            return Result.fail(
                f"Database doesn't match expected student database — missing table(s): {', '.join(missing_tables)}"
            )

        # Check key columns in students
        cur.execute("PRAGMA table_info(students);")
        student_cols = {row[1] for row in cur.fetchall()}
        if "student_id" not in student_cols or "full_name" not in student_cols:
            return Result.fail("Database 'students' table is missing required columns (student_id, full_name).")

        return Result.success({"tables": list(tables)})
    finally:
        if close_after and conn:
            conn.close()


def validate_xlsx_structure(file_path: str) -> Result:
    """Validate sheet names and header markers for xlsx roster without full parsing."""
    if not os.path.exists(file_path):
        return Result.fail(f"File not found: {file_path}")

    # Use openpyxl if available; otherwise inspect sheet names via zipfile
    sheet_names: list = []
    _openpyxl_ok = False
    try:
        import openpyxl
        _openpyxl_ok = True
    except ImportError:
        pass

    if _openpyxl_ok:
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True)
            sheet_names = wb.sheetnames
        except Exception as e:
            return Result.fail(f"Cannot read file as Excel: {e}")
    else:
        # Fallback to reading xl/workbook.xml from zipfile
        import zipfile
        import xml.etree.ElementTree as ET
        try:
            with zipfile.ZipFile(file_path, "r") as z:
                with z.open("xl/workbook.xml") as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                    sheets_elem = root.find("main:sheets", ns)
                    sheet_names = [s.attrib["name"] for s in sheets_elem] if sheets_elem else []
        except Exception as e:
            return Result.fail(f"Not a valid Excel file or failed to read sheets: {e}")

    # Check required sheets
    missing_sheets = [s for s in GRADE_SHEETS if s not in sheet_names]
    if missing_sheets:
        return Result.fail(
            f"This doesn't look like a student roster file — missing class sheet(s): {', '.join(missing_sheets)}"
        )

    return Result.success({"sheets": sheet_names})


def check_live_data_exists(conn: sqlite3.Connection) -> Tuple[bool, str]:
    """Check if database contains live application data that re-importing would wipe."""
    cur = conn.cursor()

    # Check activity_log
    cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='activity_log';")
    if cur.fetchone()[0] > 0:
        cur.execute("SELECT count(*) FROM activity_log;")
        if cur.fetchone()[0] > 0:
            return True, "activity_log contains existing event history"

    # Check books/loans
    cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='loans';")
    if cur.fetchone()[0] > 0:
        cur.execute("SELECT count(*) FROM loans;")
        if cur.fetchone()[0] > 0:
            return True, "loans table contains active or past borrowing records"

    return False, ""
