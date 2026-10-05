from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from a1_manager import launch_dish_workflow
from a1_manager import A1Manager, StageCoord
from a1_manager.autofocus.af_utils import QuitAutofocus

from gem_screening.runtime.prompt_gui import PipelineQuit
from gem_screening.runtime.prompts import FOCUS_PROMPT, prompt_to_continue
from gem_screening.infrastructure.constants import CONFIG_FOLDER
from gem_screening.settings.models import PipelineSettings
from gem_screening.workflows.initialization import initialize_pipeline

if TYPE_CHECKING:
    from gem_screening.runtime.interaction import PipelineInteraction

logger = logging.getLogger(__name__)

INJECTION_POINTS = {"96well": 2, "384well": 0}


def complete_pipeline(
    settings: PipelineSettings,
    *,
    run_dir: Path | None = None,
    interaction: PipelineInteraction | None = None,
) -> None:
    """Run a complete GEM Screening acquisition and analysis workflow."""
    if interaction is not None:
        interaction.check_cancelled()
    a1_manager, run_dir, logger, run_id = initialize_pipeline(settings, run_dir=run_dir)
    if interaction is not None:
        interaction.check_cancelled()

    if settings.dish_settings.dish_name.lower() not in ["35mm", "96well", "384well"]:
        try:
            prompt_to_continue(FOCUS_PROMPT, interaction)
        except PipelineQuit:
            logger.info("User chose to quit. Stopping pipeline.")
            if interaction is not None:
                raise
            return

    try:
        dish_kwargs = settings.dish_settings.model_dump(exclude={"well_grouping"})
        if interaction is not None:
            dish_kwargs["review_callback"] = interaction.run_autofocus_check
            dish_kwargs["cancel_check"] = interaction.check_cancelled
        dish_grid = launch_dish_workflow(
            a1_manager,
            run_dir,
            **dish_kwargs,
        )
        logger.info("Generated dish grid")
        logger.debug("dish_grid: %s", dish_grid)
    except QuitAutofocus as error:
        logger.info("User chose to quit during autofocus. Stopping pipeline.")
        if interaction is not None:
            raise PipelineQuit("User chose to quit during autofocus") from error
        return

    try:
        if interaction is not None:
            interaction.check_cancelled()
        run_complete_flow(
            dish_grid, a1_manager, run_dir, run_id, settings, interaction=interaction
        )
    except PipelineQuit:
        logger.info("User chose to quit during pipeline execution. Stopping pipeline.")
        if interaction is not None:
            raise
        return

    logger.info("Pipeline completed successfully.")


def run_complete_flow(
    dish_grid: dict[str, dict[int, StageCoord]],
    a1_manager: A1Manager,
    run_dir: Path,
    run_id: str,
    settings: PipelineSettings,
    interaction: PipelineInteraction | None = None,
) -> None:
    """
    Run the complete pipeline workflow from the beginning for the given dish grid.
    This is the fresh start entry point that performs the full workflow:
    - Round 1 imaging (baseline)
    - Ligand addition prompt  
    - Round 2 imaging (post-ligand)
    - Image processing and analysis
    - Cell selection and stimulation
    
    Args:
        dish_grid (dict[str, dict[str, StageCoord]]): The dish grid containing well coordinates.
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        run_dir (Path): The directory where the run data will be saved.
        run_id (str): The unique identifier for the run.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
    """
    # Keep server-related imports behind runtime environment initialization.
    from cp_server import ComposeManager

    from gem_screening.client.cleanup import cleanup_stale
    from gem_screening.experiment import Plate
    from gem_screening.runtime.external import run_celltinder
    from gem_screening.tasks.data_intensity import extract_measure_intensities
    from gem_screening.tasks.injection import setup_injection_device
    from gem_screening.tasks.mask_assignment import assign_masks_to_fovs
    from gem_screening.workflows.steps import scan_round1, scan_round2, stimulate_dish

    dev_mode = settings.dev_mode
    if interaction is not None:
        interaction.check_cancelled()
    with ComposeManager(dev_mode=dev_mode):
        # Clean up the redis server
        cleanup_stale()  
        if interaction is not None:
            interaction.check_cancelled()

        logger.info("Preparing segmentation settings")
        # Optimize Segmentation settings
        if interaction is None:
            from gem_screening.gui.segmentation_tuning import launch_tune_seg_gui

            server_settings = launch_tune_seg_gui(
                settings, dish_grid=dish_grid, a1_manager=a1_manager
            )
        else:
            server_settings = interaction.tune_segmentation(
                settings, dish_grid=dish_grid, a1_manager=a1_manager
            )
        if server_settings is not None:
            settings.server_settings = server_settings
            settings.to_json(run_dir / CONFIG_FOLDER / "pipeline_settings.json")
            logger.info(f"Updated server settings: {settings.server_settings}")
        if interaction is not None:
            interaction.check_cancelled()
        
        # Initialize plate object
        plate = Plate(run_dir=run_dir, run_id=run_id, dish_grid=dish_grid)

        # Prompt message mapping
        grouping_method = settings.dish_settings.well_grouping
        
        # Initialize injection device if enabled
        inj_device = setup_injection_device(a1_manager, settings)
        
        for well_sublist in plate.well_sublists(grouping_method=grouping_method):
            if interaction is not None:
                interaction.check_cancelled()
            logger.info("Processing well group: %s", ", ".join(w.well for w in well_sublist))
            # Start imaging
            scan_round1(a1_manager, settings, well_sublist, interaction=interaction)
            plate.to_json()
            if interaction is not None:
                interaction.check_cancelled()
            
            dish_name = settings.dish_settings.dish_name.lower()
            if dish_name == "96well":
                injection_point = INJECTION_POINTS['96well']
            elif dish_name == "384well":
                injection_point = INJECTION_POINTS['384well'] 
            else:
                injection_point = 0  # No injection for other dish types  
                
            stimulate_dish(
                settings, grouping_method, inj_device, well_sublist,
                injection_point=injection_point, interaction=interaction,
            )

            scan_round2(a1_manager, settings, well_sublist, interaction=interaction)
            plate.to_json()
            if interaction is not None:
                interaction.check_cancelled()
            
            assign_masks_to_fovs(well_sublist)

            sublist_fovs = [fov for well in well_sublist for fov in well.positive_fovs]
            logger.info("Extracting cell measurements for %s FOVs", len(sublist_fovs))
            extract_measure_intensities(sublist_fovs,
                                true_cell_threshold=settings.stim_settings.true_cell_threshold,
                                csv_path=plate.csv_path)
            if interaction is not None:
                interaction.check_cancelled()

        if interaction is not None:
            interaction.check_cancelled()
        logger.info("Opening CellTinder for cell selection")
        if interaction is None:
            run_celltinder(plate.csv_path, crop_size=settings.stim_settings.crop_size)
        else:
            interaction.select_cells(
                plate.csv_path, crop_size=settings.stim_settings.crop_size
            )
            interaction.check_cancelled()
        
        # illuminate(a1_manager, settings, plate)
        logger.info("Completed processing for all wells.")
