import datetime
import pytest
from data.db import get_connection
from data.migrate import apply_migrations
from core.library.policy import LibraryPolicy
from core.library.services.catalog_service import CatalogService
from core.library.services.fine_service import FineService
from core.library.services.loan_service import LoanService
from core.library.services.reservation_service import ReservationService
from core.student.services.student_service import StudentService


@pytest.fixture
def library_env(tmp_path):
    db_file = str(tmp_path / "test_library.sqlite")
    conn = get_connection(db_file, pin="333444")
    apply_migrations(conn)

    policy = LibraryPolicy(
        loan_duration_days=14,
        max_active_loans=3,
        unpaid_fines_threshold=50.0,
        overdue_fine_per_day=5.0,
    )

    catalog_svc = CatalogService(conn)
    student_svc = StudentService(conn)
    fine_svc = FineService(conn, policy)
    res_svc = ReservationService(conn)
    loan_svc = LoanService(conn, policy, fine_svc, res_svc, student_svc)

    yield {
        "conn": conn,
        "policy": policy,
        "catalog": catalog_svc,
        "student": student_svc,
        "fine": fine_svc,
        "res": res_svc,
        "loan": loan_svc,
    }
    conn.close()


def test_loan_checkout_validations(library_env):
    conn = library_env["conn"]
    loan_svc = library_env["loan"]
    cat_svc = library_env["catalog"]
    student_svc = library_env["student"]

    # Setup students
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(10, 'นักเรียน ปกติ', 'active'), "
        "(20, 'นักเรียน ลาออก', 'transferred_out')"
    )
    conn.commit()

    # Add book with 1 copy
    res_b = cat_svc.add_book(title="คณิตศาสตร์ ม.1", barcodes=["MATH-01"])
    assert res_b.ok is True
    book_id = res_b.data["book_id"]

    # 1. Block inactive student
    res_inactive = loan_svc.checkout(student_id=20, book_id=book_id)
    assert res_inactive.ok is False
    assert "transferred_out" in res_inactive.error

    # 2. Successful checkout for active student
    res_ok = loan_svc.checkout(student_id=10, barcode="MATH-01")
    assert res_ok.ok is True
    loan_id = res_ok.data["loan_id"]

    # 3. Block checkout when copy is unavailable
    res_no_copy = loan_svc.checkout(student_id=10, barcode="MATH-01")
    assert res_no_copy.ok is False
    assert "not available" in res_no_copy.error


def test_max_loans_limit(library_env):
    loan_svc = library_env["loan"]
    cat_svc = library_env["catalog"]
    conn = library_env["conn"]

    conn.execute("INSERT INTO students (student_id, full_name, status) VALUES (30, 'นักเรียน ชอบอ่าน', 'active')")
    conn.commit()

    # Create 4 books
    cat_svc.add_book(title="Book 1", barcodes=["B-01"])
    cat_svc.add_book(title="Book 2", barcodes=["B-02"])
    cat_svc.add_book(title="Book 3", barcodes=["B-03"])
    cat_svc.add_book(title="Book 4", barcodes=["B-04"])

    # 3 checkouts succeed (max is 3)
    assert loan_svc.checkout(student_id=30, barcode="B-01").ok is True
    assert loan_svc.checkout(student_id=30, barcode="B-02").ok is True
    assert loan_svc.checkout(student_id=30, barcode="B-03").ok is True

    # 4th checkout blocked
    res_4 = loan_svc.checkout(student_id=30, barcode="B-04")
    assert res_4.ok is False
    assert "limit reached" in res_4.error


def test_overdue_fines_and_reservation_promotion(library_env):
    loan_svc = library_env["loan"]
    cat_svc = library_env["catalog"]
    res_svc = library_env["res"]
    fine_svc = library_env["fine"]
    conn = library_env["conn"]

    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(40, 'ผู้ยืม คนที่ 1', 'active'), "
        "(41, 'ผู้จอง คนที่ 2', 'active')"
    )
    conn.commit()

    cat_svc.add_book(title="วิทยาศาสตร์ทั่วไป", barcodes=["SCI-X"])

    # Student 40 checks out
    res_co = loan_svc.checkout(student_id=40, barcode="SCI-X")
    assert res_co.ok is True
    loan_id = res_co.data["loan_id"]

    # Student 41 reserves (since copy is out)
    book_id = cat_svc.get_copy_by_barcode("SCI-X").data["book_id"]
    res_res = res_svc.reserve(student_id=41, book_id=book_id)
    assert res_res.ok is True

    # Renewal should be blocked because student 41 has waiting reservation
    res_renew = loan_svc.renew(loan_id)
    assert res_renew.ok is False
    assert "another student has an active reservation" in res_renew.error

    # Return book 5 days late
    borrow_dt = datetime.datetime.now(datetime.timezone.utc)
    return_late_dt = (borrow_dt + datetime.timedelta(days=19)).isoformat()  # 14 days normal + 5 late
    res_ret = loan_svc.return_book(loan_id, returned_at=return_late_dt)
    assert res_ret.ok is True
    assert res_ret.data["reservation_promoted"] is True
    assert res_ret.data["fine"] is not None
    assert res_ret.data["fine"]["amount"] == 25.0  # 5 days * 5 THB

    # Check student 41's reservation is now 'ready'
    reservations = res_svc.list_reservations(status="ready").data
    assert len(reservations) == 1
    assert reservations[0]["student_id"] == 41
