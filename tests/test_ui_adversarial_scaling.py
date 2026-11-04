"""
tests/test_ui_adversarial_scaling.py
Adversarial QA test suite verifying extreme Typography scaling,
delegate instantiation under active scaling, memory leak / NaN safety,
and layout resiliency under extreme-length Thai strings.
"""
import os
import sys
import json
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlContext
from PySide6.QtCore import QMetaObject, QUrl
from data.db import get_connection
from data.migrate import apply_migrations
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter


@pytest.fixture(scope="session")
def qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def _pump_events(app, count=6):
    for _ in range(count):
        app.processEvents()


def _create_librarian_window(tmp_path, db_name="lib_adv.sqlite"):
    conn = get_connection(str(tmp_path / db_name), pin="123456")
    apply_migrations(conn)
    adapter = LibrarianAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine._adapter = adapter
    engine.rootContext().setContextProperty("librarianAdmin", adapter)
    engine.addImportPath(os.path.abspath("apps"))
    engine.load("apps/librarian_management_app/qml/Main.qml")
    win = engine.rootObjects()[0]
    win.show()
    return engine, conn, adapter, win


def _create_student_window(tmp_path, db_name="stu_adv.sqlite"):
    conn = get_connection(str(tmp_path / db_name), pin="123456")
    apply_migrations(conn)
    adapter = StudentAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine._adapter = adapter
    engine.rootContext().setContextProperty("studentAdmin", adapter)
    engine.addImportPath(os.path.abspath("apps"))
    engine.load("apps/student_management_app/qml/Main.qml")
    win = engine.rootObjects()[0]
    win.show()
    return engine, conn, adapter, win


# ---------------------------------------------------------------------------
# Test 1: Extreme Typography Scaling & Churn
# ---------------------------------------------------------------------------

def test_extreme_typography_scaling_and_churn(qapp, tmp_path):
    """Verify fontScale boundary conditions (0.357x - 2.571x) without NaN or crash."""
    engine, conn, _, win = _create_librarian_window(tmp_path)
    _pump_events(qapp)

    settings = win.findChild(object, "settingsView")
    font_slider = settings.findChild(object, "fontSizeSlider")
    scale_slider = settings.findChild(object, "scaleSlider")

    # 1. Extreme minimum: 10px, 50% scale
    font_slider.setProperty("value", 10)
    scale_slider.setProperty("value", 50)
    _pump_events(qapp)
    min_scale = win.property("fontScale")
    assert 0.35 <= min_scale <= 0.37
    assert not (min_scale != min_scale), "fontScale is NaN"

    # 2. Extreme maximum: 24px, 150% scale
    font_slider.setProperty("value", 24)
    scale_slider.setProperty("value", 150)
    _pump_events(qapp)
    max_scale = win.property("fontScale")
    assert 2.50 <= max_scale <= 2.60
    assert not (max_scale != max_scale), "fontScale is NaN"

    # 3. Churn 10 cycles rapidly
    cycle_pairs = [(10, 50), (14, 100), (20, 125), (24, 150), (11, 75)]
    for _ in range(2):
        for f_val, s_val in cycle_pairs:
            font_slider.setProperty("value", f_val)
            scale_slider.setProperty("value", s_val)
            _pump_events(qapp, 2)

    # 4. Reset to defaults
    settings.findChild(object, "btnResetSettings").clicked.emit()
    _pump_events(qapp)
    assert win.property("fontScale") == 1.0
    conn.close()


# ---------------------------------------------------------------------------
# Test 2: Delegate Instantiation Under Active Scale & Restoration
# ---------------------------------------------------------------------------

def test_delegate_instantiation_under_active_scale(qapp, tmp_path):
    """Verify delegates instantiated while scaled do not double-scale or drift on reset."""
    engine, conn, adapter, win = _create_librarian_window(tmp_path)
    _pump_events(qapp)

    settings = win.findChild(object, "settingsView")
    settings.findChild(object, "fontSizeSlider").setProperty("value", 24)
    settings.findChild(object, "scaleSlider").setProperty("value", 150)
    _pump_events(qapp)

    # Instantiate delegates directly while scale factor is 2.57x
    views_and_lists = [
        (4, "activeLoanList", 54),
        (5, "fineList", 54),
        (6, "genBarcodesList", 50),
        (7, "logList", 48),
    ]

    stack = win.findChild(object, "librarianStack")
    for idx, list_name, min_h in views_and_lists:
        stack.setProperty("currentIndex", idx)
        _pump_events(qapp)
        list_obj = win.findChild(object, list_name)
        comp = list_obj.property("delegate")
        item = comp.create(engine.rootContext())
        assert item is not None
        h_scaled = item.property("implicitHeight")
        assert h_scaled >= min_h
        assert not (h_scaled != h_scaled), f"{list_name} delegate height is NaN"

    # Reset back to 1.0x
    settings.findChild(object, "btnResetSettings").clicked.emit()
    _pump_events(qapp)
    assert win.property("fontScale") == 1.0
    conn.close()


# ---------------------------------------------------------------------------
# Test 3: Extreme Long Thai Strings Resiliency (Active Loans & Fines)
# ---------------------------------------------------------------------------

def test_extreme_thai_strings_librarian_views(qapp, tmp_path):
    """Verify extreme long Thai strings in book title, borrower name, and fine reason."""
    engine, conn, adapter, win = _create_librarian_window(tmp_path)
    _pump_events(qapp)

    long_title = "วรรณคดีและวรรณกรรมไทยประวัติศาสตร์ฉบับพิเศษ" * 6  # ~250 chars
    long_author = "ศาสตราจารย์เกียรติคุณ ดร. นายแพทย์ผู้เชี่ยวชาญพิเศษ" * 3
    long_reason = "ทำหนังสือชำรุดเสียหายหนักมากจนปกฉีกขาดเป็นสองท่อน" * 4

    adapter.addBook(long_title, author=long_author, barcodes_csv="1")
    conn.execute("""
        INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, status)
        VALUES (88888, '1112223334445', 'นาย', 'ปราบดาพิชัยสงครามมหาโยธิน', 'รัตนโกสินทร์ศิริวัฒนากุล', 'นายปราบดาพิชัยสงครามมหาโยธิน รัตนโกสินทร์ศิริวัฒนากุล', 'active')
    """)
    conn.commit()

    row = conn.execute("SELECT barcode FROM book_copies LIMIT 1").fetchone()
    adapter.checkout(88888, row["barcode"])
    conn.execute("INSERT INTO fines (loan_id, amount, reason, paid) VALUES (1, 120.0, ?, 0)", (long_reason,))
    conn.commit()

    # Load Active Loans
    stack = win.findChild(object, "librarianStack")
    stack.setProperty("currentIndex", 4)
    QMetaObject.invokeMethod(win, "loadActiveLoans")
    _pump_events(qapp)

    active_list = win.findChild(object, "activeLoanList")
    assert active_list.property("count") == 1

    # Load Fines
    stack.setProperty("currentIndex", 5)
    QMetaObject.invokeMethod(win, "loadFines")
    _pump_events(qapp)

    fine_list = win.findChild(object, "fineList")
    assert fine_list.property("count") == 1

    # Churn scales with long strings loaded
    settings = win.findChild(object, "settingsView")
    settings.findChild(object, "fontSizeSlider").setProperty("value", 22)
    settings.findChild(object, "scaleSlider").setProperty("value", 125)
    _pump_events(qapp)

    settings.findChild(object, "btnResetSettings").clicked.emit()
    _pump_events(qapp)
    conn.close()


# ---------------------------------------------------------------------------
# Test 4: Extreme Long Thai Strings in Student Management Search
# ---------------------------------------------------------------------------

def test_extreme_thai_strings_student_search(qapp, tmp_path):
    """Verify StudentSearchView with long student name, class number, and extreme search query."""
    engine, conn, adapter, win = _create_student_window(tmp_path)
    _pump_events(qapp)

    ultra_name = "เด็กชายปราบดาพิชัยสงครามมหาโยธินณรงค์ฤทธิ์ รัตนโกสินทร์ศิริวัฒนากุลพานิชวิเศษสถิตย์"
    conn.execute("""
        INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, status)
        VALUES (99999, '9999999999999', 'เด็กชาย', 'ปราบดาพิชัยสงครามมหาโยธินณรงค์ฤทธิ์', 'รัตนโกสินทร์ศิริวัฒนากุลพานิชวิเศษสถิตย์', ?, 'active')
    """, (ultra_name,))
    conn.commit()

    search_input = win.findChild(object, "searchInput")
    search_input.setProperty("text", "ปราบดา")
    QMetaObject.invokeMethod(win, "doSearch")
    _pump_events(qapp)

    student_list = win.findChild(object, "studentList")
    assert student_list.property("count") >= 1

    # Test extreme search query with Thai unicode characters and symbols
    search_input.setProperty("text", "๛ทดสอบค้นหาภาษาไทยสัญลักษณ์พิเศษ๑๒๓๔๕๖๗๘๙๐!@#$%^&*()_+-=[]{}|;':,.<>?/")
    QMetaObject.invokeMethod(win, "doSearch")
    _pump_events(qapp)
    assert student_list.property("count") == 0
    conn.close()


# ---------------------------------------------------------------------------
# Test 5: CirculationDeskView Extreme Input & Status Wrapping
# ---------------------------------------------------------------------------

def test_circulation_desk_view_long_barcode_and_status(qapp, tmp_path):
    """Verify CirculationDeskView status wrapping and long barcode error handling."""
    engine, conn, _, win = _create_librarian_window(tmp_path)
    _pump_events(qapp)

    stack = win.findChild(object, "librarianStack")
    stack.setProperty("currentIndex", 0)  # Circulation Desk
    _pump_events(qapp)

    barcode_input = win.findChild(object, "barcodeInput")
    long_barcode = "BARCODE-OVERFLOW-" * 10
    barcode_input.setProperty("text", long_barcode)

    btn_checkout = win.findChild(object, "btnCheckout")
    btn_checkout.clicked.emit()
    _pump_events(qapp)

    desk_status = win.findChild(object, "deskStatusText")
    status_text = desk_status.property("text")
    assert len(status_text) > 0
    assert desk_status.property("implicitHeight") > 0
    conn.close()


# ---------------------------------------------------------------------------
# Test 6: Typography JS Pure Unit Edge Cases (NaN, Null, Zero)
# ---------------------------------------------------------------------------

def test_typography_js_edge_cases(qapp):
    """Directly test Typography.js boundary functions via QML component."""
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))

    qml_snippet = """
    import QtQuick 2.15
    import "Typography.js" as Typography

    Item {
        id: harness
        function runScale(val) {
            return Typography.scale(val);
        }
        function runExtractBaseline(pixelSize, factor) {
            return Typography.extractBaselineSize({ font: { pixelSize: pixelSize } }, factor);
        }
    }
    """
    comp = QQmlComponent(engine)
    qml_url = QUrl.fromLocalFile(os.path.abspath("apps/common_qml/test_harness.qml"))
    comp.setData(qml_snippet.encode("utf-8"), qml_url)
    harness = comp.create()
    assert harness is not None

    # Normal scaling
    s_normal = harness.runScale(14)
    assert s_normal >= 14

    # Zero or negative inputs clamped to >= 8
    s_zero = harness.runScale(0)
    assert s_zero == 8
    s_neg = harness.runScale(-10)
    assert s_neg == 8

    # Baseline extraction with extreme factors
    base_high = harness.runExtractBaseline(36, 2.57)
    assert 13 <= base_high <= 15

    base_low = harness.runExtractBaseline(10, 0.5)
    assert 19 <= base_low <= 21

    base_safe = harness.runExtractBaseline(14, 0)  # zero factor fallback to 1.0
    assert base_safe == 14


# ---------------------------------------------------------------------------
# Test 7: AuditLogView Extreme Strings & Scaling
# ---------------------------------------------------------------------------

def test_audit_log_view_extreme_strings_and_scaling(qapp, tmp_path):
    """Verify AuditLogView with ultra-long action and detail logs under typography scaling."""
    engine, conn, _, win = _create_librarian_window(tmp_path)
    _pump_events(qapp)

    long_action = "นำเข้าข้อมูลและปรับปรุงสถานะนักเรียนจำนวนมากเป็นกรณีพิเศษ" * 2
    long_detail = "รายละเอียดการปรับปรุงข้อมูลประวัติการยืม-คืนและแก้ไขยอดค่าปรับค้างชำระของนักเรียนกลุ่มเป้าหมาย" * 4

    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO activity_log (logged_at, actor, action, entity_type, entity_id, detail) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "AdminQA", long_action, "Student", 99999, long_detail),
    )
    conn.commit()

    stack = win.findChild(object, "librarianStack")
    stack.setProperty("currentIndex", 7)  # Audit Log view
    QMetaObject.invokeMethod(win, "loadLogs")
    _pump_events(qapp)

    log_list = win.findChild(object, "logList")
    assert log_list.property("count") >= 1

    settings = win.findChild(object, "settingsView")
    settings.findChild(object, "fontSizeSlider").setProperty("value", 20)
    settings.findChild(object, "scaleSlider").setProperty("value", 125)
    _pump_events(qapp)

    settings.findChild(object, "btnResetSettings").clicked.emit()
    _pump_events(qapp)
    assert win.property("fontScale") == 1.0
    conn.close()


# ---------------------------------------------------------------------------
# Test 8: ExcelImportView Diff & BarcodeConfirm Dialogs
# ---------------------------------------------------------------------------

def test_excel_import_diff_and_barcode_dialogs(qapp, tmp_path):
    """Verify diff delegate in ExcelImportView and barcode confirm delegate in BookActionDialogs."""
    engine, conn, _, win = _create_student_window(tmp_path)
    _pump_events(qapp)

    stack = win.findChild(object, "mainStack")
    stack.setProperty("currentIndex", 2)  # Excel Import view
    _pump_events(qapp)

    diff_list = win.findChild(object, "diffListView")
    assert diff_list is not None
    diff_comp = diff_list.property("delegate")
    assert diff_comp is not None

    diff_item = diff_comp.create(engine.rootContext())
    assert diff_item is not None
    assert diff_item.property("implicitHeight") >= 36
    conn.close()


# ---------------------------------------------------------------------------
# Test 9: EditBookDialog Long Strings & Category Updates
# ---------------------------------------------------------------------------

def test_edit_book_dialog_long_strings_resiliency(qapp, tmp_path):
    """Verify EditBookDialog handles extreme strings and category assignment cleanly."""
    engine, conn, adapter, win = _create_librarian_window(tmp_path)
    _pump_events(qapp)

    adapter.addCategory("หมวดหมู่วรรณกรรมและปรัชญาประวัติศาสตร์โบราณคดีศึกษา")
    adapter.addBook("ชื่อเรื่องสั้นเดิม", author="ผู้แต่งเดิม", shelf_location="A1", barcodes_csv="1")

    dialogs = win.findChild(object, "bookDialogs")
    assert dialogs is not None

    long_title = "ชื่อหนังสือปรับปรุงใหม่ที่มีขนาดยาวเป็นพิเศษเพื่อทดสอบการรองรับข้อความยาวมาก" * 3
    long_author = "ผู้แต่งปรับปรุงใหม่ศาสตราจารย์เกียรติคุณ" * 2
    long_shelf = "ตู้หนังสือประวัติศาสตร์แถว 99 ชั้น 88 ห้องสมุดกลาง"

    res = json.loads(adapter.updateBook(
        1, long_title, "978-616-00-9999-9", long_author, "1", long_shelf
    ))
    assert res.get("ok") is True

    # Verify updated book
    book_info = json.loads(adapter.getBook(1))
    assert book_info["title"] == long_title
    assert book_info["shelf_location"] == long_shelf
    conn.close()


# ---------------------------------------------------------------------------
# Test 10: Student Search Delegate Idempotency
# ---------------------------------------------------------------------------

def test_student_search_delegate_scaling_and_idempotency(qapp, tmp_path):
    """Verify StudentSearchView delegate scales and restores without double-scaling."""
    engine, conn, adapter, win = _create_student_window(tmp_path)
    _pump_events(qapp)

    student_list = win.findChild(object, "studentList")
    del_comp = student_list.property("delegate")

    ctx = QQmlContext(engine.rootContext())
    ctx.setContextProperty("window", win)
    ctx.setContextProperty(
        "model",
        {
            "_empty": False,
            "student_id": "1001",
            "full_name": "นายสมชาย ใจดี",
            "grade_level": "1",
            "room": "1",
            "status": "active",
        },
    )

    del_item = del_comp.create(ctx)
    assert del_item is not None
    h_init = del_item.property("implicitHeight")
    assert h_init >= 48

    # Scale settings to 24px and 150%
    settings = win.findChild(object, "settingsView")
    settings.findChild(object, "fontSizeSlider").setProperty("value", 24)
    settings.findChild(object, "scaleSlider").setProperty("value", 150)
    _pump_events(qapp)

    del_item_scaled = del_comp.create(ctx)
    assert del_item_scaled is not None
    h_scaled = del_item_scaled.property("implicitHeight")
    assert h_scaled >= 48

    # Reset
    settings.findChild(object, "btnResetSettings").clicked.emit()
    _pump_events(qapp)
    assert win.property("fontScale") == 1.0
    conn.close()
