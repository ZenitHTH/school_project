"""
tests/test_clean_and_memory_launch.py
Tests verifying fresh launch behavior when starting with zero database files,
as well as full operation on in-memory databases (:memory:) with no disk footprint.
"""
import json
import os
import pytest

import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Qt, QMetaObject

from data.db import get_connection
from data.migrate import apply_migrations
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from apps.booth_app.adapters.booth_adapter import BoothAdapter


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    return app


def find(window, name):
    return window.findChild(QObject, name)


def invoke(window, method):
    QMetaObject.invokeMethod(window, method, Qt.DirectConnection)


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


def test_student_management_full_memory_flow(qapp, tmp_path):
    """Verify Student Management App runs full lifecycle directly on :memory: DB."""
    conn = get_connection(":memory:", pin="123456")
    apply_migrations(conn)

    adapter = StudentAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("studentAdmin", adapter)

    qml_path = os.path.abspath("apps/student_management_app/qml/Main.qml")
    engine.load(qml_path)
    qapp.processEvents()

    window = engine.rootObjects()[0]
    dlg = find(window, "firstLaunchDialog")
    assert dlg is not None
    assert dlg.property("visible") is True, "First launch dialog must show on empty in-memory DB"

    # 1. Click blank database button
    blank_btn = find(window, "firstLaunchBlankBtn")
    assert blank_btn is not None
    blank_btn.clicked.emit()
    qapp.processEvents()

    assert dlg.property("visible") is False
    assert adapter.isFirstLaunch() is False

    # 2. Insert student into memory DB
    conn.execute(
        "INSERT INTO students (student_id, national_id, prefix, first_name, last_name, full_name, status) "
        "VALUES (7001, '1234567890123', 'นาย', 'สมปอง', 'มีสุข', 'นายสมปอง มีสุข', 'active');"
    )
    conn.execute(
        "INSERT INTO enrollments (student_id, academic_year, semester, grade_level, room) "
        "VALUES (7001, 2567, 1, 'ม.4', 1);"
    )
    conn.commit()

    # 3. Search in UI
    search_input = find(window, "searchInput")
    search_input.setProperty("text", "สมปอง")
    invoke(window, "doSearch")
    qapp.processEvents()

    model = find(window, "searchResultsModel")
    assert model.property("count") == 1

    # 4. Modify student name via adapter
    update_res = json.loads(adapter.updateName(7001, "นาย", "สมปอง", "เจริญพร", "แก้ไขนามสกุล", "Admin"))
    assert update_res["ok"] is True

    st_detail = json.loads(adapter.getStudent(7001))
    assert st_detail["last_name"] == "เจริญพร"

    # 5. Export snapshot from in-memory DB
    snap_path = str(tmp_path / "memory_snapshot.sqlite")
    snap_res = json.loads(adapter.exportSnapshot(snap_path, "Admin"))
    assert snap_res["ok"] is True
    assert os.path.exists(snap_path)

    # 6. Verify activity logs recorded in memory DB
    logs = json.loads(adapter.getActivityLogs())
    assert len(logs) > 0

    # 7. Clean up
    conn.close()
    engine.deleteLater()

