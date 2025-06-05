import os
import logging.config

from gem_screening.config import HOST_LOG_FOLDER


LOGFILE_NAME    = os.getenv("LOGFILE_NAME", "gem_screening.log")
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO").upper()
SERVICE_NAME    = "gem_screening"

MAX_BYTES    = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 3

# Ensure the folder exists before configuring handlers:
LOGFILE_PATH = HOST_LOG_FOLDER.joinpath(LOGFILE_NAME)

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
            "filename": LOGFILE_PATH,
            "mode": "a",
            "maxBytes": MAX_BYTES,
            "backupCount": BACKUP_COUNT,
            "encoding": "utf-8",
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
