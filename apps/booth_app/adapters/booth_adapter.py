"""Qt/QML bridge for the Self-Service Booth kiosk (LAN client + legacy local DB)."""

import json
import sqlite3
from typing import Any, Dict, Optional

from core.library.services.catalog_service import CatalogService
from core.library.services.loan_service import LoanService
from core.network.booth_config import (
    DEFAULT_BOOTH_TOKEN,
    DEFAULT_LAN_PORT,
    load_booth_config,
    save_booth_config,
)
from core.network.lan_client import BoothLanClient
from core.network.lan_discovery import discover_librarian
from core.shared.mock_qt import QObject, Slot, _sanitize_for_qml
from core.student.services.student_service import StudentService


def _format_res(ok: bool, data: Any, error: Optional[str]) -> str:
    clean = _sanitize_for_qml(data) if ok else {}
    return json.dumps({"ok": bool(ok), "data": clean, "error": error})


def _format_lan_res(res: Dict[str, Any]) -> str:
    return _format_res(bool(res.get("ok", False)), res.get("data") or {}, res.get("error"))


def _clean_conn_args(
    host: str, port: int, token: str, fallback_token: str = DEFAULT_BOOTH_TOKEN
) -> Dict[str, Any]:
    try:
        parsed_port = int(port)
    except (TypeError, ValueError):
        parsed_port = DEFAULT_LAN_PORT
    valid_port = parsed_port if 1 <= parsed_port <= 65535 else DEFAULT_LAN_PORT
    cleaned_token = (token or "").strip()
    return {
        "host": (host or "").strip(),
        "port": valid_port,
        "token": cleaned_token if cleaned_token else (fallback_token or DEFAULT_BOOTH_TOKEN),
    }


class BoothAdapter(QObject):
    """Bridge for self-service checkout kiosk (supports LAN client or local SQLite)."""

    def __init__(
        self,
        conn: Optional[sqlite3.Connection] = None,
        client: Optional[BoothLanClient] = None,
        config_path: Optional[str] = None,
    ) -> None:
        super().__init__()
        if conn is None and client is None:
            raise ValueError("Either conn or client must be provided")
        self.conn = conn
        self.client = client
        self.config_path = config_path
        self.catalog_svc = CatalogService(conn) if conn is not None else None
        self.student_svc = StudentService(conn) if conn is not None else None
        self.loan_svc = (
            LoanService(conn, student_service=self.student_svc)
            if conn is not None
            else None
        )

    def close(self) -> None:
        """Close the active LAN HTTP client if present."""
        if self.client is not None:
            self.client.close()

    @Slot(result=bool)
    def isDatabaseEmpty(self) -> bool:
        """Return True if students or books table has 0 records."""
        if self.client is not None:
            return bool(self.client.is_database_empty())
        try:
            cur = self.conn.cursor()  # type: ignore[union-attr]
            st_count = cur.execute("SELECT COUNT(*) FROM students;").fetchone()[0]
            bk_count = cur.execute("SELECT COUNT(*) FROM books;").fetchone()[0]
            return st_count == 0 or bk_count == 0
        except Exception:
            return True

    @Slot(str, result=str)
    def searchStudents(self, query: str) -> str:
        """Student self-identification lookup."""
        if self.client is not None:
            return json.dumps(_sanitize_for_qml(self.client.search_students(query)))
        res = self.student_svc.search(query=query)  # type: ignore[union-attr]
        data = _sanitize_for_qml(res.data) if res.ok else []
        return json.dumps(data)

    @Slot(str, result=str)
    def getCopyByBarcode(self, barcode: str) -> str:
        """Scan book barcode."""
        if self.client is not None:
            return _format_lan_res(self.client.get_copy_by_barcode(barcode))
        res = self.catalog_svc.get_copy_by_barcode(barcode)  # type: ignore[union-attr]
        return _format_res(res.ok, res.data, res.error)

    @Slot(int, str, result=str)
    def checkout(self, student_id: int, barcode: str) -> str:
        """Self checkout."""
        if self.client is not None:
            return _format_lan_res(self.client.checkout(student_id, barcode))
        res = self.loan_svc.checkout(  # type: ignore[union-attr]
            student_id=student_id, barcode=barcode, actor=f"Booth:{student_id}"
        )
        return _format_res(res.ok, res.data, res.error)

    @Slot(int, result=str)
    def returnBook(self, loan_id: int) -> str:
        """Self return by loan ID."""
        if self.client is not None:
            return _format_lan_res(self.client.return_book(loan_id))
        res = self.loan_svc.return_book(loan_id, actor="Booth:Return")  # type: ignore[union-attr]
        return _format_res(res.ok, res.data, res.error)

    @Slot(str, result=str)
    def returnByBarcode(self, barcode: str) -> str:
        """Self return book by barcode."""
        if self.client is not None:
            return _format_lan_res(self.client.return_by_barcode(barcode))
        copy_res = self.catalog_svc.get_copy_by_barcode(barcode)  # type: ignore[union-attr]
        if not copy_res.ok or not copy_res.data:
            return json.dumps({"ok": False, "error": copy_res.error or "ไม่พบบาร์โค้ดหนังสือนี้ในระบบ"})
        row = self.conn.cursor().execute(  # type: ignore[union-attr]
            "SELECT loan_id FROM loans WHERE copy_id = ? AND status IN ('active', 'overdue')",
            (copy_res.data["copy_id"],),
        ).fetchone()
        if not row:
            return json.dumps({"ok": False, "error": "ไม่พบรายการยืมที่ค้างอยู่สำหรับบาร์โค้ดนี้"})
        res = self.loan_svc.return_book(row[0], actor="Booth:Return")  # type: ignore[union-attr]
        return _format_res(res.ok, res.data, res.error)

    @Slot(result=str)
    def getConnectionStatus(self) -> str:
        """Return JSON status for the active LAN or local DB connection."""
        if self.client is None:
            payload = {"connected": True, "host": "local", "port": 0, "mode": "local", "error": ""}
            return json.dumps(_sanitize_for_qml(payload))
        health = self.client.health()
        ok = bool(health.get("ok", False))
        err = "" if ok else str(health.get("error") or "Unable to reach server")
        payload = {
            "connected": ok,
            "host": self.client.host,
            "port": self.client.port,
            "mode": "lan",
            "error": err,
        }
        return json.dumps(_sanitize_for_qml(payload))

    def _existing_token(self) -> str:
        if self.client is not None and self.client.token:
            return self.client.token
        if self.config_path:
            return load_booth_config(self.config_path)["token"]
        return DEFAULT_BOOTH_TOKEN

    @Slot(str, int, str, result=str)
    def configureConnection(self, host: str, port: int, token: str) -> str:
        """Persist LAN settings (when config_path is set), swap client, and probe health."""
        cfg = _clean_conn_args(host, port, token, fallback_token=self._existing_token())
        if self.config_path:
            save_booth_config(self.config_path, cfg)
        if self.client is not None:
            self.client.close()
        self.client = BoothLanClient(host=cfg["host"], port=cfg["port"], token=cfg["token"])
        return self.getConnectionStatus()

    @Slot(result=str)
    def discoverServer(self) -> str:
        """Broadcast UDP discovery for Librarian Management server."""
        found = discover_librarian()
        if not found:
            return json.dumps({"ok": False, "host": "", "port": 0})
        payload = {
            "ok": True,
            "host": str(found.get("host", "")),
            "port": int(found.get("port", DEFAULT_LAN_PORT)),
        }
        return json.dumps(_sanitize_for_qml(payload))
