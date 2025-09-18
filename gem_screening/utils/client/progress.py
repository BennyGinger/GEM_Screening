from typing import Union
import logging
import requests
import time

from progress_bar import get_corresponding_tqdm

from gem_screening.utils.client import FASTAPI_URL


logger = logging.getLogger(__name__)

def wait_for_completion(well_id: str,
                        poll_interval: float = 1.,
                        timeout: Union[float, None] = None) -> None:
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
    from typing import Any
    pbar: Any = tqdm_class(total=total, desc=f"Remaining images to be processed", unit="fov")

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