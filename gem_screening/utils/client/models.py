from dataclasses import dataclass
from typing import Any, Union


BG_SETS = {"sigma": 0.0,
           "size": 7,}

CP_SETS = {"do_denoise": True,
               "model_type": "cyto2",
               "restore_type": "denoise_cyto2",
               "gpu": True,
               "channels": None,
               "diameter": 60,
               "flow_threshold": 0.4,
               "cellprob_threshold": 0.0,
               "z_axis": None,
               "do_3D": False,
               "3D_stitch_threshold": 0,}

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
        run_id (str): Unique identifier for the processing run.
        total_fovs (int): Total number of fields of view, used to set the number of pending tracks in Redis.
        track_stitch_threshold (float, optional): Threshold for stitching masks during tracking. Default to 0.75.
        round (int): The round number for processing, build from the image path if not provided. Defaults to None.
    """
    cellpose_settings: dict[str, Any]
    dst_folder: str
    run_id: str
    total_fovs: int
    track_stitch_threshold: float = 0.75
    round: int = None

def build_payload(img_path: str, 
                   server_settings: dict[str, Any],
                   *,
                   bg_only: bool = False,
                   ) -> BackgroundPayload | ProcessPayload:
    """
    Build the payload for the image processing request.
    Args:
        img_path (str): Path to the image file.
        server_settings (dict[str, Any]): Settings for the server, including background subtraction, segmentation and tracking parameters.
        bg_only (bool): If True, only build the background settings payload. Defaults to False.
    Returns:
        (BackgroundPayload | ProcessPayload): The payload containing the image processing parameters.
    """
    # build the background settings payload
    bg_sets = BG_SETS.copy()
    
    if bg_only:
        override = {k: v for k, v in server_settings.items() if k in bg_sets}
        bg_sets.update(override)
        return BackgroundPayload(img_path=img_path, **bg_sets)
    
    # Otherwise, build the full processing payload
    cp_sets = CP_SETS.copy()
    track_stitch_threshold = server_settings.pop("track_stitch_threshold", 0.75)
    # These parameters will raise an error in the pydantic model if not provided
    run_id = server_settings.pop("run_id", "UnknownRunID")
    dst_folder = server_settings.pop("dst_folder", "UnknownFolder")
    total_fovs = server_settings.pop("total_fovs", "UnknownTotalFOVs")
    
    # Extract the different settings parameters
    for sets in (bg_sets, cp_sets):
        overrides = {k: v for k, v in server_settings.items() if k in sets}
        sets.update(overrides)
    
    # Build the payload
    return ProcessPayload(img_path=img_path,
                          dst_folder=str(dst_folder),
                          run_id=run_id,
                          total_fovs=total_fovs,
                          track_stitch_threshold=track_stitch_threshold,
                          cellpose_settings=cp_sets,
                          **bg_sets)
                          


