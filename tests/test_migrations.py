import os
import sqlite3
import pytest
from data.db import get_connection, record_failed_attempt, reset_lockout
from data.migrate import apply_migrations, get_current_version
from core.shared.result import Result
from core.shared.log_service import record_activity


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_school.sqlite")
    yield db_file
    for ext in ["", ".salt", ".lockout", ".pin_hash"]:
        f = db_file + ext
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass


def test_migrations_full_lifecycle(temp_db):
    conn = get_connection(temp_db, pin="123456")
    assert get_current_version(conn) == 0

    applied = apply_migrations(conn)
    assert applied == 6
    assert get_current_version(conn) == 6

    # Verify tables
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cur.fetchall()}

    expected_tables = {
        "students", "enrollments", "room_changes", "transfers_out",
        "transfers_in", "leave_of_absence", "retentions",
        "books", "book_copies", "loans", "reservations", "fines",
        "student_id_changes", "student_name_changes", "books_fts", "students_fts",
        "categories", "book_copy_status_log", "activity_log", "sync_state"
    }
    for t in expected_tables:
        assert t in tables, f"Missing table: {t}"

    # Verify view
    cur.execute("SELECT name FROM sqlite_master WHERE type='view';")
    views = {row[0] for row in cur.fetchall()}
    assert "v_class_statistics" in views

    # Test student insert and FTS trigger
    cur.execute(
        "INSERT INTO students (student_id, national_id, full_name, gender, status) VALUES (?, ?, ?, ?, ?)",
        (1001, "1234567890123", "สมชาย เข็มกลัด", "M", "active")
    )
    conn.commit()

    cur.execute("SELECT * FROM students_fts WHERE students_fts MATCH 'สมชาย'")
    fts_row = cur.fetchone()
    assert fts_row is not None
    assert fts_row[0] == "สมชาย เข็มกลัด"

    # Test ON UPDATE CASCADE
    cur.execute(
        "INSERT INTO enrollments (student_id, academic_year, semester, grade_level, room) VALUES (?, ?, ?, ?, ?)",
        (1001, 2567, 1, "ม.1", 1)
    )
    conn.commit()

    cur.execute("UPDATE students SET student_id = 9999 WHERE student_id = 1001")
    conn.commit()

    cur.execute("SELECT student_id FROM enrollments WHERE id = 1")
    updated_enr = cur.fetchone()
    assert updated_enr[0] == 9999, "Cascade update failed!"

    # Test activity_log
    record_activity(conn, action="student.update_id", entity_type="student", entity_id=9999, detail="1001 -> 9999")
    conn.commit()

    cur.execute("SELECT action, entity_id, detail FROM activity_log WHERE entity_id = '9999'")
    log_row = cur.fetchone()
    assert log_row is not None
    assert log_row[0] == "student.update_id"

    conn.close()


def test_pin_verification_and_lockout(temp_db):
    # Setup initial db with PIN 654321
    conn = get_connection(temp_db, pin="654321")
    conn.close()

    # Successful reconnect
    conn2 = get_connection(temp_db, pin="654321")
    conn2.close()

    # Wrong PIN fails
    with pytest.raises(sqlite3.DatabaseError):
        get_connection(temp_db, pin="000000")

    with pytest.raises(sqlite3.DatabaseError):
        get_connection(temp_db, pin="000000")

    with pytest.raises(sqlite3.DatabaseError):
        get_connection(temp_db, pin="000000")

    # 4th time hits lockout
    with pytest.raises(PermissionError):
        get_connection(temp_db, pin="654321")
