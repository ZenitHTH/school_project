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


from data.paths import get_default_db_path

def main():
    default_path = str(get_default_db_path("SMTE-Booth", "library.sqlite"))
    db_path = os.environ.get("BOOTH_DB_PATH", default_path)
    pin = os.environ.get("BOOTH_DB_PIN", "123456")

    conn = get_connection(db_path, pin=pin)
    apply_migrations(conn, db_path=db_path)


    adapter = BoothAdapter(conn)

    if adapter.isDatabaseEmpty():
        print("[Self-Service Booth] Warning: Database is empty. Please sync student records in Librarian App.")

    if not HAVE_QT:
        print("[Self-Service Booth] PySide6 not installed. Running in CLI verification mode.")
        res = adapter.searchStudents("")
        print(f"Sample booth query: {res[:100]}...")
        conn.close()
        return

    from PySide6.QtQuickControls2 import QQuickStyle
    QQuickStyle.setStyle("Fusion")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("boothAdapter", adapter)

    qml_dir = os.path.join(sys._MEIPASS, "apps", "booth_app", "qml") \
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
