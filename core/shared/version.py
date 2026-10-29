import os
import sys


DEFAULT_VERSION = "1.1.0"


def _resolve_version_file() -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    return os.path.join(base, "VERSION")


def get_version() -> str:
    """Return canonical application semantic version string."""
    version_path = _resolve_version_file()
    if os.path.exists(version_path):
        with open(version_path, "r", encoding="utf-8") as f:
            ver = f.read().strip()
            if ver:
                return ver
    return DEFAULT_VERSION


APP_VERSION = get_version()
