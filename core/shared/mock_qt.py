"""Mock Qt types for non-Qt environments and shared adapter utilities."""

import sys
from typing import Any, Set
from urllib.parse import unquote, urlparse

NUMERIC_KEYS: Set[str] = {
    "student_id", "academic_year", "semester", "room", "seq_no",
    "total_copies", "available_copies", "book_id", "copy_id",
    "loan_id", "fine_id", "reservation_id", "old_id", "new_id",
    "category_id",
}


def _sanitize_for_qml(obj: Any) -> Any:
    """Convert None values to typed defaults to prevent QML null role and type mismatch warnings."""
    if isinstance(obj, list):
        return [_sanitize_for_qml(item) for item in obj]
    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            if v is None:
                res[k] = 0 if k in NUMERIC_KEYS else ""
            elif isinstance(v, (dict, list)):
                res[k] = _sanitize_for_qml(v)
            else:
                res[k] = v
        return res
    return obj


def normalize_file_path(file_path: str) -> str:
    """Normalize local file path or file:// URL (including percent-encoded paths)."""
    if not file_path:
        return ""
    clean = file_path.strip()
    if clean.startswith("file://"):
        parsed = urlparse(clean)
        path = unquote(parsed.path)
        if len(path) >= 3 and path[0] == "/" and path[1].isalpha() and path[2] == ":":
            path = path[1:]
        return path
    return clean


class QObject:
    """Minimal QObject-like base class for adapters."""
    pass


def Slot(*types, **kwargs):
    """No-op decorator — returns original function unchanged."""
    def decorator(fn):
        return fn
    return decorator


def Signal(*types):
    """Returns a mock signal that does nothing when emitted."""
    class _MockSignal:
        def emit(self, *args, **kwargs):
            pass
    return _MockSignal()


# Check at module load time if Qt is available
try:
    from PySide6.QtCore import QObject as _RealQObject, Signal as _RealSignal, Slot as _RealSlot
    HAVE_QT = True

    # Use the real Qt types when available
    QObject = _RealQObject
    Signal = _RealSignal  
    Slot = _RealSlot

except ImportError:
    HAVE_QT = False