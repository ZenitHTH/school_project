import os
import sys
import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from data.db import get_connection
from data.migrate import apply_migrations
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from apps.booth_app.adapters.booth_adapter import BoothAdapter


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


def test_student_qml_loads(qapp, tmp_path):
    db_file = str(tmp_path / "qml_student.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    adapter = StudentAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("studentAdmin", adapter)

    qml_file = os.path.abspath("apps/student_management_app/qml/Main.qml")
    engine.load(qml_file)
    assert len(engine.rootObjects()) > 0, "Student Management Main.qml failed to load!"
    conn.close()


def test_librarian_qml_loads(qapp, tmp_path):
    db_file = str(tmp_path / "qml_library.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    adapter = LibrarianAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("librarianAdmin", adapter)

    qml_file = os.path.abspath("apps/librarian_management_app/qml/Main.qml")
    engine.load(qml_file)
    assert len(engine.rootObjects()) > 0, "Librarian Management Main.qml failed to load!"
    conn.close()


def test_booth_qml_loads(qapp, tmp_path):
    db_file = str(tmp_path / "qml_booth.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    adapter = BoothAdapter(conn)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("boothAdapter", adapter)

    qml_file = os.path.abspath("apps/booth_app/qml/Main.qml")
    engine.load(qml_file)
    assert len(engine.rootObjects()) > 0, "Booth App Main.qml failed to load!"
    conn.close()
