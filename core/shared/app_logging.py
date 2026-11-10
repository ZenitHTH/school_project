"""Application-wide logging bootstrap.

Configures the shared "smte" logger once per process:
- rotating file (1 MB x 3) in the OS log dir for the app (data.paths.get_app_log_dir)
- stderr handler at WARNING, so errors also show in the launching terminal

All service loggers use the "smte.*" namespace (e.g. "smte.isbn") so every
record lands in the app's log file. Idempotent: safe to call at startup.
"""
import logging
import logging.handlers

from data.paths import get_app_log_dir

FMT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3


def setup_app_logging(app_name: str) -> logging.Logger:
    """Configure the shared "smte" logger for this app. Returns the logger.

    app_name selects the log directory/file only (one process = one app).
    """
    root = logging.getLogger("smte")
    if getattr(root, "_smte_app", None) == app_name:
        return root
    log_dir = get_app_log_dir(app_name)
    log_dir.mkdir(parents=True, exist_ok=True)  # get_app_log_dir already does this; belt and braces
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(FMT, DATE_FMT))
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter(FMT, DATE_FMT))
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(stderr_handler)
    root.propagate = False  # keep the root "lastResort" handler from duplicating
    root._smte_app = app_name  # type: ignore[attr-defined]
    root.info("logging initialized: file=%s", file_handler.baseFilename)
    return root