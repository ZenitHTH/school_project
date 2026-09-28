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
        # Fall back to Mesa software rendering if not explicitly overridden by user.
        if "LIBGL_ALWAYS_SOFTWARE" not in os.environ:
            os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
