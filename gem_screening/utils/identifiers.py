import socket
import uuid
import logging
import re
from pathlib import Path


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


HOST_PREFIX = get_hostname()

def make_run_id() -> str:
    """
    Generate a unique run ID based on the hostname and a UUID.
    Returns:
        str: A unique run ID.
    """
    unique_id = uuid.uuid4().hex
    run_id = f"{HOST_PREFIX}-{unique_id}"
    return run_id


# regex will match e.g. the stem "A1P3_measure_02" (no extension)
_IMG_FILE_RE = re.compile(
    r'^(?P<fov_id>[^_]+)_'         # the FOV ID (e.g. "A1P3")
    r'(?P<category>[^_]+)_'       # the image category
    r'(?P<instance>\d+)$')    # the instance number

def parse_image_filename(path: Path) -> tuple[str, str, int]:
    """
    Given a Path, strip its suffix and extract (fov_id, category, instance) from a stem like "A1P3_measure_02". Raises ValueError if it doesn't match.
    """
    name = path.stem
    m = _IMG_FILE_RE.match(name)
    if not m:
        raise ValueError(f"Invalid img filename: {name}")
    
    fov_id = m.group('fov_id')
    cat = m.group('category')
    inst = m.group('instance')
    try:
        inst = int(inst)
    except ValueError:
        raise ValueError(f"Invalid instance number in filename: {name}. Expected format is '<fov_id>_<category>_<instance-number>'")
    
    return fov_id, cat, inst
   
    
_CAT_INST_RE = re.compile(
    r'^(?P<category>[^_]+)_'      # the image category
    r'(?P<instance>\d+)$')    # the instance number

def parse_category_instance(filename: str) -> tuple[str, int]:
    """
    Extract (category, instance) from a string like "measure_02" (no extension).
    Raises ValueError if it doesn't match.
    """
    m = _CAT_INST_RE.match(filename)
    if not m:
        raise ValueError(f"Invalid category-instance format: {filename!r}. "
                         "Expected '<category>_<instance-number>'")
    
    cat = m.group('category')
    inst = m.group('instance')
    try:
        inst = int(inst)
    except ValueError:
        raise ValueError(f"Invalid instance number in: {filename!r}. "
                         "Expected '<category>_<instance-number>' with a numeric instance (e.g. _1, _2...).")
    return cat, inst