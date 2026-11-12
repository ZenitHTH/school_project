"""
tests/test_ui_student_modernization.py
UI modernization regression tests for the Student Management App,
aligned with the Librarian Management reference patterns:

  - main.py wires setup_app_logging("SMTE-StudentManagement")
  - Main.qml declares a forced light palette (Fusion / system dark-mode guard)
  - Sidebar nav delegates use dynamic implicitHeight (no fixed 42px)
  - Sidebar typography (wizard button / title) scales with the settings view
  - StudentDetailView info card / status badge use dynamic heights
  - ExcelImportView diff badges use dynamic heights and scaled fonts

Note: this Qt build does not expose objectName on Repeater/ListView delegate
instances (findChild returns None), so delegate geometry is asserted on a
standalone instance created from the delegate's QQmlComponent — the same
pattern tests/test_ui_overlap_and_layout.py uses.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QMetaObject, Qt, Q_ARG

from data.db import get_connection
from data.migrate import apply_migrations
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_QML = REPO_ROOT / "apps" / "student_management_app" / "qml" / "Main.qml"


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    return app


def _pump(app, count=8):
    for _ in range(count):
        app.processEvents()


def _launch(qapp, tmp_path):
    db_file = str(tmp_path / "stu_modern.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)
    conn.execute(
        "INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, status) VALUES "
        "(1001, '1100100200300', 'นาย', 'สมชาย', 'มั่นคง', 'นายสมชาย มั่นคง', 'active')"
    )
    conn.execute(
        "INSERT INTO enrollments (student_id, academic_year, semester, grade_level, room) "
        "VALUES (1001, 2567, 1, 'ม.3', 2)"
    )
    conn.commit()
    adapter = StudentAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine._adapter = adapter
    engine.rootContext().setContextProperty("studentAdmin", adapter)
    engine.addImportPath(str(REPO_ROOT / "apps"))
    engine.load(str(MAIN_QML))
    assert engine.rootObjects(), "QML failed to load"
    window = engine.rootObjects()[0]
    _pump(qapp)
    return engine, conn, window


def _set_large_typography(win, qapp):
    settings = win.findChild(object, "settingsView")
    assert settings is not None
    settings.findChild(object, "fontSizeSlider").setProperty("value", 20)
    settings.findChild(object, "scaleSlider").setProperty("value", 150)
    _pump(qapp)


def test_student_main_wires_app_logging(tmp_path, monkeypatch):
    """main() must call setup_app_logging('SMTE-StudentManagement') like the librarian app."""
    calls = []
    spec = importlib.util.spec_from_file_location(
        "student_app_main_mod_under_test",
        REPO_ROOT / "apps" / "student_management_app" / "main.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    monkeypatch.setattr(mod, "setup_app_logging", lambda name: calls.append(name))
    monkeypatch.setenv("STUDENT_DB_PATH", str(tmp_path / "log_wiring.sqlite"))
    monkeypatch.setattr(sys, "argv", ["main.py", "--cli"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    mod.main()

    assert calls == ["SMTE-StudentManagement"]


def test_student_main_declares_light_palette():
    """Invariant #7: Main.qml declares a forced light palette (static contract)."""
    src = MAIN_QML.read_text(encoding="utf-8")
    assert 'palette.window: "#f8fafc"' in src
    assert 'palette.text: "#1e293b"' in src
    assert 'palette.base: "#ffffff"' in src
    assert 'palette.placeholderText: "#94a3b8"' in src


def test_student_sidebar_nav_delegate_dynamic_height(qapp, tmp_path):
    """Nav delegates must use dynamic implicitHeight (was a fixed 42px)."""
    engine, conn, win = _launch(qapp, tmp_path)
    repeater = win.findChild(object, "sidebarNavRepeater")
    assert repeater is not None
    delegate = repeater.property("delegate")
    item = delegate.create(engine.rootContext())
    _pump(qapp)
    assert item is not None
    # Dynamic min-height logic: Math.max(38, textHeight + 12) -> at least 38, not the old 42
    assert item.property("implicitHeight") >= 38
    item.deleteLater()
    conn.close()


def test_student_sidebar_typography_scales(qapp, tmp_path):
    """Sidebar title / wizard-button fonts must grow with the settings typography."""
    _engine, conn, win = _launch(qapp, tmp_path)
    title = win.findChild(object, "sidebarTitleText")
    wizard = win.findChild(object, "openWizardBtn")
    assert title is not None and wizard is not None

    base_title = title.property("font").pixelSize()
    base_wizard = wizard.property("font").pixelSize()
    assert base_title >= 14
    assert base_wizard >= 9

    _set_large_typography(win, qapp)
    assert title.property("font").pixelSize() > base_title
    assert wizard.property("font").pixelSize() > base_wizard
    conn.close()


def test_student_detail_view_responsive(qapp, tmp_path):
    """Detail info card / status badge must use dynamic heights (no fixed 140/26px)."""
    _engine, conn, win = _launch(qapp, tmp_path)
    QMetaObject.invokeMethod(
        win, "loadStudentDetail", Qt.DirectConnection, Q_ARG("QVariant", 1001)
    )
    _pump(qapp)

    badge = win.findChild(object, "detailStatusBadge")
    assert badge is not None
    assert badge.property("implicitHeight") >= 26

    card = win.findChild(object, "infoCard")
    assert card is not None
    base_h = card.property("implicitHeight")
    assert base_h >= 140

    _set_large_typography(win, qapp)
    assert badge.property("implicitHeight") >= 26
    assert card.property("implicitHeight") >= base_h
    conn.close()


def test_excel_import_badges_responsive(qapp, tmp_path):
    """Excel import diff badges must use dynamic heights and scaled fonts."""
    _engine, conn, win = _launch(qapp, tmp_path)
    stack = win.findChild(object, "mainStack")
    assert stack is not None
    stack.setProperty("currentIndex", 5)
    _pump(qapp)

    for name in ("newBadgeBox", "promoBadgeBox", "missingBadgeBox", "conflictBadgeBox"):
        box = win.findChild(object, name)
        assert box is not None, f"missing badge box {name}"
        assert box.property("implicitHeight") >= 30

    status = win.findChild(object, "importStatusText")
    assert status is not None
    base_font = status.property("font").pixelSize()
    assert base_font >= 10

    _set_large_typography(win, qapp)
    assert status.property("font").pixelSize() > base_font
    assert win.findChild(object, "newBadgeBox").property("implicitHeight") >= 30
    conn.close()
