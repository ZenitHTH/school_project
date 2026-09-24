import sqlite3
import pytest
from core.student.services.student_service import StudentService
from data.migrate import apply_migrations


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    apply_migrations(c)
    # Seed test records
    c.execute(
        "INSERT INTO students (student_id, national_id, full_name, first_name, last_name, status) "
        "VALUES (54321, '1234567890123', 'นายสมชาย เข็มกลัด', 'สมชาย', 'เข็มกลัด', 'active')"
    )
    c.execute(
        "INSERT INTO students (student_id, national_id, full_name, first_name, last_name, status) "
        "VALUES (94321, '9999999999999', 'นางสาวสมหญิง จริงใจ', 'สมหญิง', 'จริงใจ', 'active')"
    )
    c.execute(
        "INSERT INTO enrollments (id, student_id, academic_year, semester, grade_level, room) "
        "VALUES (1, 54321, 2567, 1, 'ม.1', 2)"
    )
    c.execute(
        "INSERT INTO enrollments (id, student_id, academic_year, semester, grade_level, room) "
        "VALUES (2, 94321, 2567, 1, 'ม.1', 3)"
    )
    c.commit()
    return c


def test_national_id_excluded(conn):
    svc = StudentService(conn)
    res = svc.search("1234567890123")
    assert res.ok
    assert len(res.data) == 0  # national_id is strictly excluded from search


def test_id_suffix_match(conn):
    svc = StudentService(conn)
    res = svc.search("4321")
    assert res.ok
    assert len(res.data) == 2  # matches 54321 and 94321 suffix


def test_grade_room_queries(conn):
    svc = StudentService(conn)
    for q in ["ม.1/2", "ม1/2", "ม.1.2", "1/2"]:
        res = svc.search(q)
        assert res.ok, f"Failed for query {q}"
        assert len(res.data) == 1
        assert res.data[0]["student_id"] == 54321


def test_thai_middle_substring(conn):
    svc = StudentService(conn)
    res = svc.search("เข็ม")
    assert res.ok
    assert len(res.data) == 1
    assert res.data[0]["student_id"] == 54321


def test_short_query_fallback(conn):
    svc = StudentService(conn)
    res = svc.search("สม")
    assert res.ok
    assert len(res.data) == 2
