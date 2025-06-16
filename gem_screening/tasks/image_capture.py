import logging
from pathlib import Path
from functools import partial

from a1_manager import A1Manager
from progress_bar import setup_progress_monitor as progress_bar

from gem_screening.utils.client.client import submit_full_processing, submit_bg_subtraction
from gem_screening.utils.client.models import build_payload
from gem_screening.utils.filesystem import imwrite_atomic
from gem_screening.utils.identifiers import parse_category_instance
from gem_screening.utils.prompts import prompt_to_continue, ADD_LIGAND_PROMPT
from gem_screening.utils.settings.models import PipelineSettings, PresetMeasure, PresetControl, PresetRefseg, ServerSettings
from gem_screening.well_data.well_classes import FieldOfView, Well


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
    
    logger.info(f"Start imaging for well {well_obj.well} with run ID {well_obj.run_id}, round 1")
    _image_all_fov(well_obj, a1_manager, settings, "measure_1")
    
    # Ask user to stimulate cells
    if not prompt_to_continue(ADD_LIGAND_PROMPT):
        raise QuitImageCapture
    
    # Second imaging loop, after cell stimulation
    logger.info(f"Start imaging for well {well_obj.well} with run ID {well_obj.run_id}, round 2")
    _image_all_fov(well_obj, a1_manager, settings, "measure_2")
    
    # Save the well object
    well_obj.to_json()


################## Imaging Functions #################
def _image_all_fov(well_obj: Well, a1_manager: A1Manager, settings: PipelineSettings, imaging_loop: str) -> None:
    """
    Take images of all the field of views in the well.
    Args:
        well_obj (Well): The well object containing the field of views.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
        settings (PipelineSettings): The settings for the imaging pipeline.
        imaging_loop (str): The imaging loop label to use for the acquisition. Expected format is `"<category>_<instance>"`.
    """
    # Setup the imaging loop
    use_refseg = settings.measure_settings.refseg
    fov_lst = well_obj.positive_fovs
    total_fovs = len(fov_lst)
    server_settings: ServerSettings = settings.server_settings
    server_settings.run_id = well_obj.run_id
    server_settings.dst_folder = str(well_obj.mask_dir)
    server_settings.total_fovs = total_fovs
    
    input_preset: PresetMeasure | PresetControl
    if 'measure' in imaging_loop:
        input_preset = settings.measure_settings.preset_measure
    elif 'control' in imaging_loop:
        input_preset = settings.control_settings.preset
        use_refseg = False
    else:
        raise ValueError(f"Invalid imaging loop: {imaging_loop}. Expected 'measure' or 'control' in the loop name.")
    
    input_preset_refseg: PresetRefseg | None = None
    if use_refseg:
        input_preset_refseg = settings.measure_settings.preset_refseg
        imaging_loop_refseg = f"refseg_{parse_category_instance(imaging_loop)[1]}"
    
    # Prepare the imaging function
    partial_take_image_fov = partial(
        _take_image_fov,
        a1_manager=a1_manager)
    
    # Go trhough all positive fov
    for fov_obj in progress_bar(fov_lst,
                        desc=f"Imaging {imaging_loop}",
                        total=total_fovs):
        # Take image of the fov
        img_path = partial_take_image_fov(fov_obj, 
                               input_preset=input_preset,
                               imaging_loop=imaging_loop)
        
        if use_refseg:
            # Send the `measure` image for bg processing
            bg_payload = build_payload(img_path=img_path,
                                       server_settings=server_settings,
                                       bg_only=True)
            submit_bg_subtraction(bg_payload)
                                              
            # Overwrite the `measure` img_path with the `refseg` image path
            img_path = partial_take_image_fov(fov_obj,
                                   input_preset=input_preset_refseg,
                                   imaging_loop=imaging_loop_refseg)
        
        # Send the `measure` or `refseg` to full processing
        full_payload = build_payload(img_path=img_path,
                                     server_settings=server_settings,
                                     )
        submit_full_processing(full_payload)

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
        server_settings (dict): Dictionary containing the server settings for the image processing.
        round_num (int): The round number for processing.
        total_fovs (int): Total number of fields of view.
    Returns:
        Path: The path where the image is saved.
    """
    # Position stage
    a1_manager.nikon.set_stage_position(fov_obj.fov_coord)
    
    # Change oc settings
    a1_manager.oc_settings(**input_preset.model_dump())
    a1_manager.load_dmd_mask() # Load the fullON mask
    
    # Take image and do background correction
    img = a1_manager.snap_image()
    
    # Save image
    img_path = fov_obj.register_img_file(imaging_loop)
    imwrite_atomic(img_path, img.astype('uint16'))
    logger.info(f"Image saved at {img_path}")
    
    # Build the payload for the image processing request
    return img_path

