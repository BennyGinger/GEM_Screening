# gem_screening/utils/env_loader.py
import os
from pathlib import Path


# TEMPLATE = """\
# # ⚠️ Please review and customize before running:
# BASE_URL=http://localhost:8000

# #----------- LOGGING CONFIGURATION -----------
# # Control logging verbosity: DEBUG, INFO, WARNING, ERROR, CRITICAL
# LOG_LEVEL=INFO
# LOGFILE_NAME=gem_screening.log
# """

# def get_env_path() -> Path:
#     if sys.platform == "win32":
#         # On Windows, use %APPDATA%\gem_screening
#         base = Path(os.getenv("APPDATA", Path.home().joinpath("AppData","Roaming")))
#     else:
#         # On Linux/macOS, use $XDG_CONFIG_HOME or ~/.config
#         base = Path(os.getenv("XDG_CONFIG_HOME", Path.home().joinpath(".config")))
#     cfg_dir = base.joinpath("gem_screening")
#     cfg_dir.mkdir(parents=True, exist_ok=True)
#     return cfg_dir.joinpath(".env")

def load_pipeline_env(
    run_dir: Path,
    base_url: str = "localhost",
    log_level: str = "INFO",
    logfile_name: str = "gem_screening.log",
    ) -> None:
    
    """
    This function sets the following environment variables:
    - BASE_URL: URL for the servers
    - LOG_LEVEL: Logging level for the application
    - LOGFILE_NAME: Name of the log file
    - HOST_DIR: Directory where the experiment data will be stored, mounted in the Docker container
    Args:
        base_url (str, optional): base URL for the servers. Defaults to `localhost`.
        log_level (str, optional): Logging level to set. Defaults to `INFO`.
        logfile_name (str, optional): Name of the log file. Defaults to `gem_screening.log`.
    """
    # Expose HOST_DIR, folder that would be mounted in the Docker container
    os.environ["HOST_DIR"] = str(run_dir)
    
    # expose BASE_URL
    os.environ["BASE_URL"] = base_url

    # Expose LOG_LEVEL
    os.environ["LOG_LEVEL"] = log_level

    # expose LOGFILE_NAME
    os.environ["LOGFILE_NAME"] = logfile_name
    



