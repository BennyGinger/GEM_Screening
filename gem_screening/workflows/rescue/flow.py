from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from a1_manager import A1Manager
from cp_server import ComposeManager

from gem_screening.client.cleanup import cleanup_stale
from gem_screening.client.mask_registration import register_masks_batch_client
from gem_screening.client.progress import wait_for_completion
from gem_screening.experiment import Plate
from gem_screening.infrastructure.constants import MEASURE_LABEL
from gem_screening.runtime.external import run_celltinder
from gem_screening.runtime.prompt_gui import PipelineQuit
from gem_screening.runtime.prompts import get_ligand_prompt, prompt_to_continue
from gem_screening.settings.models import PipelineSettings
from gem_screening.tasks.data_intensity import extract_measure_intensities
from gem_screening.tasks.image_capture import image_fovs
from gem_screening.workflows.rescue.assessment import assess_rescue
from gem_screening.workflows.steps import get_identifier, illuminate, scan_round2

if TYPE_CHECKING:
    from gem_screening.runtime.interaction import PipelineInteraction

logger = logging.getLogger(__name__)


def run_rescue_flow(
    a1_manager: A1Manager,
    settings: PipelineSettings,
    plate_obj: Plate,
    interaction: PipelineInteraction | None = None,
) -> None:
    """
    Run the rescue pipeline workflow for the given list of well objects.
    """
    if interaction is not None:
        interaction.check_cancelled()
    rescue_plan = assess_rescue(plate_obj)
    logger.info("Rescue plan: %s", rescue_plan["case"])
    logger.debug(f"Rescue plan for wells {plate_obj.wells}: {rescue_plan}")

    # Analysis-only recovery does not use the segmentation/tracking server. This
    # is the usual path when both imaging rounds completed but the pipeline was
    # closed before the CSV (or CellTinder) was started.
    if rescue_plan["case"] == "celltinder":
        _run_analysis(a1_manager, settings, plate_obj, interaction=interaction)
        return

    if interaction is not None:
        interaction.check_cancelled()
    with ComposeManager(dev_mode=settings.dev_mode):
        # Clean up the redis server
        cleanup_stale()
        if interaction is not None:
            interaction.check_cancelled()

        match rescue_plan["case"]:
            case "round1":
                # Register masks (R1 only in this case)
                if rescue_plan["masks_to_register"]:
                    if interaction is not None:
                        interaction.check_cancelled()
                    register_masks_batch_client(run_id=plate_obj.run_id,
                                                mask_paths=rescue_plan["masks_to_register"],
                                                total_fovs=rescue_plan["total_fovs"])
                # Start from round 1 imaging
                _from_scan(
                    True, a1_manager, settings, plate_obj,
                    rescue_plan["fovs_to_process"], interaction=interaction,
                )
            case "round2":
                # Register all masks (R1 + R2, server will sort them)
                if rescue_plan["masks_to_register"]:
                    if interaction is not None:
                        interaction.check_cancelled()
                    register_masks_batch_client(run_id=plate_obj.run_id,
                                                mask_paths=rescue_plan["masks_to_register"],
                                                total_fovs=rescue_plan["total_fovs"],
                                                track_stitch_threshold=settings.server_settings.track_stitch_threshold)

                # If all images already exist, only wait for re-registered masks
                # to finish tracking; do not prompt for ligand or reacquire data.
                if not rescue_plan["fovs_to_process"]:
                    wait_kwargs = {"timeout": settings.server_settings.server_timeout_sec}
                    if interaction is not None:
                        wait_kwargs["cancel_check"] = interaction.check_cancelled
                    wait_for_completion(
                        [well.well_id for well in plate_obj.well_list],
                        **wait_kwargs)
                    _run_analysis(a1_manager, settings, plate_obj, interaction=interaction)
                    return

                # Start from round 2 imaging
                _from_scan(
                    False, a1_manager, settings, plate_obj,
                    rescue_plan["fovs_to_process"], interaction=interaction,
                )


def _run_analysis(
    a1_manager: A1Manager,
    settings: PipelineSettings,
    plate_obj: Plate,
    interaction: PipelineInteraction | None = None,
) -> None:
    """Create/complete the analysis CSV, run CellTinder, then optionally illuminate."""
    if interaction is not None:
        interaction.check_cancelled()
    logger.info("Rescue analysis: extracting cell measurements")
    extract_measure_intensities(
        plate_obj.positive_fovs,
        true_cell_threshold=settings.stim_settings.true_cell_threshold,
        csv_path=plate_obj.csv_path)
    if interaction is not None:
        interaction.check_cancelled()
    logger.info("Rescue analysis: opening CellTinder")
    if interaction is None:
        run_celltinder(plate_obj.csv_path, crop_size=settings.stim_settings.crop_size)
    else:
        interaction.select_cells(
            plate_obj.csv_path, crop_size=settings.stim_settings.crop_size
        )
        interaction.check_cancelled()
    illuminate(a1_manager, settings, plate_obj, interaction=interaction)


################# Helper functions for workflows #################
def _from_scan(
    do_round1: bool,
    a1_manager: A1Manager,
    settings: PipelineSettings,
    plate_obj: Plate,
    fov_ids: list[str] | None = None,
    interaction: PipelineInteraction | None = None,
) -> None:
    """ 
    Run the pipeline workflow starting from round 1 imaging for a specific well object.
    This function is used to start the workflow from round 1 imaging, allowing for imaging continuation of specific fields of view (FOVs) if needed.
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
        well_obj (Well): The well object to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """
    # Get the ligand addition prompt message
    list_type = settings.dish_settings.well_grouping
    prompt_message = get_ligand_prompt(list_type)
    
    # Run flow from round 1
    for well_sublist in plate_obj.well_sublists(grouping_method=list_type):
        if interaction is not None:
            interaction.check_cancelled()
        if do_round1:
            for well_obj in well_sublist:
                image_fovs(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_1", fov_ids, cancel_check=interaction.check_cancelled if interaction else None)
            fov_ids = None  # After round 1, image all FOVs in round 2
            plate_obj.to_json()
        try:
            
            identifier = get_identifier(well_sublist, list_type)
            prompt = prompt_message + identifier if identifier else prompt_message
            prompt_to_continue(prompt, interaction)
        except PipelineQuit:
            logger.info("User chose to quit the pipeline during imaging/stimulation.")
            raise
        scan_round2(a1_manager, settings, well_sublist, fov_ids, interaction=interaction)
        plate_obj.to_json()
        if interaction is not None:
            interaction.check_cancelled()
        
        extract_measure_intensities(plate_obj.positive_fovs,
                                true_cell_threshold=settings.stim_settings.true_cell_threshold,
                                csv_path=plate_obj.csv_path)

    if interaction is None:
        run_celltinder(plate_obj.csv_path, crop_size=settings.stim_settings.crop_size)
    else:
        interaction.select_cells(
            plate_obj.csv_path, crop_size=settings.stim_settings.crop_size
        )
        interaction.check_cancelled()
    
    illuminate(a1_manager, settings, plate_obj, interaction=interaction)
    
    logger.info(f"Completed processing for well: {plate_obj.wells}")
