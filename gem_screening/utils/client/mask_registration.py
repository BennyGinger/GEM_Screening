from dataclasses import asdict
from pathlib import Path
import logging

from gem_screening.utils.client.service import FASTAPI_URL
from gem_screening.utils.client.models import RegisterMasksBatchPayload
from gem_screening.utils.filesystem import transform_path_for_container
from gem_screening.utils.network import make_request_with_retry


logger = logging.getLogger(__name__)

def register_masks_batch_client(well_id: str, mask_paths: list[Path], total_fovs: int, track_stitch_threshold: float = 0.75) -> list[str]:
    """
    Register multiple masks to Redis in batch and trigger tracking for R2 masks.
    
    Args:
        well_id (str): The well ID
        mask_paths (list[Path]): List of paths to mask files
        total_fovs (int): Total number of FOVs (used for pending counter initialization)
        track_stitch_threshold (float): Threshold for stitching masks during tracking. Default is 0.75.
        
    Returns:
        list[str]: List of tracking task IDs for R2 masks
    """
    # Transform all paths to container paths
    container_paths = [transform_path_for_container(mask_path) for mask_path in mask_paths]
    
    # Build the payload for batch registration using the dataclass
    payload = RegisterMasksBatchPayload(
        well_id=well_id,
        mask_paths=container_paths,
        total_fovs=total_fovs,
        track_stitch_threshold=track_stitch_threshold)
    
    # Send to the register mask endpoint
    return _send_to_register_masks_batch(payload, len(mask_paths))

def _send_to_register_masks_batch(payload: RegisterMasksBatchPayload, total_masks: int) -> list[str]:
    """
    Call the /register_mask endpoint to register multiple masks in batch.
    
    Args:
        payload (RegisterMasksBatchPayload): The payload containing the batch mask registration parameters.
        total_masks (int): Total number of masks for logging purposes.
        
    Returns:
        list[str]: List of tracking task IDs for R2 masks
    """
    url = f"{FASTAPI_URL}/register_mask"
    resp = make_request_with_retry(
        url=url, 
        payload=asdict(payload), 
        operation_name="Register masks batch",
        base_timeout=30,
        timeout_increment=10
    )
    tracking_task_ids = resp.json()  # Returns list of tracking task IDs
    
    logger.info(f"Registered {total_masks} masks in batch, {len(tracking_task_ids)} tracking tasks triggered")
    
    return tracking_task_ids