from pathlib import Path
import logging

from gem_screening.utils.identifiers import parse_image_filename
from gem_screening.well_data.well_classes import FieldOfView


MASK_NAME = 'mask'

# Set up logging
logger = logging.getLogger(__name__)

def assign_masks_to_fovs(fovs: list[FieldOfView], mask_dir: Path) -> None:
    """
    Assign masks to each FieldOfView based on the mask files in the specified directory. 
    Each mask file should be in the format '<FOVID>_mask_[1-9].tif'. Any other format will be ignored.
    
    Args:
        fovs (list[FieldOfView]): List of FieldOfView objects to assign masks to.
        mask_dir (Path): Directory containing mask files.
    """
    # Map all the fov by fov_id
    fov_map = {fov.fov_id: fov for fov in fovs}
    
    # Pre-seed grouping dict so zero-mask FOVs show up
    fov_masks: dict[str, list[Path]] = {fov_id: [] for fov_id in fov_map.keys()}
    
    # Scan the mask directory and group masks by FOV identifier
    for mask_file in mask_dir.glob("*.tif"):
        # Extract the FOV identifier from the mask file name
        fov_id, cat, _ = parse_image_filename(mask_file)
        # Check if the FOV identifier is recognized
        if fov_id not in fov_masks:
            logger.warning(f"Mask file {mask_file} has an unrecognized FOV ID: {fov_id}. Skipping.")
            continue
        # Skip if the category is not 'mask'
        if cat != MASK_NAME:
            continue
        # Append the mask file to the corresponding FOV's list
        fov_masks[fov_id].append(mask_file)
    
    # Check that each key contains the same number of masks
    counts = {fid: len(paths) for fid, paths in fov_masks.items()}
    unique_counts = set(counts.values())
    if len(unique_counts) == 1:
        logger.info(f"All FOVs have the same number of masks: {unique_counts.pop()}")
    else:
        for n in sorted(unique_counts):
            bad = [fid for fid, count in counts.items() if count == n]
            logger.warning(f"FOVs {bad} have {n} masks, which is different from the others.")
    
    # Assign masks to the corresponding FOVs
    for id, paths in fov_masks.items():
        fov = fov_map.get(id)
        for path in paths:
            fov.register_existing_tiff(path)