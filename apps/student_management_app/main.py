import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apps.common_linux_env import setup_linux_runtime_env

setup_linux_runtime_env()

import json
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

def main():
    default_path = str(get_default_db_path("SMTE-StudentManagement", "student.sqlite"))
    db_path = os.environ.get("STUDENT_DB_PATH", default_path)
    pin = os.environ.get("STUDENT_DB_PIN", "123456")

    conn = get_connection(db_path, pin=pin)
    apply_migrations(conn, db_path=db_path)


    adapter = StudentAdminAdapter(conn)

    if "--cli" in sys.argv or not HAVE_QT:
        if adapter.isFirstLaunch():
            if sys.stdin.isatty() and "--cli" in sys.argv:
                run_cli_first_launch(adapter)
            else:
                adapter.initializeBlankDatabase("CLI")
        if not HAVE_QT or "--cli" in sys.argv:
            print("[Student Management] Running in CLI mode.")
            res = adapter.searchStudents("")
            print(f"Students in database: {len(json.loads(res))}")
            conn.close()
            return

    from PySide6.QtQuickControls2 import QQuickStyle
    QQuickStyle.setStyle("Fusion")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("studentAdmin", adapter)
    engine.rootContext().setContextProperty("searchStudents", adapter.searchStudents)

    common_qml_dir = os.path.join(sys._MEIPASS, "apps", "common_qml") \
        if getattr(sys, "frozen", False) else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common_qml"))
    engine.addImportPath(common_qml_dir)
    engine.addImportPath(os.path.dirname(common_qml_dir))

    qml_dir = os.path.join(sys._MEIPASS, "apps", "student_management_app", "qml") \
        if getattr(sys, "frozen", False) else os.path.join(os.path.dirname(__file__), "qml")
    qml_file = os.path.join(qml_dir, "Main.qml")
    engine.load(qml_file)

    if not engine.rootObjects():
        sys.exit(-1)

    exit_code = app.exec()
    conn.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
