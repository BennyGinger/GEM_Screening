from functools import partial
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from skimage.measure import regionprops_table
from progress_bar import run_parallel as parallel_progress_bar

from gem_screening.well_data.well_classes import FieldOfView


logger = logging.getLogger(__name__)

def extract_all_fovs(fovs: list[FieldOfView], 
                     true_cell_threshold: float,
                     csv_path: Path,
                     *, 
                     executor: str = 'process', 
                     max_workers: int | None = None) -> None:
    """
    Extract the region properties for all FOVs in parallel, convert it to a pandas `DataFrame` and save it to a CSV file.
    Args:
        fovs (list[FieldOfView]): List of FieldOfView objects to process.
        true_cell_threshold (float): Threshold for true cell detection. Below this value, cells are considered noise and set to 0 in the output.
        csv_path (Path): Path to save the resulting CSV file.
        executor (str, optional): Type of executor to use for parallel processing ('thread' or 'process'). Defaults to 'process'.
        max_workers (int | None): Maximum number of workers to use for parallel processing. Defaults to None, which lets the executor decide based on available resources.
    """
    # Bind the threshold into a worker
    worker = partial(_regionprops_wrapper, true_cell_threshold=true_cell_threshold)
    
    # Run the worker in parallel over all FOVs
    region_dfs = parallel_progress_bar(
        worker,
        fovs,
        executor=executor,
        max_workers=max_workers,
        desc="Extracting region properties")
    
    # Concatenate all the DataFrames
    df = pd.concat(region_dfs, ignore_index=True)
    # TODO: Change that to parquet
    df.to_csv(csv_path, index=False)

def _regionprops_wrapper(fov: FieldOfView, true_cell_threshold: float) -> pd.DataFrame:
    """
    Wrapper function to extract region properties for a single FieldOfView.
    Args:
        fov (FieldOfView): The FieldOfView object to process.
        true_cell_threshold (float): Threshold for true cell detection. Below this value, cells are considered noise and set to 0 in the output.
    Returns:
        pd.DataFrame: DataFrame containing the extracted region properties for the FOV.
    """
    # Load the images and masks
    img0, imgn = fov.load_images('measure')
    mask0, maskn = fov.load_images('mask')
    logger.debug(f"Loaded image stack shape: {img0.shape}, mask stack shape: {mask0.shape} for FOV {fov.fov_id}.")
    # Extract the properties of each frame
    props0 = regionprops_table(mask0,
                              intensity_image=img0,
                              properties=["label", "mean_intensity"])
    
    propsn = regionprops_table(maskn,
                              intensity_image=imgn,
                              properties=["label", "mean_intensity", 'centroid'])
    
    # Convert the properties to DataFrames
    df0 = pd.DataFrame(props0).rename(columns={'mean_intensity': 'mean_before_stim'})
    dfn = pd.DataFrame(propsn).rename(columns={'mean_intensity': 'mean_after_stim',
                                               'centroid-0': 'centroid_y',
                                               'centroid-1': 'centroid_x'})
    df = pd.merge(df0, dfn, on='label', how='outer').rename(columns={'label': 'cell_numb'})
    
    # Apply the true cell threshold to the mean intensity, else set to 0
    df['mean_after_stim'] = df['mean_after_stim'].where(df['mean_after_stim'] >= true_cell_threshold, 0)
    # Add the FOV ID and coordinates
    fx, fy =fov.fov_coord.xy
    df['fov_y'] = fy
    df['fov_x'] = fx
    # Generate the cell ID
    df['fov_id'] = [f"{fov.fov_id}_C{cell}" for cell in df['cell_numb']]
    # Apply the ratio, avoiding division by zero
    df['ratio'] = df['mean_after_stim'] / df['mean_before_stim'].replace(0, np.nan)
    return df