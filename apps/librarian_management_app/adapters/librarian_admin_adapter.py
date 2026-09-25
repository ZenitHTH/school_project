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
    "loan_id", "fine_id", "reservation_id", "old_id", "new_id",
    "category_id",
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
        """Add book with auto-generated copies (if number) or explicit barcodes."""
        cat_id = int(category_id) if category_id and category_id.isdigit() else None
        copy_count = 0
        barcodes = None
        if barcodes_csv:
            clean = barcodes_csv.strip()
            if clean.isdigit():
                copy_count = int(clean)
            else:
                barcodes = [b.strip() for b in clean.split(",") if b.strip()]

        res = self.catalog_svc.add_book(
            title=title,
            isbn=isbn or None,
            author=author or None,
            publisher=publisher or None,
            category_id=cat_id,
            shelf_location=shelf_location or None,
            barcodes=barcodes,
            copy_count=copy_count,
        )
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, str, result=str)
    def addCopies(self, book_id: int, copies_or_barcodes: str) -> str:
        """Add additional copies (auto-generated by count or explicit barcodes)."""
        clean = copies_or_barcodes.strip()
        additional_count = 0
        barcodes = None
        if clean.isdigit():
            additional_count = int(clean)
        else:
            barcodes = [b.strip() for b in clean.split(",") if b.strip()]

        res = self.catalog_svc.add_copies(
            book_id=book_id,
            barcodes=barcodes,
            additional_count=additional_count,
        )
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(str, str, result=str)
    def exportLabelsPdf(self, barcodes_json: str, output_path: str) -> str:
        """Export barcode labels to printable A4 PDF."""
        try:
            from core.library.services.label_service import export_label_sheet_pdf
            items = json.loads(barcodes_json)
            export_label_sheet_pdf(items, output_path)
            return json.dumps({"ok": True, "data": {"output_path": output_path}})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    @Slot(int, int, result=str)
    def previewBarcodes(self, book_id: int, count: int) -> str:
        """Preview deterministic barcode generation before committing."""
        try:
            from core.library.policy import BARCODE_PREFIX
            from data.repositories import book_repo
            count = max(1, count)
            if book_id <= 0:
                cur = self.conn.cursor()
                cur.execute("SELECT COALESCE(MAX(book_id), 0) + 1 FROM books;")
                target_id = cur.fetchone()[0]
                start_seq = 1
            else:
                target_id = book_id
                start_seq = book_repo.count_copies_ever(self.conn, book_id) + 1

            barcodes = [f"{BARCODE_PREFIX}-{target_id:05d}-{seq:02d}" for seq in range(start_seq, start_seq + count)]
            return json.dumps({"ok": True, "target_book_id": target_id, "barcodes": barcodes})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e), "barcodes": []})

    @Slot(result=str)
    def getCategories(self) -> str:
        """Return list of available categories."""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT category_id, name FROM categories ORDER BY category_id;")
            cats = [{"category_id": r[0], "name": r[1]} for r in cur.fetchall()]
            return json.dumps(cats)
        except Exception:
            return json.dumps([])

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

    @Slot(int, str, result=str)
    def renameCategory(self, category_id: int, new_name: str) -> str:
        """Rename category."""
        res = self.catalog_svc.rename_category(category_id, new_name)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, result=str)
    def getBooksInCategory(self, category_id: int) -> str:
        """Get books assigned to a category."""
        res = self.catalog_svc.get_books_in_category(category_id)
        return json.dumps(res.data if res.ok else [])

    @Slot(int, str, result=str)
    def deleteCategory(self, category_id: int, reassign_to_id_str: str = "") -> str:
        """Delete category with optional book reassignment."""
        reassign_id = int(reassign_to_id_str) if reassign_to_id_str.strip() else None
        res = self.catalog_svc.delete_category(category_id, reassign_id)
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

    @Slot(int, str, str, str, str, str, result=str)
    def updateBook(
        self,
        book_id: int,
        title: str,
        isbn: str = "",
        author: str = "",
        category_id_str: str = "",
        shelf_location: str = "",
    ) -> str:
        """Update book metadata from QML."""
        cat_id = int(category_id_str) if category_id_str and category_id_str.isdigit() else None
        res = self.catalog_svc.update_book(
            book_id=book_id,
            title=title,
            isbn=isbn or None,
            author=author or None,
            category_id=cat_id,
            shelf_location=shelf_location or None,
        )
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, result=str)
    def deleteBook(self, book_id: int) -> str:
        """Retire (soft-delete) a book and all its copies."""
        res = self.catalog_svc.retire_book(book_id)
        return json.dumps({"ok": res.ok, "error": res.error})

