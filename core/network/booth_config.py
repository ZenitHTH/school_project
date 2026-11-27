"""JSON configuration persistence for Booth LAN connection settings."""

import json
import os
from typing import Any, Dict

DEFAULT_LAN_PORT = 8765
DEFAULT_DISCOVERY_PORT = 8766
DEFAULT_BOOTH_TOKEN = "123456"


def _default_config() -> Dict[str, Any]:
    """Return a fresh default Booth LAN config dictionary."""
    return {
        "host": "",
        "port": DEFAULT_LAN_PORT,
        "token": DEFAULT_BOOTH_TOKEN,
    }


def _normalize_config(raw: Any) -> Dict[str, Any]:
    """Coerce parsed JSON mapping into a valid Booth LAN config dictionary."""
    cfg = _default_config()
    if not isinstance(raw, dict):
        return cfg
    if isinstance(raw.get("host"), str):
        cfg["host"] = raw["host"].strip()
    try:
        port = int(raw.get("port", DEFAULT_LAN_PORT))
        if 1 <= port <= 65535:
            cfg["port"] = port
    except (TypeError, ValueError):
        pass
    token = raw.get("token")
    if isinstance(token, str) and token:
        cfg["token"] = token
    return cfg


def load_booth_config(path: str) -> Dict[str, Any]:
    """Load Booth LAN config from JSON, falling back to defaults if missing or corrupt."""
    if not path or not os.path.exists(path):
        return _default_config()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return _normalize_config(json.load(fh))
    except (OSError, ValueError, TypeError):
        return _default_config()


def save_booth_config(path: str, config: Dict[str, Any]) -> None:
    """Persist Booth LAN config as UTF-8 JSON, creating parent directories if needed."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    normalized = _normalize_config(config)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(normalized, fh, indent=2, ensure_ascii=False)
    if os.name == "posix":
        os.chmod(path, 0o600)
