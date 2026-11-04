"""
tests/test_ui_responsive_delegates.py
Unit tests verifying UI responsive heights, Typography double-scaling fix,
and accessibility contrast rules across QML components.
"""
import os
import sys
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from data.db import get_connection
from data.migrate import apply_migrations
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter


@pytest.fixture(scope="session")
def qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def _pump_events(app, count=8):
    for _ in range(count):
        app.processEvents()


def _launch_student_app(tmp_path):
    conn = get_connection(str(tmp_path / "stu_test.sqlite"), pin="123456")
    apply_migrations(conn)
    adapter = StudentAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine._adapter = adapter
    engine.rootContext().setContextProperty("studentAdmin", adapter)
    engine.addImportPath(os.path.abspath("apps"))
    engine.load("apps/student_management_app/qml/Main.qml")
    return engine, conn, engine.rootObjects()[0]


def _launch_librarian_app(tmp_path):
    conn = get_connection(str(tmp_path / "lib_test.sqlite"), pin="123456")
    apply_migrations(conn)
    adapter = LibrarianAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine._adapter = adapter
    engine.rootContext().setContextProperty("librarianAdmin", adapter)
    engine.addImportPath(os.path.abspath("apps"))
    engine.load("apps/librarian_management_app/qml/Main.qml")
    return engine, conn, engine.rootObjects()[0]


def test_student_search_and_sidebar_responsive(qapp, tmp_path):
    engine, conn, win = _launch_student_app(tmp_path)
    _pump_events(qapp)

    sidebar = win.findChild(object, "studentSidebarNavRect")
    assert sidebar is not None
    orig_w = sidebar.property("width")
    assert orig_w >= 260

    settings_view = win.findChild(object, "settingsView")
    settings_view.findChild(object, "fontSizeSlider").setProperty("value", 20)
    settings_view.findChild(object, "scaleSlider").setProperty("value", 150)
    _pump_events(qapp)
    assert sidebar.property("width") >= orig_w

    search_btn = win.findChild(object, "searchButton")
    search_btn.clicked.emit()
    _pump_events(qapp)

    table = win.findChild(object, "studentList")
    assert table is not None
    conn.close()


def test_librarian_loans_fines_and_category_views(qapp, tmp_path):
    engine, conn, win = _launch_librarian_app(tmp_path)
    _pump_events(qapp)

    stack = win.findChild(object, "librarianStack")
    stack.setProperty("currentIndex", 4)  # Active Loans
    _pump_events(qapp)
    active_list = win.findChild(object, "activeLoanList")
    assert active_list is not None

    stack.setProperty("currentIndex", 5)  # Fines
    _pump_events(qapp)
    fine_list = win.findChild(object, "fineList")
    assert fine_list is not None

    stack.setProperty("currentIndex", 6)  # Category & Barcode Print
    _pump_events(qapp)
    combo = win.findChild(object, "barcodeCategoryFilterCombo")
    assert combo.property("implicitHeight") >= 34

    pane_badge = win.findChild(object, "inventorySummaryBadge")
    assert pane_badge.property("implicitHeight") >= 22
    conn.close()


def test_audit_log_and_settings_reset(qapp, tmp_path):
    engine, conn, win = _launch_librarian_app(tmp_path)
    _pump_events(qapp)

    stack = win.findChild(object, "librarianStack")
    stack.setProperty("currentIndex", 7)  # Audit Log
    _pump_events(qapp)
    log_list = win.findChild(object, "logList")
    assert log_list is not None

    settings_view = win.findChild(object, "settingsView")
    settings_view.findChild(object, "scaleSlider").setProperty("value", 150)
    _pump_events(qapp)
    settings_view.findChild(object, "btnResetSettings").clicked.emit()
    _pump_events(qapp)
    assert settings_view.property("currentFontSize") == 14
    conn.close()


def test_edit_book_dialog_and_desk_status(qapp, tmp_path):
    engine, conn, win = _launch_librarian_app(tmp_path)
    _pump_events(qapp)

    status_text = win.findChild(object, "deskStatusText")
    assert status_text is not None
    assert status_text.property("color").name() == "#2563eb"

    dialog = win.findChild(object, "editBookDialog")
    assert dialog is not None
    conn.close()
