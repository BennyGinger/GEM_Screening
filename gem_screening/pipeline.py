from __future__ import annotations
import logging
from pathlib import Path

from celltinder import run_cell_tinder
from a1_manager import A1Manager, launch_dish_workflow
from cp_server import ComposeManager

from gem_screening.tasks.image_capture import QuitImageCapture, scan_cells
from gem_screening.utils.client import cleanup_stale
from gem_screening.utils.filesystem import create_timestamped_dir
from gem_screening.utils.identifiers import make_run_id
from gem_screening.utils.prompts import prompt_to_continue, FOCUS_PROMPT
from gem_screening.well_data.well_classes import Well


logger = logging.getLogger(__name__)

################# Main Function #################
def complete_pipeline(settings: dict[str, any]) -> None:
    """
    Main function to run the complete pipeline for cell imaging and stimulation.
    Args:
        settings (dict): Dictionary containing all the settings for the pipeline.
    """
    with ComposeManager():
        # Initialise mm and set up microscope
        a1_manager = A1Manager(**settings['aquisition_settings'])
        
        # Initialise pipeline
        run_dir = create_timestamped_dir(settings['savedir'], settings['savedir_name'])
        run_id = make_run_id()
        logger.info(f"Created run directory: {run_dir} with run ID: {run_id}")
        
        # Prompt user to focus on cells
        if not prompt_to_continue(FOCUS_PROMPT):
            return
        
        # Generate the dish_grid
        dish_grid = launch_dish_workflow(a1_manager, run_dir, **settings['dish_settings'])
        
        # Clean up the redis server
        cleanup_stale()
        
        # Start imaging
        for well, well_grid in dish_grid.items():
            # Create a well object
            well_obj = Well(run_dir=run_dir,
                            well_grid=well_grid,
                            well_name=well)
            
            # Scan cells
            try:
                scan_cells(well_obj, settings, a1_manager)
            
            except QuitImageCapture:  
                logger.info("User chose to quit the image capture process.")
                break
            
            logger.info("Image capture process completed.")
        

    
    
    
    

if __name__ == '__main__':
    # Load settings
    settings = {
    # savedir for images
    'savedir': r'D:\Ben',
    'savedir_name': 'test_celltinder',
    
    # Aquisition setting
    'aquisition_settings': {'objective': '20x', # Only 10x or 20x are calibrated for now
                           'lamp_name': 'pE-800',  # 'pE-800','pE-4000','DiaLamp'
                           'focus_device': 'PFSOffset'}, # 'PFSOffset' or 'ZDrive'
    #  Initiate dish
    'dish_settings': {'dish_name': '35mm', # '35mm' 'ibidi-8well' '96well'
                     'overwrite_calib': False, # if True, will overwrite the calibration file
                     'well_selection': ['A1'], # if 'all', will do all possible wells, otherwise enter a list of wells ['A1','A2',...]
                     'numb_field_view': 3, # if None, will run the whole well --> 35mm dish full coverage has 1418 field of view
                     'overlap_percent': None}, # in 0-100% Only applicable to complete well coverage (i.e. 'numb_field_view'=None). if None then will use optimal overlap for the dish
                   
    # Autofocus settings
    # if Manual, need to focus with the focus device selected above in micromanager
    'autofocus': {'method': 'sq_grad', # Choose mtd label here, ['sq_grad','Manual']
                  'overwrite': False}, # If True, will overwrite the autofocus
    
    # Channel list for measurment
    'preset_measure': {'optical_configuration': 'GFP', # Channel to seg for analysis
                  'intensity': 25}, # 0-100%
    
    # Channel list for refseg
    'refseg': True, # If True, will do a second imaging loop before and after light stimulation in the target channel 
    'refseg_threshold': 50, # Minimum pixel intensity to be considered as a cell
    'preset_refseg': {'optical_configuration': 'iRed', # Channel to seg for analysis
                  'intensity': 5}, # 0-100%
    
    # Segmetation settings
    'cellpose': {'diameter': 40, 
                 'flow_threshold': 1, 
                 'cellprob_threshold': 0}, # Cellpose settings 10x: 20-25, 20x: 40-50, tried 20 with 10x and it seemed perfect - Boldi

    # Stimulation masks
    'stimasks': {'erosion_factor': 3,}, # for the stim masks to avoid stimulation of neibourghing cells, radius size in pixels

    # Stimulation
    'preset_stim': {'optical_configuration': 'BFP', # Channel for control after light stimulation
                    'intensity': 100, # 0-100%
                    'exposure_sec': 10},  # in sec'
    
    'control_loop': True, # If True, will do a third imaging loop before and after light stimulation in the target channel
    'preset_control': {'optical_configuration': 'RFP', # Channel for control after light stimulation
                        'intensity': 40},
    }