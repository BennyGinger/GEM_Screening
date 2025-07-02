import logging
from pathlib import Path

from a1_manager import A1Manager, StageCoord
from cp_server import ComposeManager

from gem_screening.tasks.data_intensity import extract_measure_intensities, update_control_intensities
from gem_screening.tasks.image_capture import QuitImageCapture, scan_cells
from gem_screening.tasks.light_stimulation import create_stim_masks, illuminate_fovs
from gem_screening.tasks.mask_utils import assign_masks_to_fovs
from gem_screening.utils.client.client import bg_removal_client, cleanup_stale, full_process_client, wait_for_completion
from gem_screening.utils.external import run_celltinder
from gem_screening.utils.filesystem import create_timestamped_dir
from gem_screening.utils.pipeline_constants import WELL_OBJ_FILENAME, MEASURE_LABEL, REFSEG_LABEL
from gem_screening.utils.settings.models import PipelineSettings
from gem_screening.well_data.well_classes import Well


logger = logging.getLogger(__name__)

def run_pipeline(dish_grid: dict[str, dict[str, StageCoord]],
                  a1_manager: A1Manager,
                  run_dir: Path,
                  run_id: str,
                  settings: PipelineSettings,
                  ) -> None:
    """
    Run the pipeline for the given dish grid.
    Args:
        dish_grid (dict[str, dict[str, StageCoord]]): The dish grid containing well coordinates.
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        logger (logging.Logger): The logger instance for logging messages.
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
            # Scan cells
            try:
                # Scan cells in the well, images will then be sent to the server for processing
                scan_cells(well_obj, settings, a1_manager)
                # Wait for processing to complete, this will block until all celery tasks are done.
                wait_for_completion(well_obj.well_id, timeout=settings.server_settings.server_timeout_sec)
            except QuitImageCapture:  
                logger.info("User chose to quit the image capture process.")
                break
            
            # Execute well analysis
            _execute_well_analysis(a1_manager, settings, well, well_obj)
            
            logger.info(f"Completed processing for well: {well}")

def _execute_well_analysis(a1_manager: A1Manager, settings: PipelineSettings, well_obj: Well) -> None:
    """
    Execute the analysis for a well after image acquisition.
    This includes assigning masks to field of views, extracting stimulation settings,
    extracting data, running the cell tinder GUI, creating stimulation masks,
    illuminating cells, and updating control intensities.
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings,and save directory.
        well_obj (Well): The well object containing the field of views and other data.
    """
    # Assign masks to field of views
    assign_masks_to_fovs(well_obj)
            
    # Extract the stimulation settings
    stim_sets = settings.stim_settings
            
    # Extract the data
    extract_measure_intensities(well_obj.positive_fovs,
                             true_cell_threshold=stim_sets.true_cell_threshold,
                             csv_path=well_obj.csv_path,)

    # Run the cell tinder GUI
    run_celltinder(well_obj.csv_path,
                            crop_size=stim_sets.crop_size)
            
    # create stim masks
    create_stim_masks(well_obj,
                              erosion_factor=stim_sets.erosion_factor)
            
    # Illumintate the cells
    illuminate_fovs(well_obj, a1_manager, settings)

    # Extract the control data
    update_control_intensities(well_obj.positive_fovs,
                                       csv_path=well_obj.csv_path)
            
       
def after_acquisition_rescue(a1_manager: A1Manager,
                settings: PipelineSettings,
                well_selection: str | list[str] | None = None,
                ) -> None:
    """
    After acquisition rescue function to resend images to the server for processing.
    This function is used to recover from a failed acquisition or to reprocess specific wells. It collects all well objects from the saved directory, filters them based on the well selection, and resends the images to the server for processing.
    Args:
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
        well_selection (str | list[str] | None): Optional selection of wells to process. If None, all wells will be processed.
    """
    # Retrieve saved well objects from the run directory
    well_objs = _retrieve_saved_wells(settings, well_selection)
        
    # Resend the images to the server    
    with ComposeManager():
        # Clean up the redis server
        cleanup_stale()
        
        # Loop through each well object and process the images
        for well_obj in well_objs:
            fovs = well_obj.positive_fovs
            # Get the images to be processed
            measure_paths = sorted([fov.tiff_paths[MEASURE_LABEL] for fov in fovs])
            
            if settings.measure_settings.do_refseg:
                refseg_paths = sorted([fov.tiff_paths[REFSEG_LABEL] for fov in fovs])
                
                # Send measure images for background removal
                for img_path in measure_paths:
                    bg_removal_client(settings.server_settings, img_path)
                
                # Send refseg images for full processing
                for img_path in refseg_paths:
                    full_process_client(settings.server_settings, img_path)
                continue
            
            # If no refseg is used, send measure images for full processing
            for img_path in measure_paths:
                full_process_client(settings.server_settings, img_path)
                
            # Wait for completion
            wait_for_completion(well_obj.run_id, timeout=settings.server_settings.server_timeout_sec)
            
            _execute_well_analysis(a1_manager, settings, well_obj)

def _retrieve_saved_wells(settings: PipelineSettings, well_selection: str | list[str] | None = None) -> list[Well]:
    """
    Retrieve saved well objects from the run directory based on the provided settings and well selection.
    Args:
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
        well_selection (str | list[str] | None): Optional selection of wells to process. If None, all wells will be processed.
    Returns:
        list[Well]: A list of Well objects that match the well selection criteria.
    """
    # Reconstruct run_dir
    run_dir = create_timestamped_dir(settings.savedir, settings.savedir_name)
    
    # Collect all well object paths
    well_obj_paths = run_dir.rglob(f"*_{WELL_OBJ_FILENAME}")
    if well_selection is not None:
        if isinstance(well_selection, str):
            well_selection = [well_selection]
        well_obj_paths = [p for p in well_obj_paths if p.stem.split('_')[0] in well_selection]
    
    # Rebuild the well objects from the saved files
    well_objs = [Well.from_json(p) for p in well_obj_paths]
    return well_objs

def after_celltinder_rescue(a1_manager: A1Manager,
                            settings: PipelineSettings,
                            well_selection: str | list[str] | None = None) -> None:
    
    # Retrieve saved well objects from the run directory
    well_objs = _retrieve_saved_wells(settings, well_selection)

    # Resend the images to the server    
    with ComposeManager():
        # Clean up the redis server
        cleanup_stale()
        
        # Loop through each well object and process the images
        for well_obj in well_objs:
            # create stim masks
            create_stim_masks(well_obj,
                                erosion_factor=settings.stim_settings.erosion_factor)
                    
            # Illumintate the cells
            illuminate_fovs(well_obj, a1_manager, settings)

            # Extract the control data
            update_control_intensities(well_obj.positive_fovs,
                                       csv_path=well_obj.csv_path)