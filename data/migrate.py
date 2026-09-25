import os
import re
import sqlite3
from typing import List, Optional, Tuple


def get_migrations(migrations_dir: str) -> List[Tuple[int, str, str]]:
    """Return sorted list of (version, filename, full_path) for all .sql migrations."""
    if not os.path.exists(migrations_dir):
        return []
    pattern = re.compile(r"^(\d{4})_.*\.sql$")
    migrations = []
    for fname in os.listdir(migrations_dir):
        m = pattern.match(fname)
        if m:
            version = int(m.group(1))
            migrations.append((version, fname, os.path.join(migrations_dir, fname)))
    migrations.sort(key=lambda x: x[0])
    return migrations


def get_current_version(conn: sqlite3.Connection) -> int:
    """Return PRAGMA user_version."""
    cur = conn.cursor()
    cur.execute("PRAGMA user_version;")
    row = cur.fetchone()
    return row[0] if row else 0


def set_version(conn: sqlite3.Connection, version: int) -> None:
    """Update PRAGMA user_version."""
    conn.execute(f"PRAGMA user_version = {int(version)};")


def apply_migrations(
    conn: sqlite3.Connection,
    migrations_dir: Optional[str] = None,
) -> int:
    """
    Apply any pending migrations up to the latest.
    Returns the number of migrations applied.
    """
    if migrations_dir is None:
        import sys as _sys
        if getattr(_sys, "frozen", False):
            migrations_dir = os.path.join(_sys._MEIPASS, "data", "migrations")
        else:
            migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")

    current_ver = get_current_version(conn)
    migrations = get_migrations(migrations_dir)
    applied_count = 0

    for ver, fname, fpath in migrations:
        if ver > current_ver:
            with open(fpath, "r", encoding="utf-8") as f:
                sql_script = f.read()

            with conn:
                conn.executescript(sql_script)
                set_version(conn, ver)
            current_ver = ver
            applied_count += 1

    return applied_count


if __name__ == "__main__":
    import sys
    from data.db import get_connection

    if len(sys.argv) < 2:
        print("Usage: python3 -m data.migrate <path/to/database.sqlite> [pin]")
        sys.exit(1)

    db_file = sys.argv[1]
    pin_arg = sys.argv[2] if len(sys.argv) > 2 else None
    connection = get_connection(db_file, pin=pin_arg)
    count = apply_migrations(connection)
    print(f"Applied {count} migration(s). Current schema version: {get_current_version(connection)}")
    connection.close()
