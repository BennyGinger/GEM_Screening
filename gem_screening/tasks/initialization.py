from __future__ import annotations
from pathlib import Path
import logging

from a1_manager import A1Manager

from gem_screening.utils.env_loader import load_pipeline_env
from gem_screening.logger import get_logger, configure_logging
from gem_screening.utils.filesystem import create_timestamped_dir
from gem_screening.utils.identifiers import make_run_id
from gem_screening.utils.settings.models import PipelineSettings


def initialize_pipeline(settings: PipelineSettings) -> tuple[A1Manager, Path, logging.Logger, str]:
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
    logger = get_logger("main")
    
    # Log the run directory and run ID
    run_id = make_run_id()
    logger.info("=" * 80)
    logger.info(f"Created run directory: {run_dir} with run ID: {run_id}")
    return a1_manager, run_dir, logger, run_id
