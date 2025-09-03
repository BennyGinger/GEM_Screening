import os
import logging.config
from pathlib import Path


LOGFILE_NAME    = os.getenv("LOGFILE_NAME", "gem_screening.log")
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO").upper()
SERVICE_NAME    = "gem_screening"

MAX_BYTES    = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 3

def configure_logging(run_dir: Path):
    """
    Call this _once_ at runtime, after you've chosen your run_dir.
    This function sets up the logging configuration for the application.
    Args:
        run_dir (Path): The directory where `/logs` folder will created to store logfiles.
    """
    # ensure the folder exists
    host_log_folder = run_dir.joinpath("logs")
    if not host_log_folder.exists():
        # If the logs folder does not exist, create it
        host_log_folder.mkdir(parents=True, exist_ok=True)
    logfile_path = host_log_folder / LOGFILE_NAME

    logging.config.dictConfig({
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
                "level": LOG_LEVEL,
            },
            "rotating_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "level": LOG_LEVEL,
                "filename": str(logfile_path),
                "mode": "a",
                "maxBytes": MAX_BYTES,
                "backupCount": BACKUP_COUNT,
                "encoding": "utf-8",
                # Add delay to prevent file locking issues with Docker containers
                "delay": True,
            },
        },

        "root": {
            "handlers": ["console", "rotating_file"],
            "level": LOG_LEVEL,
        },
    })

def get_logger(name: str | None = None) -> logging.Logger:
    base = SERVICE_NAME
    return logging.getLogger(f"{base}.{name}") if name else logging.getLogger(base)
