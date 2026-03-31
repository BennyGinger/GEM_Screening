import logging

from a1_manager.utils.utility_classes import StageCoord
from a1_manager import A1Manager
from progress_bar import setup_progress_monitor as progress_bar

from gem_screening.tasks.injection import init_injection
from gem_screening.tasks.workflows import _get_identifier
from gem_screening.utils.prompt_gui import PipelineQuit
from gem_screening.utils.prompts import get_ligand_prompt, prompt_to_continue
from gem_screening.tasks.data_intensity import update_control_intensities
from gem_screening.tasks.image_capture import image_fovs
from gem_screening.tasks.light_stimulation import create_stim_masks, illuminate_fovs
from gem_screening.utils.client.progress import wait_for_completion
from gem_screening.utils.pipeline_constants import MEASURE_LABEL
from gem_screening.settings.models import PipelineSettings
from gem_screening.well_data.well_classes import Plate, Well



logger = logging.getLogger(__name__)

def scan_round1(a1_manager: A1Manager, settings: PipelineSettings, well_list: list[Well], fov_ids: list[str] | None = None) -> None:
    """
    Scan all the wells in the dish grid for round 1 imaging.
    
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline.
        well_list (list[Well]): List of well objects to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """
    for well_obj in progress_bar(well_list, desc="Scanning wells round 1", total=len(well_list)):
        # Run flow
        image_fovs(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_1", fov_ids)
    

def scan_round2(a1_manager: A1Manager, settings: PipelineSettings, well_list: list[Well], fov_ids: list[str] | None = None) -> None:
    """
    Scan the wells for round 2 imaging.
    
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline.
        well_list (list[Well]): List of well objects to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """

    for well_obj in progress_bar(well_list, desc="Scanning wells round 2", total=len(well_list)):
        # Run flow
        image_fovs(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_2", fov_ids)
    

    # Wait for all images to be processed
    well_ids = [w.well_id for w in well_list]
    wait_for_completion(well_ids, timeout=settings.server_settings.server_timeout_sec)
    

def illuminate(a1_manager: A1Manager, settings: PipelineSettings, plate_obj: Plate) -> None:
    """
    Illuminate the cells in the well object.
    """
    stim_sets = settings.stim_settings
    
    if not stim_sets.do_illuminate:
        logger.info("Illumination step is disabled in settings. Skipping illumination.")
        return
    
    create_stim_masks(plate_obj, erosion_factor=stim_sets.erosion_factor)
                        
    illuminate_fovs(plate_obj, a1_manager, settings)

    update_control_intensities(plate_obj.positive_fovs, csv_path=plate_obj.csv_path)


def ligand_stimulation(a1_manager: A1Manager, settings: PipelineSettings, well_list: list[Well], list_type: str) -> None:
    """
    Run the ligand stimulation part of the workflow, which includes either prompting the user to perform manual ligand addition or performing automated injection based on the settings.
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and injection settings.
        well_list (list[Well]): List of well objects to process for ligand stimulation.
        list_type (str): The type of grouping for the wells, either 'row' or 'col', used for generating the appropriate prompt message for manual ligand addition.
        dish_map (dict[str, WellCircleCoord | WellSquareCoord]): A mapping of well names to their corresponding coordinates, used for automated injection to move the stage to the correct position for ligand addition.
    
    Raises:
        PipelineQuit: If the user chooses to quit during the manual ligand addition prompt.
    """
    
    center_points: list[StageCoord] = []
    for well in well_list:
        center = well.well_grid[max(well.well_grid)]
        center_points.append(center)
    
    if not center_points:
        logger.warning("No valid center points found in dish map for ligand stimulation.")
        return
    
    if settings.injection_settings.enabled:
        logger.info("Automated injection is enabled. Starting automated ligand stimulation.")
        device_name = settings.injection_settings.injection_device
        needle_size = settings.injection_settings.needle_size
        pressure = settings.injection_settings.pressure
        injec_vol_ul = settings.injection_settings.inject_vol_ul
        inject_time_ms = settings.injection_settings.inject_time_ms
        mixing_cycles = settings.injection_settings.mixing_cycles
        pick = init_injection(a1_manager.core, settings.dish_name, device_name, needle_size, pressure) # type: ignore
        
        for coord in center_points:
            # move the stage
            a1_manager.set_stage_position(coord)
            
            # perform the injection
            pick.inject(injec_vol_ul, inject_time_ms, mixing_cycles)
        
    else:
        logger.info("Automated injection is disabled in settings. Please perform the ligand addition manually.") 
        try:
            prompt_message = get_ligand_prompt(list_type)
            identifier = _get_identifier(well_list, list_type)
            prompt = prompt_message + identifier if identifier else prompt_message
            prompt_to_continue(prompt)
        except PipelineQuit:
            raise
    