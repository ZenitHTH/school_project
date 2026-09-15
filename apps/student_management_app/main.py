import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data.db import get_connection
from data.migrate import apply_migrations
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter

try:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


def main():
    db_path = os.environ.get("STUDENT_DB_PATH", "student.sqlite")
    pin = os.environ.get("STUDENT_DB_PIN", "123456")

    conn = get_connection(db_path, pin=pin)
    apply_migrations(conn)

    adapter = StudentAdminAdapter(conn)

    if not HAVE_QT:
        print("[Student Management] PySide6 not installed. Running in CLI verification mode.")
        res = adapter.searchStudents("")
        print(f"Sample query result: {res[:100]}...")
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
