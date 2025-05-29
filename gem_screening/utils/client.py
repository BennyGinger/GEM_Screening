import logging
import requests
import os

from gem_screening.utils.identifiers import HOST_PREFIX


logger = logging.getLogger(__name__)


# Configuration, load from environment variable, which is launched in the main file (i.e. pipeline.py)
BASE_URL = os.getenv("FASTAPI_BASE_URL") 


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