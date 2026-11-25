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
