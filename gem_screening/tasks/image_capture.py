from __future__ import annotations
import logging
from pathlib import Path
from functools import partial

from a1_manager import A1Manager
from progress_bar import setup_progress_monitor as progress_bar

from gem_screening.utils.client.client import bg_removal_client, full_process_client
from gem_screening.utils.filesystem import imwrite_atomic
from gem_screening.utils.identifiers import parse_category_instance
from gem_screening.utils.pipeline_constants import REFSEG_LABEL
from gem_screening.utils.settings.models import PipelineSettings, PresetMeasure, PresetControl, ServerSettings
from gem_screening.well_data.well_classes import FieldOfView, Well


# Set up logging
logger = logging.getLogger(__name__)


def _get_fovs_from_ids(well_obj: Well, fov_ids: list[str]) -> list[FieldOfView]:
    """
    Convert a list of FOV ID strings to FieldOfView objects from the well.
    
    Args:
        well_obj (Well): The well object containing the field of views.
        fov_ids (list[str]): List of FOV ID strings (e.g., ["A1P0", "A1P1"]).
        
    Returns:
        list[FieldOfView]: List of FieldOfView objects matching the provided FOV IDs.
        
    Raises:
        ValueError: If any FOV ID is not found in the well's positive FOVs.
    """
    # Create a mapping from fov_id to FieldOfView object
    fov_map = {fov.fov_id: fov for fov in well_obj.positive_fovs}
    
    # Convert FOV IDs to FieldOfView objects
    result_fovs = []
    for fov_id in fov_ids:
        if fov_id not in fov_map:
            raise ValueError(f"FOV ID '{fov_id}' not found in well's positive FOVs. Available FOVs: {list(fov_map.keys())}")
        result_fovs.append(fov_map[fov_id])
    
    return result_fovs


def image_fovs(well_obj: Well, a1_manager: A1Manager, settings: PipelineSettings, imaging_loop: str, fov_ids: list[str] | None = None) -> None:
    """
    Take images of specified field of views in the well.
    
    If `imaging_loop` contains 'measure', we:
      1. snap a measure image → bg removal
      2. snap a refseg image → full processing
      1'. snap a measure image → full processing, if no refseg is used
    
    If `imaging_loop` contains 'control', we:
      1. snap a control image → bg removal only
    
    Args:
        well_obj (Well): The well object containing the field of views.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
        settings (PipelineSettings): The settings for the imaging pipeline.
        imaging_loop (str): The imaging loop label to use for the acquisition. Expected format is `"<category>_<instance>"`.
        fov_ids (list[str] | None): Optional list of FOV ID strings to image (e.g., ["A1P0", "A1P1"]). If None, all positive FOVs will be imaged.
    """
    # Determine which FOVs to process
    fovs_to_process = _get_fovs_from_ids(well_obj, fov_ids) if fov_ids is not None else well_obj.positive_fovs
    
    # Setup the imaging loop
    server_settings: ServerSettings = settings.server_settings
    server_settings.well_id = well_obj.well_id
    server_settings.dst_folder = str(well_obj.mask_dir)
    server_settings.total_fovs = len(fovs_to_process)
    
    # Initialize the different steps functions
    snap = partial(_take_image_fov, a1_manager=a1_manager)
    bg_removal = partial(bg_removal_client, server_settings)
    full_process = partial(full_process_client, server_settings)
    
    # Determine the different steps of the imaging loop
    
    steps = []
    if 'measure' in imaging_loop:
        measure_preset: PresetMeasure = settings.measure_settings.preset_measure
        do_refseg = settings.measure_settings.do_refseg
        steps.append((imaging_loop, measure_preset, bg_removal))
        
        if do_refseg:
            refseg_preset = settings.measure_settings.preset_refseg
            refseg_loop = f"{REFSEG_LABEL}_{parse_category_instance(imaging_loop)[1]}"
            steps.append((refseg_loop, refseg_preset, full_process))
        else:
            # If no refseg is used, we need to replace the bg_removal by full process for the measure image
            steps[0] = (imaging_loop, measure_preset, full_process)
    elif 'control' in imaging_loop:
        control_preset: PresetControl = settings.control_settings.preset
        steps.append((imaging_loop, control_preset, bg_removal))
    
    else:
        raise ValueError(f"Invalid imaging loop: {imaging_loop}. Expected 'measure' or 'control' in the loop name.")
    
    # Run the steps
    total_fovs = len(fovs_to_process)
    for fov in progress_bar(fovs_to_process,
                            desc=f"Imaging {imaging_loop}",
                            total=total_fovs):
        for loop_name, preset, post_fn in steps:
            # Take image of the fov
            img_path = snap(fov, input_preset=preset, imaging_loop=loop_name)
            
            # Post-process the image
            post_fn(img_path)
    
    # Save the well object
    well_obj.to_json()

def _take_image_fov(fov_obj: FieldOfView, input_preset: PresetMeasure | PresetControl, imaging_loop: str, a1_manager: A1Manager) -> Path:
    """
    Take an image of a field of view and save it to the specified directory.
    Args:
        fov_obj (FieldOfView): The field of view object containing the coordinates and ID.
        input_preset (PresetMeasure | PresetControl): The preset settings for the imaging.
        imaging_loop (str): The imaging loop label to use for the acquisition.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
    Returns:
        Path: The path where the image is saved.
    """
    # Position stage
    a1_manager.nikon.set_stage_position(fov_obj.fov_coord)
    
    # Change oc settings
    a1_manager.oc_settings(**input_preset.model_dump())
    a1_manager.load_dmd_mask('fullON')
    
    # Take image and do background correction
    img = a1_manager.snap_image()
    
    # Save image
    img_path = fov_obj.register_img_file(imaging_loop)
    imwrite_atomic(img_path, img.astype('uint16'))
    logger.debug(f"Image saved at {img_path}")
    
    # Build the payload for the image processing request
    return img_path

