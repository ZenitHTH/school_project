"""
tests/test_sync_edge_cases.py
Covers: diff.py and apply.py edge cases — corrupt snapshot, multi-enrollment diff,
connection leak regression (BLOCKER 1), missing file.
"""
import sqlite3
import pytest

from data.db import get_connection
from data.migrate import apply_migrations
from data.sync.diff import compute_diff
from data.sync.apply import apply_sync
from data.sync.export import export_snapshot
from data.repositories import enrollment_repo


@pytest.fixture
def two_db_env(tmp_path):
    s_conn = get_connection(str(tmp_path / "student.sqlite"), pin="111111")
    l_conn = get_connection(str(tmp_path / "library.sqlite"), pin="222222")
    apply_migrations(s_conn)
    apply_migrations(l_conn)
    yield {"s": s_conn, "l": l_conn, "tmp": tmp_path}
    s_conn.close()
    l_conn.close()


def test_diff_uses_latest_enrollment_room(two_db_env):
    """Multi-enrollment: diff must pick max(enrollment.id), not first row."""
    s_conn = two_db_env["s"]
    l_conn = two_db_env["l"]
    tmp = two_db_env["tmp"]
    snap_path = str(tmp / "snap.sqlite")

    s_conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES (501, 'ทดสอบ ห้อง', 'active')"
    )
    s_conn.commit()
    enrollment_repo.enroll_next_period(s_conn, 501, 2567, 1, "ม.1", 1)
    enrollment_repo.change_classroom(s_conn, 501, new_room=3, reason="Rebalance")

    l_conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES (501, 'ทดสอบ ห้อง', 'active')"
    )
    l_conn.commit()
    enrollment_repo.enroll_next_period(l_conn, 501, 2567, 1, "ม.1", 1)

    res_export = export_snapshot(s_conn, snap_path)
    assert res_export.ok is True

    res_diff = compute_diff(snap_path, l_conn)
    assert res_diff.ok is True

    changed = res_diff.data["changed"]
    assert len(changed) == 1
    assert changed[0]["student_id"] == 501
    assert "room" in changed[0]["changes"]
    assert changed[0]["changes"]["room"]["old"] == 1
    assert changed[0]["changes"]["room"]["new"] == 3


def test_diff_corrupt_snapshot_returns_fail(tmp_path):
    """Wrong-schema sqlite → Result.fail, no exception, no connection leak."""
    corrupt = str(tmp_path / "corrupt.sqlite")
    c = sqlite3.connect(corrupt)
    c.execute("CREATE TABLE wrong (id INTEGER)")
    c.commit()
    c.close()

    l_conn = get_connection(str(tmp_path / "lib.sqlite"), pin="333333")
    apply_migrations(l_conn)
    res = compute_diff(corrupt, l_conn)
    assert res.ok is False
    l_conn.close()


def test_apply_sync_corrupt_snapshot_returns_fail(tmp_path):
    """apply_sync with wrong-schema sqlite → Result.fail, snap_conn closed."""
    corrupt = str(tmp_path / "corrupt2.sqlite")
    c = sqlite3.connect(corrupt)
    c.execute("CREATE TABLE junk (x TEXT)")
    c.commit()
    c.close()

    l_conn = get_connection(str(tmp_path / "lib2.sqlite"), pin="444444")
    apply_migrations(l_conn)
    res = apply_sync(corrupt, l_conn)
    assert res.ok is False
    l_conn.close()


def test_diff_missing_file_returns_fail(tmp_path):
    l_conn = get_connection(str(tmp_path / "lib3.sqlite"), pin="555555")
    apply_migrations(l_conn)
    res = compute_diff(str(tmp_path / "ghost.sqlite"), l_conn)
    assert res.ok is False
    assert "not found" in res.error.lower()
    l_conn.close()


def test_apply_sync_missing_file_returns_fail(tmp_path):
    l_conn = get_connection(str(tmp_path / "lib4.sqlite"), pin="666666")
    apply_migrations(l_conn)
    res = apply_sync(str(tmp_path / "phantom.sqlite"), l_conn)
    assert res.ok is False
    l_conn.close()


def test_apply_sync_empty_student_snapshot_clears_enrollments(two_db_env):
    """Snapshot with 0 students wipes all enrollments from mirror."""
    s_conn = two_db_env["s"]
    l_conn = two_db_env["l"]
    tmp = two_db_env["tmp"]
    snap_path = str(tmp / "empty_snap.sqlite")

    l_conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES (9001, 'เก่า ระบบ', 'active')"
    )
    l_conn.commit()
    enrollment_repo.enroll_next_period(l_conn, 9001, 2567, 1, "ม.3", 2)

    # s_conn is empty → export has 0 students
    res_export = export_snapshot(s_conn, snap_path)
    assert res_export.ok is True
    assert res_export.data["student_count"] == 0

    res_apply = apply_sync(snap_path, l_conn)
    assert res_apply.ok is True

    cur = l_conn.cursor()
    cur.execute("SELECT count(*) FROM enrollments")
    assert cur.fetchone()[0] == 0
