import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apps.common_linux_env import setup_linux_runtime_env

setup_linux_runtime_env()

import json
from core.shared.version import APP_VERSION
from data.db import get_connection
from data.migrate import apply_migrations
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter

try:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


def run_cli_first_launch(adapter: StudentAdminAdapter) -> None:
    """Handle first launch interactively in terminal mode."""
    print("=" * 60)
    print("🎓 Student Management System — First Launch Setup")
    print("=" * 60)
    print("No student records found in database.")
    try:
        ans = input("Do you have an xlsx student database file? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"
    if ans == "y":
        try:
            path = input("Enter path to xlsx file: ").strip()
        except (EOFError, KeyboardInterrupt):
            path = ""
        if path and os.path.exists(path):
            res = json.loads(adapter.importXlsx(path, force=False, actor="CLI"))
            if res.get("ok"):
                print(f"✓ Imported {res.get('data', {}).get('students', 0)} students successfully.")
            else:
                print(f"✗ Import failed: {res.get('error')}")
        else:
            print("File not found or empty path. Initializing blank database instead.")
            adapter.initializeBlankDatabase("CLI")
    else:
        adapter.initializeBlankDatabase("CLI")
        print("✓ Created blank database following table rules.")


from data.paths import get_default_db_path
from core.shared.app_logging import setup_app_logging


def _run_cli_mode(conn, adapter: StudentAdminAdapter) -> None:
    if adapter.isFirstLaunch():
        if sys.stdin.isatty() and "--cli" in sys.argv:
            run_cli_first_launch(adapter)
        else:
            adapter.initializeBlankDatabase("CLI")
    print("[Student Management] Running in CLI mode.")
    res = adapter.searchStudents("")
    print(f"Students in database: {len(json.loads(res))}")
    conn.close()


def _run_gui_mode(conn, adapter: StudentAdminAdapter) -> int:
    from PySide6.QtQuickControls2 import QQuickStyle
    from core.shared.mock_qt import apply_app_icon, register_bundled_fonts

    QQuickStyle.setStyle("Fusion")
    app = QGuiApplication(sys.argv)
    app.setApplicationVersion(APP_VERSION)
    apply_app_icon(app, "studentmanagement")
    register_bundled_fonts()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("studentAdmin", adapter)
    engine.rootContext().setContextProperty("searchStudents", adapter.searchStudents)
    base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    common_dir = os.path.join(base, "apps", "common_qml") if getattr(sys, "frozen", False) else os.path.join(base, "common_qml")
    qml_dir = os.path.join(base, "apps", "student_management_app", "qml") if getattr(sys, "frozen", False) else os.path.join(os.path.dirname(__file__), "qml")
    engine.addImportPath(common_dir)
    engine.addImportPath(os.path.dirname(common_dir))
    engine.load(os.path.join(qml_dir, "Main.qml"))
    if not engine.rootObjects():
        return -1
    return app.exec()


def main():
    setup_app_logging("SMTE-StudentManagement")
    default_path = str(get_default_db_path("SMTE-StudentManagement", "student.sqlite"))
    db_path = os.environ.get("STUDENT_DB_PATH", default_path)
    pin = os.environ.get("STUDENT_DB_PIN", "123456")
    conn = get_connection(db_path, pin=pin)
    apply_migrations(conn, db_path=db_path)
    adapter = StudentAdminAdapter(conn)
    if "--cli" in sys.argv or not HAVE_QT:
        _run_cli_mode(conn, adapter)
        return
    try:
        sys.exit(_run_gui_mode(conn, adapter))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
