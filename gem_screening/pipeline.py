from __future__ import annotations
from pathlib import Path
from enum import Enum

from a1_manager import launch_dish_workflow
from a1_manager.autofocus.af_utils import QuitAutofocus

from gem_screening.tasks.initialization import initialize_pipeline, initialize_rescue_pipeline
from gem_screening.tasks.rescue_utils import load_saved_well_obj, load_saved_settings
from gem_screening.utils.prompts import prompt_to_continue, FOCUS_PROMPT
from gem_screening.utils.prompt_gui import PipelineQuit
from gem_screening.utils.settings.models import PipelineSettings

# TODO: Check that the edge case with no refseg mask will work fine
def complete_pipeline(settings: PipelineSettings) -> None:
    """
    Main function to run the complete pipeline for cell imaging and stimulation.
    Args:
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
    """
    
    # Initialise pipeline
    a1_manager, run_dir, logger, run_id = initialize_pipeline(settings)
    
    # Prompt user to focus on cells
    try: 
        prompt_to_continue(FOCUS_PROMPT)
    except PipelineQuit:
        logger.info("User chose to quit during focus prompt. Stopping pipeline.")
        return
    
    try:
        # Generate the dish_grid
        dish_grid = launch_dish_workflow(a1_manager, run_dir, **settings.dish_settings.model_dump())
        logger.info(f"Generated dish grid")
        logger.debug(f"dish_grid: {dish_grid}")
    except QuitAutofocus:
        logger.info("User chose to quit during autofocus. Stopping pipeline.")
        return
    
    # Run the pipeline workflow, lazy import to ensure all environment variables are set before importing
    from gem_screening.tasks.workflows import run_complete_flow
    try:
        run_complete_flow(dish_grid, a1_manager, run_dir, run_id, settings)
    except PipelineQuit:
        logger.info("User chose to quit during pipeline execution. Stopping pipeline.")
        return
    
    logger.info("Pipeline completed successfully.")

class PipelineStage(Enum):
    """
    Enumeration for the different stages of the pipeline.
    Attributes:
        
        ROUND1 (str): To start from the first scanning round (before cell stimulation). Can be full or partial scanning.
        
        ROUND2 (str): To start from the second scanning round. It expects that the first round was completed.
        Can be full, partial or 'empty' scanning, if only tracking is needed.
        
        CELLTINDER (str): To start the CellTinder stage. It expects that both scanning rounds were completed, including cell tracking.
        
        ILLUMINATION (str): To start the illumination stage. It expects that both scanning rounds were completed, including cell tracking and cell selection using CellTinder. Technically, this stage only requires the csv file amended by CellTinder (`process` and threshold columns).
    """
    ROUND1 = "scan_round1"
    ROUND2 = "scan_round2"
    CELLTINDER = "celltinder"
    ILLUMINATION = "illumination"


def rescue_pipeline(run_dir: Path, settings: PipelineSettings | None = None, pipeline_stage: PipelineStage | None = None, well_selection: str | list[str] | None = None) -> None:
    
    # Load the well_obj
    wells_lst = load_saved_well_obj(run_dir, well_selection)

    # Load settings if not provided
    if settings is None:
        settings = load_saved_settings(run_dir)
    
    # Get run_id from the first well object (all wells should have the same run_id)
    run_id = wells_lst[0].run_id
    
    # Initialize rescue pipeline with existing run_dir and run_id
    a1_manager, logger = initialize_rescue_pipeline(settings, run_dir, run_id)

    
        
 


   
if __name__ == '__main__':
    from gem_screening.utils.settings.settings import full_settings
    
    complete_pipeline(full_settings)