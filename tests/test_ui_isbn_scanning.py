"""
tests/test_ui_isbn_scanning.py
Covers:
  - BarcodeGeneratorView duplicate ISBN warning and copy routing
  - BarcodeGeneratorView auto form clearing and focus retention
  - BarcodeGeneratorView candidate strictness (same title, different ISBN)
  - BarcodeGeneratorView duplicate warning preservation against auto-fetch
  - BookActionDialogs duplicate warning, auto-fetch guard, and error display
"""
import os
import sys
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from data.db import get_connection
from data.migrate import apply_migrations
from data.repositories import book_repo
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    return app


@pytest.fixture
def lib_ui(qapp, tmp_path):
    conn = get_connection(str(tmp_path / "ui_library.sqlite"), pin="123456")
    apply_migrations(conn)
    b_id = book_repo.add_book(conn, title="ฟิสิกส์พื้นฐาน", author="ดร.สมชาย", isbn="978-616-01-0001-1")
    book_repo.add_copies(conn, b_id, barcodes=["PHYS-01", "PHYS-02"])
    adapter = LibrarianAdminAdapter(conn)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("librarianAdmin", adapter)
    engine.addImportPath(os.path.abspath("apps"))
    engine.load("apps/librarian_management_app/qml/Main.qml")
    window = engine.rootObjects()[0]

    yield {"app": qapp, "engine": engine, "window": window, "adapter": adapter, "conn": conn}
    conn.close()


def find_child(root, name):
    return root.findChild(object, name)


def process_events(app):
    for _ in range(5):
        app.processEvents()


# ---------------------------------------------------------------------------
# 1. Barcode Generator View Tests
# ---------------------------------------------------------------------------

def test_ui_barcode_generator_duplicate_detected_and_form_cleared(lib_ui):
    window = lib_ui["window"]
    find_child(window, "navBtnGenerator").clicked.emit()
    process_events(lib_ui["app"])

    find_child(window, "genBookIsbn").setProperty("text", "978-616-01-0001-1")
    process_events(lib_ui["app"])

    status = find_child(window, "genStatusMessage").property("text")
    assert "⚠️ พบหนังสือเดิมในระบบ" in status and "ฟิสิกส์พื้นฐาน" in status

    find_child(window, "genCopyCountInput").setProperty("text", "2")
    find_child(window, "btnExecuteGenerate").clicked.emit()
    process_events(lib_ui["app"])

    assert find_child(window, "genBookTitle").property("text") == ""
    assert find_child(window, "genBookIsbn").property("text") == ""
    assert find_child(window, "genBookAuthor").property("text") == ""
    assert find_child(window, "genCopyCountInput").property("text") == "1"
    assert "✓ เพิ่มเล่มหนังสือเดิม 'ฟิสิกส์พื้นฐาน' สำเร็จ" in find_child(window, "genStatusMessage").property("text")


def test_ui_barcode_generator_new_book_clears_form(lib_ui):
    window = lib_ui["window"]
    find_child(window, "navBtnGenerator").clicked.emit()
    process_events(lib_ui["app"])

    find_child(window, "genBookTitle").setProperty("text", "ชีววิทยา ม.ปลาย")
    find_child(window, "genBookAuthor").setProperty("text", "อ.วิทย์")
    find_child(window, "genBookIsbn").setProperty("text", "978-616-02-0002-2")
    find_child(window, "genCopyCountInput").setProperty("text", "2")
    find_child(window, "btnExecuteGenerate").clicked.emit()
    process_events(lib_ui["app"])

    assert find_child(window, "genBookTitle").property("text") == ""
    assert find_child(window, "genBookIsbn").property("text") == ""
    assert find_child(window, "genBookAuthor").property("text") == ""
    assert find_child(window, "genCopyCountInput").property("text") == "1"
    assert "✓ บันทึกหนังสือ 'ชีววิทยา ม.ปลาย'" in find_child(window, "genStatusMessage").property("text")


def test_ui_barcode_generator_duplicate_preserves_warning_over_autofill(lib_ui):
    window = lib_ui["window"]
    find_child(window, "navBtnGenerator").clicked.emit()
    process_events(lib_ui["app"])

    isbn_input = find_child(window, "genBookIsbn")
    isbn_input.setProperty("text", "9786160100011")
    isbn_input.accepted.emit()
    process_events(lib_ui["app"])

    # Warning must NOT be overwritten by auto-fetch
    status = find_child(window, "genStatusMessage").property("text")
    assert "⚠️ พบหนังสือเดิมในระบบ" in status
    assert "กำลังค้นหา..." not in status
    assert "✓ ดึงข้อมูลสำเร็จ" not in status


def test_ui_barcode_generator_different_isbn_same_title_not_hijacked(lib_ui):
    window = lib_ui["window"]
    find_child(window, "navBtnGenerator").clicked.emit()
    process_events(lib_ui["app"])

    # Enter book with SAME title ("ฟิสิกส์พื้นฐาน") but DIFFERENT ISBN
    find_child(window, "genBookTitle").setProperty("text", "ฟิสิกส์พื้นฐาน")
    find_child(window, "genBookIsbn").setProperty("text", "978-616-99-8877-6")
    find_child(window, "genCopyCountInput").setProperty("text", "1")
    find_child(window, "btnExecuteGenerate").clicked.emit()
    process_events(lib_ui["app"])

    # Must be added as a NEW book, NOT hijacked as copies of the existing one
    status = find_child(window, "genStatusMessage").property("text")
    assert "✓ บันทึกหนังสือ 'ฟิสิกส์พื้นฐาน' และสร้างบาร์โค้ดสำเร็จ" in status


# ---------------------------------------------------------------------------
# 2. Book Action Dialogs Tests
# ---------------------------------------------------------------------------

def test_ui_dialog_duplicate_warning_and_reset(lib_ui):
    window = lib_ui["window"]
    assert find_child(window, "addBookDialog") is not None
    isbn_input = find_child(window, "newBookIsbn")
    status_text = find_child(window, "addBookStatusText")

    isbn_input.setProperty("text", "978-616-01-0001-1")
    process_events(lib_ui["app"])
    assert "⚠️ หนังสือนี้มีอยู่ในระบบแล้ว" in status_text.property("text")

    isbn_input.setProperty("text", "")
    process_events(lib_ui["app"])
    assert status_text.property("text") == ""


def test_ui_dialog_duplicate_preserves_warning_over_autofill(lib_ui):
    window = lib_ui["window"]
    isbn_input = find_child(window, "newBookIsbn")
    status_text = find_child(window, "addBookStatusText")

    isbn_input.setProperty("text", "978-616-01-0001-1")
    isbn_input.accepted.emit()
    process_events(lib_ui["app"])

    assert "⚠️ หนังสือนี้มีอยู่ในระบบแล้ว" in status_text.property("text")
    assert "✓ ดึงข้อมูลสำเร็จ" not in status_text.property("text")


def test_ui_dialog_add_book_error_surfaced(lib_ui):
    window = lib_ui["window"]
    dialog = find_child(window, "addBookDialog")
    status_text = find_child(window, "addBookStatusText")

    # Trying to add duplicate ISBN via dialog
    find_child(window, "newBookTitle").setProperty("text", "ฟิสิกส์ซ้ำ")
    find_child(window, "newBookIsbn").setProperty("text", "978-616-01-0001-1")
    dialog.accept()
    process_events(lib_ui["app"])

    # Error must be surfaced in dialog status text
    assert "✗" in status_text.property("text")
    assert "Active book with this ISBN already exists" in status_text.property("text")
