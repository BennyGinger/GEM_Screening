import logging
from pathlib import Path
from typing import Any
from functools import partial

from a1_manager import A1Manager
from progress_bar import setup_progress_monitor as progress_bar

from gem_screening.utils.client import start_processing
from gem_screening.utils.filesystem import imwrite_atomic
from gem_screening.utils.prompts import prompt_to_continue, ADD_LIGAND_PROMPT
from gem_screening.well_data.well_classes import FieldOfView, Well


logger = logging.getLogger(__name__)

def scan_cells(well_obj: Well, settings: dict, a1_manager: A1Manager) -> str:
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
        settings (dict): Dictionary containing the settings for the imaging.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
    Raises:
        QuitImageCapture: If the user wants to quit the image capture process.
    """
    
    logger.info(f"Start imaging for well {well_obj.well_name} with run ID {well_obj.run_id}, round 1")
    _image_all_fov(well_obj, a1_manager, settings, "measure_1")
    
    # Ask user to stimulate cells
    if not prompt_to_continue(ADD_LIGAND_PROMPT):
        raise QuitImageCapture
    
    # Second imaging loop, after cell stimulation
    logger.info(f"Start imaging for well {well_obj.well_name} with run ID {well_obj.run_id}, round 2")
    _image_all_fov(well_obj, a1_manager, settings, "measure_2")
    
    # Save the well object
    well_obj.to_json()


################## Imaging Functions #################
def _image_all_fov(well_obj: Well, a1_manager: A1Manager, settings: dict, imaging_loop: str) -> None:
    """
    Take images of all the field of views in the well.
    Args:
        well_obj (Well): The well object containing the field of views.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
        settings (dict): Dictionary containing the settings for the imaging.
        imaging_loop (str): The imaging loop label to use for the acquisition.
    """
    # Whether to use a channel just for segmentation, otherwise fall back on the measurement channel
    use_refseg: bool = settings['refseg']
    
    # Settup imaging preset
    if imaging_loop.startswith('measure'):
        input_preset = settings['preset_measure']
        
    elif imaging_loop.__contains__('control'):
        input_preset = settings['preset_control']
        use_refseg = False
    
    if use_refseg:
        input_preset_refseg = settings['preset_refseg']
        imaging_loop_refseg = f"refseg_{imaging_loop.split('_')[-1]}"
    

    # Filter fov that contain positive cell
    fov_lst = well_obj.positive_fovs
    total_fovs = len(fov_lst)
    cp_settings: dict[str, Any] = settings['cellpose']
    
    partial_take_image_fov = partial(
        _take_image_fov,
        a1_manager=a1_manager,
        img_dir=well_obj.img_dir,
        total_fovs=total_fovs,
        run_id=well_obj.run_id,
        cp_settings=cp_settings,
    )
    # Go trhough all positive fov
    for fov_obj in progress_bar(fov_lst,
                        desc=f"Imaging {imaging_loop}",
                        total=total_fovs):
        # Take image of the fov
        partial_take_image_fov(fov_obj, 
                               input_preset=input_preset,
                               imaging_loop=imaging_loop)
        if use_refseg:
            partial_take_image_fov(fov_obj,
                                   input_preset=input_preset_refseg,
                                   imaging_loop=imaging_loop_refseg)

class QuitImageCapture:
    """
    Raised when the user wants to quit the image capture process.
    """
    pass
            
def _take_image_fov(fov_obj: FieldOfView, a1_manager: A1Manager, input_preset: dict, img_dir: Path, imaging_loop: str, total_fovs: int, run_id: str, cp_settings: dict[str, Any]) -> None:
    """
    Take an image of a field of view and save it to the specified directory.
    Args:
        fov_obj (FieldOfView): The field of view object containing the coordinates and ID.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
        input_preset (dict): Dictionary containing the settings for the imaging.
        img_dir (Path): The directory to save the image.
        imaging_loop (str): The imaging loop label to use for the acquisition.
        total_fovs (int): Total number of fields of view.
        run_id (str): Unique identifier for the processing run.
        cp_settings (dict[str, Any]): Settings for the Cellpose processing.
    """
    # Position stage
    a1_manager.nikon.set_stage_position(fov_obj.fov_coord)
    
    # Change oc settings
    a1_manager.oc_settings(**input_preset)
    a1_manager.load_dmd_mask() # Load the fullON mask
    
    # Take image and do background correction
    img = a1_manager.snap_image()
    
    # Save image
    img_path = img_dir.joinpath(f"{fov_obj.fov_ID}_{imaging_loop}.tif")
    imwrite_atomic(img_path, img.astype('uint16'))
    fov_obj.add_image(imaging_loop, img_path)
    
    # Build the payload for image processing
    process_payload = _build_payload(
        run_id=run_id,
        settings=cp_settings,
        img_file=img_path,
        round=imaging_loop.split('_')[-1],
        dst_folder=img_dir,
        total_fovs=total_fovs,)
    
    # Start the image processing task
    start_processing(process_payload)

def _build_payload(run_id: str, settings: dict[str, Any], img_file: str | list[str], round: int, dst_folder: Path, total_fovs: int) -> dict[str, Any]:
    """
    Build the payload for the image processing request.
    Args:
        settings (dict): Dictionary containing the settings for the image processing.
        img_paths (list[str]): List of image paths to process.
        round (int): The round number for processing.
        dst_folder (Path): The destination folder where processed images will be saved.
        total_fovs (int): Total number of fields of view.
    Returns:
        dict: The payload to send to the image processing endpoint.
    """
    # Default parameters for the payload
    mod_sets = {"model_type": "cyto2",
                "restore_type": "denoise_cyto2",
                "gpu": True,}
    
    cp_sets = {"channels": None,
               "diameter": 60,
               "flow_threshold": 0.4,
               "cellprob_threshold": 0.0,
               "z_axis": None,
               "do_3D": False,
               "stitch_threshold": 0,}
    
    other_params = {
        "do_denoise": True,
        "stitch_threshold": 0.75,
        "sigma": 0.0,
        "size": 7,}
    
    # Extract the model and cellpose settings from the input settings
    for k, v in settings.items():
        if k in mod_sets:
            mod_sets[k] = v
        elif k in cp_sets:
            cp_sets[k] = v
        elif k in other_params:
            other_params[k] = v
    
    # Build the payload
    return {
        'run_id': run_id,
        "mod_settings": mod_sets,
        "cp_settings": cp_sets,
        "img_file": img_file,
        "dst_folder": str(dst_folder),
        "round": round,
        "total_fovs": total_fovs if round == 2 else None,
        **other_params,}


