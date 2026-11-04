"""
tests/test_adversarial_settings_and_placeholders.py
Adversarial QA stress harness probing edge cases in SettingsService,
adapter slot boundaries, file I/O corruption, and UI placeholder rendering.
"""
import os
import sys
import json
import threading
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject

from data.db import get_connection
from data.migrate import apply_migrations
from core.shared.settings_service import SettingsService, DEFAULT_SETTINGS
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter


@pytest.fixture(scope="session")
def qapp():
    QQuickStyle.setStyle("Fusion")
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def test_corrupted_json_recovery(tmp_path):
    """Verify SettingsService returns defaults when disk file is corrupted or malformed."""
    cfg_file = tmp_path / "corrupted.json"
    svc = SettingsService(storage_path=str(cfg_file))

    for junk in (b"", b"not a json", b'{"font_size": ', b"null", b"[1, 2, 3]"):
        cfg_file.write_bytes(junk)
        loaded = svc.load_settings()
        assert loaded["font_size"] == DEFAULT_SETTINGS["font_size"]
        assert loaded["font_family"] == DEFAULT_SETTINGS["font_family"]
        assert loaded["ui_scale"] == DEFAULT_SETTINGS["ui_scale"]


def test_unwritable_path_graceful_result(tmp_path):
    """Verify SettingsService returns Err when path is unwritable instead of raising."""
    bad_dir = tmp_path / "readonly_dir"
    bad_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(str(bad_dir), 0o444)
    cfg_file = bad_dir / "unwritable.json"

    svc = SettingsService(storage_path=str(cfg_file))
    res = svc.save_settings({"font_family": "Noto Sans"})
    os.chmod(str(bad_dir), 0o777)
    assert res.ok is False or cfg_file.exists()


def test_concurrent_settings_read_write(tmp_path):
    """Verify concurrent reads and writes from multiple threads do not crash."""
    cfg_file = tmp_path / "concurrent.json"
    svc = SettingsService(storage_path=str(cfg_file))
    errors = []

    def worker(idx: int):
        try:
            for i in range(20):
                svc.save_settings({"font_family": f"Font-{idx}", "font_size": 10 + (i % 10)})
                svc.load_settings()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(errors) == 0


def test_adapter_adversarial_settings_inputs(tmp_path):
    """Verify adapter slots handle malformed/edge inputs without unhandled exceptions."""
    conn = get_connection(str(tmp_path / "adv.sqlite"), pin="123456")
    apply_migrations(conn)
    adapters = [StudentAdminAdapter(conn), LibrarianAdminAdapter(conn)]

    for adapter in adapters:
        # None/empty/unusual arguments
        res1 = json.loads(adapter.saveSettings("", 0, 0.0))
        assert res1.get("ok") is True
        res2 = json.loads(adapter.saveSettings("Custom Font 🚀", 999, 99.9))
        assert res2.get("ok") is True
        assert json.loads(adapter.resetSettings()).get("ok") is True
        loaded = json.loads(adapter.loadSettings())
        assert loaded.get("data", loaded).get("font_size") == 14
    conn.close()


def _launch_app_and_get_settings(qml_path: str, adapter_name: str, adapter: QObject):
    """Helper to launch application QML and locate its SettingsView."""
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.rootContext().setContextProperty(adapter_name, adapter)
    engine.load(os.path.abspath(qml_path))
    win = engine.rootObjects()[0]
    return engine, win, win.findChild(object, "settingsView")


def test_librarian_app_settings_persistence_flow(qapp, tmp_path):
    """Verify end-to-end settings persistence in Librarian App across engine reloads."""
    cfg_file = tmp_path / "lib_persist.json"
    conn = get_connection(str(tmp_path / "lib_persist.sqlite"), pin="123456")
    apply_migrations(conn)
    adapter1 = LibrarianAdminAdapter(conn, settings_service=SettingsService(str(cfg_file)))
    adapter1.saveSettings("Noto Sans", 19, 1.25)

    adapter2 = LibrarianAdminAdapter(conn, settings_service=SettingsService(str(cfg_file)))
    engine, win, settings = _launch_app_and_get_settings(
        "apps/librarian_management_app/qml/Main.qml", "librarianAdmin", adapter2
    )
    qapp.processEvents()
    assert settings.property("currentFontSize") == 19
    assert abs(settings.property("currentUiScale") - 1.25) < 0.01
    conn.close()


def test_student_app_settings_persistence_flow(qapp, tmp_path):
    """Verify end-to-end settings persistence in Student App across engine reloads."""
    cfg_file = tmp_path / "stu_persist.json"
    conn = get_connection(str(tmp_path / "stu_persist.sqlite"), pin="123456")
    apply_migrations(conn)
    adapter1 = StudentAdminAdapter(conn, settings_service=SettingsService(str(cfg_file)))
    adapter1.saveSettings("Sarabun", 16, 1.1)

    adapter2 = StudentAdminAdapter(conn, settings_service=SettingsService(str(cfg_file)))
    engine, win, settings = _launch_app_and_get_settings(
        "apps/student_management_app/qml/Main.qml", "studentAdmin", adapter2
    )
    qapp.processEvents()
    assert settings.property("currentFontSize") == 16
    assert abs(settings.property("currentUiScale") - 1.1) < 0.01
    conn.close()


def test_dialog_inputs_adversarial_downscaling_resilience(qapp):
    """Verify all dialog inputs retain Layout.fillWidth and min height under 0.35x downscale."""
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.load(os.path.abspath("apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml"))
    root = engine.rootObjects()[0]

    for name in ["newBookTitle", "newBookIsbn", "newBookAuthor", "newBookBarcodes"]:
        item = root.findChild(object, name)
        font = item.property("font")
        font.setPixelSize(5)
        item.setProperty("font", font)
        qapp.processEvents()
        assert item.property("implicitHeight") >= 36
        att = [c for c in item.children() if c.metaObject().className() == "QQuickLayoutAttached"]
        assert len(att) > 0 and att[0].property("fillWidth") is True
