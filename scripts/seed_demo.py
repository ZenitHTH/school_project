#!/usr/bin/env python3
import sys
sys.path.insert(0, "/Users/zenithth/Workspace/school_project")

from data.db import get_connection
from data.migrate import apply_migrations

conn = get_connection(":memory:", pin="123456")
apply_migrations(conn)

students_data = [
    (1001, "1100100200300", "นาย", "สมชาย", "มั่นคง", "นายสมชาย มั่นคง", "active"),
    (None, None, "เด็กหญิง", "มาลี", "ใจดี", "เด็กหญิงมาลี ใจดี", "active"),
    (None, None, "นางสาว", "วิภา", "สุขสันต์", "นางสาววิภา สุขสันต์", "active"),
]

conn.executemany("INSERT OR IGNORE INTO students (student_id, national_id, prefix, first_name, last_name, full_name, status) VALUES (?, ?, ?, ?, ?, ?, ?)", students_data)

print(f"✓ Inserted {len(students_data)} students")

# Verify
cur = conn.cursor()
cur.execute("SELECT student_id, full_name FROM students")
for row in cur.fetchall():
    print(f"  ID {row[0]}: {row[1]}")

conn.close()