import json
import sqlite3
import datetime
from typing import Any, Dict, List, Optional

from core.shared.mock_qt import QObject, Signal, Slot, HAVE_QT

from core.library.services.catalog_service import CatalogService
from core.library.services.fine_service import FineService
from core.library.services.loan_service import LoanService
from core.library.services.reservation_service import ReservationService
from core.student.services.student_service import StudentService
from data.repositories import log_repo
from data.sync.diff import compute_diff
from data.sync.apply import apply_sync


NUMERIC_KEYS = {
    "student_id", "academic_year", "semester", "room", "seq_no",
    "total_copies", "available_copies", "book_id", "copy_id",
    "loan_id", "fine_id", "reservation_id", "old_id", "new_id"
}


def _sanitize_for_qml(obj: Any) -> Any:
    """Convert None values to typed defaults to prevent QML null role and type mismatch warnings."""
    if isinstance(obj, list):
        return [_sanitize_for_qml(item) for item in obj]
    if isinstance(obj, dict):
        return {
            k: (0 if k in NUMERIC_KEYS else "") if v is None else _sanitize_for_qml(v)
            for k, v in obj.items()
        }
    return obj


class LibrarianAdminAdapter(QObject):
    """Bridge between PySide6/QML and core services for Librarian Management App."""

    def __init__(self, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self.catalog_svc = CatalogService(conn)
        self.fine_svc = FineService(conn)
        self.res_svc = ReservationService(conn)
        self.student_svc = StudentService(conn)
        self.loan_svc = LoanService(conn, fine_service=self.fine_svc, reservation_service=self.res_svc, student_service=self.student_svc)

    @Slot(result=bool)
    def isFirstLaunch(self) -> bool:
        """Return True if no students and no books exist and setup has not been completed."""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM students;")
            st_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM books;")
            bk_count = cur.fetchone()[0]
            if st_count > 0 or bk_count > 0:
                return False
            cur.execute("SELECT value FROM sync_state WHERE key = 'library_first_launch_done';")
            row = cur.fetchone()
            return row is None or row[0] != "1"
        except Exception:
            return False

    @Slot(str, result=str)
    def initializeBlankDatabase(self, actor: str = "Librarian") -> str:
        """Confirm blank library database initialization and mark first-launch complete."""
        try:
            self._mark_first_launch_done()
            from core.shared.log_service import record_activity
            record_activity(
                self.conn,
                action="system.init_blank_library_db",
                entity_type="system",
                entity_id=0,
                detail="Initialized blank library database following table rules.",
                actor=actor,
            )
            return json.dumps({"ok": True, "message": "Initialized blank library database successfully."})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    @Slot(str, str, result=str)
    def importRoster(self, file_path: str, actor: str = "Librarian") -> str:
        """Import or sync student records from .sqlite snapshot or .xlsx roster."""
        from urllib.parse import unquote, urlparse
        if file_path.startswith("file://"):
            parsed = urlparse(file_path)
            file_path = unquote(parsed.path)

        if file_path.endswith(".sqlite") or file_path.endswith(".db"):
            res = apply_sync(file_path, self.conn)
            if res.ok:
                self._mark_first_launch_done()
            return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            from core.importers.build_db import import_roster
            res = import_roster(file_path, conn=self.conn)
            if res.ok:
                self._mark_first_launch_done()
                from core.shared.log_service import record_activity
                record_activity(
                    self.conn,
                    action="library.import_roster_xlsx",
                    entity_type="system",
                    entity_id=0,
                    detail=f"Imported roster xlsx: {file_path}",
                    actor=actor,
                )
            return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})
        else:
            return json.dumps({"ok": False, "error": "Unsupported file format. Please select .sqlite snapshot or .xlsx file."})

    def _mark_first_launch_done(self) -> None:
        try:
            cur = self.conn.cursor()
            now = datetime.datetime.now().isoformat()
            cur.execute(
                "INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES ('library_first_launch_done', '1', ?);",
                (now,)
            )
            self.conn.commit()
        except Exception:
            pass

    @Slot(str, result=str)
    def searchStudents(self, query: str) -> str:
        """Mini student search backed by local mirror."""
        res = self.student_svc.search(query=query)
        data = _sanitize_for_qml(res.data) if res.ok else []
        return json.dumps(data)

    @Slot(str, result=str)
    def searchBooks(self, query: str) -> str:
        """FTS search for catalog."""
        res = self.catalog_svc.search(query=query)
        data = _sanitize_for_qml(res.data) if res.ok else []
        return json.dumps(data)

    @Slot(int, result=str)
    def getBook(self, book_id: int) -> str:
        """Get book info and copies."""
        res = self.catalog_svc.get_book(book_id)
        data = _sanitize_for_qml(res.data) if res.ok else {}
        return json.dumps(data)

    @Slot(str, str, str, str, str, str, str, result=str)
    def addBook(
        self,
        title: str,
        isbn: str = "",
        author: str = "",
        publisher: str = "",
        category_id: str = "",
        shelf_location: str = "",
        barcodes_csv: str = "",
    ) -> str:
        """Add book with optional barcodes."""
        cat_id = int(category_id) if category_id and category_id.isdigit() else None
        barcodes = [b.strip() for b in barcodes_csv.split(",") if b.strip()] if barcodes_csv else None
        res = self.catalog_svc.add_book(
            title=title,
            isbn=isbn or None,
            author=author or None,
            publisher=publisher or None,
            category_id=cat_id,
            shelf_location=shelf_location or None,
            barcodes=barcodes,
        )
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, str, str, result=str)
    def markCopy(self, copy_id: int, new_status: str, reason: str = "") -> str:
        """Change copy status."""
        res = self.catalog_svc.mark_copy(copy_id, new_status, reason=reason or None)
        return json.dumps({"ok": res.ok, "error": res.error})

    @Slot(str, result=str)
    def getCopyByBarcode(self, barcode: str) -> str:
        """Barcode scan lookup."""
        res = self.catalog_svc.get_copy_by_barcode(barcode)
        return json.dumps({"ok": res.ok, "data": res.data, "error": res.error})

    @Slot(int, str, result=str)
    def checkout(self, student_id: int, barcode: str) -> str:
        """Checkout book copy to student."""
        res = self.loan_svc.checkout(student_id=student_id, barcode=barcode)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, result=str)
    def returnBook(self, loan_id: int) -> str:
        """Return book copy."""
        res = self.loan_svc.return_book(loan_id)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, result=str)
    def renewLoan(self, loan_id: int) -> str:
        """Extend due date."""
        res = self.loan_svc.renew(loan_id)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(result=str)
    def getActiveLoans(self) -> str:
        """Fetch all currently borrowed books."""
        res = self.loan_svc.get_active_loans()
        return json.dumps(res.data if res.ok else [])

    @Slot(int, result=str)
    def getStudentBorrowHistory(self, student_id: int) -> str:
        """Fetch borrow history for student."""
        res = self.loan_svc.get_student_history(student_id)
        return json.dumps(res.data if res.ok else [])

    @Slot(int, result=str)
    def getCopyBorrowHistory(self, copy_id: int) -> str:
        """Fetch lending trail for copy."""
        res = self.loan_svc.get_copy_history(copy_id)
        return json.dumps(res.data if res.ok else [])

    @Slot(result=str)
    def listFines(self) -> str:
        """Fetch all fines."""
        res = self.fine_svc.list_fines()
        return json.dumps(res.data if res.ok else [])

    @Slot(int, result=str)
    def payFine(self, fine_id: int) -> str:
        """Pay fine."""
        res = self.fine_svc.record_payment(fine_id)
        return json.dumps({"ok": res.ok, "error": res.error})

    @Slot(result=str)
    def listCategories(self) -> str:
        """List categories."""
        res = self.catalog_svc.list_categories()
        return json.dumps(res.data if res.ok else [])

    @Slot(str, result=str)
    def addCategory(self, name: str) -> str:
        """Add category."""
        res = self.catalog_svc.add_category(name)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(str, result=str)
    def previewSync(self, snapshot_path: str) -> str:
        """Calculate and return diff preview from incoming snapshot."""
        from urllib.parse import unquote, urlparse
        if snapshot_path.startswith("file://"):
            parsed = urlparse(snapshot_path)
            snapshot_path = unquote(parsed.path)
        res = compute_diff(snapshot_path, self.conn)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(str, result=str)
    def applySync(self, snapshot_path: str) -> str:
        """Apply snapshot into local mirror."""
        from urllib.parse import unquote, urlparse
        if snapshot_path.startswith("file://"):
            parsed = urlparse(snapshot_path)
            snapshot_path = unquote(parsed.path)
        res = apply_sync(snapshot_path, self.conn)
        if res.ok:
            self._mark_first_launch_done()
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(result=str)
    def getActivityLogs(self) -> str:
        """Fetch local activity logs."""
        rows = log_repo.get_activity_logs(self.conn, limit=100)
        return json.dumps([dict(r) for r in rows])
