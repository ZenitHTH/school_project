"""
tests/test_adapters.py
Covers: StudentAdminAdapter, LibrarianAdminAdapter, BoothAdapter — all slots,
JSON output, URL normalization, _sanitize_for_qml, error paths.
"""
import json
import sqlite3
import pytest

from data.db import get_connection
from data.migrate import apply_migrations
from apps.student_management_app.adapters.student_admin_adapter import (
    StudentAdminAdapter, _sanitize_for_qml, NUMERIC_KEYS,
)
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from apps.booth_app.adapters.booth_adapter import BoothAdapter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def student_adapter(tmp_path):
    conn = get_connection(str(tmp_path / "student.sqlite"), pin="123456")
    apply_migrations(conn)
    conn.execute(
        "INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, status) "
        "VALUES (1001, '1100100200300', 'นาย', 'สมชาย', 'มั่นคง', 'นายสมชาย มั่นคง', 'active'), "
        "       (1002, NULL, 'เด็กหญิง', 'มาลี', 'ใจดี', 'เด็กหญิงมาลี ใจดี', 'active')"
    )
    conn.commit()
    adapter = StudentAdminAdapter(conn)
    yield adapter, conn
    conn.close()


@pytest.fixture
def librarian_adapter(tmp_path):
    conn = get_connection(str(tmp_path / "library.sqlite"), pin="123456")
    apply_migrations(conn)
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES (2001, 'ผู้ยืม ทดสอบ', 'active')"
    )
    conn.commit()
    adapter = LibrarianAdminAdapter(conn)
    yield adapter, conn
    conn.close()


@pytest.fixture
def booth_adapter(tmp_path):
    conn = get_connection(str(tmp_path / "booth.sqlite"), pin="123456")
    apply_migrations(conn)
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(3001, 'นักเรียน บูธ', 'active'), "
        "(3002, 'นักเรียน จำหน่าย', 'transferred_out')"
    )
    conn.commit()
    adapter = BoothAdapter(conn)
    yield adapter, conn
    conn.close()


# ---------------------------------------------------------------------------
# _sanitize_for_qml
# ---------------------------------------------------------------------------

def test_sanitize_numeric_null_becomes_zero():
    result = _sanitize_for_qml([{"student_id": None, "room": None}])
    assert result[0]["student_id"] == 0
    assert result[0]["room"] == 0


def test_sanitize_text_null_becomes_empty_string():
    result = _sanitize_for_qml([{"full_name": None, "grade_level": None}])
    assert result[0]["full_name"] == ""
    assert result[0]["grade_level"] == ""


def test_sanitize_existing_values_unchanged():
    result = _sanitize_for_qml([{"student_id": 42, "full_name": "ทดสอบ"}])
    assert result[0]["student_id"] == 42
    assert result[0]["full_name"] == "ทดสอบ"


def test_sanitize_nested():
    result = _sanitize_for_qml([{"items": [{"book_id": None}]}])
    assert result[0]["items"][0]["book_id"] == 0


# ---------------------------------------------------------------------------
# StudentAdminAdapter
# ---------------------------------------------------------------------------

def test_search_returns_json_list(student_adapter):
    adapter, _ = student_adapter
    data = json.loads(adapter.searchStudents(""))
    assert isinstance(data, list)
    assert len(data) == 2


def test_search_by_name(student_adapter):
    adapter, _ = student_adapter
    data = json.loads(adapter.searchStudents("สมชาย"))
    assert len(data) == 1
    assert data[0]["student_id"] == 1001


def test_get_student_found(student_adapter):
    adapter, _ = student_adapter
    data = json.loads(adapter.getStudent(1001))
    assert data["full_name"] == "นายสมชาย มั่นคง"
    for v in data.values():
        assert v is not None  # sanitized — no None


def test_get_student_not_found(student_adapter):
    adapter, _ = student_adapter
    data = json.loads(adapter.getStudent(9999))
    assert data == {}


def test_update_status_legal(student_adapter):
    adapter, _ = student_adapter
    res = json.loads(adapter.updateStatus(1001, "on_leave", "ป่วย", "Admin"))
    assert res["ok"] is True


def test_update_status_illegal_transition(student_adapter):
    adapter, _ = student_adapter
    adapter.updateStatus(1001, "transferred_out", "", "Admin")
    res = json.loads(adapter.updateStatus(1001, "on_leave", "", "Admin"))
    assert res["ok"] is False
    assert "Illegal" in res["error"]


def test_update_name_valid(student_adapter):
    adapter, _ = student_adapter
    res = json.loads(adapter.updateName(1001, "นาย", "ชัยชนะ", "มั่นคง", "แก้ไข", "Admin"))
    assert res["ok"] is True
    detail = json.loads(adapter.getStudent(1001))
    assert detail["full_name"] == "นายชัยชนะ มั่นคง"


def test_update_name_empty_first_name_rejected(student_adapter):
    adapter, _ = student_adapter
    res = json.loads(adapter.updateName(1001, "นาย", "", "มั่นคง", "", "Admin"))
    assert res["ok"] is False


def test_change_student_id_valid(student_adapter):
    adapter, _ = student_adapter
    res = json.loads(adapter.changeStudentID(1001, 9001, "แก้ไข", "Admin"))
    assert res["ok"] is True
    assert json.loads(adapter.getStudent(1001)) == {}
    assert json.loads(adapter.getStudent(9001))["full_name"] == "นายสมชาย มั่นคง"


def test_change_student_id_duplicate_rejected(student_adapter):
    adapter, _ = student_adapter
    res = json.loads(adapter.changeStudentID(1001, 1002, "collision", "Admin"))
    assert res["ok"] is False
    assert "already in use" in res["error"]


def test_export_snapshot(student_adapter, tmp_path):
    adapter, _ = student_adapter
    snap = str(tmp_path / "snap.sqlite")
    res = json.loads(adapter.exportSnapshot(snap, "Admin"))
    assert res["ok"] is True
    assert res["data"]["student_count"] == 2


def test_import_xlsx_nonexistent_file(student_adapter, tmp_path):
    adapter, _ = student_adapter
    res = json.loads(adapter.importXlsx(str(tmp_path / "no.xlsx"), False, "Admin"))
    assert res["ok"] is False


def test_import_xlsx_file_url_stripped(student_adapter, tmp_path):
    """file:// prefix stripped, still returns ok=False (file doesn't exist), not a crash."""
    adapter, _ = student_adapter
    url = "file://" + str(tmp_path / "no.xlsx")
    res = json.loads(adapter.importXlsx(url, False, "Admin"))
    assert res["ok"] is False


def test_get_activity_logs_after_action(student_adapter):
    adapter, _ = student_adapter
    adapter.updateStatus(1001, "on_leave", "ทดสอบ", "Admin")
    logs = json.loads(adapter.getActivityLogs())
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert "action" in logs[0]


# ---------------------------------------------------------------------------
# LibrarianAdminAdapter
# ---------------------------------------------------------------------------

def test_librarian_add_and_search_book(librarian_adapter):
    adapter, _ = librarian_adapter
    res = json.loads(adapter.addBook("ฟิสิกส์ ม.ปลาย", "", "ผู้แต่ง", "", "", "", "PHYS-01"))
    assert res["ok"] is True
    books = json.loads(adapter.searchBooks("ฟิสิกส์"))
    assert any(b["book_id"] == res["data"]["book_id"] for b in books)


def test_librarian_checkout_and_return(librarian_adapter):
    adapter, _ = librarian_adapter
    adapter.addBook("คณิตศาสตร์ 101", "", "", "", "", "", "MATH-01")
    co = json.loads(adapter.checkout(2001, "MATH-01"))
    assert co["ok"] is True
    ret = json.loads(adapter.returnBook(co["data"]["loan_id"]))
    assert ret["ok"] is True


def test_librarian_checkout_inactive_student_blocked(librarian_adapter):
    adapter, conn = librarian_adapter
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES (2002, 'จำหน่าย', 'transferred_out')"
    )
    conn.commit()
    adapter.addBook("หนังสือ ทดสอบ", "", "", "", "", "", "BLOCK-01")
    res = json.loads(adapter.checkout(2002, "BLOCK-01"))
    assert res["ok"] is False
    assert "transferred_out" in res["error"]


def test_librarian_get_active_loans(librarian_adapter):
    adapter, _ = librarian_adapter
    adapter.addBook("วิทย์ 2", "", "", "", "", "", "SCI-02")
    adapter.checkout(2001, "SCI-02")
    loans = json.loads(adapter.getActiveLoans())
    assert isinstance(loans, list)
    assert len(loans) >= 1


def test_librarian_preview_sync_missing_file(librarian_adapter, tmp_path):
    adapter, _ = librarian_adapter
    res = json.loads(adapter.previewSync(str(tmp_path / "no_snap.sqlite")))
    assert res["ok"] is False


def test_librarian_apply_sync_url_normalization(librarian_adapter, tmp_path):
    adapter, _ = librarian_adapter
    url = "file://" + str(tmp_path / "no_snap2.sqlite")
    res = json.loads(adapter.applySync(url))
    assert res["ok"] is False  # file not found, not a URL crash


def test_librarian_list_categories(librarian_adapter):
    adapter, _ = librarian_adapter
    adapter.addCategory("นิยาย")
    adapter.addCategory("วิทยาศาสตร์")
    cats = json.loads(adapter.listCategories())
    names = [c["name"] for c in cats]
    assert "นิยาย" in names


def test_librarian_pay_fine(librarian_adapter):
    adapter, conn = librarian_adapter
    from data.repositories import book_repo, loan_repo, fine_repo
    book_id = book_repo.add_book(conn, title="หนังสือค่าปรับ")
    copy_ids = book_repo.add_copies(conn, book_id, barcodes=["FINE-01"])
    loan_id = loan_repo.create_loan(
        conn, copy_id=copy_ids[0], student_id=2001,
        borrowed_at="2026-01-01T00:00:00", due_at="2026-01-15T00:00:00"
    )
    fine_id = fine_repo.create_fine(conn, loan_id=loan_id, amount=25.0, reason="overdue")
    res = json.loads(adapter.payFine(fine_id))
    assert res["ok"] is True
    assert fine_repo.get_unpaid_fines_total(conn, 2001) == 0.0


def test_librarian_get_activity_logs(librarian_adapter):
    adapter, _ = librarian_adapter
    adapter.addBook("กิจกรรม", "", "", "", "", "", "ACT-01")
    logs = json.loads(adapter.getActivityLogs())
    assert isinstance(logs, list)
    assert len(logs) > 0


# ---------------------------------------------------------------------------
# BoothAdapter
# ---------------------------------------------------------------------------

def test_booth_search_students(booth_adapter):
    adapter, _ = booth_adapter
    data = json.loads(adapter.searchStudents("นักเรียน"))
    assert isinstance(data, list)
    assert len(data) >= 1


def test_booth_get_copy_not_found(booth_adapter):
    adapter, _ = booth_adapter
    res = json.loads(adapter.getCopyByBarcode("NOTEXIST"))
    assert res["ok"] is False


def test_booth_checkout_and_return(booth_adapter):
    adapter, conn = booth_adapter
    from data.repositories import book_repo
    book_id = book_repo.add_book(conn, title="หนังสือ บูธ")
    book_repo.add_copies(conn, book_id, barcodes=["BOOTH-01"])
    co = json.loads(adapter.checkout(3001, "BOOTH-01"))
    assert co["ok"] is True
    ret = json.loads(adapter.returnBook(co["data"]["loan_id"]))
    assert ret["ok"] is True


def test_booth_inactive_student_blocked(booth_adapter):
    adapter, conn = booth_adapter
    from data.repositories import book_repo
    book_id = book_repo.add_book(conn, title="บล็อก")
    book_repo.add_copies(conn, book_id, barcodes=["BLK-01"])
    res = json.loads(adapter.checkout(3002, "BLK-01"))
    assert res["ok"] is False
    assert "transferred_out" in res["error"]


def test_booth_get_copy_found(booth_adapter):
    adapter, conn = booth_adapter
    from data.repositories import book_repo
    book_id = book_repo.add_book(conn, title="สแกน")
    book_repo.add_copies(conn, book_id, barcodes=["SCAN-01"])
    res = json.loads(adapter.getCopyByBarcode("SCAN-01"))
    assert res["ok"] is True
    assert res["data"]["barcode"] == "SCAN-01"
