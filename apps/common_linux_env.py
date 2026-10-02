import os
import sys


def setup_linux_runtime_env() -> None:
    """Sanitize runtime environment for Linux bundles to avoid library/GLX crashes."""
    is_linux = sys.platform.startswith("linux")
    is_frozen = getattr(sys, "frozen", False)

    if is_linux:
        # Prevent PySide6 / host GIO collision where host libgvfscommon.so looks for
        # symbols not present in bundled GLib/GIO.
        if is_frozen:
            os.environ["GIO_MODULE_DIR"] = ""

        # Avoid Qt GLX / FBConfig failure on older drivers or headless environments.
        # Fall back to Mesa software rendering and Qt Quick software backend if not overridden.
        if "LIBGL_ALWAYS_SOFTWARE" not in os.environ:
            os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
        if "QT_QUICK_BACKEND" not in os.environ:
            os.environ["QT_QUICK_BACKEND"] = "software"

        try:
            from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
            QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)
        except Exception:
            pass
