from dataclasses import dataclass
from pathlib import Path
from typing import Any


BG_SETS = {"sigma": 0.0,
               "size": 7,}

CP_SETS = {"channels": None,
               "diameter": 60,
               "flow_threshold": 0.4,
               "cellprob_threshold": 0.0,
               "z_axis": None,
               "do_3D": False,
               "3D_stitch_threshold": 0,}

MOD_SETS = {"model_type": "cyto2",
                "restore_type": "denoise_cyto2",
                "gpu": True,}

SERVER_SETS = {"do_denoise": True,
                "track_stitch_threshold": 0.75}

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
        mod_settings (dict[str, Any]): Model settings for Cellpose.
        cp_settings (dict[str, Any]): Segmentation settings for Cellpose.
        dst_folder (str): Destination folder where processed images will be saved.
        round (int): The current round of processing (1 or 2).
        run_id (str): Unique identifier for the processing run.
        total_fovs (int, optional): Total number of fields of view, used in round 2 for tracking.
        do_denoise (bool, optional): Whether to apply denoising. Defaults to True.
        track_stitch_threshold (float, optional): Threshold for stitching masks. Defaults to 0.75.
    """
    mod_settings: dict[str, Any]
    cp_settings: dict[str, Any]
    dst_folder: str
    round: int
    run_id: str
    total_fovs: int = None
    do_denoise: bool = True
    track_stitch_threshold: float = 0.75
    
def build_process_payload(img_path: str | list[str], 
                   server_settings: dict[str, Any],
                   run_id: str, 
                   round_num: int, 
                   dst_folder: Path,
                   total_fovs: int,
                   ) -> ProcessPayload:
    """
    Build the payload for the image processing request.
    Args:
        img_path (str | list[str]): Path to the image file, a directory or a list of image paths.
        server_settings (dict[str, Any]): Settings for the server, including model and segmentation settings, as well as background settings and tracking parameters.
        run_id (str): Unique identifier for the processing run.
        round_num (int): The round number for processing.
        dst_folder (Path): Destination folder where processed images will be saved.
        total_fovs (int): Total number of fields of view.
    Returns:
        ProcessPayload: The payload containing the image processing parameters.
    """
    # Default parameters for the payload
    cp_sets = CP_SETS.copy()
    mod_sets = MOD_SETS.copy()
    server_sets = SERVER_SETS.copy()
    bg_sets = BG_SETS.copy()
    
    # Extract the model and cellpose settings from the input settings
    for settings in (cp_sets, mod_sets, server_sets, bg_sets):
        # pick out only the overrides that belong in this dict
        overrides = {k: v for k, v in server_settings.items() if k in settings}
        settings.update(overrides)
    
    # Build the payload
    return ProcessPayload(img_path=img_path,
                          mod_settings=mod_sets,
                          cp_settings=cp_sets,
                          dst_folder=str(dst_folder),
                          round=round_num,
                          run_id=run_id,
                          total_fovs=total_fovs,
                          **server_sets,  # Unpack server settings
                          **bg_sets)  # Unpack background settings if provided
                          
def build_bg_sub_payload(img_path: str | list[str], 
                        server_settings: dict[str, Any]) -> BackgroundPayload:
    """
    Build the payload for the background subtraction request.
    Args:
        img_path (str | list[str]): Path to the image file, a directory or a list of image paths.
        server_settings (dict[str, Any]): Settings for the server, including background subtraction parameters.
    Returns:
        BackgroundPayload: The payload containing the background subtraction parameters.
    """
    
    bg_sets = BG_SETS.copy() 
    for k, v in server_settings.items():
        if k in bg_sets:
            bg_sets[k] = v
    return BackgroundPayload(img_path=img_path, **bg_sets)

