from __future__ import annotations

from a1_manager import A1Manager, launch_dish_workflow

from gem_screening.logger import get_logger
from gem_screening.tasks.image_capture import QuitImageCapture, scan_cells
from gem_screening.tasks.mask_utils import assign_masks_to_fovs
from gem_screening.utils.client.client import cleanup_stale, wait_for_completion
from gem_screening.utils.filesystem import create_timestamped_dir
from gem_screening.utils.identifiers import make_run_id
from gem_screening.utils.prompts import prompt_to_continue, FOCUS_PROMPT
from gem_screening.utils.settings.models import PipelineSettings, AcquisitionSettings, DishSettings
from gem_screening.well_data.well_classes import Well


# Set up logging
logger = get_logger(__name__)

################# Main Function #################
def complete_pipeline(settings: PipelineSettings) -> None:
    """
    Main function to run the complete pipeline for cell imaging and stimulation.
    Args:
        settings (dict): Dictionary containing all the settings for the pipeline.
    """
    # Lazy import to make sure all env vars are set before importing
    from cp_server import ComposeManager
    
    with ComposeManager():
        # Initialise mm and set up microscope
        acqui: AcquisitionSettings = settings.aquisition_settings
        a1_manager = A1Manager(**acqui.model_dump())
        
        # Initialise pipeline
        run_dir = create_timestamped_dir(settings.savedir, 
                                         settings.savedir_name)
        run_id = make_run_id()
        logger.info(f"Created run directory: {run_dir} with run ID: {run_id}")
        
        # Prompt user to focus on cells
        if not prompt_to_continue(FOCUS_PROMPT):
            return
        
        # Generate the dish_grid
        dish_sets: DishSettings = settings.dish_settings
        dish_grid = launch_dish_workflow(a1_manager, run_dir, **dish_sets.model_dump())
        
        # Clean up the redis server
        cleanup_stale()
        
        # Start imaging
        for well, well_grid in dish_grid.items():
            # Create a well object
            well_obj = Well(run_dir=run_dir,
                            run_id=run_id,
                            well_grid=well_grid,
                            well_name=well)
            
            # Scan cells
            try:
                # Scan cells in the well, images will then be sent to the server for processing
                scan_cells(well_obj, settings, a1_manager)
                # Wait for processing to complete, this will block until all celery tasks are done.
                wait_for_completion(run_id)
            except QuitImageCapture:  
                logger.info("User chose to quit the image capture process.")
                break
            
            # Assign masks to the well's field of views
            assign_masks_to_fovs(well_obj.positive_fovs, well_obj.mask_dir)
            
            logger.info("Image capture process completed and masks assigned successfully.")


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