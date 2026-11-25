import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apps.common_linux_env import setup_linux_runtime_env

setup_linux_runtime_env()

import json
import logging
import threading
from typing import Optional, Tuple
from core.network.booth_config import DEFAULT_BOOTH_TOKEN, DEFAULT_DISCOVERY_PORT, DEFAULT_LAN_PORT
from core.network.lan_discovery import LanDiscoveryResponder
from core.network.lan_server import BoothLanServer
from core.shared.version import APP_VERSION
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


from data.paths import get_default_db_path
from core.shared.app_logging import setup_app_logging


def _parse_port(raw: Optional[str], default: int) -> int:
    if not raw:
        return default
    try:
        port = int(raw)
        return port if 0 <= port <= 65535 else default
    except ValueError:
        return default


def _start_responder(http_port: int, disc_port: int) -> Optional[LanDiscoveryResponder]:
    responder = LanDiscoveryResponder(http_port=http_port, discovery_port=disc_port)
    try:
        responder.start()
        return responder
    except OSError as exc:
        logging.getLogger(__name__).warning("Failed to start LanDiscoveryResponder: %s", exc)
        return None


def _start_lan_services(
    conn, db_lock: Optional[threading.Lock] = None
) -> Tuple[Optional[BoothLanServer], Optional[LanDiscoveryResponder]]:
    if os.environ.get("LIBRARIAN_LAN_DISABLED", "").strip() == "1":
        return None, None
    port = _parse_port(os.environ.get("LIBRARIAN_LAN_PORT"), DEFAULT_LAN_PORT)
    disc_port = _parse_port(os.environ.get("LIBRARIAN_DISCOVERY_PORT"), DEFAULT_DISCOVERY_PORT)
    token = os.environ.get("BOOTH_SERVER_TOKEN") or DEFAULT_BOOTH_TOKEN
    server = BoothLanServer(conn, port=port, token=token, db_lock=db_lock or threading.Lock())
    try:
        server.start()
    except OSError as exc:
        logging.getLogger(__name__).warning("Failed to start BoothLanServer on port %s: %s", port, exc)
        return None, None
    return server, _start_responder(server.port, disc_port)


def _stop_lan_services(
    server: Optional[BoothLanServer], responder: Optional[LanDiscoveryResponder]
) -> None:
    for svc in (responder, server):
        if svc is not None:
            try:
                svc.stop()
            except Exception:
                pass


def _run_cli_mode(conn) -> None:
    adapter = LibrarianAdminAdapter(conn)
    if adapter.isFirstLaunch():
        if sys.stdin.isatty() and "--cli" in sys.argv:
            run_cli_first_launch(adapter)
        else:
            adapter.initializeBlankDatabase("CLI")
    print("[Librarian Management] Running in CLI mode.")
    res = adapter.searchBooks("")
    print(f"Books in catalog: {len(json.loads(res))}")
    conn.close()


def _resolve_qml_paths() -> Tuple[str, str]:
    if getattr(sys, "frozen", False):
        common_dir = os.path.join(sys._MEIPASS, "apps", "common_qml")
        qml_dir = os.path.join(sys._MEIPASS, "apps", "librarian_management_app", "qml")
    else:
        common_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common_qml"))
        qml_dir = os.path.join(os.path.dirname(__file__), "qml")
    return common_dir, os.path.join(qml_dir, "Main.qml")


def _run_gui_mode(conn) -> int:
    from PySide6.QtQuickControls2 import QQuickStyle
    from core.shared.mock_qt import register_bundled_fonts

    QQuickStyle.setStyle("Fusion")
    lan_server, discovery = _start_lan_services(conn, threading.Lock())
    adapter = LibrarianAdminAdapter(conn, lan_server=lan_server)
    app = QGuiApplication(sys.argv)
    app.setApplicationVersion(APP_VERSION)
    register_bundled_fonts()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("librarianAdmin", adapter)
    common_dir, qml_file = _resolve_qml_paths()
    engine.addImportPath(common_dir)
    engine.addImportPath(os.path.dirname(common_dir))
    exit_code = -1
    try:
        engine.load(qml_file)
        if engine.rootObjects():
            exit_code = app.exec()
    finally:
        _stop_lan_services(lan_server, discovery)
        conn.close()
    return exit_code


def main():
    setup_app_logging("SMTE-LibrarianManagement")
    default_path = str(get_default_db_path("SMTE-LibrarianManagement", "library.sqlite"))
    db_path = os.environ.get("LIBRARY_DB_PATH", default_path)
    pin = os.environ.get("LIBRARY_DB_PIN", "123456")
    is_cli = "--cli" in sys.argv or not HAVE_QT

    conn = get_connection(db_path, pin=pin, check_same_thread=is_cli)
    apply_migrations(conn, db_path=db_path)
    if is_cli:
        _run_cli_mode(conn)
        return
    sys.exit(_run_gui_mode(conn))


if __name__ == "__main__":
    main()
