"""Tests for BoothAdapter LAN mode, booth_app config loading, and LAN UI slots."""

import json
import sqlite3

import pytest

from core.network.booth_config import DEFAULT_BOOTH_TOKEN, DEFAULT_LAN_PORT, load_booth_config
from core.network.lan_client import BoothLanClient
from core.network.lan_server import BoothLanServer
from data.migrate import apply_migrations
from data.repositories import book_repo


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
    book_id = book_repo.add_book(conn, title="คู่มือ LAN", author=None, isbn=None)
    book_repo.add_copies(conn, book_id, barcodes=["BK-001"])
    return conn


@pytest.fixture
def live_server():
    conn = _make_seeded_conn()
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="secret-tok")
    server.start()
    yield server, conn
    server.stop()
    conn.close()


def test_booth_adapter_lan_mode_end_to_end(live_server, tmp_path):
    from apps.booth_app.adapters.booth_adapter import BoothAdapter

    server, _ = live_server
    cfg_path = str(tmp_path / "booth_config.json")
    client = BoothLanClient(host="127.0.0.1", port=server.port, token="secret-tok")
    adapter = BoothAdapter(client=client, config_path=cfg_path)
    try:
        status = json.loads(adapter.getConnectionStatus())
        assert status["connected"] is True
        assert status["mode"] == "lan"
        assert status["host"] == "127.0.0.1"
        assert status["port"] == server.port
        assert status["error"] == ""

        assert adapter.isDatabaseEmpty() is False

        students = json.loads(adapter.searchStudents("3001"))
        assert len(students) == 1
        assert students[0]["student_id"] == 3001

        copy_res = json.loads(adapter.getCopyByBarcode("BK-001"))
        assert copy_res["ok"] is True
        assert copy_res["data"]["author"] == ""
        assert copy_res["data"]["isbn"] == ""

        co_res = json.loads(adapter.checkout(3001, "BK-001"))
        assert co_res["ok"] is True
        loan_id = co_res["data"]["loan_id"]

        ret_res = json.loads(adapter.returnByBarcode("BK-001"))
        assert ret_res["ok"] is True
        assert ret_res["data"]["loan_id"] == loan_id

        co_res2 = json.loads(adapter.checkout(3001, "BK-001"))
        assert co_res2["ok"] is True
        ret_res2 = json.loads(adapter.returnBook(co_res2["data"]["loan_id"]))
        assert ret_res2["ok"] is True
    finally:
        adapter.close()


def test_booth_adapter_configure_connection_persists_and_swaps(live_server, tmp_path):
    from apps.booth_app.adapters.booth_adapter import BoothAdapter

    server, _ = live_server
    cfg_path = str(tmp_path / "booth_config.json")
    offline_client = BoothLanClient(host="", port=DEFAULT_LAN_PORT, token=DEFAULT_BOOTH_TOKEN)
    adapter = BoothAdapter(client=offline_client, config_path=cfg_path, auto_discover=False)
    try:
        before = json.loads(adapter.getConnectionStatus())
        assert before["connected"] is False
        assert before["mode"] == "lan"
        assert before["error"] != ""

        after = json.loads(adapter.configureConnection("127.0.0.1", server.port, "secret-tok"))
        assert after["connected"] is True
        assert after["host"] == "127.0.0.1"
        assert after["port"] == server.port
        assert after["mode"] == "lan"
        assert load_booth_config(cfg_path) == {
            "host": "127.0.0.1",
            "port": server.port,
            "token": "secret-tok",
        }

        students = json.loads(adapter.searchStudents("3001"))
        assert len(students) == 1
    finally:
        adapter.close()


def test_booth_adapter_blank_token_preserves_existing_token(live_server, tmp_path):
    from apps.booth_app.adapters.booth_adapter import BoothAdapter

    server, _ = live_server
    cfg_path = str(tmp_path / "booth_config.json")
    client = BoothLanClient(host="", port=DEFAULT_LAN_PORT, token="secret-tok")
    adapter = BoothAdapter(client=client, config_path=cfg_path)
    try:
        res = json.loads(adapter.configureConnection("127.0.0.1", server.port, ""))
        assert res["connected"] is True
        assert adapter.client.token == "secret-tok"
        assert load_booth_config(cfg_path)["token"] == "secret-tok"

        res_ws = json.loads(adapter.configureConnection("127.0.0.1", server.port, "   "))
        assert res_ws["connected"] is True
        assert adapter.client.token == "secret-tok"
    finally:
        adapter.close()


def test_booth_adapter_discover_server(monkeypatch):
    from apps.booth_app.adapters.booth_adapter import BoothAdapter

    client = BoothLanClient(host="", port=DEFAULT_LAN_PORT, token=DEFAULT_BOOTH_TOKEN)
    adapter = BoothAdapter(client=client)

    monkeypatch.setattr(
        "apps.booth_app.adapters.booth_adapter.discover_librarian",
        lambda: {"host": "192.168.1.25", "port": 8765, "version": "1.0.0"},
    )
    found = json.loads(adapter.discoverServer())
    assert found == {"ok": True, "host": "192.168.1.25", "port": 8765}

    monkeypatch.setattr(
        "apps.booth_app.adapters.booth_adapter.discover_librarian",
        lambda: None,
    )
    missing = json.loads(adapter.discoverServer())
    assert missing == {"ok": False, "host": "", "port": 0}
    adapter.close()


def test_booth_adapter_local_mode_connection_status():
    from apps.booth_app.adapters.booth_adapter import BoothAdapter

    conn = _make_seeded_conn()
    adapter = BoothAdapter(conn)
    try:
        status = json.loads(adapter.getConnectionStatus())
        assert status["connected"] is True
        assert status["mode"] == "local"
        assert status["error"] == ""
    finally:
        conn.close()


def test_booth_main_resolves_env_and_discovery(tmp_path, monkeypatch):
    from apps.booth_app.main import resolve_booth_lan_config

    cfg_path = str(tmp_path / "booth_config.json")
    monkeypatch.delenv("BOOTH_SERVER_HOST", raising=False)
    monkeypatch.delenv("BOOTH_SERVER_PORT", raising=False)
    monkeypatch.delenv("BOOTH_SERVER_TOKEN", raising=False)
    monkeypatch.setattr(
        "apps.booth_app.main.discover_librarian",
        lambda: {"host": "10.0.0.5", "port": 8770, "version": "1.0.0"},
    )
    cfg = resolve_booth_lan_config(cfg_path)
    assert cfg == {"host": "10.0.0.5", "port": 8770, "token": DEFAULT_BOOTH_TOKEN}

    monkeypatch.setenv("BOOTH_SERVER_HOST", "192.168.10.2")
    monkeypatch.setenv("BOOTH_SERVER_PORT", "9090")
    monkeypatch.setenv("BOOTH_SERVER_TOKEN", "env-tok")
    cfg_env = resolve_booth_lan_config(cfg_path)
    assert cfg_env == {"host": "192.168.10.2", "port": 9090, "token": "env-tok"}


def test_booth_qml_lan_banner_and_settings_dialog(live_server, tmp_path, monkeypatch):
    import os
    import sys
    from PySide6.QtCore import QMetaObject, QObject, Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from apps.booth_app.adapters.booth_adapter import BoothAdapter

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    server, _ = live_server
    cfg_path = str(tmp_path / "booth_config.json")
    adapter = BoothAdapter(
        client=BoothLanClient(host="", port=DEFAULT_LAN_PORT, token=DEFAULT_BOOTH_TOKEN),
        config_path=cfg_path,
        auto_discover=False,
    )
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend([w.toString() for w in ws]))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
    engine.rootContext().setContextProperty("boothAdapter", adapter)
    engine.load(os.path.abspath("apps/booth_app/qml/Main.qml"))
    assert len(engine.rootObjects()) > 0
    window = engine.rootObjects()[0]
    app.processEvents()

    for name in (
        "lanStatusBanner", "btnLanSettings", "lanSettingsDialog",
        "lanHostInput", "lanPortInput", "lanTokenInput", "btnAutoDiscover",
    ):
        assert window.findChild(QObject, name) is not None, f"Missing {name}"

    status_text = window.findChild(QObject, "lanStatusText").property("text")
    assert "ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์" in status_text

    monkeypatch.setattr(
        "apps.booth_app.adapters.booth_adapter.discover_librarian",
        lambda: {"host": "127.0.0.1", "port": server.port, "version": "1.0.0"},
    )
    QMetaObject.invokeMethod(window, "openLanSettings", Qt.DirectConnection)
    assert window.findChild(QObject, "lanTokenInput").property("text") == ""
    QMetaObject.invokeMethod(window, "runAutoDiscover", Qt.DirectConnection)
    window.findChild(QObject, "lanTokenInput").setProperty("text", "secret-tok")
    QMetaObject.invokeMethod(window, "applyLanSettings", Qt.DirectConnection)
    app.processEvents()

    assert "เชื่อมต่อเซิร์ฟเวอร์: 127.0.0.1" in window.findChild(QObject, "lanStatusText").property("text")

    QMetaObject.invokeMethod(window, "openLanSettings", Qt.DirectConnection)
    assert window.findChild(QObject, "lanTokenInput").property("text") == ""
    QMetaObject.invokeMethod(window, "applyLanSettings", Qt.DirectConnection)
    app.processEvents()
    assert adapter.client.token == "secret-tok"
    assert "เชื่อมต่อเซิร์ฟเวอร์: 127.0.0.1" in window.findChild(QObject, "lanStatusText").property("text")
    ref_errors = [w for w in warnings if "ReferenceError" in w or "TypeError" in w]
    assert not ref_errors, f"Unexpected QML errors: {ref_errors}"

    adapter.close()
    engine.deleteLater()
    app.processEvents()


def test_booth_adapter_auto_rediscovers_when_server_starts_later_or_ip_changes(tmp_path, monkeypatch):
    from apps.booth_app.adapters.booth_adapter import BoothAdapter

    cfg_path = str(tmp_path / "booth_config.json")
    dead_client = BoothLanClient(host="127.0.0.1", port=1, token="tok")
    adapter = BoothAdapter(client=dead_client, config_path=cfg_path, auto_discover=True)
    conn = _make_seeded_conn()
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="tok")
    server.start()
    try:
        monkeypatch.setattr(
            "apps.booth_app.adapters.booth_adapter.discover_librarian",
            lambda timeout=0.4: {"host": "127.0.0.1", "port": server.port, "version": "1.0"},
        )
        status = json.loads(adapter.getConnectionStatus())
        assert status["connected"] is True
        assert status["port"] == server.port
        assert load_booth_config(cfg_path) == {
            "host": "127.0.0.1",
            "port": server.port,
            "token": "tok",
        }
    finally:
        adapter.close()
        server.stop()
        conn.close()


def test_booth_qml_has_lan_reconnect_timer():
    import os
    import sys
    from PySide6.QtCore import QObject
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from apps.booth_app.adapters.booth_adapter import BoothAdapter

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    adapter = BoothAdapter(
        client=BoothLanClient(host="", port=DEFAULT_LAN_PORT, token=DEFAULT_BOOTH_TOKEN),
        auto_discover=False,
    )
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
    engine.rootContext().setContextProperty("boothAdapter", adapter)
    engine.load(os.path.abspath("apps/booth_app/qml/Main.qml"))
    assert len(engine.rootObjects()) > 0
    window = engine.rootObjects()[0]
    timer = window.findChild(QObject, "lanReconnectTimer")
    assert timer is not None
    assert timer.property("interval") == 5000
    adapter.close()
    engine.deleteLater()
    app.processEvents()


def _make_catalog_conn() -> tuple[sqlite3.Connection, int, int]:
    conn = _make_seeded_conn()
    cat_sci = book_repo.add_category(conn, "วิทยาศาสตร์")
    cat_math = book_repo.add_category(conn, "คณิตศาสตร์")
    b1 = book_repo.add_book(
        conn,
        title="เคมี ม.ปลาย",
        author="ดร.อารีย์",
        isbn="978-333",
        category_id=cat_sci,
        shelf_location="C-01",
    )
    book_repo.add_copies(conn, b1, barcodes=["CHM-001"])
    b2 = book_repo.add_book(
        conn,
        title="เรขาคณิตวิเคราะห์",
        author=None,
        isbn=None,
        category_id=cat_math,
        shelf_location=None,
    )
    book_repo.add_copies(conn, b2, barcodes=["GEO-001"])
    return conn, cat_sci, cat_math


def test_adapter_list_categories_local_and_lan():
    from apps.booth_app.adapters.booth_adapter import BoothAdapter

    conn, cat_sci, cat_math = _make_catalog_conn()
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="secret-tok")
    server.start()
    local_adapter = BoothAdapter(conn=conn)
    lan_adapter = BoothAdapter(
        client=BoothLanClient(host="127.0.0.1", port=server.port, token="secret-tok"),
        auto_discover=False,
    )
    try:
        for adapter in (local_adapter, lan_adapter):
            cats = json.loads(adapter.listCategories())
            assert [c["name"] for c in cats] == ["คณิตศาสตร์", "วิทยาศาสตร์"]
            ids = {c["name"]: c["category_id"] for c in cats}
            assert ids["วิทยาศาสตร์"] == cat_sci
            assert ids["คณิตศาสตร์"] == cat_math
    finally:
        lan_adapter.close()
        server.stop()
        conn.close()


def test_adapter_search_books_local_and_lan():
    from apps.booth_app.adapters.booth_adapter import BoothAdapter

    conn, cat_sci, cat_math = _make_catalog_conn()
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="secret-tok")
    server.start()
    local_adapter = BoothAdapter(conn=conn)
    lan_adapter = BoothAdapter(
        client=BoothLanClient(host="127.0.0.1", port=server.port, token="secret-tok"),
        auto_discover=False,
    )
    try:
        for adapter in (local_adapter, lan_adapter):
            res_q = json.loads(adapter.searchBooks("เคมี", 0, 50, 0))
            assert len(res_q) == 1
            b = res_q[0]
            assert b["title"] == "เคมี ม.ปลาย"
            assert b["shelf_location"] == "C-01"
            assert b["category_name"] == "วิทยาศาสตร์"
            assert b["available_copies"] == 1
            assert b["total_copies"] == 1

            res_cat = json.loads(adapter.searchBooks("", cat_math, 50, 0))
            assert len(res_cat) == 1
            b2 = res_cat[0]
            assert b2["title"] == "เรขาคณิตวิเคราะห์"
            assert b2["shelf_location"] == ""
            assert b2["author"] == ""
            assert b2["category_name"] == "คณิตศาสตร์"
            assert b2["available_copies"] == 1
            assert b2["total_copies"] == 1

            res_all = json.loads(adapter.searchBooks("", -1, 50, 0))
            assert len(res_all) == 3
    finally:
        lan_adapter.close()
        server.stop()
        conn.close()
