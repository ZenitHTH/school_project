import os
import sys
from pathlib import Path

try:
    import platformdirs
except ImportError:
    platformdirs = None  # type: ignore[assignment]


def _fallback_app_dir(app_name: str, kind: str) -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local"))
        return base / app_name / "logs" if kind == "logs" else base / app_name
    if sys.platform == "darwin":
        sub = "Logs" if kind == "logs" else "Application Support"
        return Path.home() / "Library" / sub / app_name
    if kind == "logs":
        base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
        return base / app_name / "logs"
    base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / app_name


def get_app_data_dir(app_name: str) -> Path:
    """Return OS-appropriate per-app data directory, creating it if needed."""
    if platformdirs is not None:
        return platformdirs.user_data_path(appname=app_name, appauthor=False, ensure_exists=True)
    p = _fallback_app_dir(app_name, "data")
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_app_log_dir(app_name: str) -> Path:
    """Return OS-appropriate per-app log directory, creating it if needed."""
    if platformdirs is not None:
        return platformdirs.user_log_path(appname=app_name, appauthor=False, ensure_exists=True)
    p = _fallback_app_dir(app_name, "logs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_default_db_path(app_name: str, db_filename: str) -> Path:
    """Return standard default database path inside the app data directory."""
    return get_app_data_dir(app_name) / db_filename


def get_default_download_dir() -> Path:
    """Return user's Downloads folder for importing student snapshot received via LINE."""
    if platformdirs is not None:
        return platformdirs.user_downloads_path()
    return Path.home() / "Downloads"


def get_default_documents_dir() -> Path:
    """Return user's Documents folder for exporting student snapshot or label PDFs."""
    if platformdirs is not None:
        return platformdirs.user_documents_path()
    return Path.home() / "Documents"
