from __future__ import annotations
from pathlib import Path

from celltinder import run_cell_tinder
from a1_manager import A1Manager, launch_dish_workflow

from gem_screening.utils.filesystem import create_timestamped_dir




################# Main Function #################
def complete_pipeline(settings: dict) -> None:
    """
    Main function to run the complete pipeline for cell imaging and stimulation.
    Args:
        settings (dict): Dictionary containing all the settings for the pipeline.
    """
    # Initialise mm and set up microscope
    aquisition = A1Manager(**settings['aquisition_settings'])
    
    # Initialise pipeline
    run_dir = create_timestamped_dir(settings['savedir'], settings['savedir_name'])