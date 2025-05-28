import logging
import requests
import os

from dotenv import load_dotenv

from gem_screening.utils.identifiers import HOST_PREFIX
from gem_screening import ROOT_DIR


logger = logging.getLogger(__name__)


def get_env_var() -> str:
    """
    Get the FASTAPI_BASE_URL from the environment variables.
    If not set, it will create a template .env file, but raise an error as the user must set it.
    Returns:
        str: The FASTAPI_BASE_URL or "http://localhost:8000" if not set.
        
    Raises:
        FileNotFoundError: If the .env file does not exist and needs to be checked.
    """

    template = """
    # ⚠️ Please review and customize this file before running again ⚠️

    # Critical, must be determined by the user:
    FASTAPI_BASE_URL=http://localhost:8000
    """

    env_path = ROOT_DIR.joinpath(".env")
    if not env_path.exists():
        # write the template out
        env_path.write_text(template)
        logger.error(f"No .env found: created template at {env_path}")
        raise FileNotFoundError(
            f".env not found. A template has been created at {env_path}. "
            "Please set FASTAPI_BASE_URL before rerunning.")
    
    # Read the .env file
    load_dotenv(env_path, override=False)
    return os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")

# Configuration
BASE_URL = get_env_var()


def cleanup_stale() -> None:
    """
    Call the FastAPI cleanup endpoint for this host_prefix.
    It will delete any pending or finished keys for this host_prefix.
    E.g. host_prefix='worker-01' will delete:
      pending_tracks:worker-01:*  
      finished:worker-01:*
    """
    url = f"{BASE_URL}/cleanup/{HOST_PREFIX}"
    resp = requests.post(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    logger.info(f"Cleanup removed {data['deleted']} stale keys for {HOST_PREFIX}")

def start_processing(run_id: str, payload: dict) -> tuple[str, list[str]]:
    """
    Call the /process endpoint to launch Celery jobs.
    Under the hood it will send tasks to the Celery worker to process images.
    Images will be background subtracted, denoised (if needed), segmented, and tracked (using IoU).
    Args:
        run_id (str): Unique identifier for the processing run.
        payload (dict): Dictionary containing the image processing parameters.
    Returns:
        tuple[str, list[str]]: A tuple containing the run_id and a list of task IDs.
    """
    url = f"{BASE_URL}/process"
    body = {**payload, "run_id": run_id}
    resp = requests.post(url, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    logger.info(f"Enqueued {data['count']} tasks under run_id {data['run_id']}")
    return data["run_id"], data["task_ids"]

if __name__ == "__main__":
    print(BASE_URL)