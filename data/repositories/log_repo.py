import sqlite3
from typing import Any, List, Optional


def get_activity_logs(
    conn: sqlite3.Connection,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[sqlite3.Row]:
    """Retrieve activity log entries with optional filters."""
    conditions = []
    params: List[Any] = []

    if entity_type:
        conditions.append("entity_type = ?")
        params.append(entity_type)

    if entity_id:
        conditions.append("entity_id = ?")
        params.append(str(entity_id))

    if action:
        conditions.append("action = ?")
        params.append(action)

    if query:
        conditions.append("detail LIKE ?")
        params.append(f"%{query.strip()}%")

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""
        SELECT * FROM activity_log
        {where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    return conn.execute(sql, params).fetchall()
