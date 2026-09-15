import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data.db import get_connection
from data.migrate import apply_migrations
from apps.booth_app.adapters.booth_adapter import BoothAdapter

try:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


def main():
    db_path = os.environ.get("BOOTH_DB_PATH", "library.sqlite")
    pin = os.environ.get("BOOTH_DB_PIN", "123456")

    conn = get_connection(db_path, pin=pin)
    apply_migrations(conn)

    adapter = BoothAdapter(conn)

    if not HAVE_QT:
        print("[Self-Service Booth] PySide6 not installed. Running in CLI verification mode.")
        res = adapter.searchStudents("")
        print(f"Sample booth query: {res[:100]}...")
        conn.close()
        return

    from PySide6.QtQuickControls2 import QQuickStyle
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("boothAdapter", adapter)

    qml_file = os.path.join(os.path.dirname(__file__), "qml", "Main.qml")
    engine.load(qml_file)

    if not engine.rootObjects():
        sys.exit(-1)

    exit_code = app.exec()
    conn.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
