from __future__ import annotations
import logging
from typing import TypeVar

from a1_manager import A1Manager
import numpy as np
from numpy.typing import NDArray
import pandas as pd
import skimage.morphology as morph
import cv2
from progress_bar import run_parallel as parallel_progress_bar
from progress_bar import setup_progress_monitor as progress_bar

from gem_screening.utils.pipeline_constants import PROCESS, FOV_ID, MASK_LABEL, STIM_LABEL, CONTROL_LABEL
from gem_screening.tasks.image_capture import image_fovs
from gem_screening.utils.filesystem import imwrite_atomic
from gem_screening.utils.settings.models import PipelineSettings, PresetStim
from gem_screening.well_data.well_classes import FieldOfView, Well


# a TypeVar for “any numpy scalar type”
T = TypeVar("T", bound=np.generic)

# Set up logging
logger = logging.getLogger(__name__)


def create_stim_masks(well_obj: Well, 
                      erosion_factor: int,
                      *,
                      executor: str = 'thread',
                      max_workers: int | None = None,) -> None:
    """
    Create stimulation masks for each FieldOfView based on the provided CSV data.
    Args:
        well_obj (Well): The well object containing the field of views and their metadata.
        erosion_factor (int): Size of the disk to erode each mask with.
        executor (str, optional): Type of executor to use for parallel processing. Default is 'thread'.
        max_workers (int, optional): Maximum number of workers for parallel processing. Default is None, which uses the default number of workers.
    """
    # FIXME: Change to parquet
    data = pd.read_csv(well_obj.csv_path)
    logger.info(f"Loaded cell data from {well_obj.csv_path} with {len(data)} rows.")
    
    # build a list of (fov, subdf) tasks
    tasks = [(fov, data[data[FOV_ID] == fov.fov_id]) for fov in well_obj.positive_fovs]
    
    def process_task(args):
        fov, subdf = args
        return _process_one_fov(fov, subdf, erosion_factor=erosion_factor)
    
    parallel_progress_bar(
        process_task,
        tasks,
        desc="Creating stimulation masks",
        executor=executor,
        max_workers=max_workers,)
    
    # Save the well object after processing
    logger.info(f"All stimulation masks created for well {well_obj.well}.")
    well_obj.to_json()

def illuminate_fovs(well_obj: Well, a1_manager: A1Manager, settings: PipelineSettings) -> None:
    """
    Illuminate all cells in the FOVs of a well object, and capture control images before and after illumination.
    Args:
        well_obj (Well): The well object containing the field of views.
        a1_manager (A1Manager): The A1Manager object to control the microscope.
        settings (PipelineSettings): The settings for the imaging pipeline.
    """
    do_control = settings.control_settings.control_loop
    
    # control loop before illumination
    if do_control:
        image_fovs(well_obj, a1_manager, settings, f"{CONTROL_LABEL}_1")
        logger.info("Captured control images before illumination.")
    
    # Illuminate all FOVs
    _illuminate_cells(well_obj, a1_manager, settings.stim_settings.preset)
    logger.info("Illuminated all cells in the FOVs.")
    
    # control loop after illumination
    if do_control:
        image_fovs(well_obj, a1_manager, settings, f"{CONTROL_LABEL}_2")
        logger.info("Captured control images after illumination.")

################## Helper Functions ##################
def _illuminate_cells(well_obj: Well, a1_manager: A1Manager, stim_preset: PresetStim) -> None:
    """
    Illuminate all cells in the FOVs.
    Args:
        fovs: List of FieldOfView objects to process.
        a1_manager: A1Manager object to control the microscope.
        stim_preset: PresetStim object containing the stimulation settings.
    Raises:
        ValueError: If no stimulation masks are found for a FOV.
    """
    preset = stim_preset.model_dump()
    duration_sec: float = preset.pop('exposure_sec', 10.)
    a1_manager.oc_settings(**preset)
    
    for fov in progress_bar(well_obj.positive_fovs,
                            desc="Illuminating cells",
                           total=len(well_obj.positive_fovs)):
        # Move to the FOV
        a1_manager.nikon.set_stage_position(fov.fov_coord)
        
        # Illuminate the cells
        dmd_masks = fov.load_images(STIM_LABEL)
        if not dmd_masks:
            raise ValueError(f"No stimulation masks found for FOV {fov.fov_id} "
                             f"({fov.contain_positive_cells=})"
                             "Please run create_stim_masks before illuminating.")
        a1_manager.load_dmd_mask(dmd_masks[-1])
        a1_manager.light_stimulate(duration_sec)

def _process_one_fov(fov: FieldOfView, fov_data: pd.DataFrame, erosion_factor: int) -> None:
    """
    Process a single FieldOfView to create stimulation masks.
    Args:
        fov: FieldOfView object containing fov's metadata.
        fov_data: DataFrame containing the cell data for the FOV.
        erosion_factor: Size of the disk to erode each mask with.
    """
    try:
        if not fov_data[PROCESS].any():
            fov.contain_positive_cells = False
            return
        
        # load only the last mask frame
        mask = fov.load_images(MASK_LABEL)[-1]
        stim_mask = _filter_labels(mask, fov_data[PROCESS].tolist())
        eroded_mask = _erode_mask(stim_mask, erosion_factor)
        
        # Register the stim mask to the FOV, and save it
        stim_name = f"{STIM_LABEL}_1" 
        stim_path = fov.register_img_file(stim_name)
        imwrite_atomic(stim_path, eroded_mask)
    except Exception as e:
        # Just log the failure, don't crash the whole pipeline
        logger.error(f"Error while creating stim_mask for FOV {fov.fov_id}: {e}")
        raise RuntimeError(
            f"Failed to create stimulation mask for FOV {fov.fov_id}. "
            "Check the logs for more details.") from e
    
def _erode_mask(mask: NDArray[T], erosion_factor: int) -> NDArray[T]:
    """
    Erode the mask using a disk-shaped structuring element.
    Args:
        mask: 2D integer array, labels in 1…n (as well as 0 for background)
        erosion_factor: Size of the disk to erode with
    Returns:
        Eroded mask as a 2D integer array.
    """
    pat_ero = morph.disk(erosion_factor)
    # Convert mask to uint8 for cv2.erode, then convert back to original dtype
    mask_uint8 = mask.astype(np.uint8)
    eroded_uint8 = cv2.erode(mask_uint8, pat_ero.astype(np.uint8))
    return eroded_uint8.astype(mask.dtype)  # type: ignore[return-value]

def _filter_labels(mask: NDArray[T], process: list[bool]) -> NDArray[T]:
    """
    Zero out any label i where process[i-1] is False.
    Args:
        mask: 2D integer array, labels in 1…n (as well as 0 for background)
        process: length-n bool list; True=>keep, False=>zero out
    """
    max_label = int(mask.max())
    if max_label > len(process):
        raise ValueError(
            f"process list too short ({len(process)}) "
            f"for max label {max_label}")
    # Build LUT of size max_label+1
    lut = np.zeros(max_label + 1, dtype=mask.dtype)
    # process[i] corresponds to label i+1, so:
    arange_vals = np.arange(1, max_label + 1, dtype=np.int32)
    process_array = np.array(process, dtype=np.int32)
    lut[1:] = (arange_vals * process_array).astype(mask.dtype)
    return lut[mask.astype(np.intp)]  # type: ignore[return-value]