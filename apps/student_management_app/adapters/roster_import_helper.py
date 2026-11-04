import logging
import datetime
import sqlite3
from typing import Any, Dict
from core.importers.xlsx_validator import validate_xlsx_structure, check_live_data_exists
from core.importers.build_db import import_roster
from core.shared.log_service import record_activity

logger = logging.getLogger(__name__)


def _record_import_sync_state(conn: sqlite3.Connection, xlsx_path: str, actor: str) -> None:
    try:
        now = datetime.datetime.now().isoformat()
        conn.execute("INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES ('first_launch_done', '1', ?);", (now,))
        conn.commit()
    except Exception as exc:
        logger.warning("Failed to record first_launch_done sync_state: %s", exc)
    record_activity(conn, action="student.import_xlsx", entity_type="system", entity_id=0, detail=f"Imported xlsx: {xlsx_path}", actor=actor)


def _perform_roster_import(conn: sqlite3.Connection, xlsx_path: str, actor: str) -> Dict[str, Any]:
    res = import_roster(xlsx_path, conn=conn)
    if res.ok:
        _record_import_sync_state(conn, xlsx_path, actor)
    return {"ok": res.ok, "error": res.error, "data": res.data}


def execute_safe_roster_import(conn: sqlite3.Connection, xlsx_path: str, actor: str = "Admin") -> Dict[str, Any]:
    """Validate structure, verify live data safeguard, and import roster."""
    val_res = validate_xlsx_structure(xlsx_path)
    if not val_res.ok:
        return {"ok": False, "error": val_res.error}

    has_live, reason = check_live_data_exists(conn)
    if has_live:
        return {
            "ok": False,
            "need_confirm": True,
            "warning": f"ตรวจพบข้อมูลการใช้งานจริงในระบบ ({reason}) การนำเข้าไฟล์ใหม่จะล้างประวัตินักเรียนเดิม ต้องการดำเนินการต่อหรือไม่?",
        }

    return _perform_roster_import(conn, xlsx_path, actor)


def execute_forced_roster_import(conn: sqlite3.Connection, xlsx_path: str, actor: str = "Admin") -> Dict[str, Any]:
    """Validate structure and bypass live data check to force re-import."""
    val_res = validate_xlsx_structure(xlsx_path)
    if not val_res.ok:
        return {"ok": False, "error": val_res.error}

    return _perform_roster_import(conn, xlsx_path, actor)


def execute_roster_import(conn: sqlite3.Connection, xlsx_path: str, force: bool = False, actor: str = "Admin") -> Dict[str, Any]:
    """Dispatch roster import based on force flag for legacy callers."""
    if force:
        return execute_forced_roster_import(conn, xlsx_path, actor)
    return execute_safe_roster_import(conn, xlsx_path, actor)
