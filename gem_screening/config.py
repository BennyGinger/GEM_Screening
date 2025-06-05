from pathlib import Path

from gem_screening.utils.env_loader import load_pipeline_env

ROOT_DIR = Path(__file__).parent.parent.resolve()
if not ROOT_DIR.exists():
    raise FileNotFoundError(f"Root directory {ROOT_DIR!r} does not exist. Please check your setup.")

# Define the path to the logs directory
HOST_LOG_FOLDER = ROOT_DIR.joinpath("logs")
if not HOST_LOG_FOLDER.exists():
    HOST_LOG_FOLDER.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env file
load_pipeline_env(ROOT_DIR, host_log_folder=str(HOST_LOG_FOLDER))