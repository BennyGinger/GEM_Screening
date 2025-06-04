import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

HOST_LOG_FOLDER = os.getenv("HOST_LOG_FOLDER", "./logs")
LOGFILE_NAME = os.getenv("LOGFILE_NAME", "gem_screening.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
SERVICE_NAME = "gem_screening"

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 3  # Keep 3 backup files

def _configure_logger() -> None:
    """
    Configure the root logger so that:
        - Matches the LOG_LEVEL environment variable throughout the pipeline
        - Both servers FastAPI and Celery log to the same file
    """
    logfile = Path(HOST_LOG_FOLDER).joinpath(LOGFILE_NAME)

    root = logging.getLogger()  # or use a named logger if you prefer
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    handlers = [type(h) for h in root.handlers]

    # 1) Ensure there's a StreamHandler (so you see FastAPI logs in docker logs)
    if logging.StreamHandler not in handlers:
        sh = logging.StreamHandler()  # defaults to stdout
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        sh.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
        root.addHandler(sh)

    # 2) Ensure there's a FileHandler writing to /app/logs/fastapi_combined.log
    if not any(isinstance(h, logging.FileHandler) for h in root.handlers):
        rfh = RotatingFileHandler(
                                  filename=str(logfile),
                                  maxBytes=MAX_BYTES,
                                  backupCount=BACKUP_COUNT,
                                  encoding="utf-8",)  # opens in 'a' mode by default
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        rfh.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
        root.addHandler(rfh)
        
def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger with the specified name, or the root logger if no name is provided.
    The logger will be configured to log to both stdout and a file.
    """
    _configure_logger()  # Ensure logging is set up before returning the logger
    base = SERVICE_NAME
    return logging.getLogger(f"{base}.{name}") if name else logging.getLogger(base)

