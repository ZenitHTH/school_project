import json
import sqlite3
from typing import Optional

try:
    from PySide6.QtCore import QObject, Signal, Slot, Property
except ImportError:
    class QObject:
        def __init__(self, *args, **kwargs):
            pass

    def Slot(*types, **kwargs):
        def decorator(fn):
            return fn
        return decorator

from core.library.services.catalog_service import CatalogService
from core.library.services.loan_service import LoanService
from core.student.services.student_service import StudentService


NUMERIC_KEYS = {
    "student_id", "academic_year", "semester", "room", "seq_no",
    "total_copies", "available_copies", "book_id", "copy_id",
    "loan_id", "fine_id", "reservation_id", "old_id", "new_id"
}


def _sanitize_for_qml(obj):
    if isinstance(obj, list):
        return [_sanitize_for_qml(item) for item in obj]
    if isinstance(obj, dict):
        return {
            k: (0 if k in NUMERIC_KEYS else "") if v is None else _sanitize_for_qml(v)
            for k, v in obj.items()
        }
    return obj


class BoothAdapter(QObject):
    """Bridge for self-service checkout kiosk."""

    def __init__(self, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self.catalog_svc = CatalogService(conn)
        self.student_svc = StudentService(conn)
        self.loan_svc = LoanService(conn, student_service=self.student_svc)

    @Slot(result=bool)
    def isDatabaseEmpty(self) -> bool:
        """Return True if students or books table has 0 records."""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM students;")
            st_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM books;")
            bk_count = cur.fetchone()[0]
            return st_count == 0 or bk_count == 0
        except Exception:
            return True

    @Slot(str, result=str)
    def searchStudents(self, query: str) -> str:
        """Student self-identification lookup."""
        res = self.student_svc.search(query=query)
        data = _sanitize_for_qml(res.data) if res.ok else []
        return json.dumps(data)

    @Slot(str, result=str)
    def getCopyByBarcode(self, barcode: str) -> str:
        """Scan book barcode."""
        res = self.catalog_svc.get_copy_by_barcode(barcode)
        return json.dumps({"ok": res.ok, "data": res.data, "error": res.error})

    @Slot(int, str, result=str)
    def checkout(self, student_id: int, barcode: str) -> str:
        """Self checkout."""
        res = self.loan_svc.checkout(student_id=student_id, barcode=barcode, actor=f"Booth:{student_id}")
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, result=str)
    def returnBook(self, loan_id: int) -> str:
        """Self return by loan ID."""
        res = self.loan_svc.return_book(loan_id, actor="Booth:Return")
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(str, result=str)
    def returnByBarcode(self, barcode: str) -> str:
        """Self return book by barcode."""
        copy_res = self.catalog_svc.get_copy_by_barcode(barcode)
        if not copy_res.ok or not copy_res.data:
            return json.dumps({"ok": False, "error": copy_res.error or "ไม่พบบาร์โค้ดหนังสือนี้ในระบบ"})
        copy_id = copy_res.data["copy_id"]
        cur = self.conn.cursor()
        cur.execute(
            "SELECT loan_id FROM loans WHERE copy_id = ? AND status IN ('active', 'overdue')",
            (copy_id,)
        )
        row = cur.fetchone()
        if not row:
            return json.dumps({"ok": False, "error": "ไม่พบรายการยืมที่ค้างอยู่สำหรับบาร์โค้ดนี้"})
        res = self.loan_svc.return_book(row[0], actor="Booth:Return")
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})
