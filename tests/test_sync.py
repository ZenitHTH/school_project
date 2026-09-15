import os
import pytest
from data.db import get_connection
from data.migrate import apply_migrations
from data.repositories import student_repo, enrollment_repo, book_repo, loan_repo
from data.sync.export import export_snapshot
from data.sync.diff import compute_diff
from data.sync.apply import apply_sync


@pytest.fixture
def sync_env(tmp_path):
    student_db_path = str(tmp_path / "student.sqlite")
    library_db_path = str(tmp_path / "library.sqlite")
    snapshot_path = str(tmp_path / "snapshot.sqlite")

    s_conn = get_connection(student_db_path, pin="111111")
    l_conn = get_connection(library_db_path, pin="222222")

    apply_migrations(s_conn)
    apply_migrations(l_conn)

    yield {
        "s_conn": s_conn,
        "l_conn": l_conn,
        "snapshot_path": snapshot_path,
    }
    s_conn.close()
    l_conn.close()


def test_sync_lifecycle_with_id_renumbering_and_loans(sync_env):
    s_conn = sync_env["s_conn"]
    l_conn = sync_env["l_conn"]
    snap_path = sync_env["snapshot_path"]

    # 1. Populate initial student in both databases
    s_conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(1001, 'สมชาย สบายดี', 'active'), "
        "(1002, 'สมหญิง จริงใจ', 'active')"
    )
    s_conn.commit()

    l_conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(1001, 'สมชาย สบายดี', 'active'), "
        "(1002, 'สมหญิง จริงใจ', 'active')"
    )
    l_conn.commit()

    # 2. In library.sqlite, student 1001 takes out a loan on a book
    book_id = book_repo.add_book(l_conn, title="คู่มือวิทยาศาสตร์")
    copy_ids = book_repo.add_copies(l_conn, book_id, barcodes=["SCI-99"])
    loan_id = loan_repo.create_loan(
        l_conn, copy_id=copy_ids[0], student_id=1001,
        borrowed_at="2026-09-01T08:00:00", due_at="2026-09-15T08:00:00"
    )

    # 3. In student.sqlite:
    # - Student 1002 transfers out
    student_repo.update_status(s_conn, 1002, "transferred_out", reason="Relocated")
    # - Student 1001 has their ID renumbered 1001 -> 1999
    student_repo.change_student_id(s_conn, old_id=1001, new_id=1999, reason="Registration fix")
    # - Add a brand new student 1003
    s_conn.execute("INSERT INTO students (student_id, full_name, status) VALUES (1003, 'มานะ อดทน', 'active')")
    s_conn.commit()

    # 4. Export snapshot from student.sqlite
    res_export = export_snapshot(s_conn, snap_path)
    assert res_export.ok is True
    assert res_export.data["student_count"] == 3

    # 5. Compute diff on library.sqlite
    res_diff = compute_diff(snap_path, l_conn)
    assert res_diff.ok is True
    summary = res_diff.data["summary"]

    assert summary["new_count"] == 1  # 1003
    assert summary["changed_count"] == 1  # 1002 (transferred_out)
    assert summary["status_changes_count"] == 1
    assert summary["id_renumbered_count"] == 1  # 1001 -> 1999

    # 6. Apply sync to library.sqlite
    res_apply = apply_sync(snap_path, l_conn)
    assert res_apply.ok is True

    # 7. Verify local mirror in library.sqlite:
    cur = l_conn.cursor()
    cur.execute("SELECT status FROM students WHERE student_id = 1002")
    assert cur.fetchone()["status"] == "transferred_out"

    cur.execute("SELECT full_name FROM students WHERE student_id = 1003")
    assert cur.fetchone() is not None

    cur.execute("SELECT student_id FROM students WHERE student_id = 1999")
    assert cur.fetchone() is not None

    # Crucial check: verify loan for student 1001 was re-linked to 1999!
    loan_record = loan_repo.get_loan(l_conn, loan_id)
    assert loan_record["student_id"] == 1999

    # Verify sync_state
    cur.execute("SELECT value FROM sync_state WHERE key = 'last_synced_at'")
    assert cur.fetchone() is not None
