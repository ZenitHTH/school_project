"""Unit and QML UI tests for Librarian LAN Server configuration and Settings UI."""

import json, os, socket, sys, threading
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from core.network.booth_config import DEFAULT_BOOTH_TOKEN, DEFAULT_DISCOVERY_PORT, DEFAULT_LAN_PORT
from core.network.lan_client import BoothLanClient
from core.network.lan_discovery import LanDiscoveryResponder
from core.network.lan_manager import LanServiceManager
from core.network.lan_server_config import default_lan_server_config, load_lan_server_config, save_lan_server_config
from data.db import get_connection
from data.migrate import apply_migrations


@pytest.fixture(scope="session")
def qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def _flush(app):
    for _ in range(5):
        app.processEvents()


def _alloc_ports(count: int):
    sockets = [socket.socket(socket.AF_INET, socket.SOCK_STREAM) for _ in range(count)]
    try:
        for sock in sockets:
            sock.bind(("127.0.0.1", 0))
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


def _make_conn(tmp_path, name="lan_ui.sqlite"):
    db_path = str(tmp_path / name)
    conn = get_connection(db_path, pin="123456", check_same_thread=False)
    apply_migrations(conn, db_path=db_path)
    return conn


def test_lan_server_config_load_fallback_and_save_normalization(tmp_path):
    assert load_lan_server_config(str(tmp_path / "missing.json")) == default_lan_server_config()
    corrupt = tmp_path / "corrupt.json"
    for raw in ("{bad-json", "[1, 2, 3]"):
        corrupt.write_text(raw, encoding="utf-8")
        assert load_lan_server_config(str(corrupt)) == default_lan_server_config()

    cfg_path = str(tmp_path / "nested" / "lan_server_config.json")
    norm = save_lan_server_config(cfg_path, {"enabled": "yes", "port": 70000, "discovery_port": True, "token": "   "})
    assert norm == {"enabled": True, "port": DEFAULT_LAN_PORT, "discovery_port": DEFAULT_DISCOVERY_PORT, "token": DEFAULT_BOOTH_TOKEN}
    saved = save_lan_server_config(cfg_path, {"enabled": False, "port": 9101, "discovery_port": 9102, "token": "  kiosk-77  "})
    assert saved == {"enabled": False, "port": 9101, "discovery_port": 9102, "token": "kiosk-77"}
    assert load_lan_server_config(cfg_path) == saved


def test_lan_service_manager_apply_validate_disable_and_bind_errors(tmp_path, monkeypatch):
    conn = _make_conn(tmp_path)
    cfg_path = str(tmp_path / "lan_server_config.json")
    p1, u1, p2, u2, busy_p = _alloc_ports(5)
    mgr = LanServiceManager(conn, config_path=cfg_path, db_lock=threading.Lock())
    try:
        res1 = mgr.apply_config(True, p1, u1, "tok1")
        assert res1["ok"] and res1["running"] and res1["port"] == p1 and res1["discovery_port"] == u1
        c1 = BoothLanClient("127.0.0.1", p1, "tok1")
        assert c1.health()["ok"] is True
        c1.close()

        res2 = mgr.apply_config(True, p2, u2, "tok2")
        assert res2["ok"] and res2["running"] and res2["port"] == p2 and res2["discovery_port"] == u2
        c2 = BoothLanClient("127.0.0.1", p2, "tok2")
        try:
            assert c2.health()["ok"] is True
            for bad in [(True, 0, u2, "tok2"), (True, 70000, u2, "tok2"), (True, p2, p2, "tok2"), (True, p2, u2, "  ")]:
                err_res = mgr.apply_config(*bad)
                assert err_res["ok"] is False and err_res["error"]
            assert mgr.status_dict()["port"] == p2 and c2.health()["ok"] is True
            assert load_lan_server_config(cfg_path)["port"] == p2
        finally:
            c2.close()

        off_res = mgr.apply_config(False, p2, u2, "tok2")
        assert off_res["ok"] is True and off_res["running"] is False and off_res["enabled"] is False

        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("0.0.0.0", busy_p))
        blocker.listen(1)
        try:
            fail_res = mgr.apply_config(True, busy_p, u1, "tok3")
            assert fail_res["ok"] is False and fail_res["error"]
            assert mgr.lan_server is None and mgr.discovery_responder is None
        finally:
            blocker.close()

        monkeypatch.setattr(LanDiscoveryResponder, "start", lambda self: (_ for _ in ()).throw(OSError("udp blocked")))
        partial_fail = mgr.apply_config(True, p1, u1, "tok4")
        assert partial_fail["ok"] is False and "udp blocked" in partial_fail["error"]
        assert mgr.lan_server is None and mgr.discovery_responder is None
    finally:
        mgr.stop()
        conn.close()


def test_librarian_admin_adapter_lan_slots(tmp_path):
    conn = _make_conn(tmp_path, "adapter.sqlite")
    cfg_path = str(tmp_path / "lan_server_config.json")
    p1, u1 = _alloc_ports(2)
    mgr = LanServiceManager(conn, config_path=cfg_path, db_lock=threading.Lock())
    adapter = LibrarianAdminAdapter(conn, lan_manager=mgr, lan_config_path=cfg_path)
    try:
        res = json.loads(adapter.saveAndApplyLanConfig(True, p1, u1, "adm-tok"))
        assert res["ok"] is True and res["running"] is True and res["port"] == p1
        cfg = json.loads(adapter.getLanConfig())
        assert cfg["port"] == p1 and cfg["discovery_port"] == u1 and cfg["token"] == "adm-tok"
        info = json.loads(adapter.getLanServerInfo())
        assert set(info.keys()) == {"running", "ip", "port", "token"}
        assert info["running"] is True and info["port"] == p1 and info["token"] == "adm-tok"
        off = json.loads(adapter.saveAndApplyLanConfig(False, p1, u1, "adm-tok"))
        assert off["ok"] is True and off["running"] is False
        assert json.loads(adapter.getLanServerInfo()) == {"running": False, "ip": "", "port": 0, "token": ""}
    finally:
        mgr.stop()
        conn.close()


def test_settings_view_standalone_hides_lan_card(qapp):
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.load(os.path.abspath("apps/common_qml/SettingsView.qml"))
    _flush(qapp)
    root = engine.rootObjects()[0]
    assert root.property("showLanServerCard") is False
    lan_card = root.findChild(QObject, "lanServerCard")
    assert lan_card is not None and lan_card.property("visible") is False


def test_librarian_qml_lan_settings_live_flow(qapp, tmp_path):
    conn = _make_conn(tmp_path, "qml_lan.sqlite")
    cfg_path = str(tmp_path / "lan_server_config.json")
    p1, u1, p2, u2 = _alloc_ports(4)
    mgr = LanServiceManager(conn, config_path=cfg_path, db_lock=threading.Lock())
    assert mgr.apply_config(True, p1, u1, "tok1")["ok"] is True
    adapter = LibrarianAdminAdapter(conn, lan_server=mgr.lan_server, lan_manager=mgr)
    engine = QQmlApplicationEngine()
    try:
        engine.rootContext().setContextProperty("librarianAdmin", adapter)
        engine.addImportPath(os.path.abspath("apps"))
        engine.load(os.path.abspath("apps/librarian_management_app/qml/Main.qml"))
        _flush(qapp)
        win = engine.rootObjects()[0]
        win.findChild(QObject, "navBtnSettings").clicked.emit()
        _flush(qapp)

        card = win.findChild(QObject, "lanServerCard")
        assert card is not None and card.property("visible") is True
        badge = card.findChild(QObject, "lanStatusBadgeText")
        ip_lbl = card.findChild(QObject, "lanIpValueText")
        ep_lbl = card.findChild(QObject, "lanEndpointValueText")
        status_txt = card.findChild(QObject, "lanSaveStatusText")
        assert badge.property("text") == "● กำลังทำงาน (Online)"
        assert ip_lbl.property("text") not in ("", "-")
        assert ep_lbl.property("text") == f"http://{ip_lbl.property('text')}:{p1}"

        card.findChild(QObject, "lanPortInput").setProperty("text", str(p2))
        card.findChild(QObject, "lanDiscoveryPortInput").setProperty("text", str(u2))
        card.findChild(QObject, "lanTokenInput").setProperty("text", "tok2")
        card.findChild(QObject, "btnSaveLanConfig").clicked.emit()
        _flush(qapp)
        assert status_txt.property("text").startswith("✓")
        assert ep_lbl.property("text") == f"http://{ip_lbl.property('text')}:{p2}"
        assert load_lan_server_config(cfg_path) == {"enabled": True, "port": p2, "discovery_port": u2, "token": "tok2"}

        card.findChild(QObject, "lanTokenInput").setProperty("text", "")
        card.findChild(QObject, "btnSaveLanConfig").clicked.emit()
        _flush(qapp)
        assert status_txt.property("text").startswith("✗") and badge.property("text") == "● กำลังทำงาน (Online)"

        card.findChild(QObject, "lanEnabledCheck").setProperty("checked", False)
        card.findChild(QObject, "lanTokenInput").setProperty("text", "tok2")
        card.findChild(QObject, "btnSaveLanConfig").clicked.emit()
        _flush(qapp)
        assert badge.property("text") == "○ ปิดใช้งาน (Disabled)" and ep_lbl.property("text") == "ไม่ได้เปิดให้บริการ"
    finally:
        del engine
        mgr.stop()
        conn.close()
