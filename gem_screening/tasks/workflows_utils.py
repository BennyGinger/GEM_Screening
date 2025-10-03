import logging
from pathlib import Path

import pandas as pd
from a1_manager import A1Manager, StageCoord

from gem_screening.tasks.data_intensity import extract_measure_intensities, update_control_intensities
from gem_screening.tasks.image_capture import image_fovs
from gem_screening.tasks.light_stimulation import create_stim_masks, illuminate_fovs
from gem_screening.tasks.mask_utils import assign_masks_to_fovs
from gem_screening.utils.client.progress import wait_for_completion
from gem_screening.utils.external import run_celltinder
from gem_screening.utils.pipeline_constants import MEASURE_LABEL
from gem_screening.settings.models import PipelineSettings
from gem_screening.well_data.well_classes import Well, Plate


logger = logging.getLogger(__name__)

def scan_round1(a1_manager: A1Manager, settings: PipelineSettings, run_dir: Path, run_id: str, dish_grid: dict[str, dict[int, StageCoord]], fov_ids: list[str] | None = None) -> Plate:
    """
    Scan the well object for round 1 imaging.
    
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline.
        well_obj (Well): The well object to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """
    plate = Plate()
    # Create a well object
    for well, well_grid in dish_grid.items():
            
        logger.info(f"Processing well: {well}")

        # Create a well object and add to plate
        well_obj = Well(run_dir=run_dir,
                        run_id=run_id,
                        well_grid=well_grid,
                        well=well)
        plate.well_list.append(well_obj)

        # Run flow
        image_fovs(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_1", fov_ids)
    return plate

def scan_round2(a1_manager: A1Manager, settings: PipelineSettings, plate_obj: Plate, fov_ids: list[str] | None = None) -> None:
    """
    Scan the well object for round 2 imaging.
    
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline.
        well_obj (Well): The well object to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """
    
    for well_obj in plate_obj.well_list:
        # Run flow
        image_fovs(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_2", fov_ids)

    # Wait for all images to be processed
    well_ids = [w.well_id for w in plate_obj.well_list]
    wait_for_completion(well_ids, timeout=settings.server_settings.server_timeout_sec)
        
def after_scan(a1_manager: A1Manager, settings: PipelineSettings, plate_obj: Plate) -> None:
    """ 
    Run the analysis and illumination workflow after scanning is complete.
    This function handles cell selection and illumination for wells where both 
    round 1 and round 2 imaging have been completed.
    
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
        plate_obj (Plate): The plate object containing the wells to process.
    """
    _cell_selection(settings, plate_obj)

    _illuminate(a1_manager, settings, plate_obj)
    
    logger.info(f"Completed processing for well: {plate_obj.wells}")

################## Helper Functions ##################
def _cell_selection(settings: PipelineSettings, plate_obj: Plate) -> None:
    """
    Select cells in the well object for further processing, using CellTinder.
    """
    assign_masks_to_fovs(plate_obj)
                        
    stim_sets = settings.stim_settings
                        
    extract_measure_intensities(plate_obj.positive_fovs,
                                true_cell_threshold=stim_sets.true_cell_threshold,
                                csv_path=plate_obj.csv_path)

    if _is_csv_ready_for_processing(plate_obj):
        run_celltinder(plate_obj.csv_path, crop_size=stim_sets.crop_size)

def _illuminate(a1_manager: A1Manager, settings: PipelineSettings, plate_obj: Plate) -> None:
    """
    Illuminate the cells in the well object.
    """
    stim_sets = settings.stim_settings
    
    create_stim_masks(plate_obj, erosion_factor=stim_sets.erosion_factor)
                        
    illuminate_fovs(plate_obj, a1_manager, settings)

    update_control_intensities(plate_obj.positive_fovs, csv_path=plate_obj.csv_path)

def _is_csv_ready_for_processing(plate_obj: Plate) -> bool:
    """ 
    Check if the CSV file contains any cells marked for processing.
    If the CSV file does not exist or cannot be read, return True to indicate that CellTinder should be run.
    Args:
        plate_obj (Plate): List of Well object to check.
    Returns:
        bool: True if CellTinder should be run, False otherwise.
    """
    try:
        df = pd.read_csv(plate_obj.csv_path)
        if 'process' in df.columns and df['process'].any():
            logger.info(f"CSV exists with {df['process'].sum()} cells to process - skipping CellTinder")
            return False  # CSV has already selected cells, skip CellTinder
        else:
            logger.info("CSV exists but no processed cells found - will run CellTinder")
            return True  # CSV exists but no processed cells
    except Exception as e:
        logger.warning(f"Error reading CSV {plate_obj.csv_path}: {e}. Will run CellTinder")
        return True  # Error reading CSV, safer to run CellTinder