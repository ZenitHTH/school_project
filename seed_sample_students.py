"""Seed sample students for testing/demo."""
import sqlite3
from data.db import get_connection
from data.migrate import apply_migrations


def main():
    # Use in-memory DB for demo, or replace with your path
    db_path = ":memory:"
    
    conn = get_connection(db_path, pin="123456")
    apply_migrations(conn)
    
    # Seed sample students (Thailand names)
    students = [
        ("1100100200300", "นาย", "สมชาย", "มั่นคง", "นายสมชาย มั่นคง", "active"),
        (None, "เด็กหญิง", "มาลี", "ใจดี", "เด็กหญิงมาลี ใจดี", "active"),
        (None, "นางสาว", "วิภา", "สุขสันต์", "นางสาววิภา สุขสันต์", "active"),
    ]
    
    conn.executemany("""
        INSERT OR IGNORE INTO students 
        (student_id, national_id, prefix, first_name, last_name, full_name, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [(1001,) + s for s in students])
    
    # Seed enrollments (disable FK constraint for this script)
    enrollments = [
        (2567, 1, "ม.3", 2),
        (2567, 1, "ม.4", 3),
        (2567, 1, "ม.5", 1),
    ]
    
    conn.execute("PRAGMA foreign_keys = OFF;")
    try:
        conn.executemany("""
            INSERT OR IGNORE INTO enrollments 
            (student_id, academic_year, semester, grade_level, room) 
            VALUES (?, ?, ?, ?, ?)
        """, [(sid,) + e for sid, e in zip(range(1001, 1004), enrollments)])
    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
    
    conn.commit()
    
    print(f"✓ Seeded {len(students)} students")
    
    # Verify
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM students")
    count = cur.fetchone()[0]
    print(f"Total students in DB: {count}")
    
    cur.execute("SELECT student_id, full_name, status FROM students")
    for row in cur.fetchall():
        print(f"  - ID {row[0]}: {row[1]} (Status: {row[2]})")
    
    conn.close()


if __name__ == "__main__":
    main()