import sqlite3
from data.migrate import apply_migrations


def test_trigram_students_fts_creation():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)

    # Insert Thai student
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES (1001, 'นายเจษฎา งาคชสาร', 'active')"
    )

    # Substring search in middle of first name matches under trigram (fails under unicode61)
    cur = conn.execute("SELECT rowid FROM students_fts WHERE students_fts MATCH 'ษฎา'")
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 1001
