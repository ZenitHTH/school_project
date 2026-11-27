import importlib.util
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apps.common_linux_env import setup_linux_runtime_env

import json
import threading
from typing import Optional, Tuple
from core.network.lan_discovery import LanDiscoveryResponder
from core.network.lan_manager import LanServiceManager, _parse_port
from core.network.lan_server import BoothLanServer
from core.shared.version import APP_VERSION
from data.db import get_connection
from data.migrate import apply_migrations
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter

HAVE_QT = importlib.util.find_spec("PySide6") is not None


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


def _start_lan_services(
    conn, db_lock: Optional[threading.Lock] = None
) -> Tuple[Optional[BoothLanServer], Optional[LanDiscoveryResponder]]:
    """Start LAN HTTP and discovery services using environment overrides."""
    mgr = LanServiceManager(conn, config_path=None, db_lock=db_lock)
    mgr.start_with_env_overrides()
    return mgr.lan_server, mgr.discovery_responder


def _stop_lan_services(
    server: Optional[BoothLanServer], responder: Optional[LanDiscoveryResponder]
) -> None:
    """Stop LAN HTTP and discovery services cleanly."""
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


def _create_qml_engine(adapter: LibrarianAdminAdapter):
    from PySide6.QtQml import QQmlApplicationEngine
    from core.shared.mock_qt import register_startup_fonts

    register_startup_fonts()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("librarianAdmin", adapter)
    common_dir, qml_file = _resolve_qml_paths()
    engine.addImportPath(common_dir)
    engine.addImportPath(os.path.dirname(common_dir))
    return engine, qml_file


def _create_lan_manager(conn) -> LanServiceManager:
    """Resolve persisted LAN config path and start LanServiceManager."""
    config_path = os.environ.get("LIBRARIAN_LAN_CONFIG_PATH") or str(
        get_default_db_path("SMTE-LibrarianManagement", "lan_server_config.json")
    )
    lan_manager = LanServiceManager(conn, config_path=config_path, db_lock=threading.Lock())
    lan_manager.start_with_env_overrides()
    return lan_manager


def _create_qt_app():
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuickControls2 import QQuickStyle
    from core.shared.mock_qt import apply_app_icon

    QQuickStyle.setStyle("Fusion")
    app = QGuiApplication(sys.argv)
    app.setApplicationVersion(APP_VERSION)
    apply_app_icon(app, "librarianmanagement")
    return app


def _run_gui_mode(conn) -> int:
    setup_linux_runtime_env()
    lan_manager = _create_lan_manager(conn)
    adapter = LibrarianAdminAdapter(conn, lan_server=lan_manager.lan_server, lan_manager=lan_manager)
    app = _create_qt_app()
    engine, qml_file = _create_qml_engine(adapter)
    exit_code = -1
    try:
        engine.load(qml_file)
        if engine.rootObjects():
            exit_code = app.exec()
    finally:
        lan_manager.stop()
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
