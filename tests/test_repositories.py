import os
import sqlite3
import pytest
from data.db import get_connection
from data.migrate import apply_migrations
from data.repositories import (
    student_repo,
    enrollment_repo,
    book_repo,
    loan_repo,
    reservation_repo,
    fine_repo,
    log_repo,
)
from core.importers.xlsx_validator import validate_sqlite_file, check_live_data_exists


@pytest.fixture
def repo_db(tmp_path):
    db_file = str(tmp_path / "test_repo.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)
    yield conn
    conn.close()


def test_student_and_enrollment_repositories(repo_db):
    # Insert students
    repo_db.execute(
        "INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, gender, status) "
        "VALUES (2001, '1100112233445', 'นาย', 'อนันต์', 'สุขใจ', 'นายอนันต์ สุขใจ', 'M', 'active')"
    )
    repo_db.commit()

    # Search
    results = student_repo.search_students(repo_db, "อนันต์")
    assert len(results) == 1
    assert results[0]["student_id"] == 2001

    # Enroll
    enr_id = enrollment_repo.enroll_next_period(
        repo_db, student_id=2001, academic_year=2567, semester=1, grade_level="ม.1", room=2
    )
    assert enr_id > 0

    cur_enr = enrollment_repo.get_current_enrollment(repo_db, 2001)
    assert cur_enr["room"] == 2

    # Change classroom mid-year
    enrollment_repo.change_classroom(repo_db, student_id=2001, new_room=4, reason="Rebalance")
    cur_enr2 = enrollment_repo.get_current_enrollment(repo_db, 2001)
    assert cur_enr2["room"] == 4

    # Status transition active -> on_leave
    student_repo.update_status(repo_db, student_id=2001, new_status="on_leave", reason="Family travel")
    s = student_repo.get_student(repo_db, 2001)
    assert s["status"] == "on_leave"

    # Status transition on_leave -> active
    student_repo.update_status(repo_db, student_id=2001, new_status="active", reason="Returned")
    s = student_repo.get_student(repo_db, 2001)
    assert s["status"] == "active"

    # Name update
    student_repo.update_name(repo_db, student_id=2001, prefix="นาย", first_name="อนันตชัย", last_name="สุขใจ", reason="Legal correction")
    s = student_repo.get_student(repo_db, 2001)
    assert s["full_name"] == "นายอนันตชัย สุขใจ"

    # Change student ID with cascade
    student_repo.change_student_id(repo_db, old_id=2001, new_id=3001, reason="Typo correction")
    s_new = student_repo.get_student(repo_db, 3001)
    assert s_new is not None
    s_old = student_repo.get_student(repo_db, 2001)
    assert s_old is None

    enr_cascaded = enrollment_repo.get_current_enrollment(repo_db, 3001)
    assert enr_cascaded["student_id"] == 3001

    # History
    history = student_repo.get_student_history(repo_db, 3001)
    assert len(history["room_changes"]) == 1
    assert len(history["leave_of_absence"]) == 1
    assert len(history["name_changes"]) == 1
    assert len(history["id_changes"]) == 1


def test_library_domain_repositories(repo_db):
    # Setup student
    repo_db.execute(
        "INSERT INTO students (student_id, full_name, gender, status) VALUES (5001, 'กมล ชัยชนะ', 'M', 'active')"
    )
    repo_db.commit()

    # Category and book
    cat_id = book_repo.add_category(repo_db, "วิทยาศาสตร์")
    book_id = book_repo.add_book(
        repo_db,
        title="ฟิสิกส์ ม.ปลาย เล่ม 1",
        isbn="9780123456789",
        author="ศ.ดร. สมปอง",
        category_id=cat_id,
    )
    assert book_id > 0

    # Add copies
    copy_ids = book_repo.add_copies(repo_db, book_id=book_id, barcodes=["SCI-001", "SCI-002"])
    assert len(copy_ids) == 2

    book_info = book_repo.get_book(repo_db, book_id)
    assert book_info["total_copies"] == 2

    # Check available copy
    avail = book_repo.get_available_copy(repo_db, book_id)
    assert avail["barcode"] == "SCI-001"

    # Create loan
    loan_id = loan_repo.create_loan(
        repo_db,
        copy_id=avail["copy_id"],
        student_id=5001,
        borrowed_at="2026-09-01T10:00:00",
        due_at="2026-09-15T10:00:00",
    )
    assert loan_id > 0
    assert loan_repo.get_active_loans_count(repo_db, 5001) == 1

    # Second copy mark damaged
    c2 = book_repo.get_copy_by_barcode(repo_db, "SCI-002")
    book_repo.mark_copy(repo_db, copy_id=c2["copy_id"], new_status="damaged", reason="Cover torn")

    # Reservation for third student
    repo_db.execute(
        "INSERT INTO students (student_id, full_name, gender, status) VALUES (5002, 'สมหญิง จริงใจ', 'F', 'active')"
    )
    repo_db.commit()

    res_id = reservation_repo.create_reservation(
        repo_db, book_id=book_id, student_id=5002, reserved_at="2026-09-02T11:00:00"
    )
    assert res_id > 0
    assert reservation_repo.has_waiting_reservation(repo_db, book_id) is True

    # Return loan
    loan_repo.return_loan(repo_db, loan_id=loan_id, returned_at="2026-09-16T10:00:00")
    assert loan_repo.get_active_loans_count(repo_db, 5001) == 0

    # Assess fine for 1 day overdue
    fine_id = fine_repo.create_fine(repo_db, loan_id=loan_id, amount=10.0, reason="overdue")
    assert fine_repo.get_unpaid_fines_total(repo_db, 5001) == 10.0

    fine_repo.record_payment(repo_db, fine_id=fine_id, paid_at="2026-09-16T12:00:00")
    assert fine_repo.get_unpaid_fines_total(repo_db, 5001) == 0.0

    # Promote reservation
    promoted = reservation_repo.promote_next_reservation(repo_db, book_id=book_id)
    assert promoted == res_id

    # Activity log inspection
    logs = log_repo.get_activity_logs(repo_db, limit=20)
    assert len(logs) > 5


def test_validator_and_live_data_check(repo_db):
    res_val = validate_sqlite_file("", conn=repo_db)
    assert res_val.ok is True

    has_live_initial, _ = check_live_data_exists(repo_db)
    assert has_live_initial is False

    from core.shared.log_service import record_activity
    record_activity(repo_db, action="test", entity_type="test", entity_id=1)
    repo_db.commit()

    has_live, reason = check_live_data_exists(repo_db)
    assert has_live is True
    assert "activity_log" in reason
