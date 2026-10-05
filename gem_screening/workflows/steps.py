from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from a1_manager import A1Manager
from progress_bar import setup_progress_monitor as progress_bar

from gem_screening.runtime.prompt_gui import PipelineQuit
from gem_screening.runtime.prompts import get_ligand_prompt, prompt_to_continue
from gem_screening.tasks.injection import Injection
from gem_screening.tasks.data_intensity import update_control_intensities
from gem_screening.tasks.image_capture import image_fovs
from gem_screening.tasks.light_stimulation import create_stim_masks, illuminate_fovs
from gem_screening.client.progress import wait_for_completion
from gem_screening.infrastructure.constants import MEASURE_LABEL
from gem_screening.settings.models import InjectionSettings, PipelineSettings
from gem_screening.experiment import Plate, Well

if TYPE_CHECKING:
    from gem_screening.runtime.interaction import PipelineInteraction


logger = logging.getLogger(__name__)

def scan_round1(a1_manager: A1Manager, settings: PipelineSettings, well_list: list[Well], fov_ids: list[str] | None = None, *, interaction: PipelineInteraction | None = None) -> None:
    """
    Scan all the wells in the dish grid for round 1 imaging.
    
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline.
        well_list (list[Well]): List of well objects to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """
    for index, well_obj in enumerate(progress_bar(well_list, desc="Scanning wells round 1", total=len(well_list)), 1):
        if interaction is not None:
            interaction.check_cancelled()
        logger.info("Round 1 imaging: well %s (%s/%s)", well_obj.well, index, len(well_list))
        # Run flow
        image_fovs(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_1", fov_ids, cancel_check=interaction.check_cancelled if interaction else None)
    

def scan_round2(a1_manager: A1Manager, settings: PipelineSettings, well_list: list[Well], fov_ids: list[str] | None = None, *, interaction: PipelineInteraction | None = None) -> None:
    """
    Scan the wells for round 2 imaging.
    
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline.
        well_list (list[Well]): List of well objects to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """

    for index, well_obj in enumerate(progress_bar(well_list, desc="Scanning wells round 2", total=len(well_list)), 1):
        if interaction is not None:
            interaction.check_cancelled()
        logger.info("Round 2 imaging: well %s (%s/%s)", well_obj.well, index, len(well_list))
        # Run flow
        image_fovs(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_2", fov_ids, cancel_check=interaction.check_cancelled if interaction else None)
    

    # Wait for all images to be processed
    well_ids = [w.well_id for w in well_list]
    logger.debug(f"Polling for completion of image processing for wells: {', '.join(well_ids)}")
    wait_for_completion(well_ids, timeout=settings.server_settings.server_timeout_sec, cancel_check=interaction.check_cancelled if interaction else None)
    

def stimulate_dish(settings: PipelineSettings,
                    grouping_method: str,
                    inj_device: Injection | None,
                    well_sublist: list[Well],
                    injection_point: int,
                    interaction: PipelineInteraction | None = None,
                    ) -> None:
    """
    Perform ligand stimulation for a sublist of wells in the dish, either using an automated injection device or by prompting the user for manual addition based on the settings.
    Args:
        settings (PipelineSettings): The settings for the pipeline, including stimulation settings and dish settings.
        grouping_method (str): The type of grouping for the wells (e.g., 'row', 'col', 'well').
        inj_device (Injection | None): An instance of the Injection class if automated injection is enabled, or None if manual addition is required.
        well_sublist (list[Well]): A list of Well objects representing the sublist of wells to be stimulated.
        injection_point (int): The injection point index to use for the injection device (e.g., 0 for center, 1 for top, 2 for top left, 3 for top left bottom and 4 for top left bottom right).
    """
    if inj_device is not None:
        logger.info("Automated injection is enabled in settings. Performing ligand addition using injection device.") 
        inj_sets = settings.injection_settings
        _injection(well_sublist, inj_device, inj_sets, injection_point, cancel_check=interaction.check_cancelled if interaction else None)
    else:
        try:
            logger.info("Automated injection is disabled in settings. Please perform the ligand addition manually.") 
            prompt_message = get_ligand_prompt(grouping_method)
            identifier = get_identifier(well_sublist, grouping_method)
            prompt = prompt_message + identifier if identifier else prompt_message
            prompt_to_continue(prompt, interaction)
        except PipelineQuit:
            logger.info("User chose to quit the pipeline during ligand stimulation.")
            raise


def illuminate(a1_manager: A1Manager, settings: PipelineSettings, plate_obj: Plate, *, interaction: PipelineInteraction | None = None) -> None:
    """
    Illuminate the cells in the well object.
    """
    stim_sets = settings.stim_settings
    
    if not stim_sets.do_illuminate:
        logger.info("Illumination step is disabled in settings. Skipping illumination.")
        return
    if interaction is not None:
        interaction.check_cancelled()
    
    create_stim_masks(plate_obj, erosion_factor=stim_sets.erosion_factor)
    if interaction is not None:
        interaction.check_cancelled()
                        
    illuminate_fovs(plate_obj, a1_manager, settings, cancel_check=interaction.check_cancelled if interaction else None)

    if interaction is not None:
        interaction.check_cancelled()

    update_control_intensities(plate_obj.positive_fovs, csv_path=plate_obj.csv_path)


def get_identifier(well_sublist: list[Well], list_type: str) -> str:
    """
    Get the identifier (row or column) for the well sublist based on the grouping type.
    """
    if list_type == 'col':
        return well_sublist[0].well[1]  # e.g., '1' for column 1
    elif list_type == 'row':
        return well_sublist[0].well[0]  # e.g., 'A' for row A
    elif list_type == 'well':
        return well_sublist[0].well  # e.g., 'A1' for well A1
    return ''


def _injection(well_sublist: list[Well], inj_device: Injection, inj_sets: InjectionSettings, injection_point: int, *, cancel_check: Callable[[], None] | None = None) -> None:
    """
    Perform the injection for a list of wells using the specified injection device and settings.
    Args:
        - well_sublist (list[Well]): List of Well objects to perform injection on.
        - inj_device (Injection): An instance of the Injection class to control the injection process.
        - inj_sets (InjectionSettings): Settings for the injection, including injection volume, time, and mixing cycles.
    """
    if injection_point == 0:
        position = ["center"]
    elif injection_point == 1:
        position = ["top"]
    elif injection_point == 2:
        position = ["top", "left"]
    elif injection_point == 3:
        position = ["top", "left", "bottom"]
    elif injection_point == 4:
        position = ["top", "left", "bottom", "right"]
    else:
        raise ValueError(f"Invalid injection point index: {injection_point}. Must be between 0 and 4.")
    
    for well in progress_bar(well_sublist, desc="Performing injection", total=len(well_sublist)):
        if cancel_check is not None:
            cancel_check()
        for pos in position:
            inj_device.move_to_position(well, position=pos)
            #print(f"Injecting {inj_sets.inject_vol_ul/len(position)} uL into well {well.well} at position {pos}")
            inj_device.inject(inject_vol_ul=inj_sets.inject_vol_ul/len(position), mixing_cycles=inj_sets.mixing_cycles)
        inj_device.dip_needle()
