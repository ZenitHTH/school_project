import datetime
from typing import Optional
import sqlite3


def record_activity(
    conn: sqlite3.Connection,
    action: str,
    entity_type: str,
    entity_id: str | int,
    detail: Optional[str] = None,
    actor: Optional[str] = None,
) -> None:
    """Record an audit event into activity_log inside the caller's active transaction."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO activity_log (logged_at, actor, action, entity_type, entity_id, detail)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (now_iso, actor, action, str(entity_type), str(entity_id), detail),
    )
