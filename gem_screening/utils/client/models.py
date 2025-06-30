from dataclasses import dataclass
from typing import Any

from gem_screening.utils.pipeline_constants import BG_SETS, CP_SETS
from gem_screening.utils.settings.models import ServerSettings


@dataclass
class BackgroundPayload():
    """
    Payload Model for the `/process_bg_sub` endpoint.
    This model is used to send background subtraction parameters to the server.
    Attributes:
        img_path (str): Path to the image file to be processed.
        sigma (float): Sigma value for background subtraction.
        size (int): Size parameter for background subtraction.
    """
    img_path: str
    sigma: float = 0.0
    size: int = 7

@dataclass
class ProcessPayload(BackgroundPayload):
    """
    Payload Model for the `/process` endpoint.
    This model is used to send image processing parameters to the server.
    It inherits from `BackgroundPayload` and adds additional parameters for segmentation and tracking.
    
    Attributes Inherited:
        img_path (str): Path to the image file to be processed.
        sigma (float): Sigma value for background subtraction.
        size (int): Size parameter for background subtraction.
    
    Attributes:
        cellpose_settings (dict): Model and segmentation settings for Cellpose.
        dst_folder (str): Destination folder where processed images will be saved.
        well_id (str): Unique identifier for the processing well.
        total_fovs (int): Total number of fields of view, used to set the number of pending tracks in Redis.
        track_stitch_threshold (float, optional): Threshold for stitching masks during tracking. Default to 0.75.
        round (int): The round number for processing, build from the image path if not provided. Defaults to None.
    """
    cellpose_settings: dict[str, Any]
    dst_folder: str
    well_id: str
    total_fovs: int
    track_stitch_threshold: float = 0.75
    round: int = None

def build_payload(img_path: str, 
                   server_settings: ServerSettings,
                   *,
                   bg_only: bool = False,
                   ) -> BackgroundPayload | ProcessPayload:
    """
    Build the payload for the image processing request.
    Args:
        img_path (str): Path to the image file.
        server_settings (ServerSettings): The server settings containing parameters for image processing.
        bg_only (bool): If True, only build the background settings payload. Defaults to False.
    Returns:
        (BackgroundPayload | ProcessPayload): The payload containing the image processing parameters.
    """
    # build the background settings payload
    
    bg_sets = BG_SETS.copy()
    settings_dict = server_settings.model_dump()
    if bg_only:
        override = {k: v for k, v in settings_dict.items() if k in bg_sets}
        bg_sets.update(override)
        return BackgroundPayload(img_path=img_path, **bg_sets)
    
    # Otherwise, build the full processing payload
    cp_sets = CP_SETS.copy()
    track_stitch_threshold = settings_dict.pop("track_stitch_threshold", 0.75)
    # These parameters will raise an error in the pydantic model if not provided
    well_id = settings_dict.pop("well_id", "UnknownRunID")
    dst_folder = settings_dict.pop("dst_folder", "UnknownFolder")
    total_fovs = settings_dict.pop("total_fovs", "UnknownTotalFOVs")
    
    # Extract the different settings parameters
    for sets in (bg_sets, cp_sets):
        overrides = {k: v for k, v in settings_dict.items() if k in sets}
        sets.update(overrides)
    
    # Build the payload
    return ProcessPayload(img_path=img_path,
                          dst_folder=str(dst_folder),
                          well_id=well_id,
                          total_fovs=total_fovs,
                          track_stitch_threshold=track_stitch_threshold,
                          cellpose_settings=cp_sets,
                          **bg_sets)
                          


