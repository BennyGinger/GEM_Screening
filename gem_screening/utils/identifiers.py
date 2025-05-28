import socket
import uuid
import logging


logger = logging.getLogger(__name__)


def get_hostname() -> str:
    """
    Get the hostname of the current machine.
    Returns:
        str: The hostname of the machine.
    
    Raises:
        OSError: If there is an error retrieving the hostname.
        Exception: For any unexpected errors.
    """
    try:
        hname = socket.gethostname()
    except OSError as o:
        logger.error(f"Error getting hostname: {o}")
        hname = "unknown-host"
    except Exception as e:
        logger.error(f"Unexpected error getting hostname: {e}")
        hname = "unknown-host"
    return hname

def make_run_id() -> str:
    """
    Generate a unique run ID based on the hostname and a UUID.
    Returns:
        str: A unique run ID.
    """
    hostname = get_hostname()
    
    unique_id = uuid.uuid4().hex
    run_id = f"{hostname}-{unique_id}"
    return run_id