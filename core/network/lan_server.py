"""Embedded stdlib HTTP/1.1 keep-alive LAN server for Librarian Management."""

import hmac
import json
import socket
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlsplit

from core.library.services.catalog_service import CatalogService
from core.library.services.loan_service import LoanService
from core.network.booth_config import DEFAULT_BOOTH_TOKEN, DEFAULT_LAN_PORT
from core.shared.mock_qt import _sanitize_for_qml
from core.shared.version import APP_VERSION
from core.student.services.student_service import StudentService


def _is_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


class _LanHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, addr: Tuple[str, int], ctx: "BoothLanServer") -> None:
        self.ctx = ctx
        super().__init__(addr, _LanRequestHandler)


class _LanRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _check_auth(self) -> bool:
        token = self.headers.get("X-Booth-Token", "")
        if hmac.compare_digest(token, self.server.ctx.token):  # type: ignore[attr-defined]
            return True
        self._send_json(401, {"ok": False, "error": "Unauthorized"})
        return False

    def _read_json_body(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None, "Invalid Content-Length"
        if length <= 0:
            return None, "Empty request body"
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, "Malformed JSON payload"
        if not isinstance(data, dict):
            return None, "JSON body must be an object"
        return data, None

    def do_GET(self) -> None:
        if not self._check_auth():
            return
        parsed = urlsplit(self.path)
        path = parsed.path
        if path == "/api/health":
            self._send_json(200, self.server.ctx.handle_health())  # type: ignore[attr-defined]
        elif path == "/api/students":
            q = parse_qs(parsed.query).get("q", [""])[0]
            self._send_json(200, self.server.ctx.handle_students(q))  # type: ignore[attr-defined]
        elif path.startswith("/api/copies/") and len(path) > len("/api/copies/"):
            barcode = unquote(path[len("/api/copies/"):])
            self._send_json(200, self.server.ctx.handle_copy(barcode))  # type: ignore[attr-defined]
        else:
            self._send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        if not self._check_auth():
            return
        path = urlsplit(self.path).path
        if path not in ("/api/checkout", "/api/return"):
            self._send_json(404, {"ok": False, "error": "Not found"})
            return
        body, err = self._read_json_body()
        if err or body is None:
            self._send_json(400, {"ok": False, "error": err or "Invalid body"})
            return
        status, payload = (
            self.server.ctx.handle_checkout(body)  # type: ignore[attr-defined]
            if path == "/api/checkout"
            else self.server.ctx.handle_return(body)  # type: ignore[attr-defined]
        )
        self._send_json(status, payload)


class BoothLanServer:
    """Thread-safe embedded HTTP/1.1 server exposing Booth kiosk operations."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        host: str = "0.0.0.0",
        port: int = DEFAULT_LAN_PORT,
        token: str = DEFAULT_BOOTH_TOKEN,
        db_lock: Optional[threading.Lock] = None,
    ) -> None:
        self.conn = conn
        self.host = host
        self._requested_port = port
        self.token = token
        self.db_lock = db_lock or threading.Lock()
        self._httpd: Optional[_LanHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        return self._httpd.server_address[1] if self._httpd else self._requested_port

    def start(self) -> None:
        if self._httpd is not None:
            return
        self._httpd = _LanHTTPServer((self.host, self._requested_port), self)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._httpd = None
        self._thread = None

    def get_lan_ip(self) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("10.255.255.255", 1))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"
        finally:
            sock.close()

    def handle_health(self) -> Dict[str, Any]:
        with self.db_lock:
            try:
                cur = self.conn.cursor()
                st_count = cur.execute("SELECT COUNT(*) FROM students;").fetchone()[0]
                bk_count = cur.execute("SELECT COUNT(*) FROM books;").fetchone()[0]
                empty = st_count == 0 or bk_count == 0
            except Exception:
                empty = True
        return {"ok": True, "empty": empty, "version": APP_VERSION}

    def handle_students(self, query: str) -> Dict[str, Any]:
        with self.db_lock:
            res = StudentService(self.conn).search(query=query)
            data = _sanitize_for_qml(res.data) if res.ok else []
        return {"ok": True, "data": data}

    def handle_copy(self, barcode: str) -> Dict[str, Any]:
        with self.db_lock:
            res = CatalogService(self.conn).get_copy_by_barcode(barcode)
            data = _sanitize_for_qml(res.data) if res.ok else {}
        return {"ok": res.ok, "data": data, "error": res.error}

    def handle_checkout(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        student_id = body.get("student_id")
        barcode = body.get("barcode")
        if not _is_int(student_id) or not isinstance(barcode, str) or not barcode.strip():
            return 400, {"ok": False, "error": "Missing or invalid student_id or barcode"}
        with self.db_lock:
            student_svc = StudentService(self.conn)
            loan_svc = LoanService(self.conn, student_service=student_svc)
            res = loan_svc.checkout(
                student_id=student_id, barcode=barcode.strip(), actor=f"Booth:{student_id}"
            )
            data = _sanitize_for_qml(res.data) if res.ok else {}
        return 200, {"ok": res.ok, "data": data, "error": res.error}

    def handle_return(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        loan_id = body.get("loan_id")
        barcode = body.get("barcode")
        if _is_int(loan_id):
            return 200, self._return_by_loan_id(loan_id)
        if isinstance(barcode, str) and barcode.strip():
            return 200, self._return_by_barcode(barcode.strip())
        return 400, {"ok": False, "error": "Missing or invalid loan_id or barcode"}

    def _return_by_loan_id(self, loan_id: int) -> Dict[str, Any]:
        with self.db_lock:
            res = LoanService(self.conn).return_book(loan_id, actor="Booth:Return")
            data = _sanitize_for_qml(res.data) if res.ok else {}
        return {"ok": res.ok, "data": data, "error": res.error}

    def _return_by_barcode(self, barcode: str) -> Dict[str, Any]:
        with self.db_lock:
            copy_res = CatalogService(self.conn).get_copy_by_barcode(barcode)
            if not copy_res.ok or not copy_res.data:
                return {"ok": False, "data": {}, "error": copy_res.error or "ไม่พบบาร์โค้ดหนังสือนี้ในระบบ"}
            row = self.conn.cursor().execute(
                "SELECT loan_id FROM loans WHERE copy_id = ? AND status IN ('active', 'overdue')",
                (copy_res.data["copy_id"],),
            ).fetchone()
            if not row:
                return {"ok": False, "data": {}, "error": "ไม่พบรายการยืมที่ค้างอยู่สำหรับบาร์โค้ดนี้"}
            res = LoanService(self.conn).return_book(row[0], actor="Booth:Return")
            data = _sanitize_for_qml(res.data) if res.ok else {}
        return {"ok": res.ok, "data": data, "error": res.error}
