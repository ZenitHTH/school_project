"""JSON configuration persistence for Librarian embedded LAN server settings."""

import json
import os
from typing import Any, Dict, Optional

from core.network.booth_config import (
    DEFAULT_BOOTH_TOKEN,
    DEFAULT_DISCOVERY_PORT,
    DEFAULT_LAN_PORT,
)


def default_lan_server_config() -> Dict[str, Any]:
    """Return a fresh default Librarian LAN server config dictionary."""
    return {
        "enabled": True,
        "port": DEFAULT_LAN_PORT,
        "discovery_port": DEFAULT_DISCOVERY_PORT,
        "token": DEFAULT_BOOTH_TOKEN,
    }


def _parse_valid_port(raw: Any, default: int) -> int:
    """Return an integer port in 1..65535, falling back to default."""
    if isinstance(raw, bool):
        return default
    try:
        port = int(raw)
        return port if 1 <= port <= 65535 else default
    except (TypeError, ValueError):
        return default


def _normalize_config(raw: Any) -> Dict[str, Any]:
    """Coerce parsed JSON mapping into a validated LAN server config dict."""
    cfg = default_lan_server_config()
    if not isinstance(raw, dict):
        return cfg
    if isinstance(raw.get("enabled"), bool):
        cfg["enabled"] = raw["enabled"]
    cfg["port"] = _parse_valid_port(raw.get("port"), DEFAULT_LAN_PORT)
    cfg["discovery_port"] = _parse_valid_port(raw.get("discovery_port"), DEFAULT_DISCOVERY_PORT)
    token = raw.get("token")
    if isinstance(token, str) and token.strip():
        cfg["token"] = token.strip()
    return cfg


def load_lan_server_config(path: Optional[str]) -> Dict[str, Any]:
    """Load Librarian LAN server config from JSON, falling back to defaults."""
    if not path or not os.path.exists(path):
        return default_lan_server_config()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return _normalize_config(json.load(fh))
    except (OSError, ValueError, TypeError):
        return default_lan_server_config()


def save_lan_server_config(path: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Persist Librarian LAN server config as UTF-8 JSON and return normalized dict."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    normalized = _normalize_config(cfg)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(normalized, fh, indent=2, ensure_ascii=False)
    if os.name == "posix":
        os.chmod(path, 0o600)
    return normalized
