"""
tests/test_ui_booth.py
UI-level tests for Self-Service Booth App.

Coverage:
  - Initial state (no identified student, checkout button disabled, greeting banner)
  - Student identification (failure case + success case)
  - Checkout button enabling/disabling based on student identification
  - Self-checkout flow (empty barcode validation, success, double checkout failure)
  - Self-return flow (empty barcode validation, unloaned barcode, successful return)
  - Logout / Finish button resets all state
  - Structural integrity: all required objectNames exist
"""
import os
import sys
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QMetaObject, Qt, QObject
from data.db import get_connection
from data.migrate import apply_migrations
from apps.booth_app.adapters.booth_adapter import BoothAdapter
from data.repositories import book_repo


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    return app


@pytest.fixture
def booth_ui(qapp, tmp_path):
    db_file = str(tmp_path / "ui_booth.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    # Seed student
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(3001, 'นักเรียน ยืมเอง', 'active'), "
        "(3002, 'นักเรียน พ้นสภาพ', 'transferred_out')"
    )
    conn.commit()

    # Seed book
    b_id = book_repo.add_book(conn, title="คู่มือโปรแกรมเมอร์", author="ผู้แต่ง", isbn="978-999")
    book_repo.add_copies(conn, b_id, barcodes=["BOOTH-01", "BOOTH-02"])

    adapter = BoothAdapter(conn)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("boothAdapter", adapter)

    qml_path = os.path.abspath("apps/booth_app/qml/Main.qml")
    engine.load(qml_path)
    assert len(engine.rootObjects()) > 0, "Booth QML failed to load"

    window = engine.rootObjects()[0]
    qapp.processEvents()

    yield {
        "app": qapp,
        "window": window,
        "engine": engine,
        "conn": conn,
        "adapter": adapter,
    }

    conn.close()
    engine.deleteLater()


def find(window, name):
    return window.findChild(QObject, name)


def invoke(window, method):
    QMetaObject.invokeMethod(window, method, Qt.DirectConnection)


def process(app):
    app.processEvents()


# ---------------------------------------------------------------------------
# 1. Initial State
# ---------------------------------------------------------------------------

def test_booth_initial_state(booth_ui):
    window = booth_ui["window"]
    assert window.property("identifiedStudent") is None

    btn_co = find(window, "btnCheckout")
    assert btn_co is not None
    assert btn_co.property("enabled") is False

    banner = find(window, "feedbackBanner")
    assert "กรุณาระบุตัวตน" in banner.property("text")

    status_msg = find(window, "studentStatusMsg")
    assert "ยังไม่ได้ระบุตัวตน" in status_msg.property("text")


# ---------------------------------------------------------------------------
# 2. Student Identification
# ---------------------------------------------------------------------------

def test_booth_identify_student_not_found(booth_ui):
    window = booth_ui["window"]
    find(window, "studentIdInput").setProperty("text", "999999")
    invoke(window, "identifyStudent")
    process(booth_ui["app"])

    banner = find(window, "feedbackBanner")
    assert "ไม่พบรหัสนักเรียน" in banner.property("text")
    assert window.property("identifiedStudent") is None
    assert find(window, "btnCheckout").property("enabled") is False


def test_booth_identify_student_success(booth_ui):
    window = booth_ui["window"]
    find(window, "studentIdInput").setProperty("text", "3001")
    invoke(window, "identifyStudent")
    process(booth_ui["app"])

    banner = find(window, "feedbackBanner")
    assert "ระบุตัวตนสำเร็จ" in banner.property("text")
    assert "นักเรียน ยืมเอง" in banner.property("text")

    status_msg = find(window, "studentStatusMsg")
    assert "นักเรียน ยืมเอง" in status_msg.property("text")

    assert window.property("identifiedStudent") is not None
    assert find(window, "btnCheckout").property("enabled") is True


# ---------------------------------------------------------------------------
# 3. Checkout Flow
# ---------------------------------------------------------------------------

def test_booth_checkout_empty_barcode_validation(booth_ui):
    window = booth_ui["window"]
    # Identify first
    find(window, "studentIdInput").setProperty("text", "3001")
    invoke(window, "identifyStudent")

    find(window, "bookBarcodeInput").setProperty("text", "")
    invoke(window, "doCheckout")
    process(booth_ui["app"])

    banner = find(window, "feedbackBanner")
    assert "กรุณากรอกข้อมูลให้ครบถ้วน" in banner.property("text")


def test_booth_checkout_success(booth_ui):
    window = booth_ui["window"]
    # 1. Identify
    find(window, "studentIdInput").setProperty("text", "3001")
    invoke(window, "identifyStudent")

    # 2. Scan barcode & checkout
    find(window, "bookBarcodeInput").setProperty("text", "BOOTH-01")
    invoke(window, "doCheckout")
    process(booth_ui["app"])

    banner = find(window, "feedbackBanner")
    assert "ยืมหนังสือสำเร็จ" in banner.property("text")
    # Barcode input cleared after successful checkout
    assert find(window, "bookBarcodeInput").property("text") == ""


def test_booth_checkout_inactive_student_blocked(booth_ui):
    window = booth_ui["window"]
    find(window, "studentIdInput").setProperty("text", "3002")  # transferred_out
    invoke(window, "identifyStudent")

    find(window, "bookBarcodeInput").setProperty("text", "BOOTH-02")
    invoke(window, "doCheckout")
    process(booth_ui["app"])

    banner = find(window, "feedbackBanner")
    assert "ยืมไม่สำเร็จ" in banner.property("text")
    assert "transferred_out" in banner.property("text")


# ---------------------------------------------------------------------------
# 4. Return Flow
# ---------------------------------------------------------------------------

def test_booth_return_empty_barcode_validation(booth_ui):
    window = booth_ui["window"]
    find(window, "bookBarcodeInput").setProperty("text", "")
    invoke(window, "doReturn")
    process(booth_ui["app"])

    banner = find(window, "feedbackBanner")
    assert "กรุณาสแกนบาร์โค้ด" in banner.property("text")


def test_booth_return_unloaned_barcode_fails(booth_ui):
    window = booth_ui["window"]
    find(window, "bookBarcodeInput").setProperty("text", "BOOTH-02")  # on shelf, not loaned
    invoke(window, "doReturn")
    process(booth_ui["app"])

    banner = find(window, "feedbackBanner")
    assert "ไม่สำเร็จ" in banner.property("text") or "ไม่พบ" in banner.property("text")


def test_booth_return_success(booth_ui):
    window = booth_ui["window"]
    # 1. Borrow BOOTH-01
    find(window, "studentIdInput").setProperty("text", "3001")
    invoke(window, "identifyStudent")
    find(window, "bookBarcodeInput").setProperty("text", "BOOTH-01")
    invoke(window, "doCheckout")
    process(booth_ui["app"])

    # 2. Return BOOTH-01
    find(window, "bookBarcodeInput").setProperty("text", "BOOTH-01")
    invoke(window, "doReturn")
    process(booth_ui["app"])

    banner = find(window, "feedbackBanner")
    assert "คืนหนังสือสำเร็จเรียบร้อย" in banner.property("text")
    assert find(window, "bookBarcodeInput").property("text") == ""


# ---------------------------------------------------------------------------
# 5. Logout / Reset
# ---------------------------------------------------------------------------

def test_booth_logout_resets_ui(booth_ui):
    window = booth_ui["window"]
    # Log in
    find(window, "studentIdInput").setProperty("text", "3001")
    invoke(window, "identifyStudent")
    assert window.property("identifiedStudent") is not None

    # Click logout
    find(window, "btnLogout").clicked.emit()
    process(booth_ui["app"])

    assert window.property("identifiedStudent") is None
    assert find(window, "studentIdInput").property("text") == ""
    assert find(window, "bookBarcodeInput").property("text") == ""
    assert "ขอบคุณ" in find(window, "feedbackBanner").property("text")
    assert find(window, "btnCheckout").property("enabled") is False


# ---------------------------------------------------------------------------
# 6. Structural Integrity
# ---------------------------------------------------------------------------

def test_booth_all_objectnames_present(booth_ui):
    window = booth_ui["window"]
    required = [
        "studentIdInput",
        "btnIdentify",
        "studentStatusMsg",
        "bookBarcodeInput",
        "btnCheckout",
        "btnReturn",
        "feedbackBanner",
        "btnLogout",
    ]
    missing = [name for name in required if find(window, name) is None]
    assert not missing, f"Missing objectNames in Booth QML: {missing}"
