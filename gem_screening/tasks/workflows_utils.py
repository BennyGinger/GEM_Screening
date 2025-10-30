import logging

import pandas as pd
from a1_manager import A1Manager
from progress_bar import setup_progress_monitor as progress_bar

from gem_screening.tasks.data_intensity import extract_measure_intensities, update_control_intensities
from gem_screening.tasks.image_capture import image_fovs
from gem_screening.tasks.light_stimulation import create_stim_masks, illuminate_fovs
from gem_screening.tasks.mask_utils import assign_masks_to_fovs
from gem_screening.utils.client.progress import wait_for_completion
from gem_screening.utils.external import run_celltinder
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
    
    assign_masks_to_fovs(well_list)

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

