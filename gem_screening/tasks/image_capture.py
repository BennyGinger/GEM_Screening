from __future__ import annotations
import logging
from pathlib import Path
from functools import partial

from a1_manager import A1Manager
from progress_bar import setup_progress_monitor as progress_bar

from gem_screening.utils.client.client import bg_removal_client, full_process_client
from gem_screening.utils.filesystem import imwrite_atomic
from gem_screening.utils.identifiers import parse_category_instance
from gem_screening.utils.pipeline_constants import MEASURE_LABEL, REFSEG_LABEL
from gem_screening.utils.prompts import prompt_to_continue, ADD_LIGAND_PROMPT
from gem_screening.utils.settings.models import PipelineSettings, PresetMeasure, PresetControl, ServerSettings
from gem_screening.well_data.well_classes import FieldOfView, Well


# Set up logging
logger = logging.getLogger(__name__)


def scan_cells(well_obj: Well, settings: PipelineSettings, a1_manager: A1Manager) -> None:
    """
    Main function to scan cells in a well. It takes images of all the field of views in the well and saves them.
    The images are then sent to the server for processing, which includes background subtraction, segmentation, and tracking.
    The function performs two imaging loops:
    1. The first imaging loop captures images of the cells in the well.
    2. The user is prompted to stimulate the cells after the first imaging loop.
    3. If the user chooses to continue, a second imaging loop captures images after the stimulation.
    4. If the user chooses to quit, a QuitImageCapture exception is raised and the process is terminated.
    The well object is saved after the imaging loops.
    Args:
        well_obj (Well): The well object containing the field of views.
        settings (PipelineSettings): The settings for the imaging pipeline.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
    Raises:
        QuitImageCapture: If the user wants to quit the image capture process.
    """
    
    logger.info(f"Start imaging for well ID {well_obj.well_id}, round 1")
    image_all_fov(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_1")
    
    # Ask user to stimulate cells
    if not prompt_to_continue(ADD_LIGAND_PROMPT):
        raise QuitImageCapture
    
    # Second imaging loop, after cell stimulation
    logger.info(f"Start imaging for well ID {well_obj.well_id}, round 2")
    image_all_fov(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_2")
    
    logger.info(f"Finished imaging for well ID {well_obj.well_id}")
        
def image_all_fov(well_obj: Well, a1_manager: A1Manager, settings: PipelineSettings, imaging_loop: str) -> None:
    """
    Take images of all the field of views in the well.
    
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
    """
    # Setup the imaging loop
    server_settings: ServerSettings = settings.server_settings
    server_settings.well_id = well_obj.well_id
    server_settings.dst_folder = str(well_obj.mask_dir)
    server_settings.total_fovs = len(well_obj.positive_fovs)
    
    # Initialize the different steps functions
    snap = partial(_take_image_fov, a1_manager=a1_manager)
    bg_removal = partial(bg_removal_client, server_settings=server_settings)
    full_process = partial(full_process_client, server_settings=server_settings)
    
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
    total_fovs = len(well_obj.positive_fovs)
    for fov in progress_bar(well_obj.positive_fovs,
                            desc=f"Imaging {imaging_loop}",
                            total=total_fovs):
        for loop_name, preset, post_fn in steps:
            # Take image of the fov
            img_path = snap(fov, input_preset=preset, imaging_loop=loop_name)
            
            # Post-process the image
            post_fn(img_path)
    
    # Save the well object
    well_obj.to_json()

class QuitImageCapture:
    """
    Raised when the user wants to quit the image capture process.
    """
    pass

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
    logger.info(f"Image saved at {img_path}")
    
    # Build the payload for the image processing request
    return img_path

