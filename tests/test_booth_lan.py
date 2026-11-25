import http.client
import json
import sqlite3
import threading

import pytest

from core.network.booth_config import (
    DEFAULT_BOOTH_TOKEN,
    DEFAULT_DISCOVERY_PORT,
    DEFAULT_LAN_PORT,
    load_booth_config,
    save_booth_config,
)
from data.migrate import apply_migrations
from data.repositories import book_repo


def _make_seeded_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    apply_migrations(conn)
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(3001, 'นักเรียน ทดสอบ', 'active')"
    )
    conn.commit()
    book_id = book_repo.add_book(conn, title="คู่มือ LAN", author="ผู้แต่ง", isbn="978-001")
    book_repo.add_copies(conn, book_id, barcodes=["BK-001"])
    return conn


def _raw_request(port, method, path, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3.0)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        return resp.status, dict(resp.getheaders()), json.loads(raw)
    finally:
        conn.close()


def test_booth_config_defaults_and_roundtrip(tmp_path):
    cfg_path = str(tmp_path / "nested" / "booth_config.json")
    assert DEFAULT_DISCOVERY_PORT == 8766
    assert load_booth_config(cfg_path) == {
        "host": "",
        "port": DEFAULT_LAN_PORT,
        "token": DEFAULT_BOOTH_TOKEN,
    }
    save_booth_config(cfg_path, {"host": "192.168.1.50", "port": 9000, "token": "secret"})
    assert load_booth_config(cfg_path) == {
        "host": "192.168.1.50",
        "port": 9000,
        "token": "secret",
    }


def test_booth_config_handles_corrupt_json(tmp_path):
    cfg_path = tmp_path / "booth_config.json"
    cfg_path.write_text("{not valid json", encoding="utf-8")
    assert load_booth_config(str(cfg_path)) == {
        "host": "",
        "port": DEFAULT_LAN_PORT,
        "token": DEFAULT_BOOTH_TOKEN,
    }


def test_lan_server_rejects_missing_or_wrong_token():
    from core.network.lan_server import BoothLanServer

    conn = _make_seeded_conn()
    conn.close()  # Must return 401 without touching SQLite
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="secret-tok")
    server.start()
    try:
        status, headers, data = _raw_request(server.port, "GET", "/api/health")
        assert status == 401
        assert "Content-Length" in headers
        assert data == {"ok": False, "error": "Unauthorized"}

        status2, _, data2 = _raw_request(
            server.port, "GET", "/api/health", headers={"X-Booth-Token": "wrong"}
        )
        assert status2 == 401
        assert data2 == {"ok": False, "error": "Unauthorized"}
    finally:
        server.stop()


def test_lan_server_health_students_copy_checkout_return():
    from core.network.lan_server import BoothLanServer

    conn = _make_seeded_conn()
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="tok")
    server.start()
    hdrs = {"X-Booth-Token": "tok", "Content-Type": "application/json"}
    try:
        assert isinstance(server.get_lan_ip(), str)

        st, resp_hdrs, health = _raw_request(server.port, "GET", "/api/health", headers=hdrs)
        assert st == 200
        assert "Content-Length" in resp_hdrs
        assert health["ok"] is True
        assert health["empty"] is False
        assert isinstance(health["version"], str) and health["version"]

        st, _, students = _raw_request(server.port, "GET", "/api/students?q=3001", headers=hdrs)
        assert st == 200 and students["ok"] is True
        assert len(students["data"]) == 1
        assert students["data"][0]["student_id"] == 3001

        st, _, copy_res = _raw_request(server.port, "GET", "/api/copies/BK-001", headers=hdrs)
        assert st == 200 and copy_res["ok"] is True
        assert copy_res["data"]["barcode"] == "BK-001"

        co_body = json.dumps({"student_id": 3001, "barcode": "BK-001"})
        st, _, co = _raw_request(server.port, "POST", "/api/checkout", headers=hdrs, body=co_body)
        assert st == 200 and co["ok"] is True
        assert "loan_id" in co["data"]

        ret_body = json.dumps({"barcode": "BK-001"})
        st, _, ret = _raw_request(server.port, "POST", "/api/return", headers=hdrs, body=ret_body)
        assert st == 200 and ret["ok"] is True
        assert ret["data"]["loan_id"] == co["data"]["loan_id"]

        st, _, missing = _raw_request(server.port, "GET", "/api/unknown", headers=hdrs)
        assert st == 404 and missing["ok"] is False
    finally:
        server.stop()
        conn.close()


def test_lan_server_bad_json_returns_400():
    from core.network.lan_server import BoothLanServer

    conn = _make_seeded_conn()
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="tok")
    server.start()
    hdrs = {"X-Booth-Token": "tok", "Content-Type": "application/json"}
    try:
        st, _, data = _raw_request(server.port, "POST", "/api/checkout", headers=hdrs, body="{bad")
        assert st == 400 and data["ok"] is False

        st, _, data = _raw_request(
            server.port, "POST", "/api/checkout", headers=hdrs, body=json.dumps({"student_id": "x"})
        )
        assert st == 400 and data["ok"] is False

        st, _, data = _raw_request(
            server.port, "POST", "/api/return", headers=hdrs, body=json.dumps({})
        )
        assert st == 400 and data["ok"] is False
    finally:
        server.stop()
        conn.close()


def test_lan_client_keep_alive_and_operations():
    from core.network.lan_client import BoothLanClient
    from core.network.lan_server import BoothLanServer

    conn = _make_seeded_conn()
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="tok")
    server.start()
    client = BoothLanClient(host="127.0.0.1", port=server.port, token="tok")
    try:
        health = client.health()
        assert health["ok"] is True
        assert client.is_database_empty() is False

        students = client.search_students("3001")
        assert len(students) == 1
        assert students[0]["student_id"] == 3001

        copy_res = client.get_copy_by_barcode("BK-001")
        assert copy_res["ok"] is True
        assert copy_res["data"]["barcode"] == "BK-001"

        co_res = client.checkout(3001, "BK-001")
        assert co_res["ok"] is True
        loan_id = co_res["data"]["loan_id"]

        ret_res = client.return_by_barcode("BK-001")
        assert ret_res["ok"] is True
        assert ret_res["data"]["loan_id"] == loan_id

        co_res2 = client.checkout(3001, "BK-001")
        assert co_res2["ok"] is True
        ret_res2 = client.return_book(co_res2["data"]["loan_id"])
        assert ret_res2["ok"] is True
    finally:
        client.close()
        server.stop()
        conn.close()


def test_lan_client_handles_offline_server_gracefully():
    from core.network.lan_client import BoothLanClient
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        unused_port = s.getsockname()[1]

    client = BoothLanClient(host="127.0.0.1", port=unused_port, token="tok", timeout=0.5)
    try:
        health = client.health()
        assert health["ok"] is False
        assert "error" in health and health["error"]
        assert client.is_database_empty() is False
        assert client.search_students("3001") == []
        assert client.get_copy_by_barcode("BK-001")["ok"] is False
        assert client.checkout(3001, "BK-001")["ok"] is False
        assert client.return_by_barcode("BK-001")["ok"] is False
    finally:
        client.close()


def test_lan_client_reconnects_after_server_restart():
    from core.network.lan_client import BoothLanClient
    from core.network.lan_server import BoothLanServer

    conn = _make_seeded_conn()
    server1 = BoothLanServer(conn, host="127.0.0.1", port=0, token="tok")
    server1.start()
    port = server1.port
    client = BoothLanClient(host="127.0.0.1", port=port, token="tok")
    try:
        assert client.health()["ok"] is True
        server1.stop()

        server2 = BoothLanServer(conn, host="127.0.0.1", port=port, token="tok")
        server2.start()
        try:
            assert client.health()["ok"] is True
        finally:
            server2.stop()
    finally:
        client.close()
        conn.close()


def test_udp_discovery_finds_responder():
    from core.network.lan_discovery import LanDiscoveryResponder, discover_librarian

    responder = LanDiscoveryResponder(
        http_port=8765, discovery_port=0, bind_host="127.0.0.1"
    )
    responder.start()
    try:
        result = discover_librarian(
            discovery_port=responder.discovery_port,
            timeout=1.0,
            broadcast_addr="127.0.0.1",
        )
        assert result is not None
        assert result["host"] == "127.0.0.1"
        assert result["port"] == 8765
        assert isinstance(result["version"], str) and result["version"]
    finally:
        responder.stop()


def test_udp_discovery_timeout_returns_none():
    from core.network.lan_discovery import discover_librarian
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        unused_port = s.getsockname()[1]

    result = discover_librarian(
        discovery_port=unused_port, timeout=0.1, broadcast_addr="127.0.0.1"
    )
    assert result is None
