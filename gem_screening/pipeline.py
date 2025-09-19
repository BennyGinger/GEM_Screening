from __future__ import annotations
from pathlib import Path
from enum import Enum

from a1_manager import launch_dish_workflow
from a1_manager.autofocus.af_utils import QuitAutofocus

from gem_screening.tasks.initialization import initialize_pipeline, initialize_rescue_pipeline
from gem_screening.tasks.rescue_utils import load_saved_well_obj, load_saved_settings
from gem_screening.utils.prompts import prompt_to_continue, FOCUS_PROMPT
from gem_screening.utils.prompt_gui import PipelineQuit
from gem_screening.settings.models import PipelineSettings

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
    if settings.dish_settings.dish_name.lower() != '35mm':
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

def rescue_pipeline(run_dir: Path, settings: PipelineSettings | None = None, well_selection: str | list[str] | None = None) -> None:
    """
    Function to rescue a previously run pipeline from a specified run directory.
    Args:
        run_dir (Path): The directory where the previous run data is stored.
        settings (PipelineSettings | None): The settings for the pipeline. If None, settings will be loaded from the run directory.
        well_selection (str | list[str] | None): Specific wells to rescue. If None, all wells will be rescued.
    """
    # Load the well_obj
    wells_lst = load_saved_well_obj(run_dir, well_selection)

    # Load settings if not provided
    if settings is None:
        settings = load_saved_settings(run_dir)
    
    # Get run_id from the first well object (all wells should have the same run_id)
    run_id = wells_lst[0].run_id
    
    # Initialize rescue pipeline with existing run_dir and run_id
    a1_manager, logger = initialize_rescue_pipeline(settings, run_dir, run_id)

    from gem_screening.tasks.workflows import run_rescue_flow
    try:
        run_rescue_flow(a1_manager, settings, wells_lst)
    except PipelineQuit:
        logger.info("User chose to quit during pipeline execution. Stopping pipeline.")
        return
    
    logger.info("Pipeline rescue completed successfully.")
        
 


   
if __name__ == '__main__':
    from gem_screening.settings.settings import full_settings
    
    complete_pipeline(full_settings)