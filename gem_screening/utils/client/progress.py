from typing import Any, Protocol, runtime_checkable, cast
import logging
import requests
import time

from progress_bar import get_corresponding_tqdm

from gem_screening.utils.client import FASTAPI_URL


logger = logging.getLogger(__name__)

@runtime_checkable
class ProgressBar(Protocol):
    """Protocol class to define the progress bar"""
    def update(self, n: int) -> Any: ...
    def close(self) -> None: ...

def _normalize_well_ids(well_id: str | list[str]) -> list[str]:
    """
    Normalize input to a unique, ordered list of well IDs.
    """
    if isinstance(well_id, str):
        return [well_id]
    return well_id

def _initialize_progress(well_ids: list[str]) -> tuple[list[str], int]:
    """
    Poll all wells, return (active_wells, remaining_by_well, total_initial_remaining).
    """
    logger.info(f"Checking status of runs: {', '.join(well_ids)}")
    active_wells = []
    remaining_by_well: dict[str, int] = {}
    for wid in well_ids:
        data = _fetch_status(wid)
        logger.debug(f"Status for well {wid}: {data}")
        status = data.get('status')
        if status == 'finished':
            logger.info(f"Run {wid} already finished.")
            remaining_by_well[wid] = 0
        else:
            rem = int(data.get('remaining', 0))
            remaining_by_well[wid] = rem
            active_wells.append(wid)
    total_initial_remaining = sum(remaining_by_well.values())
    return active_wells, total_initial_remaining

def _fetch_status(wid: str) -> dict[str, Any]:
    url = f"{FASTAPI_URL}/process/{wid}/status"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

def _poll_active_wells(active_wells: list[str],
                      total_initial_remaining: int,
                      poll_interval: float,
                      timeout: float | None,
                      well_ids: list[str]) -> None:
    def _create_progress_bar(total: int, wells_count: int) -> ProgressBar:
        tqdm_class = get_corresponding_tqdm()
        return cast(ProgressBar, tqdm_class(
            total=total,
            desc=f"Remaining images to be processed ({wells_count} wells)",
            unit="fov",
        ))
    
    def _check_timeout(start: float, timeout_s: float | None, active: list[str]) -> None:
        if timeout_s is not None and (time.monotonic() - start) > timeout_s:
            msg = (
                f"Timed out after {timeout_s:.0f}s waiting for wells: "
                f"{', '.join(active)}")
            logger.error(msg)
            raise TimeoutError(msg)

    def _poll_status_for_wells(wells: list[str]) -> tuple[dict[str, int], list[str]]:
        """
        Return (remaining_by_well, still_active) for the provided wells.
        """
        remaining_map: dict[str, int] = {}
        still_active: list[str] = []
        for wid in wells:
            data = _fetch_status(wid)
            status = data.get('status')
            if status == 'finished':
                remaining_map[wid] = 0
            else:
                remaining_map[wid] = int(data.get('remaining', 0))
                still_active.append(wid)
        return remaining_map, still_active

    def _update_progress_bar(pbar: ProgressBar, prev_total: int, new_total: int) -> int:
        done = prev_total - new_total
        if done > 0:
            pbar.update(done)
            return new_total
        return prev_total

    def _finish_progress_bar(pbar: ProgressBar, leftover: int) -> None:
        if leftover > 0:
            pbar.update(leftover)

    pbar: ProgressBar = _create_progress_bar(total_initial_remaining, len(active_wells))
    prev_total_remaining = total_initial_remaining
    start_time = time.monotonic()
    try:
        while active_wells:
            _check_timeout(start_time, timeout, active_wells)
            time.sleep(poll_interval)
            remaining_map, still_active = _poll_status_for_wells(active_wells)
            new_total_remaining = sum(remaining_map.values())
            prev_total_remaining = _update_progress_bar(pbar, prev_total_remaining, new_total_remaining)
            active_wells = still_active
        _finish_progress_bar(pbar, prev_total_remaining)
    finally:
        if hasattr(pbar, 'close'):
            pbar.close()
    logger.info(f"Completed waiting for {len(well_ids)} well(s): {', '.join(well_ids)}")

def wait_for_completion(well_id: str | list[str],
                        poll_interval: float = 1.,
                        timeout: float | None = None) -> None:
    """
    Wait until one or more wells complete processing, displaying a single aggregated progress bar.
    For each well, polls GET {FASTAPI_URL}/process/{well_id}/status until all are "finished".
    The progress bar shows the combined remaining 'images' across all active wells.
    Args:
        well_id (str | list[str]): A single well ID or a sequence of well IDs to track.
        poll_interval (float): Seconds between polls (default: 1.0).
        timeout (float | None): Optional timeout in seconds applied to the overall wait.
    Raises:
        TimeoutError: If not all wells finish within the specified timeout.
        requests.HTTPError: If any status request fails.
    """
    well_ids = _normalize_well_ids(well_id)
    if not well_ids:
        logger.info("No well IDs provided; nothing to wait for.")
        return
    active_wells, total_initial_remaining = _initialize_progress(well_ids)
    if not active_wells or total_initial_remaining == 0:
        logger.info("All requested wells are already finished.")
        return
    _poll_active_wells(active_wells, total_initial_remaining, poll_interval, timeout, well_ids)