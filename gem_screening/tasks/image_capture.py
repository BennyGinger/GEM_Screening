from pathlib import Path

from a1_manager import A1Manager
from tifffile import imwrite
from progress_bar import setup_progress_monitor as progress_bar

from gem_screening.utils.prompts import prompt_to_continue, ADD_LIGAND_PROMPT
from gem_screening.well_data.well_classes import FieldOfView, Well



def scan_cells(well_obj: Well, settings: dict, a1_manager: A1Manager)-> None:
    """
    Main function to scan cells in a well. It takes images of all the field of views in the well and saves them. The user is prompted to stimulate the cells after the first imaging loop. If the user chooses to quit, a QuitImageCapture exception is raised.
    The second imaging loop is performed after the user has stimulated the cells.
    The well object is saved after the imaging loops.
    Args:
        well_obj (Well): The well object containing the field of views.
        settings (dict): Dictionary containing the settings for the imaging.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
    Raises:
        QuitImageCapture: If the user wants to quit the image capture process.
    """
    
    _image_all_fov(well_obj, a1_manager, settings, "measure_1")
    
    # Ask user to stimulate cells
    if not prompt_to_continue(ADD_LIGAND_PROMPT):
        raise QuitImageCapture
    
    # Second imaging loop, after cell stimulation
    _image_all_fov(well_obj, a1_manager, settings, "measure_2")
    
    # Save the well object
    well_obj.to_json()


def _image_all_fov(well_obj: Well, a1_manager: A1Manager, settings: dict, imaging_loop: str)-> None:
    """
    Take images of all the field of views in the well.
    Args:
        well_obj (Well): The well object containing the field of views.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
        settings (dict): Dictionary containing the settings for the imaging.
        imaging_loop (str): The imaging loop label to use for the acquisition.
    """
    print(f"\nStart imaging for loop {imaging_loop}")
    
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
    fov_lst = [fov for fov in well_obj.positive_fovs]
    
    # Go trhough all positive fov
    for fov_obj in progress_bar(fov_lst,
                        desc=f"Imaging {imaging_loop}",
                        total=len(fov_lst)):
        _take_image_fov(fov_obj, a1_manager, input_preset, well_obj.img_dir, imaging_loop)
        
        if use_refseg:
            _take_image_fov(fov_obj, a1_manager, input_preset_refseg, well_obj.img_dir, imaging_loop_refseg)
            
            

def _take_image_fov(fov_obj: FieldOfView, a1_manager: A1Manager, input_preset: dict, img_dir: Path, imaging_loop: str)-> None:
    """
    Take an image of a field of view and save it to the specified directory.
    Args:
        fov_obj (FieldOfView): The field of view object containing the coordinates and ID.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
        input_preset (dict): Dictionary containing the settings for the imaging.
        img_dir (Path): The directory to save the image.
        imaging_loop (str): The imaging loop label to use for the acquisition.
    """
    # Position stage
    a1_manager.nikon.set_stage_position(fov_obj.fov_coord)
    
    # Change oc settings
    a1_manager.oc_settings(**input_preset)
    a1_manager.load_dmd_mask() # Load the fullON mask
    
    # Take image and do background correction
    img = a1_manager.snap_image()
    
    # Save image
    img_path = img_dir.joinpath(f"{fov_obj.fov_ID}_{imaging_loop}.png")
    # FIXME: Need to check the atomic saving from server
    imwrite(img_path, img.astype('uint16'), compression='zlib')
    fov_obj.add_image(imaging_loop, img_path)
    

class QuitImageCapture:
    """
    Raised when the user wants to quit the image capture process.
    """
    pass