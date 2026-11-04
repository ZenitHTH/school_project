import json
import sqlite3
import datetime
from typing import Any, Dict, List, Optional

from core.shared.mock_qt import (
    QObject, Signal, Slot, HAVE_QT,
    NUMERIC_KEYS, _sanitize_for_qml, normalize_file_path,
    apply_qt_app_font,
)
from core.shared.settings_service import SettingsService
from core.shared.settings_adapter_mixin import SettingsAdapterMixin
from core.importers.xlsx_validator import validate_xlsx_structure
from core.student.services.student_service import StudentService
from core.student.services.enrollment_service import EnrollmentService
from data.repositories import log_repo
from data.sync.export import export_snapshot
from apps.student_management_app.adapters.roster_import_helper import (
    execute_safe_roster_import,
    execute_forced_roster_import,
)


class StudentAdminAdapter(QObject, SettingsAdapterMixin):
    """Bridge between PySide6/QML and core services for Student Management App."""

    def __init__(self, conn: sqlite3.Connection, settings_service: Optional[SettingsService] = None):
        super().__init__()
        self.conn = conn
        self.student_svc = StudentService(conn)
        self.enrollment_svc = EnrollmentService(conn)
        self.settings_svc = settings_service or SettingsService()

    @Slot(result=bool)
    def isFirstLaunch(self) -> bool:
        """Return True if no students exist and first-launch setup has not been completed."""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM students;")
            if cur.fetchone()[0] > 0:
                return False
            cur.execute("SELECT value FROM sync_state WHERE key = 'first_launch_done';")
            row = cur.fetchone()
            return row is None or row[0] != "1"
        except Exception:
            return False

    @Slot(str, result=str)
    def initializeBlankDatabase(self, actor: str = "Admin") -> str:
        """Confirm blank database initialization and mark first-launch complete."""
        try:
            now = datetime.datetime.now().isoformat()
            self.conn.execute(
                "INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES ('first_launch_done', '1', ?);",
                (now,),
            )
            self.conn.commit()
            from core.shared.log_service import record_activity
            record_activity(
                self.conn, action="system.init_blank_db", entity_type="system", entity_id=0,
                detail="Initialized blank database following table rules.", actor=actor,
            )
            return json.dumps({"ok": True, "message": "Initialized blank database successfully."})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    @Slot(str, int, result=str)
    def searchStudents(self, query: str, offset: int = 0) -> str:
        """Search students and return JSON string for QML ListModel."""
        res = self.student_svc.search(query=query, limit=50, offset=offset)
        data = _sanitize_for_qml(res.data) if res.ok else []
        return json.dumps(data)

    @Slot(str, result=int)
    def countStudents(self, query: str) -> int:
        """Count total students matching query for pagination."""
        res = self.student_svc.count(query=query)
        return res.data if res.ok else 0

    @Slot(int, result=str)
    def getStudent(self, student_id: int) -> str:
        """Get student detail and return JSON string."""
        res = self.student_svc.get(student_id)
        data = _sanitize_for_qml(res.data) if res.ok else {}
        return json.dumps(data)

    @Slot(int, str, str, str, result=str)
    def updateStatus(self, student_id: int, new_status: str, reason: str = "", actor: str = "Admin") -> str:
        """Execute legal status change."""
        res = self.student_svc.update_status(student_id, new_status, reason=reason or None, actor=actor)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, int, str, str, result=str)
    def changeStudentID(self, old_id: int, new_id: int, reason: str = "", actor: str = "Admin") -> str:
        """Change student ID with cascade."""
        res = self.student_svc.change_student_id(old_id, new_id, reason=reason or None, actor=actor)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, str, str, str, str, str, result=str)
    def updateName(self, student_id: int, prefix: str, first_name: str, last_name: str, reason: str = "", actor: str = "Admin") -> str:
        """Update student name."""
        res = self.student_svc.update_name(
            student_id, prefix=prefix or None, first_name=first_name,
            last_name=last_name, reason=reason or None, actor=actor,
        )
        return json.dumps({"ok": res.ok, "error": res.error})

    @Slot(int, int, str, str, result=str)
    def changeClassroom(self, student_id: int, new_room: int, reason: str = "", actor: str = "Admin") -> str:
        """Move student to another room."""
        res = self.enrollment_svc.change_classroom(student_id, new_room, reason=reason or None, actor=actor)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, int, int, int, str, result=str)
    def bulkPromote(self, src_year: int, src_sem: int, tgt_year: int, tgt_sem: int, actor: str = "Admin") -> str:
        """Run year-end bulk promotion."""
        res = self.enrollment_svc.promote_students(src_year, src_sem, tgt_year, tgt_sem, actor=actor)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(str, str, result=str)
    def exportSnapshot(self, output_path: str, actor: str = "Admin") -> str:
        """Export snapshot for LINE sync."""
        res = export_snapshot(self.conn, output_path, actor=actor)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data})

    @Slot(int, result=str)
    def getHistory(self, student_id: int) -> str:
        """Fetch student audit history."""
        res = self.student_svc.get_history(student_id)
        return json.dumps(_sanitize_for_qml(res.data) if res.ok else {})

    @Slot(str, bool, str, result=str)
    def importXlsx(self, xlsx_path: str, force: bool = False, actor: str = "Admin") -> str:
        """Validate and import student roster xlsx with re-import safeguard."""
        clean_path = normalize_file_path(xlsx_path)
        if force:
            res = execute_forced_roster_import(self.conn, clean_path, actor=actor)
        else:
            res = execute_safe_roster_import(self.conn, clean_path, actor=actor)
        return json.dumps(res)

    @Slot(str, result=str)
    def previewXlsxDiff(self, xlsx_path: str) -> str:
        """Preview categorized diff for recurring xlsx re-import / promotion."""
        clean_path = normalize_file_path(xlsx_path)
        val_res = validate_xlsx_structure(clean_path)
        if not val_res.ok:
            return json.dumps({"ok": False, "error": val_res.error})
        from core.importers.xlsx_diff_importer import calculate_xlsx_diff
        res = calculate_xlsx_diff(self.conn, clean_path)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data, "warnings": res.warnings})

    @Slot(str, int, int, str, result=str)
    def applyXlsxDiff(self, xlsx_path: str, academic_year: int, semester: int, actor: str = "Admin") -> str:
        """Apply xlsx diff atomically inside one transaction."""
        clean_path = normalize_file_path(xlsx_path)
        from core.importers.xlsx_diff_importer import calculate_xlsx_diff, apply_xlsx_diff
        diff_res = calculate_xlsx_diff(self.conn, clean_path)
        if not diff_res.ok:
            return json.dumps({"ok": False, "error": diff_res.error, "warnings": diff_res.warnings})
        res = apply_xlsx_diff(self.conn, diff_res.data, academic_year, semester, actor=actor)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data, "warnings": res.warnings})

    @Slot(result=str)
    def getActivityLogs(self) -> str:
        """Fetch local activity log entries."""
        rows = log_repo.get_activity_logs(self.conn, limit=100)
        return json.dumps(_sanitize_for_qml([dict(r) for r in rows]))

    @Slot(str, int)
    def setAppFont(self, family: str, pixel_size: int) -> None:
        """Update application-level font family and pixel size."""
        apply_qt_app_font(family, pixel_size)
