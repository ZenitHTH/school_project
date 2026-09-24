import sqlite3
import pytest
from core.library.services.catalog_service import CatalogService
from core.library.services.fine_service import FineService
from core.library.services.loan_service import LoanService
from core.library.services.reservation_service import ReservationService
from core.student.services.enrollment_service import EnrollmentService
from core.student.services.student_service import StudentService
from data.migrate import apply_migrations
from data.repositories import book_repo, fine_repo, loan_repo, reservation_repo, student_repo


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    apply_migrations(c)
    # Seed sample student
    c.execute(
        "INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, gender, status) "
        "VALUES (1001, '1234567890123', 'นาย', 'กิตติ', 'มีสุข', 'นายกิตติ มีสุข', 'M', 'active')"
    )
    c.commit()
    return c


# ---------------------------------------------------------------------------
# StudentService & Student Repo Tests
# ---------------------------------------------------------------------------

def test_student_service_get_and_status(conn):
    svc = StudentService(conn)
    res = svc.get(1001)
    assert res.ok
    assert res.data["student_id"] == 1001
    assert svc.get_status(1001) == "active"

    # Non-existent student
    res_not_found = svc.get(9999)
    assert not res_not_found.ok
    assert svc.get_status(9999) is None


def test_student_service_status_state_machine(conn):
    svc = StudentService(conn)
    # active -> on_leave (allowed)
    r1 = svc.update_status(1001, "on_leave", reason="Medical")
    assert r1.ok
    assert svc.get_status(1001) == "on_leave"

    # on_leave -> on_leave (same status rejected)
    r_same = svc.update_status(1001, "on_leave")
    assert not r_same.ok

    # on_leave -> active (allowed)
    r2 = svc.update_status(1001, "active", reason="Returned")
    assert r2.ok

    # active -> transferred_out (allowed)
    r3 = svc.update_status(1001, "transferred_out", reason="Moved school")
    assert r3.ok

    # transferred_out -> active (allowed per confirmed design doc)
    r4 = svc.update_status(1001, "active", reason="Re-enrolled")
    assert r4.ok


def test_student_service_id_and_name_edits(conn):
    svc = StudentService(conn)
    # Update name
    r_name = svc.update_name(1001, "นาย", "กิตติพงษ์", "มีสุขยิ่ง")
    assert r_name.ok
    s = svc.get(1001).data
    assert s["first_name"] == "กิตติพงษ์"
    assert s["full_name"] == "นายกิตติพงษ์ มีสุขยิ่ง"

    # Empty names rejected
    assert not svc.update_name(1001, "นาย", "", "สุข").ok
    assert not svc.update_name(1001, "นาย", "กิตติ", "").ok

    # Change ID
    r_id = svc.change_student_id(1001, 1002, reason="Typo in ID")
    assert r_id.ok
    assert svc.get(1001).data is None or not svc.get(1001).ok
    assert svc.get(1002).ok

    # Same ID or duplicate rejected
    assert not svc.change_student_id(1002, 1002).ok

    # History audit check
    hist = svc.get_history(1002)
    assert hist.ok
    assert "name_changes" in hist.data
    assert len(hist.data["name_changes"]) >= 1


# ---------------------------------------------------------------------------
# EnrollmentService & Repo Tests
# ---------------------------------------------------------------------------

def test_enrollment_service_operations(conn):
    svc = EnrollmentService(conn)
    # Enroll next period
    r_enr = svc.enroll_next_period(
        student_id=1001,
        academic_year=2567,
        semester=1,
        grade_level="ม.1",
        room=2,
        track="วิทย์-คณิต",
        seq_no=1,
    )
    assert r_enr.ok
    enr_id = r_enr.data["enrollment_id"]

    # Current enrollment
    curr = svc.current_enrollment(1001)
    assert curr.ok
    assert curr.data["room"] == 2

    # Change classroom
    r_change = svc.change_classroom(1001, new_room=3, reason="Rebalanced")
    assert r_change.ok
    assert svc.current_enrollment(1001).data["room"] == 3

    # Same room rejected
    assert not svc.change_classroom(1001, new_room=3).ok

    # Class roster
    r_roster = svc.get_class_roster(2567, 1, "ม.1", 3)
    assert r_roster.ok
    assert len(r_roster.data) == 1
    assert r_roster.data[0]["student_id"] == 1001

    # Class statistics
    r_stats = svc.get_class_statistics()
    assert r_stats.ok
    assert len(r_stats.data) >= 1

    # Re-enrolling same student in same period fails
    r_dup = svc.enroll_next_period(1001, 2567, 1, "ม.1", 3)
    assert not r_dup.ok


# ---------------------------------------------------------------------------
# CatalogService & Book Repo Tests
# ---------------------------------------------------------------------------

def test_catalog_service_operations(conn):
    svc = CatalogService(conn)
    # Add category
    r_cat = svc.add_category("วรรณกรรม")
    assert r_cat.ok
    cat_id = r_cat.data["category_id"]

    # List categories
    r_cats = svc.list_categories()
    assert r_cats.ok
    assert any(c["name"] == "วรรณกรรม" for c in r_cats.data)

    # Add book with copies
    r_book = svc.add_book(
        title="สี่แผ่นดิน",
        isbn="9786161800000",
        author="ม.ร.ว.คึกฤทธิ์ ปราโมช",
        category_id=cat_id,
        barcodes=["B001", "B002"],
    )
    assert r_book.ok
    book_id = r_book.data["book_id"]
    assert len(r_book.data["copy_ids"]) == 2

    # Get book and copies
    b_res = svc.get_book(book_id)
    assert b_res.ok
    assert b_res.data["title"] == "สี่แผ่นดิน"
    assert len(b_res.data["copies"]) == 2

    # Get copy by barcode
    c_res = svc.get_copy_by_barcode("B001")
    assert c_res.ok
    copy_id = c_res.data["copy_id"]

    # Mark copy damaged
    m_res = svc.mark_copy(copy_id, status="damaged", reason="Water damage")
    assert m_res.ok

    # Update book
    u_res = svc.update_book(book_id, title="สี่แผ่นดิน ฉบับสมบูรณ์")
    assert u_res.ok
    assert svc.get_book(book_id).data["title"] == "สี่แผ่นดิน ฉบับสมบูรณ์"

    # Search books
    r_search = svc.search("แผ่นดิน")
    assert r_search.ok
    assert len(r_search.data) == 1

    # Retire book
    ret_res = svc.retire_book(book_id)
    assert ret_res.ok


# ---------------------------------------------------------------------------
# LoanService, ReservationService, and FineService Tests
# ---------------------------------------------------------------------------

def test_reservation_and_fine_services(conn):
    cat_svc = CatalogService(conn)
    r_book = cat_svc.add_book(title="คู่มือคณิตศาสตร์", barcodes=["MATH01"])
    book_id = r_book.data["book_id"]

    res_svc = ReservationService(conn)
    # Reserving when copy is available fails
    r_res_fail = res_svc.reserve(student_id=1001, book_id=book_id)
    assert not r_res_fail.ok

    # Checkout copy MATH01
    loan_svc = LoanService(conn)
    r_loan = loan_svc.checkout(student_id=1001, barcode="MATH01")
    assert r_loan.ok
    loan_id = r_loan.data["loan_id"]

    # Active loans
    active = loan_svc.get_active_loans()
    assert active.ok
    assert len(active.data) >= 1

    # Overdue loans
    overdue = loan_svc.get_overdue_loans()
    assert overdue.ok

    # Renew loan
    r_renew = loan_svc.renew(loan_id)
    assert r_renew.ok

    # Now reserving succeeds since all copies are on loan
    # Seed 2nd student to reserve
    conn.execute("INSERT INTO students (student_id, full_name, status) VALUES (1002, 'สมหญิง', 'active')")
    r_res = res_svc.reserve(student_id=1002, book_id=book_id)
    assert r_res.ok
    reservation_id = r_res.data["reservation_id"]
    assert res_svc.has_waiting(book_id)

    # Cancel reservation
    r_cancel = res_svc.cancel(reservation_id)
    assert r_cancel.ok

    # Return book
    r_ret = loan_svc.return_book(loan_id)
    assert r_ret.ok

    # History checks
    s_hist = loan_svc.get_student_history(1001)
    assert s_hist.ok
    assert len(s_hist.data) >= 1

    c_hist = loan_svc.get_copy_history(r_loan.data["copy_id"])
    assert c_hist.ok
    assert len(c_hist.data) >= 1

    # Fine service: assess overdue and payment
    fine_svc = FineService(conn)
    r_fine = fine_svc.assess_overdue(loan_id, days_overdue=3)
    assert r_fine.ok
    fine_id = r_fine.data["fine_id"]
    assert fine_svc.get_unpaid_total(1001) > 0

    # List fines
    f_list = fine_svc.list_fines(paid=False)
    assert f_list.ok
    assert len(f_list.data) >= 1

    # Pay fine
    r_pay = fine_svc.record_payment(fine_id)
    assert r_pay.ok
    assert fine_svc.get_unpaid_total(1001) == 0

    # Assess lost book fee
    r_lost = fine_svc.assess_lost_book(loan_id)
    assert r_lost.ok
