"""Thread-safe GUI, terminal, and file logging for pipeline runs."""

import logging
import logging.config
import os
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal


LOGFILE_NAME = os.getenv("LOGFILE_NAME", "gem_screening.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
SERVICE_NAME = "gem_screening"
MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 3


class LogEmitter(QObject):
    message = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    """Forward log records to Qt through a queued, thread-safe signal."""

    preserve_during_configuration = True

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__()
        self.emitter = LogEmitter(parent)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            self.handleError(record)
            return
        self.emitter.message.emit(message)


def configure_logging(
    run_dir: Path,
    *,
    log_level: str | None = None,
    logfile_name: str | None = None,
) -> None:
    """Configure terminal/file logging while preserving the GUI handler."""
    host_log_folder = run_dir / "logs"
    host_log_folder.mkdir(parents=True, exist_ok=True)
    level = (log_level or LOG_LEVEL).upper()
    filename = logfile_name or LOGFILE_NAME
    if Path(filename).name != filename:
        raise ValueError("Logfile name must be a filename, not a path")
    logfile_path = host_log_folder / filename

    root_logger = logging.getLogger()
    preserved_handlers = [
        handler
        for handler in root_logger.handlers
        if getattr(handler, "preserve_during_configuration", False)
    ]

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": level,
                },
                "rotating_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "standard",
                    "level": level,
                    "filename": str(logfile_path),
                    "mode": "a",
                    "maxBytes": MAX_BYTES,
                    "backupCount": BACKUP_COUNT,
                    "encoding": "utf-8",
                    "delay": True,
                },
            },
            "root": {
                "handlers": ["console", "rotating_file"],
                "level": level,
            },
        }
    )

    for handler in preserved_handlers:
        if handler not in root_logger.handlers:
            root_logger.addHandler(handler)


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(f"{SERVICE_NAME}.{name}" if name else SERVICE_NAME)
