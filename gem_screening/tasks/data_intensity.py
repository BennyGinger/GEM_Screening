from functools import partial
import logging
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
import pandas as pd
from skimage.measure import regionprops_table
from progress_bar import run_parallel as parallel_progress_bar

from gem_screening.well_data.well_classes import FieldOfView


logger = logging.getLogger(__name__)

def extract_measure_intensities(fovs: list[FieldOfView], 
                     true_cell_threshold: int,
                     csv_path: Path,
                     *, 
                     executor: str = 'process', 
                     max_workers: int | None = None) -> None:
    """
    Extract the region properties for all FOVs in parallel, convert it to a pandas `DataFrame` and save it to a CSV file.
    Args:
        fovs (list[FieldOfView]): List of FieldOfView objects to process.
        true_cell_threshold (int): Threshold for true cell detection. Below this intensity value, cells are considered noise and set to 0 in the output.
        csv_path (Path): Path to save the resulting CSV file.
        executor (str, optional): Type of executor to use for parallel processing ('thread' or 'process'). Defaults to 'process'.
        max_workers (int | None): Maximum number of workers to use for parallel processing. Defaults to None, which lets the executor decide based on available resources.
    """
    # Bind the threshold into a worker
    worker = partial(_create_regionprops, true_cell_threshold=true_cell_threshold)
    
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

def update_control_intensities(fovs: list[FieldOfView],
                               csv_path: Path,
                               *,
                               executor: str = 'process',
                               max_workers: int | None = None) -> None:
    """
    Update the region properties DataFrame with control images for all FOVs in parallel.
    Args:
        fovs (list[FieldOfView]): List of FieldOfView objects to process.
        csv_path (Path): Path to the CSV file containing the original region properties.
        executor (str, optional): Type of executor to use for parallel processing ('thread' or 'process'). Defaults to 'process'.
        max_workers (int | None): Maximum number of workers to use for parallel processing. Defaults to None, which lets the executor decide based on available resources.
    """
    # Build (fov, subdf) tuples by filtering on cell_id prefix
    df_ori = pd.read_csv(csv_path)
    tasks = [(fov, df_ori[df_ori["fov_id"] == fov.fov_id].copy())
        for fov in fovs]
    
    # Run the worker in parallel over all FOVs
    sub_dfs = parallel_progress_bar(
        lambda x: _update_regionprops(*x),
        tasks,
        executor=executor,
        max_workers=max_workers,
        desc="Updating region properties with control images")
    
    # Concatenate all the DataFrames
    df = pd.concat(sub_dfs, ignore_index=True)
    df.to_csv(csv_path, index=False)

def _create_regionprops(fov: FieldOfView, true_cell_threshold: int) -> pd.DataFrame:
    """
    Wrapper function to extract region properties for a single FieldOfView.
    Args:
        fov (FieldOfView): The FieldOfView object to process.
        true_cell_threshold (int): Threshold for true cell detection. Below this intensity value, cells are considered noise and set to 0 in the output.
    Returns:
        pd.DataFrame: DataFrame containing the extracted region properties for the FOV.
    """
    # Extract region properties for the measure images
    props0, propsn = _regionprops_wrapper(fov, False)
    
    # Convert the properties to DataFrames
    df0 = pd.DataFrame(props0).rename(columns={'mean_intensity': 'mean_pre_stim'})
    dfn = pd.DataFrame(propsn).rename(columns={'mean_intensity': 'mean_post_stim',
                                               'centroid-0': 'centroid_y',
                                               'centroid-1': 'centroid_x'})
    df = pd.merge(df0, dfn, on='label', how='inner').rename(columns={'label': 'cell_label'})
    
    # Apply the true cell threshold to the mean intensity, else set to 0
    df['mean_post_stim'] = df['mean_post_stim'].where(df['mean_post_stim'] >= true_cell_threshold, 0)
    # Add the FOV ID and coordinates
    fx, fy =fov.fov_coord.xy
    df['fov_y'] = fy
    df['fov_x'] = fx
    # Generate the cell ID
    df['fov_id'] = fov.fov_id
    df['cell_id'] = [f"{fov.fov_id}C{cell}" for cell in df['cell_label']]
    # Apply the ratio, avoiding division by zero
    df['ratio'] = df['mean_post_stim'] / df['mean_pre_stim'].replace(0, np.nan)
    return df

def _update_regionprops(fov: FieldOfView, df_ori: pd.DataFrame) -> pd.DataFrame:
    """
    Update the region properties DataFrame with control images.
    Args:
        fov (FieldOfView): The FieldOfView object to process.
        df_ori (pd.DataFrame): Original DataFrame containing region properties.
    Returns:
        pd.DataFrame: Updated DataFrame with control images' region properties.
    """
    # Extract region properties for the control images
    props0, propsn = _regionprops_wrapper(fov, True)
    
    # Convert the properties to DataFrames
    df0 = pd.DataFrame(props0).rename(columns={'mean_intensity': 'mean_pre_illumination',
                                               'label': 'cell_label'})
    dfn = pd.DataFrame(propsn).rename(columns={'mean_intensity': 'mean_post_illumination',
                                               'label': 'cell_label'})
    
    # Merge the new properties with the original DataFrame
    df = pd.merge(df_ori, df0, on='cell_label', how='left')
    df = pd.merge(df, dfn, on='cell_label', how='left')
    return df

def _regionprops_wrapper(fov: FieldOfView, is_control: bool) -> tuple[dict[str, NDArray], dict[str, NDArray]]:
    """
    Wrapper function to extract region properties for a single FieldOfView.
    Args:
        fov (FieldOfView): The FieldOfView object to process.
        is_control (bool): Whether to extract properties for control images or measure images.
    Returns:
        tuple[dict[str, NDArray], dict[str, NDArray]]:
            A tuple containing two dictionaries with region properties for the initial and final images.
            The keys are property names and the values are numpy arrays of the corresponding properties.
    """
    # Determine the category of images and masks based on whether it's a control or measure FOV
    if is_control:
        img_cat = 'control'
        mask_cat = 'stim'
        propn = ['label', 'mean_intensity']
    else:
        img_cat = 'measure'
        mask_cat = 'mask'
        propn = ['label', 'mean_intensity', 'centroid']
    
    # Load the images and masks for the FOV
    img0, imgn = fov.load_images(img_cat)
    mask0, maskn = fov.load_images(mask_cat)
    logger.debug(f"Loaded image stack shape: {img0.shape}, mask stack shape: {mask0.shape} for FOV {fov.fov_id}.")
    
    # Extract the properties of each frame
    props0 = regionprops_table(mask0,
                              intensity_image=img0,
                              properties=["label", "mean_intensity"])
    
    propsn = regionprops_table(maskn,
                              intensity_image=imgn,
                              properties=propn)                       
    return props0,propsn