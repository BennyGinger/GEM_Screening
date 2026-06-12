import requests
import logging

from gem_screening.utils.client import FASTAPI_URL
from gem_screening.utils.identifiers import HOST_PREFIX


logger = logging.getLogger(__name__)

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