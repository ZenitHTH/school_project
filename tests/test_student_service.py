import pytest
from data.db import get_connection
from data.migrate import apply_migrations
from core.student.services.student_service import StudentService
from core.student.services.enrollment_service import EnrollmentService


@pytest.fixture
def service_conn(tmp_path):
    db_file = str(tmp_path / "test_services.sqlite")
    conn = get_connection(db_file, pin="111222")
    apply_migrations(conn)
    yield conn
    conn.close()


def test_student_service_status_rules(service_conn):
    s_svc = StudentService(service_conn)

    # Insert test student
    service_conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES (101, 'สมเกียรติ มั่นคง', 'active')"
    )
    service_conn.commit()

    # 1. Legal transition: active -> on_leave
    res = s_svc.update_status(101, "on_leave", reason="Sick leave")
    assert res.ok is True
    assert s_svc.get_status(101) == "on_leave"

    # 2. Illegal transition: on_leave -> on_leave (same)
    res2 = s_svc.update_status(101, "on_leave")
    assert res2.ok is False
    assert "already in 'on_leave'" in res2.error

    # 3. Legal transition: on_leave -> transferred_out
    res3 = s_svc.update_status(101, "transferred_out", reason="Moved to Chiang Mai")
    assert res3.ok is True
    assert s_svc.get_status(101) == "transferred_out"

    # 4. Illegal transition: transferred_out -> on_leave
    res4 = s_svc.update_status(101, "on_leave")
    assert res4.ok is False
    assert "Illegal status transition" in res4.error

    # 5. Legal transition: transferred_out -> active (rare return)
    res5 = s_svc.update_status(101, "active", reason="Returned to school")
    assert res5.ok is True
    assert s_svc.get_status(101) == "active"


def test_student_id_and_name_edits(service_conn):
    s_svc = StudentService(service_conn)
    service_conn.execute(
        "INSERT INTO students (student_id, prefix, first_name, last_name, full_name, status) "
        "VALUES (201, 'เด็กชาย', 'ชาตรี', 'มีชัย', 'เด็กชายชาตรี มีชัย', 'active'), "
        "       (202, 'เด็กหญิง', 'มาลี', 'มีชัย', 'เด็กหญิงมาลี มีชัย', 'active')"
    )
    service_conn.commit()

    # Reject duplicate new_id
    res_dup = s_svc.change_student_id(old_id=201, new_id=202, reason="Collision test")
    assert res_dup.ok is False
    assert "already in use" in res_dup.error

    # Accept valid new_id
    res_ok = s_svc.change_student_id(old_id=201, new_id=299, reason="Correcting registration number")
    assert res_ok.ok is True
    assert s_svc.get(201).ok is False
    assert s_svc.get(299).ok is True

    # Name update validation
    res_empty = s_svc.update_name(299, prefix="นาย", first_name="", last_name="มีชัย")
    assert res_empty.ok is False

    res_name = s_svc.update_name(299, prefix="นาย", first_name="ชาญชัย", last_name="มีชัย")
    assert res_name.ok is True
    st = s_svc.get(299).data
    assert st["full_name"] == "นายชาญชัย มีชัย"


def test_enrollment_service_bulk_promote(service_conn):
    s_svc = StudentService(service_conn)
    e_svc = EnrollmentService(service_conn)

    # Setup class of ม.1 and ม.6 students
    service_conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(301, 'นักเรียน ม1', 'active'), "
        "(302, 'นักเรียน ม6', 'active')"
    )
    service_conn.commit()

    e_svc.enroll_next_period(301, 2567, 1, "ม.1", 1)
    e_svc.enroll_next_period(302, 2567, 1, "ม.6", 1)

    # Change classroom validation
    res_same = e_svc.change_classroom(301, 1)
    assert res_same.ok is False
    assert "already in room 1" in res_same.error

    res_move = e_svc.change_classroom(301, 3, reason="Transfer room")
    assert res_move.ok is True

    # Bulk promote to 2567/2 or 2568/1
    res_promote = e_svc.promote_students(
        source_year=2567, source_semester=1, target_year=2568, target_semester=1
    )
    assert res_promote.ok is True
    data = res_promote.data
    assert data["promoted_count"] == 1  # 301 promoted to ม.2
    assert data["graduated_count"] == 1  # 302 graduated

    enr_301 = e_svc.current_enrollment(301).data
    assert enr_301["grade_level"] == "ม.2"
    assert enr_301["academic_year"] == 2568
