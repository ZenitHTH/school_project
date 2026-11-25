"""Lifecycle and live configuration manager for Librarian LAN services."""

import os
import threading
from typing import Any, Dict, Optional

from core.network.lan_discovery import LanDiscoveryResponder
from core.network.lan_server import BoothLanServer
from core.network.lan_server_config import (
    default_lan_server_config,
    load_lan_server_config,
    save_lan_server_config,
)


def _parse_port(raw: Optional[str], default: int) -> int:
    """Parse an integer port in 0..65535 for startup/env overrides."""
    if not raw:
        return default
    try:
        port = int(raw)
        return port if 0 <= port <= 65535 else default
    except (TypeError, ValueError):
        return default


def _is_valid_gui_port(val: Any) -> bool:
    """Return True if val is an integer port in 1..65535 (excluding bool)."""
    return isinstance(val, int) and not isinstance(val, bool) and 1 <= val <= 65535


def _validate_gui_config(port: int, discovery_port: int, token: str) -> str:
    """Validate GUI/saved LAN config values and return error text or empty str."""
    if not _is_valid_gui_port(port):
        return "พอร์ต HTTP ต้องอยู่ระหว่าง 1-65535 (HTTP port must be 1-65535)"
    if not _is_valid_gui_port(discovery_port):
        return "พอร์ต Discovery UDP ต้องอยู่ระหว่าง 1-65535 (Discovery port must be 1-65535)"
    if port == discovery_port:
        return "พอร์ต HTTP และพอร์ต Discovery UDP ต้องไม่ซ้ำกัน (HTTP and discovery ports must differ)"
    if not isinstance(token, str) or not token.strip():
        return "กรุณาระบุ Token สำหรับเชื่อมต่อ (Token must not be empty)"
    return ""


def _server_is_running(server: Optional[Any]) -> bool:
    """Check whether a BoothLanServer (or mock) is actively listening."""
    if server is None:
        return False
    if hasattr(server, "running"):
        return bool(server.running)
    return getattr(server, "_httpd", None) is not None


def _safe_stop(svc: Optional[Any]) -> None:
    """Stop a network service without propagating cleanup exceptions."""
    if svc is not None:
        try:
            svc.stop()
        except Exception:
            pass


class LanServiceManager:
    """Manages BoothLanServer and LanDiscoveryResponder startup, status, and reload."""

    def __init__(
        self,
        conn: Any,
        config_path: Optional[str] = None,
        db_lock: Optional[threading.Lock] = None,
        lan_server: Optional[Any] = None,
    ) -> None:
        self.conn = conn
        self.config_path = config_path
        self.db_lock = db_lock or threading.Lock()
        self.lan_server: Optional[Any] = lan_server
        self.discovery_responder: Optional[LanDiscoveryResponder] = None
        self.config = self._load_base_config()
        self.last_error: str = ""

    def _load_base_config(self) -> Dict[str, Any]:
        if self.config_path:
            return load_lan_server_config(self.config_path)
        return default_lan_server_config()

    def start_with_env_overrides(self) -> Dict[str, Any]:
        """Load persisted config, apply LIBRARIAN_* / BOOTH_* env overrides, and start."""
        cfg = self._load_base_config()
        if os.environ.get("LIBRARIAN_LAN_DISABLED", "").strip() == "1":
            cfg["enabled"] = False
        cfg["port"] = _parse_port(os.environ.get("LIBRARIAN_LAN_PORT"), cfg["port"])
        cfg["discovery_port"] = _parse_port(
            os.environ.get("LIBRARIAN_DISCOVERY_PORT"), cfg["discovery_port"]
        )
        env_token = os.environ.get("BOOTH_SERVER_TOKEN")
        if env_token:
            cfg["token"] = env_token
        self.config = cfg
        if not cfg["enabled"]:
            self.stop()
            self.last_error = ""
            return self.status_dict()
        self.start()
        return self.status_dict()

    def _fail_start(
        self, exc: OSError, server: Optional[Any] = None, responder: Optional[Any] = None
    ) -> bool:
        _safe_stop(responder)
        _safe_stop(server)
        self.lan_server = None
        self.discovery_responder = None
        self.last_error = str(exc)
        return False

    def _start_responder(self, server: BoothLanServer) -> bool:
        responder = LanDiscoveryResponder(
            http_port=server.port,
            discovery_port=int(self.config["discovery_port"]),
        )
        try:
            responder.start()
        except OSError as exc:
            return self._fail_start(exc, server=server, responder=responder)
        self.lan_server = server
        self.discovery_responder = responder
        return True

    def start(self) -> bool:
        """Start HTTP LAN server and UDP discovery responder using current config."""
        self.stop()
        self.last_error = ""
        if not self.config.get("enabled", True):
            return True
        server = BoothLanServer(
            self.conn,
            port=int(self.config["port"]),
            token=str(self.config["token"]),
            db_lock=self.db_lock,
        )
        try:
            server.start()
        except OSError as exc:
            return self._fail_start(exc, server=server)
        return self._start_responder(server)

    def stop(self) -> None:
        """Stop both UDP discovery responder and HTTP LAN server cleanly."""
        _safe_stop(self.discovery_responder)
        _safe_stop(self.lan_server)
        self.discovery_responder = None
        self.lan_server = None

    def status_dict(self) -> Dict[str, Any]:
        """Return full LAN server status and configuration snapshot."""
        cfg = self.config
        server = self.lan_server
        running = _server_is_running(server)
        responder = self.discovery_responder
        disc_port = responder.discovery_port if responder is not None else cfg["discovery_port"]
        return {
            "ok": True,
            "running": running,
            "enabled": bool(cfg.get("enabled", True)),
            "ip": str(server.get_lan_ip()) if running else "",
            "port": int(server.port) if running else int(cfg["port"]),
            "discovery_port": int(disc_port) if running else int(cfg["discovery_port"]),
            "token": str(server.token) if running else str(cfg["token"]),
            "error": self.last_error,
        }

    def apply_config(self, enabled: bool, port: int, discovery_port: int, token: str) -> Dict[str, Any]:
        """Validate, save, and live-restart LAN services without leaving partial state."""
        err = _validate_gui_config(port, discovery_port, token)
        if err:
            return {**self.status_dict(), "ok": False, "error": err}
        new_cfg = {
            "enabled": bool(enabled), "port": int(port),
            "discovery_port": int(discovery_port), "token": token.strip(),
        }
        self.config = save_lan_server_config(self.config_path, new_cfg) if self.config_path else new_cfg
        self.stop()
        self.last_error = ""
        if not self.config["enabled"]:
            return self.status_dict()
        started = self.start()
        return {**self.status_dict(), "ok": bool(started)}
