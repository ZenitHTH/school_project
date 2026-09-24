import sqlite3
from unittest.mock import patch
from core.importers.xlsx_diff_importer import apply_xlsx_diff, calculate_xlsx_diff
from data.migrate import apply_migrations


def test_xlsx_diff_categorization_and_atomic_apply():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)

    # Seed initial student 101 and existing enrollment in 2566
    conn.execute(
        "INSERT INTO students (student_id, national_id, full_name, first_name, last_name, status) "
        "VALUES (101, '111', 'นายเดิม แท้', 'เดิม', 'แท้', 'active')"
    )
    conn.execute(
        "INSERT INTO enrollments (id, student_id, academic_year, semester, grade_level, room) "
        "VALUES (1, 101, 2566, 2, 'ม.1', 1)"
    )
    conn.commit()

    # Mocked parsed rows from a new yearly xlsx roster
    parsed_rows = [
        # Student 101 promoted from ม.1 room 1 to ม.2 room 1
        {
            "student_id": 101,
            "national_id": "111",
            "prefix": "นาย",
            "first_name": "เดิม",
            "last_name": "แท้",
            "full_name": "นายเดิม แท้",
            "gender": "ชาย",
            "grade_level": "ม.2",
            "room": 1,
            "track": "วิทย์-คณิต",
        },
        # Student 102 newly entering school
        {
            "student_id": 102,
            "national_id": "222",
            "prefix": "เด็กหญิง",
            "first_name": "ใหม่",
            "last_name": "สุข",
            "full_name": "เด็กหญิงใหม่ สุข",
            "gender": "หญิง",
            "grade_level": "ม.1",
            "room": 1,
            "track": None,
        },
    ]

    with patch("core.importers.xlsx_diff_importer.parse_roster_sheets", return_value=parsed_rows):
        res = calculate_xlsx_diff(conn, "dummy.xlsx", academic_year=2567, semester=1)
        assert res.ok
        diff = res.data

        # Verify categorization per design doc §6a
        assert len(diff["new_students"]) == 1
        assert diff["new_students"][0]["student_id"] == 102

        assert len(diff["grade_room_changes"]) == 1
        change = diff["grade_room_changes"][0]
        assert change["student_id"] == 101
        assert change["old_grade"] == "ม.1"
        assert change["new_grade"] == "ม.2"

        # Apply diff atomically
        apply_res = apply_xlsx_diff(conn, diff, academic_year=2567, semester=1, actor="registrar")
        assert apply_res.ok

        # Verify new student inserted
        s102 = conn.execute("SELECT * FROM students WHERE student_id = 102").fetchone()
        assert s102 is not None
        assert s102["full_name"] == "เด็กหญิงใหม่ สุข"

        # Verify student 101 new enrollment period added without clobbering history
        e101 = conn.execute(
            "SELECT * FROM enrollments WHERE student_id = 101 AND academic_year = 2567"
        ).fetchone()
        assert e101 is not None
        assert e101["grade_level"] == "ม.2"

        # Previous enrollment still preserved
        all_e = conn.execute("SELECT * FROM enrollments WHERE student_id = 101").fetchall()
        assert len(all_e) == 2
