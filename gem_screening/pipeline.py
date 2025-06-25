from __future__ import annotations

from a1_manager import A1Manager, launch_dish_workflow

from gem_screening.utils.env_loader import load_pipeline_env
load_pipeline_env()
from gem_screening.logger import get_logger, configure_logging
from gem_screening.tasks.data_intensity import extract_measure_intensities, update_control_intensities
from gem_screening.tasks.image_capture import QuitImageCapture, scan_cells
from gem_screening.tasks.light_stimulation import create_stim_masks, illuminate_fovs
from gem_screening.tasks.mask_utils import assign_masks_to_fovs
from gem_screening.utils.client.client import cleanup_stale, wait_for_completion
from gem_screening.utils.external import run_celltinder
from gem_screening.utils.filesystem import create_timestamped_dir
from gem_screening.utils.identifiers import make_run_id
from gem_screening.utils.prompts import prompt_to_continue, FOCUS_PROMPT
from gem_screening.utils.settings.models import PipelineSettings
from gem_screening.well_data.well_classes import Well


# TODO: Create different entry point to the pipeline, if anything goes wrong in the pipeline
################# Main Function #################
def complete_pipeline(settings: PipelineSettings) -> None:
    """
    Main function to run the complete pipeline for cell imaging and stimulation.
    Args:
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
    """
    # Lazy import to make sure all env vars are set before importing
    from cp_server import ComposeManager
    
    with ComposeManager():
        # Initialise mm and set up microscope
        acqui = settings.acquisition_settings
        a1_manager = A1Manager(**acqui.model_dump())
        
        # Initialise pipeline
        run_dir = create_timestamped_dir(settings.savedir, 
                                         settings.savedir_name)
        
        # Set up logging
        configure_logging(run_dir)
        logger = get_logger(__name__)
        
        # Log the run directory and run ID
        run_id = make_run_id()
        logger.info(f"Created run directory: {run_dir} with run ID: {run_id}")
        
        # Prompt user to focus on cells
        if not prompt_to_continue(FOCUS_PROMPT):
            return
        
        # Generate the dish_grid
        dish_sets = settings.dish_settings
        dish_grid = launch_dish_workflow(a1_manager, run_dir, **dish_sets.model_dump())
        logger.info(f"Generated dish grid: {dish_grid}")
        
        # Clean up the redis server
        cleanup_stale()
        
        # Start imaging
        for well, well_grid in dish_grid.items():
            
            logger.info(f"Processing well: {well}")
            
            # Create a well object
            well_obj = Well(run_dir=run_dir,
                            run_id=run_id,
                            well_grid=well_grid,
                            well=well)
            # Scan cells
            try:
                # Scan cells in the well, images will then be sent to the server for processing
                scan_cells(well_obj, settings, a1_manager)
                # Wait for processing to complete, this will block until all celery tasks are done.
                wait_for_completion(run_id, timeout=settings.server_settings.server_timeout_sec)
            except QuitImageCapture:  
                logger.info("User chose to quit the image capture process.")
                break
            
            # Assign masks to the well's field of views (save the well object)
            assign_masks_to_fovs(well_obj)
            
            # Extract the stimulation settings
            stim_sets = settings.stim_settings
            
            # Extract the data
            extract_measure_intensities(well_obj.positive_fovs,
                             true_cell_threshold=stim_sets.true_cell_threshold,
                             csv_path=well_obj.csv_path,)

            # Run the cell tinder GUI
            run_celltinder(well_obj.csv_path,
                            crop_size=stim_sets.crop_size)
            
            # create stim masks
            create_stim_masks(well_obj,
                              erosion_factor=stim_sets.erosion_factor)
            
            # Illumintate the cells
            illuminate_fovs(well_obj, a1_manager, settings)

            # Extract the control data
            update_control_intensities(well_obj.positive_fovs,
                                       csv_path=well_obj.csv_path)
            
if __name__ == '__main__':
    from time import sleep
    def fake_main():
        # Lazy import to make sure all env vars are set before importing
        from cp_server import ComposeManager
        with ComposeManager():
            print("Starting the complete pipeline...")
            # resp = input("Press Enter to continue or Ctrl+C to exit...")
            sleep(10)
            print("Pipeline started successfully.")
    fake_main()