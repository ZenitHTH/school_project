import os
import sys
from pathlib import Path
from typing import Optional

try:
    import platformdirs
    HAVE_PLATFORMDIRS = True
except ImportError:
    HAVE_PLATFORMDIRS = False


def get_app_data_dir(app_name: str) -> Path:
    """
    Return OS-appropriate per-app data directory.
    Follows platformdirs standard (Windows: %LOCALAPPDATA%\\<app>,
    Linux: ~/.local/share/<app>, macOS: ~/Library/Application Support/<app>).
    Falls back to stdlib/env if platformdirs is not installed.
    """
    if HAVE_PLATFORMDIRS:
        path_str = platformdirs.user_data_dir(appname=app_name, appauthor=False)
        p = Path(path_str)
    else:
        # Fallback without platformdirs
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
            p = Path(base) / app_name
        elif sys.platform == "darwin":
            p = Path.home() / "Library" / "Application Support" / app_name
        else:
            base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
            p = Path(base) / app_name

    p.mkdir(parents=True, exist_ok=True)
    return p


def get_app_log_dir(app_name: str) -> Path:
    """
    Return OS-appropriate per-app log directory.
    (Windows: %LOCALAPPDATA%\\<app>\\logs, Linux: ~/.local/state/<app>/logs, macOS: ~/Library/Logs/<app>).
    """
    if HAVE_PLATFORMDIRS:
        path_str = platformdirs.user_log_dir(appname=app_name, appauthor=False)
        p = Path(path_str)
    else:
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
            p = Path(base) / app_name / "logs"
        elif sys.platform == "darwin":
            p = Path.home() / "Library" / "Logs" / app_name
        else:
            base = os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
            p = Path(base) / app_name / "logs"

    p.mkdir(parents=True, exist_ok=True)
    return p


def get_default_db_path(app_name: str, db_filename: str) -> Path:
    """
    Return standard default database path inside app data directory.
    Honors environment variable overrides if provided.
    """
    return get_app_data_dir(app_name) / db_filename


def get_default_download_dir() -> Path:
    """
    Return user's Downloads folder for importing student snapshot received via LINE.
    """
    if HAVE_PLATFORMDIRS:
        return Path(platformdirs.user_downloads_dir())
    return Path.home() / "Downloads"


def get_default_documents_dir() -> Path:
    """
    Return user's Documents folder for exporting student snapshot or label PDFs.
    """
    if HAVE_PLATFORMDIRS:
        return Path(platformdirs.user_documents_dir())
    return Path.home() / "Documents"
