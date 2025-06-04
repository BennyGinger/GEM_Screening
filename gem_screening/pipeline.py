from __future__ import annotations

from a1_manager import A1Manager, launch_dish_workflow

# Load environment variables from .env file
from gem_screening.config import ROOT_DIR, HOST_LOG_FOLDER
from gem_screening.utils.env_loader import load_pipeline_env
load_pipeline_env(ROOT_DIR, host_log_folder=str(HOST_LOG_FOLDER))

# Set up logging
from gem_screening.logger import get_logger
logger = get_logger(__name__)

from gem_screening.tasks.image_capture import QuitImageCapture, scan_cells
from gem_screening.utils.client import cleanup_stale
from gem_screening.utils.filesystem import create_timestamped_dir
from gem_screening.utils.identifiers import make_run_id
from gem_screening.utils.prompts import prompt_to_continue, FOCUS_PROMPT
from gem_screening.well_data.well_classes import Well


################# Main Function #################
def complete_pipeline(settings: dict[str, any]) -> None:
    """
    Main function to run the complete pipeline for cell imaging and stimulation.
    Args:
        settings (dict): Dictionary containing all the settings for the pipeline.
    """
    # Lazy import to make sure all env vars are set before importing
    from cp_server import ComposeManager
    
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
                # TODO: add the process call to scan_cells
                scan_cells(well_obj, settings, a1_manager)
            
            except QuitImageCapture:  
                logger.info("User chose to quit the image capture process.")
                break
            
            logger.info("Image capture process completed.")


if __name__ == '__main__':
    
    def fake_main():
        # Lazy import to make sure all env vars are set before importing
        from cp_server import ComposeManager
        with ComposeManager():
            print("Starting the complete pipeline...")
            resp = input("Press Enter to continue or Ctrl+C to exit...")
            print("Pipeline started successfully.")
    fake_main()