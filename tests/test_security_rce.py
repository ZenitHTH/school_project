"""Security & RCE/injection regression tests for data/ and core/."""

import http.client
import json
import os
import socket
import sqlite3
import threading
import urllib.error
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from core.importers.xlsx_validator import validate_sqlite_file, validate_xlsx_structure
from core.library.services import isbn_providers
from core.network.booth_config import save_booth_config
from core.network.lan_discovery import DISCOVERY_MAGIC, LanDiscoveryResponder, discover_librarian
from core.network.lan_server import BoothLanServer
from core.network.lan_server_config import save_lan_server_config
from core.shared.log_service import record_activity
from core.shared.version import calculate_next_version
from data.db import get_connection
from data.migrate import apply_migrations
from data.repositories import book_repo, log_repo, student_repo
from data.sync.apply import apply_sync
from data.sync.diff import compute_diff, load_snapshot_data


def _make_seeded_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    apply_migrations(conn)
    conn.execute(
        "INSERT INTO students (student_id, national_id, full_name, status) "
        "VALUES (1001, '1100223344556', 'เด็กชายทดสอบ ระบบ', 'active')"
    )
    conn.commit()
    return conn


def test_snapshot_rejects_malicious_views_and_triggers(tmp_path):
    # 1. Malicious VIEW with infinite WITH RECURSIVE CTE
    evil_view_snap = str(tmp_path / "evil_view.sqlite")
    c = sqlite3.connect(evil_view_snap)
    c.execute("CREATE TABLE snapshot_meta (exported_at TEXT, student_count INT, enrollment_count INT)")
    c.execute("INSERT INTO snapshot_meta VALUES ('2026-01-01', 1, 0)")
    c.execute(
        "CREATE VIEW students AS "
        "WITH RECURSIVE inf(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM inf) "
        "SELECT x AS student_id, '' AS national_id, '' AS prefix, '' AS first_name, "
        "'' AS last_name, 'evil' AS full_name, 'M' AS gender, 'active' AS status FROM inf"
    )
    c.execute("CREATE TABLE enrollments (id INT, student_id INT, academic_year INT, semester INT, grade_level TEXT, room INT, track TEXT)")
    c.execute("CREATE TABLE student_id_changes (id INT, old_id INT, new_id INT, reason TEXT, changed_at TEXT)")
    c.commit()
    c.close()

    with pytest.raises(ValueError, match="Unsafe snapshot schema"):
        load_snapshot_data(evil_view_snap)

    local_conn = _make_seeded_db()
    try:
        res_diff = compute_diff(evil_view_snap, local_conn)
        assert res_diff.ok is False
        res_apply = apply_sync(evil_view_snap, local_conn)
        assert res_apply.ok is False
    finally:
        local_conn.close()

    # 2. Malicious TRIGGER inside snapshot.sqlite
    evil_trig_snap = str(tmp_path / "evil_trig.sqlite")
    c2 = sqlite3.connect(evil_trig_snap)
    c2.execute("CREATE TABLE snapshot_meta (exported_at TEXT, student_count INT, enrollment_count INT)")
    c2.execute("CREATE TABLE students (student_id INT, national_id TEXT, prefix TEXT, first_name TEXT, last_name TEXT, full_name TEXT, gender TEXT, status TEXT)")
    c2.execute("CREATE TABLE enrollments (id INT, student_id INT, academic_year INT, semester INT, grade_level TEXT, room INT, track TEXT)")
    c2.execute("CREATE TABLE student_id_changes (id INT, old_id INT, new_id INT, reason TEXT, changed_at TEXT)")
    c2.execute("CREATE TRIGGER evil_trig AFTER INSERT ON students BEGIN SELECT 1; END;")
    c2.commit()
    c2.close()

    with pytest.raises(ValueError, match="Unsafe snapshot schema"):
        load_snapshot_data(evil_trig_snap)

    # 3. validate_sqlite_file rejects VIEW disguised as students table
    res_val = validate_sqlite_file(evil_view_snap)
    assert res_val.ok is False


def test_lan_server_rejects_oversized_content_length_with_413():
    conn = _make_seeded_db()
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="sec-tok")
    server.start()
    try:
        sock = socket.create_connection(("127.0.0.1", server.port), timeout=2.0)
        try:
            raw_req = (
                "POST /api/checkout HTTP/1.1\r\n"
                "Host: 127.0.0.1\r\n"
                "X-Booth-Token: sec-tok\r\n"
                "Content-Length: 2147483647\r\n"
                "Connection: close\r\n\r\n"
            ).encode("ascii")
            sock.sendall(raw_req)
            resp = sock.recv(4096).decode("utf-8", errors="replace")
            assert resp.startswith("HTTP/1.1 413")
        finally:
            sock.close()

        sock2 = socket.create_connection(("127.0.0.1", server.port), timeout=2.0)
        try:
            raw_req2 = (
                "POST /api/checkout HTTP/1.1\r\n"
                "Host: 127.0.0.1\r\n"
                "X-Booth-Token: sec-tok\r\n"
                "Content-Length: -5\r\n"
                "Connection: close\r\n\r\n"
            ).encode("ascii")
            sock2.sendall(raw_req2)
            resp2 = sock2.recv(4096).decode("utf-8", errors="replace")
            assert resp2.startswith("HTTP/1.1 413")
        finally:
            sock2.close()
    finally:
        server.stop()
        conn.close()


def test_lan_server_strips_national_id_from_students():
    conn = _make_seeded_db()
    server = BoothLanServer(conn, host="127.0.0.1", port=0, token="sec-tok")
    server.start()
    try:
        hc = http.client.HTTPConnection("127.0.0.1", server.port, timeout=2.0)
        hc.request("GET", "/api/students?q=1001", headers={"X-Booth-Token": "sec-tok"})
        resp = hc.getresponse()
        payload = json.loads(resp.read().decode("utf-8"))
        hc.close()
        assert resp.status == 200 and payload["ok"] is True
        assert len(payload["data"]) == 1
        assert payload["data"][0]["student_id"] == 1001
        assert "national_id" not in payload["data"][0]
    finally:
        server.stop()
        conn.close()


def test_udp_discovery_rejects_forged_reply_without_valid_hmac():
    # Rogue UDP responder sends unauthenticated or wrong-HMAC reply first
    rogue_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rogue_sock.bind(("127.0.0.1", 0))
    rogue_port = rogue_sock.getsockname()[1]

    def _rogue_loop():
        rogue_sock.settimeout(1.0)
        try:
            data, addr = rogue_sock.recvfrom(1024)
            parts = data.decode("ascii", errors="ignore").strip().split(" ", 1)
            nonce = parts[1] if len(parts) == 2 else ""
            forged = json.dumps({
                "service": "smte-librarian",
                "port": 9999,
                "version": "1.0",
                "nonce": nonce,
                "hmac": "0" * 64,
            }).encode("utf-8")
            rogue_sock.sendto(forged, addr)
        except OSError:
            pass

    t = threading.Thread(target=_rogue_loop, daemon=True)
    t.start()
    try:
        res = discover_librarian(
            discovery_port=rogue_port, timeout=0.3, broadcast_addr="127.0.0.1", token="real-secret"
        )
        assert res is None
    finally:
        rogue_sock.close()
        t.join(timeout=1.0)

    # Legitimate responder with matching token succeeds
    responder = LanDiscoveryResponder(http_port=8765, discovery_port=0, bind_host="127.0.0.1", token="real-secret")
    responder.start()
    try:
        res_ok = discover_librarian(
            discovery_port=responder.discovery_port, timeout=1.0, broadcast_addr="127.0.0.1", token="real-secret"
        )
        assert res_ok is not None
        assert res_ok["port"] == 8765
    finally:
        responder.stop()


def test_isbn_providers_block_redirects_cap_size_and_reject_traversal_ids(monkeypatch):
    class _MockHTTPHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:8765/api/health")
                self.end_headers()
            elif self.path == "/huge":
                body = b"x" * 2_100_000
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

    httpd = HTTPServer(("127.0.0.1", 0), _MockHTTPHandler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        with pytest.raises(urllib.error.HTTPError):
            isbn_providers._fetch_json(f"http://127.0.0.1:{port}/redirect", timeout=1.0)
        assert isbn_providers._fetch_text(f"http://127.0.0.1:{port}/redirect", timeout=1.0) is None

        with pytest.raises(ValueError, match="exceeds"):
            isbn_providers._fetch_json(f"http://127.0.0.1:{port}/huge", timeout=2.0)
        assert isbn_providers._fetch_text(f"http://127.0.0.1:{port}/huge", timeout=2.0) is None
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join(timeout=1.0)

    # Path traversal IDs rejected before issuing detail request
    called_urls = []
    monkeypatch.setattr(isbn_providers, "_fetch_json", lambda url, timeout=5.0, extra_headers=None: called_urls.append(url) or {
        "rows": [{"id": "../../admin", "barcode": "9786169444541"}]
    })
    assert isbn_providers._fetch_chulabook("9786169444541", 1.0) is None
    assert len(called_urls) == 1  # detail URL never called

    called_seed = []
    monkeypatch.setattr(isbn_providers, "_fetch_json", lambda url, timeout=5.0: called_seed.append(url))
    assert isbn_providers._fetch_seed_detail("../etc/passwd", 1.0) is None
    assert called_seed == []

    assert isbn_providers._validate_provider_id("715593") == "715593"
    assert isbn_providers._validate_provider_id("../../secret") is None
    assert isbn_providers._validate_provider_id("123?admin=1") is None


def test_xlsx_validator_rejects_zip_bomb_workbook_xml(tmp_path, monkeypatch):
    # Force zipfile fallback path
    import builtins
    real_import = builtins.__import__

    def _block_openpyxl(name, *args, **kwargs):
        if name == "openpyxl":
            raise ImportError("mocked missing openpyxl")
        return real_import(name, *args, **kwargs)

    xlsx_path = tmp_path / "bomb.xlsx"
    with zipfile.ZipFile(xlsx_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # > 10 MB uncompressed XML compresses to tiny zip
        z.writestr("xl/workbook.xml", b"<workbook>" + (b" " * (10 * 1024 * 1024 + 128)) + b"</workbook>")

    monkeypatch.setattr(builtins, "__import__", _block_openpyxl)
    res = validate_xlsx_structure(str(xlsx_path))
    assert res.ok is False
    assert "exceeds maximum allowed size" in res.error


def test_like_wildcards_are_escaped_in_search_and_logs():
    conn = _make_seeded_db()
    try:
        # '%' and '_' must not act as wildcards matching 'เด็กชายทดสอบ ระบบ'
        assert student_repo.search_students(conn, query="%") == []
        assert student_repo.search_students(conn, query="__") == []

        book_repo.add_book(conn, title="Normal Book", author="Author")
        assert book_repo.search_books(conn, query="%") == []
        assert book_repo.search_books(conn, query="__") == []

        record_activity(conn, action="test.act", entity_type="book", entity_id=1, detail="100% genuine")
        record_activity(conn, action="test.act", entity_type="book", entity_id=2, detail="other entry")
        conn.commit()
        hits = log_repo.get_activity_logs(conn, query="%")
        assert len(hits) == 1 and hits[0]["entity_id"] == "1"
    finally:
        conn.close()


def test_calculate_next_version_rejects_semver_injection():
    with pytest.raises(ValueError):
        calculate_next_version("1.0.0", '1.0.0"\n[Run]\nFilename: cmd.exe')
    with pytest.raises(ValueError):
        calculate_next_version("1.0.0", "1.2.3;id")
    assert calculate_next_version("1.0.0", "1.2.3-rc.1") == "1.2.3-rc.1"


@pytest.mark.skipif(os.name != "posix", reason="POSIX file mode check")
def test_lan_config_files_saved_with_0600_permissions(tmp_path):
    srv_cfg = str(tmp_path / "srv.json")
    booth_cfg = str(tmp_path / "booth.json")
    save_lan_server_config(srv_cfg, {"enabled": True, "port": 8765, "discovery_port": 8766, "token": "s3cr3t"})
    save_booth_config(booth_cfg, {"host": "127.0.0.1", "port": 8765, "token": "s3cr3t"})
    assert (os.stat(srv_cfg).st_mode & 0o777) == 0o600
    assert (os.stat(booth_cfg).st_mode & 0o777) == 0o600
