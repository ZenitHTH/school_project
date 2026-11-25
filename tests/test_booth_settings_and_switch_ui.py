"""Unit and QML UI tests for Booth System Settings and Connect/Switch Server UI."""

import json
import os
import sqlite3
import sys
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from apps.booth_app.adapters.booth_adapter import BoothAdapter
from core.network.booth_config import load_booth_config
from core.network.lan_client import BoothLanClient
from core.network.lan_server import BoothLanServer
from core.shared.mock_qt import apply_qt_app_font
from core.shared.settings_service import SettingsService
from data.migrate import apply_migrations
from data.repositories import book_repo


@pytest.fixture(scope="session")
def qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def _flush(app):
    for _ in range(5):
        app.processEvents()


def _make_seeded_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    apply_migrations(conn)
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(3001, 'นักเรียน ทดสอบ', 'active')"
    )
    conn.commit()
    book_id = book_repo.add_book(conn, title="คู่มือ LAN", author="ผู้แต่ง", isbn="978-1")
    book_repo.add_copies(conn, book_id, barcodes=["BK-001"])
    return conn


def test_booth_adapter_visual_settings_persistence(qapp, tmp_path):
    settings_path = str(tmp_path / "settings.json")
    adapter = BoothAdapter(
        client=BoothLanClient(host="127.0.0.1", port=1, token="tok"),
        settings_service=SettingsService(settings_path),
        auto_discover=False,
    )
    try:
        initial = json.loads(adapter.loadSettings())
        assert initial == {
            "ok": True,
            "data": {"font_family": "System Default", "font_size": 14, "ui_scale": 1.0},
        }

        saved = json.loads(adapter.saveSettings("Noto Sans", 18, 1.25))
        assert saved["ok"] is True
        assert os.path.exists(settings_path)
        loaded = json.loads(adapter.loadSettings())
        assert loaded["data"] == {"font_family": "Noto Sans", "font_size": 18, "ui_scale": 1.25}

        adapter.setAppFont("Noto Sans", 18)
        assert qapp.font().pixelSize() == 18

        reset_res = json.loads(adapter.resetSettings())
        assert reset_res["ok"] is True
        assert json.loads(adapter.loadSettings())["data"] == {
            "font_family": "System Default",
            "font_size": 14,
            "ui_scale": 1.0,
        }
    finally:
        apply_qt_app_font("", 14)
        adapter.close()


def test_settings_view_standalone_hides_lan_client_card(qapp):
    engine = QQmlApplicationEngine()
    try:
        engine.addImportPath(os.path.abspath("apps"))
        engine.addImportPath(os.path.abspath("apps/common_qml"))
        engine.load(os.path.abspath("apps/common_qml/SettingsView.qml"))
        _flush(qapp)
        root = engine.rootObjects()[0]
        assert root.property("showLanClientCard") is False
        lan_client_card = root.findChild(QObject, "lanClientCard")
        assert lan_client_card is not None
        assert lan_client_card.property("visible") is False
    finally:
        engine.deleteLater()
        _flush(qapp)


def test_booth_settings_and_switch_server_end_to_end(qapp, tmp_path, monkeypatch):
    conn_a, conn_b = _make_seeded_conn(), _make_seeded_conn()
    server_a = BoothLanServer(conn_a, host="127.0.0.1", port=0, token="tok-a")
    server_b = BoothLanServer(conn_b, host="127.0.0.1", port=0, token="tok-b")
    server_a.start()
    server_b.start()

    cfg_path = str(tmp_path / "booth_config.json")
    settings_path = str(tmp_path / "settings.json")
    adapter = BoothAdapter(
        client=BoothLanClient(host="127.0.0.1", port=server_a.port, token="tok-a"),
        config_path=cfg_path,
        settings_service=SettingsService(settings_path),
        auto_discover=False,
    )
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend([w.toString() for w in ws]))
    try:
        engine.addImportPath(os.path.abspath("apps/common_qml"))
        engine.addImportPath(os.path.abspath("apps"))
        engine.rootContext().setContextProperty("boothAdapter", adapter)
        engine.load(os.path.abspath("apps/booth_app/qml/Main.qml"))
        assert len(engine.rootObjects()) > 0
        win = engine.rootObjects()[0]
        _flush(qapp)

        win.findChild(QObject, "btnOpenBoothSettings").clicked.emit()
        _flush(qapp)

        kiosk_stack = win.findChild(QObject, "kioskStack")
        settings_view = win.findChild(QObject, "boothSettingsView")
        client_card = settings_view.findChild(QObject, "lanClientCard")
        server_card = settings_view.findChild(QObject, "lanServerCard")
        assert kiosk_stack.property("currentIndex") == 1
        assert settings_view.property("visible") is True
        assert client_card.property("visible") is True
        assert server_card.property("visible") is False

        settings_view.findChild(QObject, "fontSizeSlider").setProperty("value", 18)
        _flush(qapp)
        settings_view.findChild(QObject, "btnSaveSettings").clicked.emit()
        _flush(qapp)
        assert SettingsService(settings_path).load_settings()["font_size"] == 18

        monkeypatch.setattr(
            "apps.booth_app.adapters.booth_adapter.discover_librarian",
            lambda: {"host": "127.0.0.1", "port": server_b.port, "version": "1.0"},
        )
        client_card.findChild(QObject, "btnDiscoverClientServer").clicked.emit()
        _flush(qapp)
        assert client_card.findChild(QObject, "lanDiscoverFeedbackText").property("text").startswith("✓ พบเซิร์ฟเวอร์")
        assert client_card.findChild(QObject, "lanClientHostInput").property("text") == "127.0.0.1"
        assert client_card.findChild(QObject, "lanClientPortInput").property("text") == str(server_b.port)

        client_card.findChild(QObject, "lanClientTokenInput").setProperty("text", "tok-b")
        client_card.findChild(QObject, "btnConnectSwitchServer").clicked.emit()
        _flush(qapp)
        assert client_card.findChild(QObject, "lanClientSaveStatusText").property("text").startswith("✓ เชื่อมต่อเซิร์ฟเวอร์")
        assert f"http://127.0.0.1:{server_b.port}" in client_card.findChild(QObject, "lanClientEndpointText").property("text")
        assert load_booth_config(cfg_path) == {"host": "127.0.0.1", "port": server_b.port, "token": "tok-b"}

        client_card.findChild(QObject, "lanClientHostInput").setProperty("text", "")
        client_card.findChild(QObject, "btnConnectSwitchServer").clicked.emit()
        _flush(qapp)
        assert client_card.findChild(QObject, "lanClientSaveStatusText").property("text").startswith("✗")
        assert load_booth_config(cfg_path) == {"host": "127.0.0.1", "port": server_b.port, "token": "tok-b"}

        win.findChild(QObject, "btnBackToKiosk").clicked.emit()
        _flush(qapp)
        assert kiosk_stack.property("currentIndex") == 0
        assert f"เชื่อมต่อเซิร์ฟเวอร์: 127.0.0.1:{server_b.port}" in win.findChild(QObject, "lanStatusText").property("text")

        ref_errors = [w for w in warnings if "ReferenceError" in w or "TypeError" in w]
        assert not ref_errors, f"Unexpected QML errors: {ref_errors}"
    finally:
        apply_qt_app_font("", 14)
        engine.deleteLater()
        _flush(qapp)
        adapter.close()
        server_a.stop()
        server_b.stop()
        conn_a.close()
        conn_b.close()
