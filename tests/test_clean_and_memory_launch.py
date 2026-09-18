"""
tests/test_clean_and_memory_launch.py
Tests verifying fresh launch behavior when starting with zero database files,
as well as full operation on in-memory databases (:memory:) with no disk footprint.
"""
import json
import os
import pytest

from data.db import get_connection
from data.migrate import apply_migrations
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from apps.booth_app.adapters.booth_adapter import BoothAdapter


def test_in_memory_db_creates_no_disk_files():
    """Verify get_connection(':memory:') operates purely in memory with zero disk files."""
    conn = get_connection(":memory:", pin="123456")
    apply_migrations(conn)

    # Verify no :memory:.salt or :memory:.pin_hash files were created
    assert not os.path.exists(":memory:.salt")
    assert not os.path.exists(":memory:.pin_hash")
    assert not os.path.exists(":memory:.lockout")

    # Verify student adapter in memory
    student_adapter = StudentAdminAdapter(conn)
    assert student_adapter.isFirstLaunch() is True

    init_res = json.loads(student_adapter.initializeBlankDatabase("Tester"))
    assert init_res["ok"] is True
    assert student_adapter.isFirstLaunch() is False

    # Verify librarian adapter in memory
    lib_adapter = LibrarianAdminAdapter(conn)
    assert lib_adapter.isFirstLaunch() is True

    lib_init = json.loads(lib_adapter.initializeBlankDatabase("Tester"))
    assert lib_init["ok"] is True
    assert lib_adapter.isFirstLaunch() is False

    # Verify booth adapter in memory (students and books still 0)
    booth_adapter = BoothAdapter(conn)
    assert booth_adapter.isDatabaseEmpty() is True

    conn.close()


def test_fresh_disk_database_launch(tmp_path):
    """Verify first launch flow from a freshly initialized disk database."""
    student_db = str(tmp_path / "fresh_student.sqlite")
    conn_st = get_connection(student_db, pin="123456")
    apply_migrations(conn_st)

    st_adapter = StudentAdminAdapter(conn_st)
    assert st_adapter.isFirstLaunch() is True

    # User chooses blank database
    res = json.loads(st_adapter.initializeBlankDatabase("Admin"))
    assert res["ok"] is True
    assert st_adapter.isFirstLaunch() is False
    assert len(json.loads(st_adapter.searchStudents(""))) == 0
    conn_st.close()

    # Re-open the database - should remember setup was completed
    conn_st2 = get_connection(student_db, pin="123456")
    st_adapter2 = StudentAdminAdapter(conn_st2)
    assert st_adapter2.isFirstLaunch() is False
    conn_st2.close()


def test_fresh_librarian_and_booth_launch(tmp_path):
    """Verify librarian first launch and booth response on clean database."""
    lib_db = str(tmp_path / "fresh_library.sqlite")
    conn_lib = get_connection(lib_db, pin="123456")
    apply_migrations(conn_lib)

    lib_adapter = LibrarianAdminAdapter(conn_lib)
    booth_adapter = BoothAdapter(conn_lib)

    assert lib_adapter.isFirstLaunch() is True
    assert booth_adapter.isDatabaseEmpty() is True

    # Initialize blank library DB
    res = json.loads(lib_adapter.initializeBlankDatabase("Librarian"))
    assert res["ok"] is True
    assert lib_adapter.isFirstLaunch() is False

    # Still empty of books & students until added
    assert booth_adapter.isDatabaseEmpty() is True

    # Add a student and book
    from data.repositories import book_repo
    b_id = book_repo.add_book(conn_lib, title="Fresh Launch Book")
    conn_lib.execute("INSERT INTO students (student_id, full_name, status) VALUES (9001, 'นักเรียน ใหม่', 'active');")
    conn_lib.commit()

    assert booth_adapter.isDatabaseEmpty() is False
    conn_lib.close()
