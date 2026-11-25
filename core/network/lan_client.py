"""Stdlib HTTP/1.1 keep-alive LAN client for Booth kiosk."""

import http.client
import json
import threading
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from core.network.booth_config import DEFAULT_BOOTH_TOKEN, DEFAULT_LAN_PORT

_RETRYABLE_ERRORS = (
    http.client.RemoteDisconnected,
    http.client.BadStatusLine,
    http.client.CannotSendRequest,
    http.client.ResponseNotReady,
    BrokenPipeError,
    ConnectionResetError,
    ConnectionAbortedError,
)


class BoothLanClient:
    """Thread-safe HTTP/1.1 keep-alive client talking to BoothLanServer."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_LAN_PORT,
        token: str = DEFAULT_BOOTH_TOKEN,
        timeout: float = 3.0,
    ) -> None:
        self.host = host.strip()
        self.port = int(port)
        self.token = token
        self.timeout = float(timeout)
        self._lock = threading.Lock()
        self._conn: Optional[http.client.HTTPConnection] = None

    def close(self) -> None:
        with self._lock:
            self._reset_conn()

    def _reset_conn(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def _ensure_conn(self) -> http.client.HTTPConnection:
        if self._conn is None:
            self._conn = http.client.HTTPConnection(
                self.host, self.port, timeout=self.timeout
            )
        return self._conn

    def _send_once(
        self, method: str, path: str, body: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        conn = self._ensure_conn()
        headers = {"X-Booth-Token": self.token, "Connection": "keep-alive"}
        raw_body: Optional[bytes] = None
        if body is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
            raw_body = json.dumps(body).encode("utf-8")
        conn.request(method, path, body=raw_body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8", errors="replace")
        if resp.getheader("Connection", "").lower() == "close":
            self._reset_conn()
        parsed = json.loads(raw) if raw else {}
        if not isinstance(parsed, dict):
            return {"ok": False, "error": f"Unexpected response format (HTTP {resp.status})"}
        return parsed

    def _request(
        self, method: str, path: str, body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self.host:
            return {"ok": False, "error": "Server host is not configured"}
        with self._lock:
            for attempt in range(2):
                try:
                    return self._send_once(method, path, body)
                except _RETRYABLE_ERRORS as exc:
                    self._reset_conn()
                    if attempt == 1:
                        return {"ok": False, "error": str(exc)}
                except (OSError, http.client.HTTPException, ValueError) as exc:
                    self._reset_conn()
                    return {"ok": False, "error": str(exc)}
        return {"ok": False, "error": "Request failed"}

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/api/health")

    def is_database_empty(self) -> bool:
        res = self.health()
        return bool(res.get("empty", False)) if res.get("ok") else False

    def search_students(self, query: str) -> List[Dict[str, Any]]:
        res = self._request("GET", f"/api/students?q={quote(query, safe='')}")
        data = res.get("data") if res.get("ok") else None
        return data if isinstance(data, list) else []

    def get_copy_by_barcode(self, barcode: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/copies/{quote(barcode, safe='')}")

    def checkout(self, student_id: int, barcode: str) -> Dict[str, Any]:
        return self._request(
            "POST", "/api/checkout", {"student_id": int(student_id), "barcode": barcode}
        )

    def return_book(self, loan_id: int) -> Dict[str, Any]:
        return self._request("POST", "/api/return", {"loan_id": int(loan_id)})

    def return_by_barcode(self, barcode: str) -> Dict[str, Any]:
        return self._request("POST", "/api/return", {"barcode": barcode})
