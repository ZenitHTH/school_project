import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json
from data.db import get_connection
from data.migrate import apply_migrations
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter

try:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


def run_cli_first_launch(adapter: LibrarianAdminAdapter) -> None:
    """Handle first launch interactively in terminal mode."""
    print("=" * 60)
    print("📚 Library Management System — First Launch Setup")
    print("=" * 60)
    print("No books or student records found in database.")
    try:
        ans = input("Do you have a student snapshot (.sqlite) or roster (.xlsx) file? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"
    if ans == "y":
        try:
            path = input("Enter path to file (.sqlite or .xlsx): ").strip()
        except (EOFError, KeyboardInterrupt):
            path = ""
        if path and os.path.exists(path):
            res = json.loads(adapter.importRoster(path, actor="CLI"))
            if res.get("ok"):
                print("✓ Imported/synced records successfully.")
            else:
                print(f"✗ Import failed: {res.get('error')}")
        else:
            print("File not found or empty path. Initializing blank library database instead.")
            adapter.initializeBlankDatabase("CLI")
    else:
        adapter.initializeBlankDatabase("CLI")
        print("✓ Created blank library database following table rules.")


def main():
    db_path = os.environ.get("LIBRARY_DB_PATH", "library.sqlite")
    pin = os.environ.get("LIBRARY_DB_PIN", "123456")

    conn = get_connection(db_path, pin=pin)
    apply_migrations(conn)

    adapter = LibrarianAdminAdapter(conn)

    if "--cli" in sys.argv or not HAVE_QT:
        if adapter.isFirstLaunch():
            if sys.stdin.isatty() and "--cli" in sys.argv:
                run_cli_first_launch(adapter)
            else:
                adapter.initializeBlankDatabase("CLI")
        if not HAVE_QT or "--cli" in sys.argv:
            print("[Librarian Management] Running in CLI mode.")
            res = adapter.searchBooks("")
            print(f"Books in catalog: {len(json.loads(res))}")
            conn.close()
            return

    from PySide6.QtQuickControls2 import QQuickStyle
    QQuickStyle.setStyle("Fusion")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("librarianAdmin", adapter)

    qml_dir = os.path.join(sys._MEIPASS, "apps", "librarian_management_app", "qml") \
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
