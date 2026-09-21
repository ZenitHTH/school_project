"""Mock Qt types for non-Qt environments (fallback when PySide6 not available)."""

import sys


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