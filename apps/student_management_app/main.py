import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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


def main():
    db_path = os.environ.get("STUDENT_DB_PATH", "student.sqlite")
    pin = os.environ.get("STUDENT_DB_PIN", "123456")

    conn = get_connection(db_path, pin=pin)
    apply_migrations(conn)

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
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("studentAdmin", adapter)

    qml_file = os.path.join(os.path.dirname(__file__), "qml", "Main.qml")
    engine.load(qml_file)

    if not engine.rootObjects():
        sys.exit(-1)

    exit_code = app.exec()
    conn.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
