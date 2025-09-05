from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gem_screening.utils.pipeline_constants import BG_SETS, CP_SETS
from gem_screening.utils.settings.models import ServerSettings

def _transform_path_for_container(img_path: Path) -> str:
    """Transform a Windows path to the corresponding Docker container path."""
    import os
    host_dir = os.getenv("HOST_DIR")
    if not host_dir:
        raise ValueError("HOST_DIR environment variable must be set")
    
    host_path = Path(host_dir)
    img_path = img_path.resolve()
    host_path = host_path.resolve()
    
    try:
        relative_path = img_path.relative_to(host_path)
    except ValueError as e:
        raise ValueError(f"Path {img_path} is not within HOST_DIR {host_path}") from e
    
    container_path = "/data/" + str(relative_path).replace("\\", "/")
    return container_path


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

@dataclass(kw_only=True) # To allow non-default values after inheritance of default values from BackgroundPayload
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
    cellpose_settings: dict[str, Any] = field(default_factory=dict)
    dst_folder: str
    well_id: str
    total_fovs: int
    track_stitch_threshold: float = 0.75
    round: int | None = None


@dataclass
class RegisterMaskPayload:
    """
    Payload Model for the `/register_mask` endpoint.
    This model is used to register a single mask to Redis and optionally trigger tracking.
    
    Attributes:
        well_id (str): Unique identifier for the processing well.
        mask_path (str): Path to the mask file (container path).
        total_fovs (int): Total number of FOVs (used for pending counter initialization).
        track_stitch_threshold (float): Threshold for stitching masks during tracking. Default to 0.75.
    """
    well_id: str
    mask_path: str
    total_fovs: int
    track_stitch_threshold: float = 0.75


    

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
    # Required parameters — raise if missing
    well_id = settings_dict.pop("well_id", None)
    dst_folder = settings_dict.pop("dst_folder", None)
    total_fovs = settings_dict.pop("total_fovs", None)

    missing: list[str] = []
    if well_id is None:
        missing.append("well_id")
    if dst_folder is None:
        missing.append("dst_folder")
    if total_fovs is None:
        missing.append("total_fovs")
    if missing:
        raise ValueError(f"Missing required settings for ProcessPayload: {', '.join(missing)}")

    # Normalize types
    try:
        total_fovs = int(total_fovs)  # type: ignore[assignment]
    except Exception as e:
        raise ValueError(f"total_fovs must be an integer, got {total_fovs!r}") from e
    
    # Extract the different settings parameters
    for sets in (bg_sets, cp_sets):
        overrides = {k: v for k, v in settings_dict.items() if k in sets}
        sets.update(overrides)
    
    # Build the payload
    return ProcessPayload(
        img_path=img_path,
        dst_folder=_transform_path_for_container(Path(dst_folder)),
        well_id=str(well_id),
        total_fovs=total_fovs,  # int ensured above
        track_stitch_threshold=track_stitch_threshold,
        cellpose_settings=cp_sets,
        **bg_sets,
    )
                          


