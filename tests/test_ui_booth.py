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
from PySide6.QtQuick import QQuickItem
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
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
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

    qapp.processEvents()
    conn.close()
    engine.deleteLater()
    qapp.processEvents()


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
        "emptyDbWarningBanner",
        "btnOpenBookSearch",
        "boothBookSearchView",
        "btnBackFromBookSearch",
        "boothBookSearchInput",
        "boothCategoryFilter",
        "btnBoothSearchBooks",
        "boothBookSearchStatus",
        "boothBookResultsList",
    ]
    missing = [name for name in required if find(window, name) is None]
    assert not missing, f"Missing objectNames in Booth QML: {missing}"


# ---------------------------------------------------------------------------
# 7. Self-Service Book Search & Shelf Locator
# ---------------------------------------------------------------------------

def test_booth_open_book_search_and_back(booth_ui):
    window = booth_ui["window"]
    stack = find(window, "kioskStack")
    assert stack.property("currentIndex") == 0

    find(window, "btnOpenBookSearch").clicked.emit()
    process(booth_ui["app"])
    assert stack.property("currentIndex") == 2

    find(window, "btnBackFromBookSearch").clicked.emit()
    process(booth_ui["app"])
    assert stack.property("currentIndex") == 0


def test_booth_book_search_displays_shelf_category_and_availability(booth_ui):
    window = booth_ui["window"]
    conn = booth_ui["conn"]

    sci_id = book_repo.add_category(conn, "วิทยาศาสตร์")
    b1 = book_repo.add_book(
        conn,
        title="ฟิสิกส์พื้นฐาน",
        author="ดร.สมชาย",
        isbn="978-111",
        category_id=sci_id,
        shelf_location="S-01",
    )
    book_repo.add_copies(conn, b1, barcodes=["SCI-01", "SCI-02"])

    b_empty = book_repo.add_book(
        conn,
        title="หนังสือไร้หมวด",
        author="ไม่ทราบ",
        isbn="978-222",
        category_id=None,
        shelf_location=None,
    )
    book_repo.add_copies(conn, b_empty, barcodes=["EMPTY-01"])
    # Borrow the single copy so available_copies == 0
    booth_ui["adapter"].checkout(3001, "EMPTY-01")

    find(window, "btnOpenBookSearch").clicked.emit()
    process(booth_ui["app"])

    search_input = find(window, "boothBookSearchInput")
    search_input.setProperty("text", "ฟิสิกส์")
    find(window, "btnBoothSearchBooks").clicked.emit()
    process(booth_ui["app"])

    results_list = find(window, "boothBookResultsList")
    results_model = find(window, "bookResultsModel")
    status_text = find(window, "boothBookSearchStatus")
    assert results_list.property("count") == 1
    assert "พบ 1 รายการ" in status_text.property("text")

    row = results_model.get(0)
    assert row.property("title").toString() == "ฟิสิกส์พื้นฐาน"
    assert row.property("shelf_location").toString() == "S-01"
    assert row.property("category_name").toString() == "วิทยาศาสตร์"
    assert row.property("available_copies").toInt() == 2
    assert row.property("total_copies").toInt() == 2

    # Verify book with missing category/shelf and 0 available copies renders safely
    search_input.setProperty("text", "หนังสือไร้หมวด")
    find(window, "btnBoothSearchBooks").clicked.emit()
    process(booth_ui["app"])
    assert results_list.property("count") == 1
    row_empty = results_model.get(0)
    assert row_empty.property("shelf_location").toString() == ""
    assert row_empty.property("category_name").toString() == ""
    assert row_empty.property("available_copies").toInt() == 0
    assert row_empty.property("total_copies").toInt() == 1

    # Verify empty results message
    search_input.setProperty("text", "ไม่มีหนังสือชื่อนี้แน่นอน")
    find(window, "btnBoothSearchBooks").clicked.emit()
    process(booth_ui["app"])
    assert results_list.property("count") == 0
    assert "ไม่พบหนังสือที่ตรงกับการค้นหา" in status_text.property("text")


def test_booth_book_search_category_filter(booth_ui):
    window = booth_ui["window"]
    conn = booth_ui["conn"]

    sci_id = book_repo.add_category(conn, "วิทยาศาสตร์")
    lit_id = book_repo.add_category(conn, "วรรณกรรม")
    b_sci = book_repo.add_book(conn, title="เคมีเบื้องต้น", category_id=sci_id, shelf_location="A-1")
    book_repo.add_copies(conn, b_sci, barcodes=["CHEM-01"])
    b_lit = book_repo.add_book(conn, title="นิทานพื้นบ้าน", category_id=lit_id, shelf_location="B-2")
    book_repo.add_copies(conn, b_lit, barcodes=["LIT-01"])

    find(window, "btnOpenBookSearch").clicked.emit()
    process(booth_ui["app"])

    cat_combo = find(window, "boothCategoryFilter")
    cat_model = find(window, "boothCategoryFilterModel")
    results_list = find(window, "boothBookResultsList")
    results_model = find(window, "bookResultsModel")

    assert cat_model.get(0).property("name").toString() == "ทุกหมวดหมู่"
    assert cat_model.property("count") == 3  # All + 2 categories
    total_all = results_list.property("count")
    assert total_all >= 3

    # Find index for "วรรณกรรม"
    lit_idx = next(
        i for i in range(cat_model.property("count"))
        if cat_model.get(i).property("name").toString() == "วรรณกรรม"
    )
    find(window, "boothBookSearchInput").setProperty("text", "")
    cat_combo.setProperty("currentIndex", lit_idx)
    process(booth_ui["app"])

    assert results_list.property("count") == 1
    assert results_model.get(0).property("title").toString() == "นิทานพื้นบ้าน"

    # Reset back to "ทุกหมวดหมู่"
    cat_combo.setProperty("currentIndex", 0)
    process(booth_ui["app"])
    assert results_list.property("count") == total_all


def test_booth_warning_banner_hidden_when_seeded(booth_ui):
    """When students and books exist, emptyDbWarningBanner is not visible."""
    window = booth_ui["window"]
    banner = find(window, "emptyDbWarningBanner")
    assert banner is not None
    assert banner.property("visible") is False


def test_booth_warning_banner_visible_on_empty_db(qapp, tmp_path):
    """When DB is empty, emptyDbWarningBanner is visible."""
    db_file = str(tmp_path / "empty_booth_ui.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    adapter = BoothAdapter(conn)
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
    engine.rootContext().setContextProperty("boothAdapter", adapter)

    qml_path = os.path.abspath("apps/booth_app/qml/Main.qml")
    engine.load(qml_path)
    qapp.processEvents()

    window = engine.rootObjects()[0]
    banner = find(window, "emptyDbWarningBanner")
    assert banner is not None
    assert banner.property("visible") is True

    qapp.processEvents()
    conn.close()
    engine.deleteLater()
    qapp.processEvents()


def test_lan_settings_dialog_height_wraps_content(booth_ui):
    """StyledDialog grows vertically to wrap its content, header, and footer."""
    window = booth_ui["window"]
    dialog = find(window, "lanSettingsDialog")
    assert dialog is not None

    invoke(window, "openLanSettings")
    process(booth_ui["app"])
    process(booth_ui["app"])

    content_item = dialog.property("contentItem")
    children_h = content_item.property("childrenRect").height()
    dialog_h = dialog.property("height")
    assert dialog_h >= 250
    assert dialog_h >= children_h
    invoke(dialog, "close")
    process(booth_ui["app"])


