from dataclasses import asdict
from typing import Any, TypeVar, cast
import logging
from pathlib import Path

from numpy.typing import NDArray
import numpy as np
import requests
from cp_server.tasks_server.utils.serialization_utils import custom_encoder, custom_decoder

from gem_screening.utils.client import FASTAPI_URL
from gem_screening.utils.client.models import BackgroundPayload, ProcessPayload, build_payload
from gem_screening.utils.filesystem import transform_path_for_container
from gem_screening.utils.network import make_request_with_retry
from gem_screening.settings.models import ServerSettings


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=np.generic)

def bg_removal_client(server_settings: ServerSettings, img_path: Path | list[Path]) -> None:
    """
    Send a background subtraction task (single or batch) to the server. Payload is built using the provided image path(s) and server settings.
    Args:
        server_settings (ServerSettings): The server settings containing the host prefix and other parameters.
        img_path (Path | list[Path]): The path(s) to the image file(s) to be processed.
    """
    # Accept both single Path or list[Path]
    if isinstance(img_path, Path):
        img_path = [img_path]
    
    # Transform all paths
    container_paths = [transform_path_for_container(p) for p in img_path]
    
    # If only one, send as str for backward compatibility
    payload_img_path = container_paths[0] if len(container_paths) == 1 else container_paths
    bg_payload = build_payload(img_path=payload_img_path,
                              server_settings=server_settings,
                              bg_only=True)
    _send_to_process_bg_sub(bg_payload)

def full_process_client(server_settings: ServerSettings, img_path: Path | list[Path]) -> None:
    """
    Send a full processing task (single or batch) to the server. Payload is built using the provided image path(s) and server settings.
    Args:
        server_settings (ServerSettings): The server settings containing the host prefix and other parameters.
        img_path (Path | list[Path]): The path(s) to the image file(s) to be processed.
    """
    # Accept both single Path or list[Path]
    if isinstance(img_path, Path):
        img_path = [img_path]
        
    # Transform all paths
    container_paths = [transform_path_for_container(p) for p in img_path]
    
    # If only one, send as str for backward compatibility
    payload_img_path = container_paths[0] if len(container_paths) == 1 else container_paths
    full_payload = build_payload(img_path=payload_img_path,
                                server_settings=server_settings,
                                bg_only=False)
    _send_to_process(full_payload)

def optimise_segmentation(img: NDArray[T], cellpose_settings: dict[str, Any]) -> NDArray[T]:
    """
    Send an ndarray to the FastAPI server for segmentation and receive the mask.
    Args:
        img (np.ndarray): The image to segment.
        cellpose_settings (dict): Settings for segmentation.
    Returns:
        np.ndarray: The segmented mask.
    """
    payload = {
        "array": custom_encoder(img),
        "cellpose_settings": cellpose_settings}
    
    url = f"{FASTAPI_URL}/segment_ndarray"
    resp = make_request_with_retry(url, payload, "segment_ndarray")
    resp.raise_for_status()
    result = resp.json()
    # result["array"] is a dict (already parsed); custom_decoder can accept dict
    mask = cast(NDArray[T], custom_decoder(result["array"]))
    return mask

def cellpose_metadata_client() -> dict[str, Any]:
    """
    Retrieve Cellpose metadata from the server, including available model names and version.
    Returns:
        dict: Metadata containing 'model_names' and 'version'.
    """
    url = f"{FASTAPI_URL}/cellpose_metadata"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    return result

def _send_to_process_bg_sub(payload: BackgroundPayload) -> None:
    """
    Call the /process_bg_sub endpoint to launch Celery jobs for background subtraction (single or batch).
    Args:
        payload (BackgroundPayload): The payload containing the background subtraction parameters.
    """
    url = f"{FASTAPI_URL}/process_bg_sub"
    resp = make_request_with_retry(
        url=url, 
        payload=asdict(payload), 
        operation_name="Background subtraction",
        timeout_increment=10
    )
    # The endpoint may return a string (single) or dict/list (batch)
    try:
        result = resp.json()
    except Exception:
        result = resp.text
    logger.debug(f"Enqueued background subtraction task(s): {result} for {payload.img_path}.")

def _send_to_process(payload: ProcessPayload | BackgroundPayload) -> None:
    """
    Call the /process endpoint to launch Celery jobs (single or batch). Images will be background subtracted, denoised (if needed), segmented, and tracked (using IoU).
    Args:
        payload (ProcessPayload | BackgroundPayload): The payload containing the image processing parameters.
    """
    url = f"{FASTAPI_URL}/process"
    resp = make_request_with_retry(
        url=url, 
        payload=asdict(payload), 
        operation_name="Process"
    )
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    logger.debug(f"Enqueued process task(s): {data}")

