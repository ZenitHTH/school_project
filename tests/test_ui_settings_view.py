"""
tests/test_ui_settings_view.py
Tests SettingsView component and typography propagation across apps:
  - Default properties and Noto Sans font selection
  - Font size controls (10-24px) & UI scale limits (50%-150%)
  - Reset to defaults action
  - Cross-view font family and pixelSize propagation in Librarian and Student apps
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


def process_events(app):
    for _ in range(5):
        app.processEvents()


@pytest.fixture
def settings_comp(qapp):
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.load(os.path.abspath("apps/common_qml/SettingsView.qml"))
    assert len(engine.rootObjects()) > 0
    return {"engine": engine, "root": engine.rootObjects()[0], "app": qapp}


def _launch_app(qapp, tmp_path, db_name, qml_file, adapter_name, adapter_cls):
    conn = get_connection(str(tmp_path / f"{db_name}.sqlite"), pin="123456")
    apply_migrations(conn)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty(adapter_name, adapter_cls(conn))
    engine.addImportPath(os.path.abspath("apps"))
    engine.load(qml_file)
    process_events(qapp)
    return engine, conn, engine.rootObjects()[0]


def test_settings_view_defaults(settings_comp):
    root = settings_comp["root"]
    assert root.property("currentFontFamily") == "System Default"
    assert root.property("activeFontFamily") == ""
    assert root.property("currentFontSize") == 14
    assert abs(root.property("currentUiScale") - 1.0) < 0.001


def test_settings_view_noto_sans_and_font_family_selection(settings_comp):
    root = settings_comp["root"]
    combo = root.findChild(object, "fontFamilyCombo")
    assert combo is not None

    combo.setProperty("currentIndex", 1)  # Noto Sans
    process_events(settings_comp["app"])
    assert root.property("currentFontFamily") == "Noto Sans"
    assert root.property("activeFontFamily") == "Noto Sans"

    combo.setProperty("currentIndex", 2)  # Sarabun
    process_events(settings_comp["app"])
    assert root.property("currentFontFamily") == "Sarabun"
    assert root.property("activeFontFamily") == "Sarabun"

    combo.setProperty("currentIndex", 0)  # System Default
    process_events(settings_comp["app"])
    assert root.property("currentFontFamily") == "System Default"
    assert root.property("activeFontFamily") == ""


def test_settings_view_font_size_controls(settings_comp):
    root = settings_comp["root"]
    slider = root.findChild(object, "fontSizeSlider")
    btn_minus = root.findChild(object, "btnFontSizeMinus")
    btn_plus = root.findChild(object, "btnFontSizePlus")

    slider.setProperty("value", 18)
    process_events(settings_comp["app"])
    assert root.property("currentFontSize") == 18

    btn_plus.clicked.emit()
    process_events(settings_comp["app"])
    assert root.property("currentFontSize") == 19

    btn_minus.clicked.emit()
    process_events(settings_comp["app"])
    assert root.property("currentFontSize") == 18

    slider.setProperty("value", 5)  # Under limit
    process_events(settings_comp["app"])
    assert slider.property("value") == 10
    assert root.property("currentFontSize") == 10


def test_settings_view_ui_scale_limits(settings_comp):
    root = settings_comp["root"]
    scale_slider = root.findChild(object, "scaleSlider")

    scale_slider.setProperty("value", 50)  # Min limit 50%
    process_events(settings_comp["app"])
    assert abs(root.property("currentUiScale") - 0.5) < 0.001

    scale_slider.setProperty("value", 150)  # Max limit 150%
    process_events(settings_comp["app"])
    assert abs(root.property("currentUiScale") - 1.5) < 0.001

    scale_slider.setProperty("value", 100)
    process_events(settings_comp["app"])
    assert abs(root.property("currentUiScale") - 1.0) < 0.001


def test_settings_view_reset_to_defaults(settings_comp):
    root = settings_comp["root"]
    combo = root.findChild(object, "fontFamilyCombo")
    font_slider = root.findChild(object, "fontSizeSlider")
    scale_slider = root.findChild(object, "scaleSlider")
    btn_reset = root.findChild(object, "btnResetSettings")

    combo.setProperty("currentIndex", 1)  # Noto Sans
    font_slider.setProperty("value", 20)
    scale_slider.setProperty("value", 125)
    process_events(settings_comp["app"])

    btn_reset.clicked.emit()
    process_events(settings_comp["app"])
    assert root.property("currentFontFamily") == "System Default"
    assert root.property("activeFontFamily") == ""
    assert root.property("currentFontSize") == 14
    assert abs(root.property("currentUiScale") - 1.0) < 0.001


def test_librarian_app_settings_navigation_and_typography(qapp, tmp_path):
    _engine, conn, win = _launch_app(qapp, tmp_path, "lib", "apps/librarian_management_app/qml/Main.qml", "librarianAdmin", LibrarianAdminAdapter)
    nav_btn = win.findChild(object, "navBtnSettings")
    settings_view = win.findChild(object, "settingsView")
    assert nav_btn is not None and settings_view is not None

    nav_btn.clicked.emit()
    process_events(qapp)
    assert win.findChild(object, "librarianStack").property("currentIndex") == 8

    orig_size = nav_btn.property("font").pixelSize()
    settings_view.findChild(object, "fontFamilyCombo").setProperty("currentIndex", 1)  # Noto Sans
    settings_view.findChild(object, "fontSizeSlider").setProperty("value", 18)
    settings_view.findChild(object, "scaleSlider").setProperty("value", 125)
    process_events(qapp)

    assert nav_btn.property("font").family() == "Noto Sans"
    assert nav_btn.property("font").pixelSize() > orig_size

    settings_view.findChild(object, "btnResetSettings").clicked.emit()
    process_events(qapp)
    assert nav_btn.property("font").pixelSize() == orig_size
    conn.close()


def test_student_app_settings_navigation_and_typography(qapp, tmp_path):
    _engine, conn, win = _launch_app(qapp, tmp_path, "stu", "apps/student_management_app/qml/Main.qml", "studentAdmin", StudentAdminAdapter)
    settings_view = win.findChild(object, "settingsView")
    search_btn = win.findChild(object, "searchButton")
    assert settings_view is not None and search_btn is not None

    stack = win.findChild(object, "mainStack")
    stack.setProperty("currentIndex", 6)
    process_events(qapp)
    assert stack.property("currentIndex") == 6

    orig_size = search_btn.property("font").pixelSize()
    settings_view.findChild(object, "fontFamilyCombo").setProperty("currentIndex", 1)  # Noto Sans
    settings_view.findChild(object, "fontSizeSlider").setProperty("value", 18)
    settings_view.findChild(object, "scaleSlider").setProperty("value", 125)
    process_events(qapp)

    assert search_btn.property("font").family() == "Noto Sans"
    assert search_btn.property("font").pixelSize() > orig_size

    settings_view.findChild(object, "btnResetSettings").clicked.emit()
    process_events(qapp)
    assert search_btn.property("font").pixelSize() == orig_size
    conn.close()
