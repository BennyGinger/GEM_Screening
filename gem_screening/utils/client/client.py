from dataclasses import asdict
from typing import Any
import logging
from pathlib import Path
import time
import requests
import os

from progress_bar import get_corresponding_tqdm

from gem_screening.utils.client.models import BackgroundPayload, ProcessPayload, build_payload
from gem_screening.utils.identifiers import HOST_PREFIX
from gem_screening.utils.settings.models import ServerSettings


logger = logging.getLogger(__name__)


BASE_URL = os.getenv("BASE_URL", "localhost") 
FASTAPI_URL = f"http://{BASE_URL}:8000"

def _transform_path_for_container(img_path: Path) -> str:
    """
    Transform a Windows path to the corresponding Docker container path.
    The HOST_DIR is mounted as /data in the container.
    
    Args:
        img_path (Path): The Windows file path
        
    Returns:
        str: The corresponding container path
    """
    host_dir = os.getenv("HOST_DIR")
    if not host_dir:
        raise ValueError("HOST_DIR environment variable must be set")
    
    host_path = Path(host_dir)
    
    # Convert paths to absolute and resolve any relative components
    img_path = img_path.resolve()
    host_path = host_path.resolve()
    
    # Get the relative path from the host directory
    try:
        relative_path = img_path.relative_to(host_path)
    except ValueError as e:
        raise ValueError(f"Image path {img_path} is not within HOST_DIR {host_path}") from e
    
    # Convert to container path using forward slashes
    container_path = "/data/" + str(relative_path).replace("\\", "/")
    return container_path

def cleanup_stale() -> None:
    """
    Call the FastAPI cleanup endpoint for this host_prefix.
    It will delete any pending or finished keys for this host_prefix.
    E.g. host_prefix='worker-01' will delete:
      pending_tracks:worker-01:*  
      finished:worker-01:*
    """
    url = f"{FASTAPI_URL}/cleanup/{HOST_PREFIX}"
    resp = requests.post(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    logger.info(f"Cleanup removed {data['deleted']} stale keys for {HOST_PREFIX}")

def bg_removal_client(server_settings: ServerSettings, img_path: Path) -> None:
    """
    Send a background subtraction task to the server. Payload is built using the provided image path and server settings.
    Args:
        server_settings (ServerSettings): The server settings containing the host prefix and other parameters.
        img_path (Path): The path to the image file to be processed.
    """
    # Transform the Windows path to the container path
    container_path = _transform_path_for_container(img_path)
    bg_payload = build_payload(img_path=container_path,
                                       server_settings=server_settings,
                                       bg_only=True)
    _send_to_process_bg_sub(bg_payload)

def full_process_client(server_settings: ServerSettings, img_path: Path) -> None:
    """
    Send a full processing task to the server. Payload is built using the provided image path and server settings.
    Args:
        server_settings (ServerSettings): The server settings containing the host prefix and other parameters.
        img_path (Path): The path to the image file to be processed.
    """
    # Transform the Windows path to the container path
    container_path = _transform_path_for_container(img_path)
    full_payload = build_payload(img_path=container_path,
                                     server_settings=server_settings,
                                     bg_only=False)
    _send_to_process(full_payload)

def _send_to_process_bg_sub(payload: BackgroundPayload) -> None:
    """
    Call the /process_bg_sub endpoint to launch Celery jobs for background subtraction.
    Args:
        payload (BackgroundPayload): The payload containing the background subtraction parameters.
    """
    url = f"{FASTAPI_URL}/process_bg_sub"
    resp = requests.post(url, json=asdict(payload), timeout=10)
    resp.raise_for_status()
    task_id = resp.json()  # This endpoint returns just the task ID as a string
    logger.info(f"Enqueued background subtraction task {task_id} for {payload.img_path}.")

def _send_to_process(payload: ProcessPayload | BackgroundPayload) -> None:
    """
    Call the /process endpoint to launch Celery jobs. Images will be background subtracted, denoised (if needed), segmented, and tracked (using IoU).
    Args:
        payload (ProcessPayload | BackgroundPayload): The payload containing the image processing parameters.
    """
    url = f"{FASTAPI_URL}/process"
    resp = requests.post(url, json=asdict(payload), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    logger.info(f"Enqueued task {data['task_ids']} under well_id {data['well_id']}")

def wait_for_completion(well_id: str,
                        poll_interval: float = 1.,
                        timeout: float | None = None) -> None:
    """
    Polls GET {base_url}/process/{well_id}/status until it returns "finished".
    Displays a progress bar based on the 'remaining' count.
    If timeout is set, raises TimeoutError after that many seconds.
    Args:
        well_id (str): The well ID to check the status for.
        poll_interval (float): The interval in seconds to wait between polls. Default is 1 second.
        timeout (float | None): Optional timeout in seconds. If set, raises TimeoutError if the run does not finish within this time.
    Raises:
        TimeoutError: If the run does not finish within the specified timeout.
    """
    status_url = f"{FASTAPI_URL}/process/{well_id}/status"
    total = None
    remaining = None

    # First poll to bootstrap the bar
    logger.info(f"Checking status of run {well_id}...")
    resp = requests.get(status_url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data['status'] == 'finished':
        logger.info(f"Run {well_id} already finished.")
        return

    total = data['remaining']
    remaining = total

    tqdm_class = get_corresponding_tqdm()
    pbar: Any = tqdm_class(total=total, desc=f"Run {well_id}", unit="fov")

    # Keep track of the start time
    start_time = time.monotonic()
    try:
        while True:
            if timeout is not None and (time.monotonic() - start_time) > timeout:
                msg = f"Timed out after {timeout:.0f}s waiting for well {well_id}"
                logger.error(msg)
                raise TimeoutError(msg)
            
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
    finally:
        if hasattr(pbar, 'close'):
            pbar.close()

    logger.info(f"Run {well_id} completed.")



if __name__ == "__main__":
    print(BASE_URL)