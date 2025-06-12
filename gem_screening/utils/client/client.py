from dataclasses import asdict, dataclass
import logging
import time
from typing import Any
import requests
import os

from progress_bar import get_corresponding_tqdm

from gem_screening.utils.client.models import BackgroundPayload, ProcessPayload
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

def submit_bg_subtraction(payload: BackgroundPayload) -> None:
    """
    Call the /process_bg_sub endpoint to launch Celery jobs for background subtraction.
    Args:
        payload (BackgroundPayload): The payload containing the background subtraction parameters.
    Returns:
        None
    """
    url = f"{BASE_URL}/process_bg_sub"
    resp = requests.post(url, json=asdict(payload), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    logger.info(f"Enqueued {data['count']} tasks for background subtraction.")

def submit_full_processing(payload: ProcessPayload) -> None:
    """
    Call the /process endpoint to launch Celery jobs.
    Under the hood it will send tasks to the Celery worker to process images.
    Images will be background subtracted, denoised (if needed), segmented, and tracked (using IoU).
    Args:
        payload (ProcessPaylaod): The payload containing the image processing parameters.
    Returns:
        tuple[str, list[str]]: A tuple containing the run_id and a list of task IDs.
    """
    url = f"{BASE_URL}/process"
    resp = requests.post(url, json=asdict(payload), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    logger.info(f"Enqueued {data['count']} tasks under run_id {data['run_id']}")

def wait_for_completion(run_id: str,
                        poll_interval: float = 1.) -> None:
    """
    Polls GET {base_url}/process/{run_id}/status until it returns "finished".
    Displays a progress bar based on the 'remaining' count.
    """
    status_url = f"{BASE_URL}/process/{run_id}/status"
    total = None
    remaining = None

    # First poll to bootstrap the bar
    logger.info(f"Checking status of run {run_id}...")
    resp = requests.get(status_url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data['status'] == 'finished':
        logger.info(f"Run {run_id} already finished.")
        return

    total = data['remaining']
    remaining = total
    tqdm_ins = get_corresponding_tqdm()
    pbar = tqdm_ins(total=total, desc=f"Run {run_id}", unit="fov")

    try:
        while True:
            time.sleep(poll_interval)
            resp = requests.get(status_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data['status'] == 'processing':
                new_rem = data['remaining']
                # How many got done since last poll?
                done = remaining - new_rem
                if done > 0:
                    pbar.update(done)
                    remaining = new_rem
            elif data['status'] == 'finished':
                # finish out the bar
                pbar.update(remaining)
                break
            else:
                raise RuntimeError(f"Unknown status: {data['status']}")
    finally:
        pbar.close()

    logger.info(f"Run {run_id} completed.")



if __name__ == "__main__":
    print(BASE_URL)