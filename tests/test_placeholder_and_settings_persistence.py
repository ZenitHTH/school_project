"""
tests/test_placeholder_and_settings_persistence.py
Reproduction and regression test suite for:
  1. Placeholder visibility, sizing, and Layout.fillWidth in dialogs and StyledSearchField.
  2. Settings persistence feature via SettingsService and adapter slots.
"""
import os
import sys
import json
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject

from data.db import get_connection
from data.migrate import apply_migrations
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter


@pytest.fixture(scope="session")
def qapp():
    QQuickStyle.setStyle("Fusion")
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def _has_layout_fill_width(item: QObject) -> bool:
    """Return True if item has Layout.fillWidth attached and set to True."""
    for child in item.children():
        if child.metaObject().className() == "QQuickLayoutAttached":
            return bool(child.property("fillWidth"))
    return False


def _create_engine(extra_context: dict = None) -> QQmlApplicationEngine:
    """Instantiate a QQmlApplicationEngine with apps import paths and context properties."""
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    if extra_context:
        ctx = engine.rootContext()
        for key, val in extra_context.items():
            ctx.setContextProperty(key, val)
    return engine


def _get_settings_service_cls():
    """Import and return the SettingsService class."""
    try:
        from core.shared.settings_service import SettingsService
        return SettingsService
    except ImportError:
        from core.settings.settings_service import SettingsService
        return SettingsService


def _verify_adapter_persistence(adapter: QObject) -> None:
    """Verify save, load, and reset cycle on an adapter instance."""
    cls_name = adapter.__class__.__name__
    for slot_name in ("saveSettings", "loadSettings", "resetSettings"):
        assert hasattr(adapter, slot_name), f"{cls_name} missing {slot_name} slot"

    assert json.loads(adapter.saveSettings("Noto Sans", 18, 1.25)).get("ok") is True
    loaded = json.loads(adapter.loadSettings())
    data = loaded.get("data", loaded)
    assert data.get("font_family") == "Noto Sans" and data.get("font_size") == 18

    assert json.loads(adapter.resetSettings()).get("ok") is True
    restored = json.loads(adapter.loadSettings()).get("data", {})
    assert restored.get("font_size") == 14


def test_styled_search_field_sizing_and_padding(qapp):
    """Verify StyledSearchField has minimum implicitWidth, implicitHeight, and padding."""
    engine = _create_engine()
    engine.load(os.path.abspath("apps/common_qml/StyledSearchField.qml"))
    assert len(engine.rootObjects()) > 0
    field = engine.rootObjects()[0]

    assert field.property("implicitWidth") >= 180, "StyledSearchField collapsed width"
    assert field.property("implicitHeight") >= 38, "StyledSearchField insufficient height"
    assert field.property("leftPadding") >= 8, "Left padding too small for text"
    assert field.property("rightPadding") >= 8, "Right padding too small for text"


def test_styled_search_field_extreme_downscaling(qapp):
    """Verify StyledSearchField maintains minimum dimensions under extreme 0.35x downscaling."""
    engine = _create_engine()
    engine.load(os.path.abspath("apps/common_qml/StyledSearchField.qml"))
    field = engine.rootObjects()[0]

    font = field.property("font")
    font.setPixelSize(5)
    field.setProperty("font", font)
    qapp.processEvents()

    assert field.property("implicitHeight") >= 36, "Height collapsed under 0.35x scaling"
    assert field.property("implicitWidth") >= 120, "Width collapsed under 0.35x scaling"


def test_student_dialogs_inputs_fill_width_and_height(qapp):
    """Verify text fields in StudentActionDialogs have Layout.fillWidth and minimum height."""
    engine = _create_engine()
    engine.load(os.path.abspath("apps/student_management_app/qml/dialogs/StudentActionDialogs.qml"))
    assert len(engine.rootObjects()) > 0
    root = engine.rootObjects()[0]

    field_names = ["newRoomInput", "roomReasonInput", "statusReasonInput", "editFirstNameInput", "newIdInput"]
    for name in field_names:
        item = root.findChild(object, name)
        assert item is not None, f"Field {name} not found"
        assert _has_layout_fill_width(item), f"{name} missing Layout.fillWidth: true"
        assert item.property("implicitHeight") >= 36, f"{name} implicitHeight too small"


def test_book_dialogs_inputs_fill_width_and_height(qapp):
    """Verify text fields in BookActionDialogs have Layout.fillWidth and minimum height."""
    engine = _create_engine()
    engine.load(os.path.abspath("apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml"))
    assert len(engine.rootObjects()) > 0
    root = engine.rootObjects()[0]

    field_names = ["newBookTitle", "newBookIsbn", "newBookAuthor", "newBookBarcodes"]
    for name in field_names:
        item = root.findChild(object, name)
        assert item is not None, f"Field {name} not found"
        assert _has_layout_fill_width(item), f"{name} missing Layout.fillWidth: true"
        assert item.property("implicitHeight") >= 36, f"{name} implicitHeight too small"


def test_settings_service_disk_persistence(tmp_path):
    """Verify SettingsService persists settings to disk and restores them."""
    cls = _get_settings_service_cls()
    cfg_file = tmp_path / "app_settings.json"
    svc = cls(storage_path=str(cfg_file))

    assert svc.save_settings({"font_family": "Noto Sans", "font_size": 18, "ui_scale": 1.25}).ok
    assert cfg_file.exists()

    svc2 = cls(storage_path=str(cfg_file))
    loaded = svc2.load_settings()
    assert loaded["font_family"] == "Noto Sans" and loaded["font_size"] == 18

    assert svc2.reset_settings().ok
    restored = svc2.load_settings()
    assert restored["font_size"] == 14 and abs(restored["ui_scale"] - 1.0) < 0.01


def test_student_adapter_settings_slots(tmp_path):
    """Verify student adapter exposes settings persistence slots."""
    conn = get_connection(str(tmp_path / "student.sqlite"), pin="123456")
    apply_migrations(conn)
    adapter = StudentAdminAdapter(conn)
    _verify_adapter_persistence(adapter)
    conn.close()


def test_librarian_adapter_settings_slots(tmp_path):
    """Verify librarian adapter exposes settings persistence slots."""
    conn = get_connection(str(tmp_path / "librarian.sqlite"), pin="123456")
    apply_migrations(conn)
    adapter = LibrarianAdminAdapter(conn)
    _verify_adapter_persistence(adapter)
    conn.close()


def test_settings_view_auto_loads_persisted_settings(qapp, tmp_path):
    """Verify SettingsView loads persisted settings on creation when adapter is present."""
    conn = get_connection(str(tmp_path / "lib.sqlite"), pin="123456")
    apply_migrations(conn)
    adapter = LibrarianAdminAdapter(conn)
    if hasattr(adapter, "saveSettings"):
        adapter.saveSettings("Noto Sans", 20, 1.25)

    engine = _create_engine({"librarianAdmin": adapter})
    engine.load(os.path.abspath("apps/common_qml/SettingsView.qml"))
    assert len(engine.rootObjects()) > 0
    root = engine.rootObjects()[0]
    qapp.processEvents()

    assert root.property("currentFontSize") == 20, "SettingsView did not load persisted font size"
    assert abs(root.property("currentUiScale") - 1.25) < 0.01, "SettingsView did not load persisted ui scale"
    assert root.property("currentFontFamily") == "Noto Sans", "SettingsView did not load persisted font family"
    conn.close()
