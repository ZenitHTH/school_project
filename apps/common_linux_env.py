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

        # Force Mesa software rendering only when headless or explicitly requested,
        # allowing hardware OpenGL on normal desktop sessions.
        is_headless = (
            os.environ.get("QT_QPA_PLATFORM") == "offscreen"
            or (not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"))
        )
        force_software = os.environ.get("SMTE_SOFTWARE_RENDER") == "1" or is_headless

        if force_software:
            if "LIBGL_ALWAYS_SOFTWARE" not in os.environ:
                os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
            if "QT_QUICK_BACKEND" not in os.environ:
                os.environ["QT_QUICK_BACKEND"] = "software"

            try:
                from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
                QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)
            except Exception:
                pass
