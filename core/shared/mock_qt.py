"""Mock Qt types for non-Qt environments and shared adapter utilities."""

import sys
from typing import Any, List, Optional, Set
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
_LOADED_FONT_FILES: Set[str] = set()
_SUBSTITUTIONS_CONFIGURED = False


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
    global _SUBSTITUTIONS_CONFIGURED
    if _SUBSTITUTIONS_CONFIGURED:
        return
    from PySide6.QtGui import QFont
    QFont.insertSubstitution("Noto Sans", "Noto Sans Thai")
    QFont.insertSubstitution("Sarabun", "TH Sarabun New")
    QFont.insertSubstitution("Sarabun", "TH SarabunPSK")
    _SUBSTITUTIONS_CONFIGURED = True


def _load_font_files(prefixes: Optional[tuple] = None) -> List[str]:
    """Load matching font files from bundled fonts dir without duplicating loaded files."""
    if not HAVE_QT:
        return []
    import os
    from PySide6.QtGui import QFontDatabase

    font_dir = get_bundled_fonts_dir()
    if not os.path.isdir(font_dir):
        return []

    for f in sorted(os.listdir(font_dir)):
        if not f.lower().endswith((".ttf", ".ttc", ".otf")):
            continue
        if prefixes and not any(f.lower().startswith(p) for p in prefixes):
            continue
        full_path = os.path.join(font_dir, f)
        if full_path in _LOADED_FONT_FILES:
            continue
        fid = QFontDatabase.addApplicationFont(full_path)
        _LOADED_FONT_FILES.add(full_path)
        if fid >= 0:
            for fam in QFontDatabase.applicationFontFamilies(fid):
                if fam not in _LOADED_FONTS:
                    _LOADED_FONTS.append(fam)

    _setup_font_substitutions()
    return list(_LOADED_FONTS)


def register_startup_fonts(preferred_family: str = "") -> List[str]:
    """Register minimal startup fonts (Noto Sans Thai + configured family if any)."""
    prefixes = ["notosansthai"]
    fam_norm = (preferred_family or "").strip().lower().replace(" ", "")
    if fam_norm and fam_norm != "systemdefault":
        if "sarabun" in fam_norm:
            prefixes.append("thsarabun")
        elif "tahoma" in fam_norm:
            prefixes.append("tahoma")
        elif "sukhumvit" in fam_norm:
            prefixes.append("sukhumvit")
    return _load_font_files(tuple(prefixes))


def register_bundled_fonts() -> List[str]:
    """Register all project bundled fonts with QFontDatabase."""
    return _load_font_files(None)


def apply_qt_app_font(family: str, pixel_size: int) -> None:
    """Update application-level font family and pixel size."""
    if not HAVE_QT:
        return
    try:
        from PySide6.QtGui import QGuiApplication
        app = QGuiApplication.instance()
        if not app:
            return
        if family and family != "System Default":
            register_bundled_fonts()
        else:
            register_startup_fonts(family)
        font = app.font()
        if family:
            font.setFamily(family)
        if pixel_size > 0:
            font.setPixelSize(pixel_size)
        app.setFont(font)
    except Exception:
        pass


def apply_app_icon(app: Any, icon_stem: str) -> None:
    """Set QGuiApplication window icon from bundled assets/icons/<icon_stem>.png."""
    if not HAVE_QT or app is None or not icon_stem:
        return
    import os
    base = sys._MEIPASS if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    icon_path = os.path.join(base, "assets", "icons", f"{icon_stem}.png")
    if not os.path.isfile(icon_path):
        return
    try:
        from PySide6.QtGui import QGuiApplication, QIcon
        if QGuiApplication.instance() is None:
            return
        app.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass

