import logging
from pathlib import Path

from a1_manager import A1Manager, StageCoord
from cp_server import ComposeManager

from gem_screening.tasks.workflows_utils import scan_round1, scan_round2, cell_selection, illuminate
from gem_screening.utils.client.client import cleanup_stale, register_masks_batch_client
from gem_screening.tasks.rescue_assessment import assess_rescue
from gem_screening.utils.prompt_gui import PipelineQuit
from gem_screening.utils.settings.models import PipelineSettings
from gem_screening.well_data.well_classes import Well


logger = logging.getLogger(__name__)

def run_complete_flow(dish_grid: dict[str, dict[int, StageCoord]],
                  a1_manager: A1Manager,
                  run_dir: Path,
                  run_id: str,
                  settings: PipelineSettings,
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
    with ComposeManager():
        # Clean up the redis server
        cleanup_stale()  
        
        # Start imaging
        for well, well_grid in dish_grid.items():
            
            logger.info(f"Processing well: {well}")
            
            # Create a well object
            well_obj = Well(run_dir=run_dir,
                            run_id=run_id,
                            well_grid=well_grid,
                            well=well)
            
            # Run flow
            scan_round1(a1_manager, settings, well_obj)
            
            try:
                scan_round2(a1_manager, settings, well_obj)
            except PipelineQuit:
                logger.info("User chose to quit the pipeline during imaging/stimulation.")
                raise
            
            _after_scan(a1_manager, settings, well_obj)
            
            logger.info(f"Completed processing for well: {well}")

def run_rescue_flow(a1_manager: A1Manager,
                    settings: PipelineSettings,
                    well_objs: list[Well],
                    ) -> None:
    """
    Run the rescue pipeline workflow for the given list of well objects.
    """
    with ComposeManager():
        # Clean up the redis server
        cleanup_stale()
        
        # Loop through each well object and process the images
        for well_obj in well_objs:
            # Determine the rescue plan for the well
            rescue_plan = assess_rescue(well_obj)
            logger.debug(f"Rescue plan for well {well_obj.well_id}: {rescue_plan}")
            
            match rescue_plan["case"]:
                case "round1":
                    # Register masks (R1 only in this case)
                    register_masks_batch_client(well_obj.well_id,
                                                rescue_plan["masks_to_register"],
                                                rescue_plan["total_fovs"])
                    # Start from round 1 imaging
                    _from_scan(True, a1_manager, settings, well_obj, rescue_plan["fovs_to_process"])
                case "round2":
                    # Register all masks (R1 + R2, server will sort them)
                    register_masks_batch_client(well_obj.well_id,
                                                rescue_plan["masks_to_register"],
                                                rescue_plan["total_fovs"],
                                                settings.server_settings.track_stitch_threshold)
                    # Start from round 2 imaging
                    _from_scan(False, a1_manager, settings, well_obj, rescue_plan["fovs_to_process"])
                case "celltinder":
                    _after_scan(a1_manager, settings, well_obj)
            

def _from_scan(do_round1: bool, a1_manager: A1Manager, settings: PipelineSettings, well_obj: Well, fov_ids: list[str] | None = None) -> None:
    """ 
    Run the pipeline workflow starting from round 1 imaging for a specific well object.
    This function is used to start the workflow from round 1 imaging, allowing for imaging continuation of specific fields of view (FOVs) if needed.
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
        well_obj (Well): The well object to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """
    # Run flow from round 1
    if do_round1:
        scan_round1(a1_manager, settings, well_obj, fov_ids)
        fov_ids = None  # After round 1, image all FOVs in round 2
    try:
        scan_round2(a1_manager, settings, well_obj, fov_ids)
    except PipelineQuit:
        logger.info("User chose to quit the pipeline during imaging/stimulation.")
        raise
    _after_scan(a1_manager, settings, well_obj)
    
    logger.info(f"Completed processing for well: {well_obj.well_id}")
        
def _after_scan(a1_manager: A1Manager, settings: PipelineSettings, well_obj: Well) -> None:
    """ 
    Run the analysis and illumination workflow after scanning is complete.
    This function handles cell selection and illumination for wells where both 
    round 1 and round 2 imaging have been completed.
    
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
        well_obj (Well): The well object to process.
    """
    cell_selection(settings, well_obj)

    illuminate(a1_manager, settings, well_obj)
    
    logger.info(f"Completed processing for well: {well_obj.well_id}")

        

        