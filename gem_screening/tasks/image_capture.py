from __future__ import annotations
import logging
from pathlib import Path
from functools import partial
from typing import Callable, TypeVar

import numpy as np
from a1_manager import A1Manager, StageCoord
from numpy.typing import NDArray
from progress_bar import setup_progress_monitor as progress_bar

from gem_screening.utils.client.service import bg_removal_client, full_process_client
from gem_screening.utils.filesystem import imwrite_atomic
from gem_screening.utils.identifiers import parse_category_instance
from gem_screening.utils.pipeline_constants import REFSEG_LABEL
from gem_screening.settings.models import PipelineSettings, PresetMeasure, PresetRefseg, PresetControl, ServerSettings
from gem_screening.well_data.well_classes import FieldOfView, Well


# Set up logging
logger = logging.getLogger(__name__)
T = TypeVar("T", bound=np.generic)
BATCH_SIZE = 1

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
    server_settings = _init_settings(well_obj, settings, fovs_to_process)
    
    # Define the steps based on the imaging loop
    steps = _create_imaging_steps(settings, imaging_loop, server_settings)

    # Process the FOVs as batches
    _process_fovs(imaging_loop, fovs_to_process, a1_manager, steps)

def snap_image(coord: StageCoord, input_preset: PresetMeasure | PresetControl | PresetRefseg, a1_manager: A1Manager) -> NDArray:
    # Move to position
    a1_manager.set_stage_position(coord)
    
    # Set oc settings
    a1_manager.oc_settings(**input_preset.model_dump())
    a1_manager.load_dmd_mask('fullON')
    
    # Take image
    img = a1_manager.snap_image()
    return img

def _create_imaging_steps(settings: PipelineSettings, imaging_loop: str, server_settings: ServerSettings) -> list[tuple[str, PresetMeasure | PresetControl | PresetRefseg, Callable]]:
    """
    Set up the imaging steps based on the imaging loop type. Returns a list of tuples containing (loop_name, preset, post_fn), with post_fn being either bg_removal or full_process.
    """
    
    # Define the post-processing functions
    bg_removal = partial(bg_removal_client, server_settings)
    full_process = partial(full_process_client, server_settings)
    
    # Define the steps based on the imaging loop
    steps: list[tuple[str, PresetMeasure | PresetControl | PresetRefseg, Callable]] = []
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
    return steps

def _init_settings(well_obj: Well, settings: PipelineSettings, fovs_to_process: list[FieldOfView]) -> ServerSettings:
    """
    Initialize server settings for the imaging process, by updating the well ID, destination folder, and total FOVs.
    """
    server_settings: ServerSettings = settings.server_settings
    server_settings.well_id = well_obj.well_id
    server_settings.dst_folder = str(well_obj.mask_dir)
    server_settings.total_fovs = len(fovs_to_process)
    return server_settings

def _process_fovs(imaging_loop: str, fovs_to_process: list[FieldOfView], a1_manager: A1Manager, steps: list[tuple]) -> None:
    """
    Process the FOVs in batches, taking images and applying post-processing functions.
    """
    # Define the snap function
    snap = partial(_process_single_fov, a1_manager=a1_manager)
    
    # Initialize process
    batches = [[] for _ in steps]
    well = fovs_to_process[0].well  # Assume all FOVs belong to the same well
    fovs_list = fovs_to_process[:-1] # Remove the last point which is the middle of the well (only for injection)
    total_fovs = len(fovs_list)
    
    # Process each FOV
    for fov in progress_bar(fovs_list, desc=f"Imaging {imaging_loop} of well {well}", total=total_fovs):
        for i, (loop_name, preset, post_fn) in enumerate(steps):
            img_path = snap(fov, input_preset=preset, imaging_loop=loop_name)
            if img_path is None:
                continue
            batches[i].append(img_path)
            if len(batches[i]) >= BATCH_SIZE:
                post_fn(batches[i])
                batches[i] = []

    # Process any remaining images in each batch
    for batch, (_, _, post_fn) in zip(batches, steps):
        if batch:
            post_fn(batch)

def _get_fovs_from_ids(well_obj: Well, fov_ids: list[str]) -> list[FieldOfView]:
    """
    Convert a list of FOV ID strings to list of FieldOfView objects from the well.
    
    Raises:
        ValueError: If any FOV ID is not found in the well's positive FOVs.
    """
    # Create a mapping from fov_id to FieldOfView object
    fov_map = {fov.fov_id: fov for fov in well_obj.positive_fovs}
    
    # Convert FOV IDs to FieldOfView objects
    result_fovs: list[FieldOfView] = []
    for fov_id in fov_ids:
        if fov_id not in fov_map:
            raise ValueError(f"FOV ID '{fov_id}' not found in well's positive FOVs. Available FOVs: {list(fov_map.keys())}")
        result_fovs.append(fov_map[fov_id])
    
    return result_fovs

def _process_single_fov(fov_obj: FieldOfView, input_preset: PresetMeasure | PresetControl | PresetRefseg, imaging_loop: str, a1_manager: A1Manager) -> Path | None:
    """
    Snap an image at the specified FOV using the given A1Manager and preset settings.
    """
    # Snap image
    img = snap_image(fov_obj.fov_coord, input_preset, a1_manager)
    
    # Check if image is empty (PFS initialization failed)
    if np.all(img == 0):
        logger.warning(f"Empty image captured for FOV {fov_obj.fov_id} in {imaging_loop}. PFS may have failed to initialize. Skipping save.")
        fov_obj.contain_positive_cells = False
        return None
    
    # Save image
    return _save_image(fov_obj, imaging_loop, img)

def _save_image(fov_obj: FieldOfView, imaging_loop: str, img: NDArray) -> Path:
    """
    Save the image to the appropriate directory and return the file path.
    """
    img_path = fov_obj.register_img_file(imaging_loop)
    imwrite_atomic(img_path, img.astype('uint16'))
    logger.debug(f"Image saved at {img_path}")
    return img_path

if __name__ == "__main__":
    a = [1,2,3]
    b = a[:-1]
    b[0] = 0
    print(a)
    print(b)
