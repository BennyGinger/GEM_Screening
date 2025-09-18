from pathlib import Path
from datetime import datetime
from typing import Union
import os

import numpy as np
from tifffile import imwrite


def create_timestamped_dir(parent: Union[str, Path], suffix: str = "", date_format: str = "%Y%m%d") -> Path:
    """
    Create (or return) a directory named by today's date plus an optional suffix.

    Args:
        parent: base folder (will be created if missing)
        suffix: extra text to append (no leading underscore — it'll be added for you)
        date_format: any valid strftime format, default 'YYYYMMDD'

    Returns:
        Path to the directory (always exists when returned)
    """
    p = Path(parent)
    p.mkdir(parents=True, exist_ok=True)

    date_part = datetime.now().strftime(date_format)
    name = f"{date_part}_{suffix}" if suffix else date_part
    target = p.joinpath(name)
    target.mkdir(exist_ok=True)
    return target

def imwrite_atomic(final_path: Path, image_data: np.ndarray, **kwargs):
    """
    Atomically write a TIFF image.
    
    The image is first written to a temporary file (with a .tmp extension)
    and then renamed to the final filename. Ensure that the final file is
    completely written before any file watcher sees it.
    """
    temp_path = final_path.with_suffix(final_path.suffix + '.tmp')
    imwrite(temp_path, image_data, compression='zlib', **kwargs)
    os.rename(temp_path, final_path)
    
def transform_path_for_container(img_path: Path) -> str:
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