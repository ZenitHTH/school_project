"""Mock Qt types for non-Qt environments and shared adapter utilities."""

import sys
from typing import Any, List, Set
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

_LOADED_FONTS: List[str] = []


def get_bundled_fonts_dir() -> str:
    """Return path to bundled font directory in source or frozen binary mode."""
    import os
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "apps", "common_qml", "fonts")
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "apps", "common_qml", "fonts")
    )


def _setup_font_substitutions() -> None:
    """Configure font substitutions for cross-platform compatibility."""
    from PySide6.QtGui import QFont
    QFont.insertSubstitution("Noto Sans", "Noto Sans Thai")
    QFont.insertSubstitution("Sarabun", "TH Sarabun New")
    QFont.insertSubstitution("Sarabun", "TH SarabunPSK")


def register_bundled_fonts() -> List[str]:
    """Register all project bundled fonts with QFontDatabase."""
    global _LOADED_FONTS
    if not HAVE_QT:
        return []
    if _LOADED_FONTS:
        return list(_LOADED_FONTS)

    import os
    from PySide6.QtGui import QFontDatabase
    font_dir = get_bundled_fonts_dir()
    if not os.path.isdir(font_dir):
        return []

    families = []
    for f in sorted(os.listdir(font_dir)):
        if f.lower().endswith((".ttf", ".ttc", ".otf")):
            fid = QFontDatabase.addApplicationFont(os.path.join(font_dir, f))
            if fid >= 0:
                families.extend(QFontDatabase.applicationFontFamilies(fid))

    _setup_font_substitutions()
    _LOADED_FONTS = families
    return list(_LOADED_FONTS)


def apply_qt_app_font(family: str, pixel_size: int) -> None:
    """Update application-level font family and pixel size."""
    if not HAVE_QT:
        return
    try:
        from PySide6.QtGui import QGuiApplication
        app = QGuiApplication.instance()
        if not app:
            return
        register_bundled_fonts()
        font = app.font()
        if family:
            font.setFamily(family)
        if pixel_size > 0:
            font.setPixelSize(pixel_size)
        app.setFont(font)
    except Exception:
        pass

