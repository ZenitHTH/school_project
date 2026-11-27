"""Entrypoint for the Self-Service Booth thin LAN client application."""

import importlib.util
import os
import sys
from typing import Any, Dict

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apps.common_linux_env import setup_linux_runtime_env
from apps.booth_app.adapters.booth_adapter import BoothAdapter
from core.network.booth_config import load_booth_config
from core.network.lan_client import BoothLanClient
from core.network.lan_discovery import discover_librarian
from core.shared.version import APP_VERSION
from data.paths import get_default_db_path

HAVE_QT = importlib.util.find_spec("PySide6") is not None


def _apply_env_overrides(cfg: Dict[str, Any]) -> str:
    env_host = os.environ.get("BOOTH_SERVER_HOST", "").strip()
    env_port = os.environ.get("BOOTH_SERVER_PORT", "").strip()
    env_token = os.environ.get("BOOTH_SERVER_TOKEN", "").strip()
    if env_host:
        cfg["host"] = env_host
    if env_port:
        try:
            port_val = int(env_port)
            if 1 <= port_val <= 65535:
                cfg["port"] = port_val
        except ValueError:
            pass
    if env_token:
        cfg["token"] = env_token
    return env_port


def resolve_booth_lan_config(config_path: str, discover: bool = True) -> Dict[str, Any]:
    """Load booth_config.json, apply env overrides, and optionally auto-discover if host is empty."""
    cfg = load_booth_config(config_path)
    env_port = _apply_env_overrides(cfg)
    if discover and not cfg["host"]:
        found = discover_librarian()
        if found:
            cfg["host"] = str(found.get("host", ""))
            if not env_port and isinstance(found.get("port"), int):
                cfg["port"] = found["port"]
    return cfg


def _resource_dir(*parts: str) -> str:
    base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if getattr(sys, "frozen", False):
        return os.path.join(base, "apps", *parts)
    return os.path.join(base, *parts)


def _run_qt_app(adapter: BoothAdapter) -> int:
    setup_linux_runtime_env()
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from core.shared.mock_qt import apply_app_icon, register_startup_fonts

    QQuickStyle.setStyle("Fusion")
    app = QGuiApplication(sys.argv)
    app.setApplicationVersion(APP_VERSION)
    apply_app_icon(app, "boothapp")
    register_startup_fonts()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("boothAdapter", adapter)
    common_qml_dir = _resource_dir("common_qml")
    engine.addImportPath(common_qml_dir)
    engine.addImportPath(os.path.dirname(common_qml_dir))
    engine.load(os.path.join(_resource_dir("booth_app", "qml"), "Main.qml"))
    if not engine.rootObjects():
        return -1
    return app.exec()


def main() -> None:
    """Launch the Booth LAN client in GUI mode (or CLI probe when PySide6 is absent)."""
    is_cli = "--cli" in sys.argv or not HAVE_QT
    config_path = str(get_default_db_path("SMTE-Booth", "booth_config.json"))
    cfg = resolve_booth_lan_config(config_path, discover=is_cli)
    client = BoothLanClient(host=cfg["host"], port=cfg["port"], token=cfg["token"])
    adapter = BoothAdapter(client=client, config_path=config_path)
    try:
        if is_cli:
            if adapter.isDatabaseEmpty():
                print("[Self-Service Booth] Warning: Server database is empty.")
            print("[Self-Service Booth] Running in CLI verification mode.")
            print(f"Connection status: {adapter.getConnectionStatus()}")
            return
        sys.exit(_run_qt_app(adapter))
    finally:
        adapter.close()


if __name__ == "__main__":
    main()
