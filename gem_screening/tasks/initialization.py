from __future__ import annotations
from pathlib import Path
import logging

from a1_manager import A1Manager

from gem_screening.utils.env_loader import load_pipeline_env
from gem_screening.logger import get_logger, configure_logging
from gem_screening.utils.filesystem import create_timestamped_dir
from gem_screening.utils.identifiers import get_run_id
from gem_screening.utils.pipeline_constants import CONFIG_FOLDER
from gem_screening.settings.models import PipelineSettings, MeasureSettings


PRE_STAGE_POS = {'35mm':{'ZDrive':2500,'PFSOffset':8200},
                 '96well':{'ZDrive':5500,'PFSOffset':8200},
                 '384well':{'ZDrive':5500,'PFSOffset':8200}}


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
    
    # Move the stage to a predefined safe position before starting autofocus
    _set_predefined_position(a1_manager, settings)

    # Set up the optical config
    _set_oc(settings, a1_manager)
    
    # Initialise pipeline
    run_dir = create_timestamped_dir(settings.savedir, 
                                        settings.savedir_name)
    
    # Save the settings to the config folder
    config_dir = run_dir.joinpath(CONFIG_FOLDER)
    config_dir.mkdir(exist_ok=True)
    settings_path = config_dir.joinpath("pipeline_settings.json")
    settings.to_json(settings_path)
    
    # Load environment variables for the pipeline
    logging_sets = settings.logging_settings
    base_url = settings.base_url
    load_pipeline_env(run_dir, base_url=base_url, **logging_sets.model_dump())
    
    # Set up logging
    configure_logging(run_dir)
    logger = get_logger("main")
    
    # Log the run directory and run ID
    run_id = get_run_id(config_dir)
    logger.info("=" * 80)
    logger.info(f"Created run directory: {run_dir} with run ID: {run_id}")
    return a1_manager, run_dir, logger, run_id

def initialize_rescue_pipeline(settings: PipelineSettings, run_dir: Path, run_id: str) -> tuple[A1Manager, logging.Logger]:
    """
    Initialise the pipeline for rescue scenarios by setting up the A1Manager and configuring logging
    using existing run directory and run ID from a previous failed run.
    
    This function handles cases where the server failed but Python runtime is still active (logger may
    still be running) or complete restarts. The logging configuration is safely reconfigured to ensure
    proper setup regardless of the failure scenario.
    
    Args:
        settings (PipelineSettings): The settings for the pipeline, loaded from the previous run.
        run_dir (Path): The existing run directory from the previous run.
        run_id (str): The existing run ID from the previous run.
        
    Returns:
        tuple: A tuple containing the A1Manager instance and logger instance.
    """
    # Create A1Manager from loaded settings
    acqui = settings.acquisition_settings
    a1_manager = A1Manager(**acqui.model_dump())
    
    # Move the stage to a predefined safe position before starting autofocus
    _set_predefined_position(a1_manager, settings)

    # Set up the optical config
    _set_oc(settings, a1_manager)
    
    # Load environment variables for the pipeline using existing run_dir
    logging_sets = settings.logging_settings
    base_url = settings.base_url
    load_pipeline_env(run_dir, base_url=base_url, **logging_sets.model_dump())
    
    # Set up logging using existing run_dir (safe to call multiple times)
    configure_logging(run_dir)
    logger = get_logger("main")
    
    # Log the rescue initialization
    logger.info("=" * 80)
    logger.info(f"RESCUE MODE: Resuming pipeline with existing run directory: {run_dir}")
    logger.info(f"RESCUE MODE: Using existing run ID: {run_id}")
    logger.info("=" * 80)
    
    return a1_manager, logger

def _set_oc(settings: PipelineSettings, a1_manager: A1Manager) -> None:
    """
    Set the optical configuration based on the provided settings.
    """
    measure_sets: MeasureSettings = settings.measure_settings
    if measure_sets.do_refseg:
        a1_manager.oc_settings(**measure_sets.preset_refseg.model_dump())
    else:
        a1_manager.oc_settings(**measure_sets.preset_measure.model_dump())

def _set_predefined_position(a1_manager: A1Manager, settings: PipelineSettings) -> None:
    """
    Move the stage to a predefined safe position based on the dish type. 
    """
    af_method = settings.dish_settings.af_method
    if af_method == 'Manual':
        return
    dish_name = settings.dish_settings.dish_name
    zdrive = 'ZDrive'
    pfs = 'PFSOffset'
    posZ = PRE_STAGE_POS.get(dish_name, {}).get(zdrive, None)
    if posZ is not None:
        a1_manager.core.set_position(zdrive, posZ) # type: ignore
    posPFS = PRE_STAGE_POS.get(dish_name, {}).get(pfs, None)
    if posPFS is not None:
        a1_manager.core.set_position(pfs, posPFS) # type: ignore