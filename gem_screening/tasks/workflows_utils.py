import logging
from pathlib import Path

from a1_manager import A1Manager, StageCoord
from cp_server.tasks_server.utils.redis_com import redis_client

from gem_screening.tasks.data_intensity import extract_measure_intensities, update_control_intensities
from gem_screening.tasks.image_capture import image_fovs
from gem_screening.utils.prompt_gui import PipelineQuit
from gem_screening.utils.prompts import prompt_to_continue, ADD_LIGAND_PROMPT
from gem_screening.tasks.light_stimulation import create_stim_masks, illuminate_fovs
from gem_screening.tasks.mask_utils import assign_masks_to_fovs
from gem_screening.utils.client.client import bg_removal_client, cleanup_stale, full_process_client, wait_for_completion
from gem_screening.utils.external import run_celltinder
from gem_screening.utils.filesystem import create_timestamped_dir
from gem_screening.utils.pipeline_constants import WELL_OBJ_FILENAME, MEASURE_LABEL, REFSEG_LABEL
from gem_screening.utils.settings.models import PipelineSettings
from gem_screening.well_data.well_classes import Well


logger = logging.getLogger(__name__)

def scan_round1(a1_manager: A1Manager, settings: PipelineSettings, well_obj: Well, fov_ids: list[str] | None = None) -> None:
    """
    Scan the well object for round 1 imaging.
    
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline.
        well_obj (Well): The well object to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """
    image_fovs(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_1", fov_ids)

def scan_round2(a1_manager: A1Manager, settings: PipelineSettings, well_obj: Well, fov_ids: list[str] | None = None) -> None:
    """
    Scan the well object for round 2 imaging.
    
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline.
        well_obj (Well): The well object to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """
    
    prompt_to_continue(ADD_LIGAND_PROMPT)
                
    image_fovs(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_2", fov_ids)
                
    wait_for_completion(well_obj.well_id, timeout=settings.server_settings.server_timeout_sec)

def select_cells(settings: PipelineSettings, well_obj: Well) -> None:
    """
    Select cells in the well object for further processing, using CellTinder.
    """
    assign_masks_to_fovs(well_obj)
                        
    stim_sets = settings.stim_settings
                        
    extract_measure_intensities(well_obj.positive_fovs,
                                true_cell_threshold=stim_sets.true_cell_threshold,
                                csv_path=well_obj.csv_path,)

    run_celltinder(well_obj.csv_path, crop_size=stim_sets.crop_size)

def illuminate(a1_manager: A1Manager, settings: PipelineSettings, well_obj: Well) -> None:
    """
    Illuminate the cells in the well object.
    """
    stim_sets = settings.stim_settings
    
    create_stim_masks(well_obj, erosion_factor=stim_sets.erosion_factor)
                        
    illuminate_fovs(well_obj, a1_manager, settings)

    update_control_intensities(well_obj.positive_fovs, csv_path=well_obj.csv_path)

