import os
import json
import sqlite3
import datetime
from typing import Any, Dict, List, Optional, Tuple

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
from data.paths import get_app_data_dir, get_default_documents_dir
from data.repositories import log_repo
from data.sync.export import export_snapshot
from apps.student_management_app.adapters.roster_import_helper import (
    execute_safe_roster_import,
    execute_forced_roster_import,
)


def _active_db_realpath(conn: sqlite3.Connection) -> Optional[str]:
    """Return canonical path of the main file-backed SQLite database, or None if in-memory."""
    try:
        for _seq, name, db_file in conn.execute("PRAGMA database_list;").fetchall():
            if name == "main" and db_file:
                return os.path.realpath(db_file)
    except Exception:
        pass
    return None


def _validate_input_path(
    raw_path: str,
    allowed_exts: Tuple[str, ...],
    conn: sqlite3.Connection,
) -> Tuple[Optional[str], Optional[str]]:
    """Normalize and validate an input file path (regular file, allowed extension, not active DB)."""
    clean = normalize_file_path(raw_path)
    if not clean or "\x00" in clean:
        return None, "Invalid file path."
    if os.path.splitext(clean)[1].lower() not in allowed_exts:
        return None, f"Unsupported file format. Allowed: {', '.join(allowed_exts)}"
    if os.path.islink(clean):
        return None, "Symbolic links are not allowed."
    real_path = os.path.realpath(clean)
    if os.path.splitext(real_path)[1].lower() not in allowed_exts:
        return None, f"Unsupported target file format. Allowed: {', '.join(allowed_exts)}"
    if not os.path.isfile(real_path):
        return None, f"File not found: {clean}"
    active_db = _active_db_realpath(conn)
    if active_db and real_path == active_db:
        return None, "Refusing to read the active application database."
    return real_path, None


def _validate_output_path(
    raw_path: str,
    allowed_exts: Tuple[str, ...],
    conn: sqlite3.Connection,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Normalize and validate an output path. Returns (normalized_path, real_path, error)."""
    clean = normalize_file_path(raw_path)
    if not clean or "\x00" in clean:
        return None, None, "Invalid output file path."
    if os.path.splitext(clean)[1].lower() not in allowed_exts:
        return None, None, f"Unsupported output extension. Expected: {', '.join(allowed_exts)}"
    if os.path.islink(clean):
        return None, None, "Refusing to write to a symbolic link."
    real_path = os.path.realpath(clean)
    if os.path.splitext(real_path)[1].lower() not in allowed_exts:
        return None, None, "Invalid resolved output extension."
    if os.path.isdir(real_path):
        return None, None, "Output path refers to a directory."
    parent_dir = os.path.dirname(real_path)
    if not parent_dir or not os.path.isdir(parent_dir):
        return None, None, f"Output directory does not exist: {os.path.dirname(clean)}"
    active_db = _active_db_realpath(conn)
    if active_db and real_path == active_db:
        return None, None, "Refusing to overwrite the active application database."
    return clean, real_path, None


def _default_snapshot_output_path() -> str:
    """Resolve a safe user-writable default path for snapshot export."""
    docs = get_default_documents_dir()
    if docs.is_dir() and os.access(docs, os.W_OK):
        return str(docs / "snapshot.sqlite")
    return str(get_app_data_dir("SMTE-StudentManagement") / "snapshot.sqlite")


class StudentAdminAdapter(QObject, SettingsAdapterMixin):
    """Bridge between PySide6/QML and core services for Student Management App."""

    def __init__(self, conn: sqlite3.Connection, settings_service: Optional[SettingsService] = None):
        super().__init__()
        self.conn = conn
        self.student_svc = StudentService(conn)
        self.enrollment_svc = EnrollmentService(conn)
        self.settings_svc = settings_service or SettingsService()
        self._diff_cache: Optional[Tuple[str, int, int, int, Any]] = None

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
    def exportSnapshot(self, output_path: str = "", actor: str = "Admin") -> str:
        """Export snapshot for LINE sync."""
        target = output_path if (output_path or "").strip() else _default_snapshot_output_path()
        normalized, real_path, err = _validate_output_path(target, (".sqlite", ".db"), self.conn)
        if err or not real_path or not normalized:
            return json.dumps({"ok": False, "error": err or "Invalid snapshot output path.", "data": None})
        res = export_snapshot(self.conn, real_path, actor=actor)
        data = dict(res.data) if res.ok and isinstance(res.data, dict) else res.data
        if res.ok and isinstance(data, dict):
            data["output_path"] = normalized
        return json.dumps({"ok": res.ok, "error": res.error, "data": data})

    @Slot(int, result=str)
    def getHistory(self, student_id: int) -> str:
        """Fetch student audit history."""
        res = self.student_svc.get_history(student_id)
        return json.dumps(_sanitize_for_qml(res.data) if res.ok else {})

    @Slot(str, bool, str, result=str)
    def importXlsx(self, xlsx_path: str, force: bool = False, actor: str = "Admin") -> str:
        """Validate and import student roster xlsx with re-import safeguard."""
        clean_path, err = _validate_input_path(xlsx_path, (".xlsx", ".xls"), self.conn)
        if err or not clean_path:
            return json.dumps({"ok": False, "error": err or "Invalid Excel path."})
        if force:
            res = execute_forced_roster_import(self.conn, clean_path, actor=actor)
        else:
            res = execute_safe_roster_import(self.conn, clean_path, actor=actor)
        return json.dumps(res)

    def _xlsx_cache_key(self, clean_path: str) -> Optional[Tuple[str, int, int, int]]:
        try:
            st = os.stat(clean_path)
            return (clean_path, st.st_mtime_ns, st.st_size, self.conn.total_changes)
        except OSError:
            return None

    @Slot(str, result=str)
    def previewXlsxDiff(self, xlsx_path: str) -> str:
        """Preview categorized diff for recurring xlsx re-import / promotion."""
        clean_path, err = _validate_input_path(xlsx_path, (".xlsx", ".xls"), self.conn)
        if err or not clean_path:
            return json.dumps({"ok": False, "error": err or "Invalid Excel path."})
        key = self._xlsx_cache_key(clean_path)
        if key is not None and self._diff_cache is not None and self._diff_cache[:4] == key:
            res = self._diff_cache[4]
            return json.dumps({"ok": res.ok, "error": res.error, "data": res.data, "warnings": res.warnings})
        val_res = validate_xlsx_structure(clean_path)
        if not val_res.ok:
            return json.dumps({"ok": False, "error": val_res.error})
        from core.importers.xlsx_diff_importer import calculate_xlsx_diff
        res = calculate_xlsx_diff(self.conn, clean_path)
        if res.ok and key is not None:
            self._diff_cache = (*key, res)
        return json.dumps({"ok": res.ok, "error": res.error, "data": res.data, "warnings": res.warnings})

    @Slot(str, int, int, str, result=str)
    def applyXlsxDiff(self, xlsx_path: str, academic_year: int, semester: int, actor: str = "Admin") -> str:
        """Apply xlsx diff atomically inside one transaction."""
        clean_path, err = _validate_input_path(xlsx_path, (".xlsx", ".xls"), self.conn)
        if err or not clean_path:
            return json.dumps({"ok": False, "error": err or "Invalid Excel path.", "warnings": []})
        from core.importers.xlsx_diff_importer import calculate_xlsx_diff, apply_xlsx_diff
        key = self._xlsx_cache_key(clean_path)
        if key is not None and self._diff_cache is not None and self._diff_cache[:4] == key:
            diff_res = self._diff_cache[4]
        else:
            diff_res = calculate_xlsx_diff(self.conn, clean_path)
        self._diff_cache = None
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
