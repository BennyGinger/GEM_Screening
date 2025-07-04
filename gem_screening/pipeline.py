from __future__ import annotations
from pathlib import Path
import logging

from a1_manager import A1Manager, launch_dish_workflow

from gem_screening.utils.env_loader import load_pipeline_env
from gem_screening.logger import get_logger, configure_logging
from gem_screening.utils.filesystem import create_timestamped_dir
from gem_screening.utils.identifiers import make_run_id
from gem_screening.utils.prompts import prompt_to_continue, FOCUS_PROMPT
from gem_screening.utils.settings.models import PipelineSettings


# TODO: Create different entry point to the pipeline, if anything goes wrong in the pipeline
################# Main Function #################
def complete_pipeline(settings: PipelineSettings) -> None:
    """
    Main function to run the complete pipeline for cell imaging and stimulation.
    Args:
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
    """
    
    # Initialise pipeline
    a1_manager, run_dir, logger, run_id = _initialize_pipeline(settings)
    
    # Prompt user to focus on cells
    if not prompt_to_continue(FOCUS_PROMPT):
        return
    
    # Generate the dish_grid
    dish_grid = launch_dish_workflow(a1_manager, run_dir, **settings.dish_settings.model_dump())
    logger.info(f"Generated dish grid: {dish_grid}")
    
    # Run the pipeline workflow, lazy import to ensure all environment variables are set before importing
    from gem_screening.tasks.pipeline_workflows import run_pipeline
    run_pipeline(dish_grid, a1_manager, run_dir, run_id, settings)
    
    logger.info("Pipeline completed successfully.")

############### Helper Functions ##############
def _initialize_pipeline(settings: PipelineSettings) -> tuple[A1Manager, Path, logging.Logger, str]:
    """
    Initialise the pipeline by setting up the A1Manager, creating a run directory,
    and configuring logging.
    Args:
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
    Returns:
        tuple: A tuple containing the A1Manager instance, run directory path, logger instance, and run ID.
    """
    acqui = settings.acquisition_settings
    a1_manager = A1Manager(**acqui.model_dump())
    
    # Initialise pipeline
    run_dir = create_timestamped_dir(settings.savedir, 
                                        settings.savedir_name)
    
    # Load environment variables for the pipeline
    logging_sets = settings.logging_settings
    base_url = settings.base_url
    load_pipeline_env(run_dir, base_url=base_url, **logging_sets.model_dump())
    
    # Set up logging
    configure_logging(run_dir)
    logger = get_logger(__name__)
    
    # Log the run directory and run ID
    run_id = make_run_id()
    logger.info("=" * 80)
    logger.info(f"Created run directory: {run_dir} with run ID: {run_id}")
    return a1_manager,run_dir,logger,run_id

       
if __name__ == '__main__':
    from gem_screening.utils.settings.settings import full_settings
    
    complete_pipeline(full_settings)