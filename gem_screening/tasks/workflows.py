import logging
from pathlib import Path

from a1_manager import A1Manager, StageCoord
from cp_server import ComposeManager

from gem_screening.tasks.workflows_utils import scan_round1, scan_round2, select_cells, illuminate
from gem_screening.utils.client.client import cleanup_stale
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
            try:
                scan_round1(a1_manager, settings, well_obj)
                
                scan_round2(a1_manager, settings, well_obj)
                
                select_cells(settings, well_obj)

                illuminate(a1_manager, settings, well_obj)
                
            except PipelineQuit:
                logger.info("User chose to quit the pipeline during imaging/stimulation.")
                raise
            
            logger.info(f"Completed processing for well: {well}")

def run_from_round1(a1_manager: A1Manager, settings: PipelineSettings, well_obj: Well, fov_ids: list[str] | None = None) -> None:
    """ 
    Run the pipeline workflow starting from round 1 imaging for a specific well object.
    This function is used to start the workflow from round 1 imaging, allowing for imaging continuation of specific fields of view (FOVs) if needed.
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
        well_obj (Well): The well object to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """
    with ComposeManager():
        # Clean up the redis server
        cleanup_stale()

        logger.info(f"Processing well: {well_obj.well_id}")
        
        # Run flow from round 1
        try:
            scan_round1(a1_manager, settings, well_obj, fov_ids)
            scan_round2(a1_manager, settings, well_obj)    
            select_cells(settings, well_obj)
            illuminate(a1_manager, settings, well_obj)
            
        except PipelineQuit:
            logger.info("User chose to quit the pipeline during imaging/stimulation.")
            raise
        
        logger.info(f"Completed processing for well: {well_obj.well_id}")
        
def run_from_round2(a1_manager: A1Manager, settings: PipelineSettings, well_obj: Well, fov_ids: list[str] | None = None) -> None:
    """ 
    Run the pipeline workflow starting from round 2 imaging for a specific well object. Meaning that round 1 was already completed.
    This function is used to start the workflow from round 2 imaging, allowing for imaging start or continuation of specific fields of view (FOVs) if needed.
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
        well_obj (Well): The well object to process.
        fov_ids (list[str] | None): Optional list of specific FOV IDs to image. If None, all positive FOVs will be imaged.
    """
    with ComposeManager():
        # Clean up the redis server
        cleanup_stale()

        


  
# def after_acquisition_rescue(a1_manager: A1Manager,
#                 settings: PipelineSettings,
#                 well_selection: str | list[str] | None = None,
#                 ) -> None:
#     """
#     After acquisition rescue function to resend images to the server for processing.
#     This function is used to recover from a failed acquisition or to reprocess specific wells. It collects all well objects from the saved directory, filters them based on the well selection, and resends the images to the server for processing.
#     Args:
#         a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
#         settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
#         well_selection (str | list[str] | None): Optional selection of wells to process. If None, all wells will be processed.
#     """
#     # Retrieve saved well objects from the run directory
#     well_objs = _retrieve_saved_wells(settings, well_selection)
        
#     # Resend the images to the server    
#     with ComposeManager():
#         # Clean up the redis server
#         cleanup_stale()
        
#         # Loop through each well object and process the images
#         for well_obj in well_objs:
#             fovs = well_obj.positive_fovs
#             # Get the images to be processed by flattening the lists of Paths
#             measure_paths = sorted([img for fov in fovs for img in fov.tiff_paths[MEASURE_LABEL]])
            
#             if settings.measure_settings.do_refseg:
#                 refseg_paths = sorted([img for fov in fovs for img in fov.tiff_paths[REFSEG_LABEL]])
                
#                 # Send measure images for background removal
#                 for img_path in measure_paths:
#                     bg_removal_client(settings.server_settings, img_path)
                
#                 # Send refseg images for full processing
#                 for img_path in refseg_paths:
#                     full_process_client(settings.server_settings, img_path)
#                 continue
            
#             # If no refseg is used, send measure images for full processing
#             for img_path in measure_paths:
#                 full_process_client(settings.server_settings, img_path)
                
#             # Wait for completion
#             wait_for_completion(well_obj.run_id, timeout=settings.server_settings.server_timeout_sec)
            
#             _execute_well_analysis(a1_manager, settings, well_obj)

# def _retrieve_saved_wells(settings: PipelineSettings, well_selection: str | list[str] | None = None) -> list[Well]:
#     """
#     Retrieve saved well objects from the run directory based on the provided settings and well selection.
#     Args:
#         settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
#         well_selection (str | list[str] | None): Optional selection of wells to process. If None, all wells will be processed.
#     Returns:
#         list[Well]: A list of Well objects that match the well selection criteria.
#     """
#     # Reconstruct run_dir
#     run_dir = create_timestamped_dir(settings.savedir, settings.savedir_name)
    
#     # Collect all well object paths
#     well_obj_paths = run_dir.rglob(f"*_{WELL_OBJ_FILENAME}")
#     if well_selection is not None:
#         if isinstance(well_selection, str):
#             well_selection = [well_selection]
#         well_obj_paths = [p for p in well_obj_paths if p.stem.split('_')[0] in well_selection]
    
#     # Rebuild the well objects from the saved files
#     well_objs = [Well.from_json(p) for p in well_obj_paths]
#     return well_objs

# def after_celltinder_rescue(a1_manager: A1Manager,
#                             settings: PipelineSettings,
#                             well_selection: str | list[str] | None = None) -> None:
    
#     # Retrieve saved well objects from the run directory
#     well_objs = _retrieve_saved_wells(settings, well_selection)

#     # Resend the images to the server    
#     with ComposeManager():
#         # Clean up the redis server
#         cleanup_stale()
        
#         # Loop through each well object and process the images
#         for well_obj in well_objs:
#             # create stim masks
#             create_stim_masks(well_obj,
#                                 erosion_factor=settings.stim_settings.erosion_factor)
                    
#             # Illumintate the cells
#             illuminate_fovs(well_obj, a1_manager, settings)

#             # Extract the control data
#             update_control_intensities(well_obj.positive_fovs,
#                                        csv_path=well_obj.csv_path)