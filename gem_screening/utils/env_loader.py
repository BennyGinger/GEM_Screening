# gem_screening/utils/env_loader.py
import os
from dotenv import load_dotenv


FASTAPI_BASE_URL = "http://localhost:8000"
DEFAULT_LOG_LEVEL = "INFO"
LOGFILE_NAME = "gem_screening.log"
HOST_LOG_FOLDER = "./logs"

TEMPLATE = """\
# ⚠️ Please review and customize before running:
FASTAPI_BASE_URL=http://localhost:8000

#----------- LOGGING CONFIGURATION -----------
# Control logging verbosity: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
LOGFILE_NAME=gem_screening.log
HOST_LOG_FOLDER=./logs
"""

def load_pipeline_env(
    root_dir: str,
    fastapi_url: str | None = None,
    log_level: str | None = None,
    logfile_name: str | None = None,
    host_log_folder: str | None = None,
                    ) -> None:
    
    """
    Load environment variables for the pipeline from a .env file.
    If the .env file does not exist, it creates a template and raises an error.
    This function sets the following environment variables:
    - FASTAPI_BASE_URL: URL for the FastAPI server
    - LOG_LEVEL: Logging level for the application
    - LOGFILE_NAME: Name of the log file   
    - HOST_LOG_FOLDER: Directory where logs will be stored
    Args:
        fastapi_url (str | None): URL for the FastAPI server. If None, uses the value from .env or defaults to "http://localhost:8000".
        log_level (str | None): Logging level to set. If None, uses the value from .env or defaults to "INFO".
        logfile_name (str | None): Name of the log file. If None, uses the value from .env or defaults to "gem_screening.log".
        host_log_folder (str | None): Directory where logs will be stored. If None, uses the HOST_LOG_FOLDER constant.
    """
    env_path = root_dir.joinpath(".env")
    if not env_path.exists():
        env_path.write_text(TEMPLATE)
        raise FileNotFoundError(
            f".env not found; template created at {env_path}. Please update it and rerun.")

    load_dotenv(env_path, override=False)

    # set FASTAPI_BASE_URL
    if fastapi_url:
        base_url = fastapi_url
    else:
        base_url = os.getenv("FASTAPI_BASE_URL", FASTAPI_BASE_URL)
    os.environ["FASTAPI_BASE_URL"] = base_url

    # set LOG_LEVEL (override first, then file, then default)
    if log_level:
        lvl = log_level.upper()
    else:
        lvl = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    os.environ["LOG_LEVEL"] = lvl

    # set LOGFILE_NAME
    if logfile_name:
        log_file = logfile_name
    else:
        log_file = os.getenv("LOGFILE_NAME", LOGFILE_NAME)
    os.environ["LOGFILE_NAME"] = log_file
    
    # set HOST_LOG_FOLDER
    if host_log_folder:
        log_folder = host_log_folder
    else:
        log_folder = str(HOST_LOG_FOLDER)
    os.environ["HOST_LOG_FOLDER"] = log_folder



