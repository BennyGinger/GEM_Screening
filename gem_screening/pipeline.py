from __future__ import annotations

from a1_manager import launch_dish_workflow
from a1_manager.autofocus.af_utils import QuitAutofocus

from gem_screening.tasks.initialization import initialize_pipeline
from gem_screening.utils.prompts import prompt_to_continue, FOCUS_PROMPT
from gem_screening.utils.prompt_gui import PipelineQuit
from gem_screening.utils.settings.models import PipelineSettings


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

       
if __name__ == '__main__':
    from gem_screening.utils.settings.settings import full_settings
    
    complete_pipeline(full_settings)