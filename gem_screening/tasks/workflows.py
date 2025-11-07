import logging
from pathlib import Path

from a1_manager import A1Manager, StageCoord
from cp_server import ComposeManager

from gem_screening.tasks.data_intensity import extract_measure_intensities
from gem_screening.tasks.image_capture import image_fovs
from gem_screening.tasks.tune_seg_gui import launch_tune_seg_gui
from gem_screening.tasks.workflows_utils import scan_round1, scan_round2, illuminate
from gem_screening.utils.client.cleanup import cleanup_stale
from gem_screening.utils.client.mask_registration import register_masks_batch_client
from gem_screening.utils.external import run_celltinder
from gem_screening.utils.pipeline_constants import MEASURE_LABEL
from gem_screening.utils.prompts import get_ligand_prompt, prompt_to_continue
from gem_screening.tasks.rescue_assessment import assess_rescue
from gem_screening.utils.prompt_gui import PipelineQuit
from gem_screening.settings.models import PipelineSettings
from gem_screening.well_data.well_classes import Plate, Well


logger = logging.getLogger(__name__)

def run_complete_flow(dish_grid: dict[str, dict[int, StageCoord]], a1_manager: A1Manager, run_dir: Path, run_id: str, settings: PipelineSettings,) -> None:
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
    dev_mode = settings.dev_mode
    with ComposeManager(dev_mode=dev_mode):
        # Clean up the redis server
        cleanup_stale()  
        
        # Optimize Segmentation settings
        server_settings = launch_tune_seg_gui(settings)
        
        # Initialize plate object
        plate = Plate(run_dir=run_dir, run_id=run_id, dish_grid=dish_grid)

        # Prompt message mapping
        list_type = settings.dish_settings.well_grouping
        prompt_message = get_ligand_prompt(list_type)

        for well_sublist in plate.well_sublists(list_type=list_type):
            # Start imaging
            scan_round1(a1_manager, settings, well_sublist)
            plate.to_json()

            try:
                identifier = _get_identifier(well_sublist, list_type)
                prompt = prompt_message + identifier if identifier else prompt_message
                prompt_to_continue(prompt)
            except PipelineQuit:
                logger.info("User chose to quit the pipeline during imaging/stimulation.")
                raise

            scan_round2(a1_manager, settings, well_sublist)
            plate.to_json()
            
            extract_measure_intensities(plate.positive_fovs,
                                true_cell_threshold=settings.stim_settings.true_cell_threshold,
                                csv_path=plate.csv_path)

        run_celltinder(plate.csv_path, crop_size=settings.stim_settings.crop_size)
        
        illuminate(a1_manager, settings, plate)
        logger.info("Completed processing for all wells.")

def run_rescue_flow(a1_manager: A1Manager, settings: PipelineSettings, plate_obj: Plate,) -> None:
    """
    Run the rescue pipeline workflow for the given list of well objects.
    """
    with ComposeManager():
        # Clean up the redis server
        cleanup_stale()
        
        # Determine the rescue plan for the well
        rescue_plan = assess_rescue(plate_obj)
        logger.debug(f"Rescue plan for well {plate_obj.wells}: {rescue_plan}")
        
        match rescue_plan["case"]:
            case "round1":
                # Register masks (R1 only in this case)
                register_masks_batch_client(run_id=plate_obj.run_id,
                                            mask_paths=rescue_plan["masks_to_register"],
                                            total_fovs=rescue_plan["total_fovs"])
                # Start from round 1 imaging
                _from_scan(True, a1_manager, settings, plate_obj, rescue_plan["fovs_to_process"])
            case "round2":
                # Register all masks (R1 + R2, server will sort them)
                register_masks_batch_client(run_id=plate_obj.run_id,
                                            mask_paths=rescue_plan["masks_to_register"],
                                            total_fovs=rescue_plan["total_fovs"],
                                            track_stitch_threshold=settings.server_settings.track_stitch_threshold)
                # Start from round 2 imaging
                _from_scan(False, a1_manager, settings, plate_obj, rescue_plan["fovs_to_process"])
            case "celltinder":
                extract_measure_intensities(plate_obj.positive_fovs,
                                true_cell_threshold=settings.stim_settings.true_cell_threshold,
                                csv_path=plate_obj.csv_path)
                
                run_celltinder(plate_obj.csv_path, crop_size=settings.stim_settings.crop_size)

                illuminate(a1_manager, settings, plate_obj)

def _from_scan(do_round1: bool, a1_manager: A1Manager, settings: PipelineSettings, plate_obj: Plate, fov_ids: list[str] | None = None) -> None:
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
    for well_sublist in plate_obj.well_sublists(list_type=list_type):
        if do_round1:
            for well_obj in well_sublist:
                image_fovs(well_obj, a1_manager, settings, f"{MEASURE_LABEL}_1", fov_ids)
            fov_ids = None  # After round 1, image all FOVs in round 2
            plate_obj.to_json()
        try:
            
            identifier = _get_identifier(well_sublist, list_type)
            prompt = prompt_message + identifier if identifier else prompt_message
            prompt_to_continue(prompt)
        except PipelineQuit:
            logger.info("User chose to quit the pipeline during imaging/stimulation.")
            raise
        scan_round2(a1_manager, settings, well_sublist, fov_ids)
        plate_obj.to_json()
        
        extract_measure_intensities(plate_obj.positive_fovs,
                                true_cell_threshold=settings.stim_settings.true_cell_threshold,
                                csv_path=plate_obj.csv_path)

    run_celltinder(plate_obj.csv_path, crop_size=settings.stim_settings.crop_size)
    
    illuminate(a1_manager, settings, plate_obj)
    
    logger.info(f"Completed processing for well: {plate_obj.wells}")

def _get_identifier(well_sublist: list[Well], list_type: str) -> str:
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

        

        