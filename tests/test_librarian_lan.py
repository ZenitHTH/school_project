"""Tests for Librarian Management embedded LAN server and adapter info."""

import json
from concurrent.futures import ThreadPoolExecutor

from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from core.network.booth_config import DEFAULT_BOOTH_TOKEN, DEFAULT_LAN_PORT
from core.network.lan_client import BoothLanClient
from core.network.lan_server import BoothLanServer
from data.db import get_connection
from data.migrate import apply_migrations
from data.repositories import book_repo


def _seed_db(db_path: str, check_same_thread: bool = False):
    conn = get_connection(db_path, pin="123456", check_same_thread=check_same_thread)
    apply_migrations(conn, db_path=db_path)
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(4001, 'นักเรียน แลน', 'active')"
    )
    conn.commit()
    book_id = book_repo.add_book(conn, title="หนังสือทดสอบ LAN", author="ผู้แต่ง", isbn="978-999")
    book_repo.add_copies(conn, book_id, barcodes=["LAN-001", "LAN-002"])
    return conn


def test_get_lan_server_info_without_server(tmp_path):
    conn = _seed_db(str(tmp_path / "lib.sqlite"), check_same_thread=True)
    try:
        adapter = LibrarianAdminAdapter(conn)
        info = json.loads(adapter.getLanServerInfo())
        assert info == {"running": False, "ip": "", "port": 0, "token": ""}
    finally:
        conn.close()


def test_get_lan_server_info_with_running_and_stopped_server(tmp_path):
    conn = _seed_db(str(tmp_path / "lib.sqlite"), check_same_thread=False)
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="sec-tok")
    adapter = LibrarianAdminAdapter(conn, lan_server=server)
    try:
        stopped_info = json.loads(adapter.getLanServerInfo())
        assert stopped_info == {"running": False, "ip": "", "port": 0, "token": ""}

        server.start()
        running_info = json.loads(adapter.getLanServerInfo())
        assert running_info["running"] is True
        assert isinstance(running_info["ip"], str) and running_info["ip"]
        assert running_info["port"] == server.port and running_info["port"] > 0
        assert running_info["token"] == "sec-tok"

        server.stop()
        after_stop = json.loads(adapter.getLanServerInfo())
        assert after_stop == {"running": False, "ip": "", "port": 0, "token": ""}
    finally:
        server.stop()
        conn.close()


def test_concurrent_lan_server_access_with_get_connection(tmp_path):
    db_path = str(tmp_path / "concurrent_lib.sqlite")
    conn = _seed_db(db_path, check_same_thread=False)
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="tok")
    server.start()
    try:
        def _worker(idx: int) -> bool:
            client = BoothLanClient(host="127.0.0.1", port=server.port, token="tok")
            try:
                health = client.health()
                students = client.search_students("4001")
                copy_res = client.get_copy_by_barcode("LAN-001")
                return (
                    health.get("ok") is True
                    and len(students) == 1
                    and copy_res.get("ok") is True
                )
            finally:
                client.close()

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(_worker, range(12)))
        assert all(results)

        client = BoothLanClient(host="127.0.0.1", port=server.port, token="tok")
        try:
            co = client.checkout(4001, "LAN-002")
            assert co["ok"] is True
            ret = client.return_by_barcode("LAN-002")
            assert ret["ok"] is True
        finally:
            client.close()
    finally:
        server.stop()
        conn.close()


def test_librarian_main_lan_helpers_and_env_config(tmp_path, monkeypatch):
    from apps.librarian_management_app import main as lib_main

    conn = _seed_db(str(tmp_path / "main_lib.sqlite"), check_same_thread=False)
    try:
        monkeypatch.setenv("LIBRARIAN_LAN_DISABLED", "1")
        server, responder = lib_main._start_lan_services(conn)
        assert server is None and responder is None

        monkeypatch.delenv("LIBRARIAN_LAN_DISABLED", raising=False)
        monkeypatch.setenv("LIBRARIAN_LAN_PORT", "0")
        monkeypatch.setenv("BOOTH_SERVER_TOKEN", "custom-tok")
        monkeypatch.setenv("LIBRARIAN_DISCOVERY_PORT", "0")
        server, responder = lib_main._start_lan_services(conn)
        try:
            assert server is not None
            assert responder is not None
            assert server.token == "custom-tok"
            assert server.port > 0
            assert responder.http_port == server.port
        finally:
            lib_main._stop_lan_services(server, responder)

        assert lib_main._parse_port("not-a-number", DEFAULT_LAN_PORT) == DEFAULT_LAN_PORT
        assert DEFAULT_BOOTH_TOKEN == "123456"
    finally:
        conn.close()
