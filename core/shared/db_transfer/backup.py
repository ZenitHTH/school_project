"""Timestamped online SQLite backup helper executed prior to destructive imports."""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from core.shared.result import Err, Ok, Result


def create_pre_import_backup(conn: sqlite3.Connection, db_path: str) -> Result[str, str]:
    """Create a verified timestamped pre-import backup using SQLite online backup API."""
    if not db_path or db_path == ":memory:":
        return Err("Cannot create file backup for in-memory database")
    dest_path = ""
    try:
        db_p = Path(db_path).resolve()
        backup_dir = db_p.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dest_path = str(backup_dir / f"{db_p.stem}.pre_import_{ts}{db_p.suffix}")

        dst_conn = sqlite3.connect(dest_path)
        try:
            conn.backup(dst_conn)
        finally:
            dst_conn.close()

        salt_file = Path(f"{db_p}.salt")
        if salt_file.exists():
            shutil.copy2(salt_file, backup_dir / f"{Path(dest_path).name}.salt")
        return Ok(dest_path)
    except Exception as exc:
        if dest_path and os.path.exists(dest_path):
            os.remove(dest_path)
        return Err(f"Pre-import backup failed: {exc}")
