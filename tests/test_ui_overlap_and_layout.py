"""
tests/test_ui_overlap_and_layout.py
Tests UI layout resiliency under scaled fonts (20px, 150% scale):
  - StyledSearchField dynamic height expansion
  - CirculationDeskView student name row separation
  - BookInventoryRightPane header and search row separation
  - SettingsView label and control clearance
"""
import os
import sys
import time
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from data.db import get_connection
from data.migrate import apply_migrations
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter


@pytest.fixture(scope="session")
def qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def _process_events(app, count=5):
    for _ in range(count):
        app.processEvents()


def _launch_librarian_with_large_font(qapp, tmp_path):
    conn = get_connection(str(tmp_path / "lib_layout.sqlite"), pin="123456")
    apply_migrations(conn)
    adapter = LibrarianAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine._adapter = adapter
    engine.rootContext().setContextProperty("librarianAdmin", adapter)
    engine.addImportPath(os.path.abspath("apps"))
    engine.load("apps/librarian_management_app/qml/Main.qml")
    win = engine.rootObjects()[0]

    settings_view = win.findChild(object, "settingsView")
    settings_view.findChild(object, "fontSizeSlider").setProperty("value", 20)
    settings_view.findChild(object, "scaleSlider").setProperty("value", 150)
    _process_events(qapp, 10)
    return engine, conn, win


def test_styled_search_field_scales_height(qapp):
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.load(os.path.abspath("apps/common_qml/StyledSearchField.qml"))
    field = engine.rootObjects()[0]
    font = field.property("font")
    font.setPixelSize(20)
    field.setProperty("font", font)
    _process_events(qapp)
    assert field.property("implicitHeight") >= 44


def test_circulation_desk_no_text_overlap(qapp, tmp_path):
    _engine, conn, win = _launch_librarian_with_large_font(qapp, tmp_path)
    stack = win.findChild(object, "librarianStack")
    stack.setProperty("currentIndex", 1)  # Circulation Desk View
    _process_events(qapp, 10)

    student_col = win.findChild(object, "studentCol")
    row = student_col.children()[1]
    name_lbl = win.findChild(object, "checkoutStudentName")

    assert name_lbl.property("y") >= row.property("y") + row.property("height")
    conn.close()


def test_inventory_pane_header_no_overlap(qapp, tmp_path):
    _engine, conn, win = _launch_librarian_with_large_font(qapp, tmp_path)
    stack = win.findChild(object, "librarianStack")
    stack.setProperty("currentIndex", 0)  # Catalog View with right pane
    _process_events(qapp, 10)

    badge = win.findChild(object, "inventorySummaryBadge")
    badge_row = badge.parent()
    search_inp = win.findChild(object, "inventorySearchInput")
    search_row = search_inp.parent()

    assert search_row.property("y") >= badge_row.property("y") + badge_row.property("height")
    conn.close()


def test_settings_view_labels_positive_spacing(qapp, tmp_path):
    _engine, conn, win = _launch_librarian_with_large_font(qapp, tmp_path)
    settings_view = win.findChild(object, "settingsView")
    combo = settings_view.findChild(object, "fontFamilyCombo")
    slider = settings_view.findChild(object, "scaleSlider")

    # Wait for the font-scaling layout to settle; a fixed processEvents
    # count can be insufficient under load (template control sizes arrive late)
    deadline = time.time() + 10.0
    while slider.property("height") < 24 and time.time() < deadline:
        _process_events(qapp)

    assert combo.property("height") >= 30
    assert slider.property("height") >= 24
    conn.close()


def test_librarian_sidebar_nav_btn_height_and_bounds(qapp, tmp_path):
    _engine, conn, win = _launch_librarian_with_large_font(qapp, tmp_path)
    nav_btn = win.findChild(object, "navBtnSettings")
    sidebar = win.findChild(object, "sidebarNavRect")

    assert nav_btn.property("height") >= 38
    assert nav_btn.property("implicitHeight") >= 38
    assert sidebar.property("width") >= 260
    assert nav_btn.property("textElideMode") == 1
    assert nav_btn.property("textClip") is True
    conn.close()


def test_right_pane_print_button_within_card_bounds(qapp, tmp_path):
    _engine, conn, win = _launch_librarian_with_large_font(qapp, tmp_path)
    stack = win.findChild(object, "librarianStack")
    stack.setProperty("currentIndex", 6)
    _process_events(qapp, 10)

    btn = win.findChild(object, "btnGoToPrintPage")
    parent_w = btn.parent().property("width")
    btn_right = btn.property("x") + btn.property("width")

    assert btn is not None
    assert btn_right <= parent_w + 2
    conn.close()


def test_category_management_pills_and_button_height(qapp, tmp_path):
    _engine, conn, win = _launch_librarian_with_large_font(qapp, tmp_path)
    gen_list = win.findChild(object, "genBarcodesList")
    del_comp = gen_list.property("delegate")
    del_item = del_comp.create(_engine.rootContext())

    cat_pill = del_item.findChild(object, "categoryPillRect")
    copy_pill = del_item.findChild(object, "copyCountPillRect")
    btn_add = del_item.findChild(object, "btnAddCopiesRow")

    assert cat_pill.property("height") >= 24
    assert copy_pill.property("height") >= 24
    assert btn_add.property("height") >= 28
    conn.close()


def test_inventory_books_list_delegate_scales_with_font_size(qapp, tmp_path):
    _engine, conn, win = _launch_librarian_with_large_font(qapp, tmp_path)
    inv_list = win.findChild(object, "inventoryBooksList")
    del_comp = inv_list.property("delegate")
    del_item = del_comp.create(_engine.rootContext())
    title_text = del_item.findChild(object, "invBookTitleText")

    assert del_item.property("implicitHeight") >= 48
    assert title_text.property("font").pixelSize() >= 14
    conn.close()


def test_category_management_delegate_scales_with_font_size(qapp, tmp_path):
    _engine, conn, win = _launch_librarian_with_large_font(qapp, tmp_path)
    gen_list = win.findChild(object, "genBarcodesList")
    del_comp = gen_list.property("delegate")
    del_item = del_comp.create(_engine.rootContext())
    title_text = del_item.findChild(object, "catBookTitleText")

    assert del_item.property("implicitHeight") >= 50
    assert title_text.property("font").pixelSize() >= 14
    conn.close()


def test_student_sidebar_responsive_bounds(qapp, tmp_path):
    conn = get_connection(str(tmp_path / "stu_layout.sqlite"), pin="123456")
    apply_migrations(conn)
    from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter
    adapter = StudentAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine._adapter = adapter
    engine.rootContext().setContextProperty("studentAdmin", adapter)
    engine.addImportPath(os.path.abspath("apps"))
    engine.load("apps/student_management_app/qml/Main.qml")
    win = engine.rootObjects()[0]

    sidebar = win.findChild(object, "studentSidebarNavRect")
    assert sidebar is not None
    assert sidebar.property("width") >= 260
    conn.close()


