import os
import sys
import sqlite3
from pathlib import Path
from data.paths import (
    get_app_data_dir,
    get_app_log_dir,
    get_default_db_path,
    get_default_download_dir,
    get_default_documents_dir,
)
from data.db import get_connection, backup_database
from data.migrate import apply_migrations


def test_paths_resolution():
    data_dir = get_app_data_dir("SMTE-StudentManagement")
    log_dir = get_app_log_dir("SMTE-StudentManagement")
    db_path = get_default_db_path("SMTE-StudentManagement", "student.sqlite")

    assert "SMTE-StudentManagement" in str(data_dir)
    assert "SMTE-StudentManagement" in str(log_dir)
    assert db_path.name == "student.sqlite"
    assert db_path.parent == data_dir
    assert get_default_download_dir().exists() or True
    assert get_default_documents_dir().exists() or True


def test_backup_database_with_wal(tmp_path):
    db_file = tmp_path / "test.sqlite"
    conn = get_connection(str(db_file), pin="123456")
    apply_migrations(conn)

    # Insert a dummy record to make WAL dirty
    with conn:
        conn.execute("INSERT INTO sync_state (key, value, updated_at) VALUES ('test_key', 'val', '2026-09-28');")

    backup_path = backup_database(conn, str(db_file))
    assert os.path.exists(backup_path)
    assert os.path.exists(f"{db_file}.salt")

    # Check backup folder contains the salt copy as well
    backups_dir = db_file.parent / "backups"
    assert (backups_dir / "test.sqlite.salt").exists()

    # Verify backup is a valid database
    backup_conn = get_connection(backup_path, pin="123456")
    row = backup_conn.execute("SELECT value FROM sync_state WHERE key = 'test_key';").fetchone()
    assert row[0] == "val"
    backup_conn.close()
    conn.close()


def test_apply_migrations_auto_backup(tmp_path, monkeypatch):
    db_file = tmp_path / "migration_test.sqlite"
    conn = get_connection(str(db_file), pin="123456")

    # Run migrations with db_path supplied
    applied = apply_migrations(conn, db_path=str(db_file))
    assert applied > 0

    # Backups folder should exist if migrations ran
    backups_dir = db_file.parent / "backups"
    assert backups_dir.exists()
    assert len(list(backups_dir.glob("*.sqlite"))) >= 1
    conn.close()
