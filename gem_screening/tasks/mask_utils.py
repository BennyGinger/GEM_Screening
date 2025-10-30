from pathlib import Path
import logging

from gem_screening.utils.identifiers import parse_image_filename
from gem_screening.utils.pipeline_constants import MASK_LABEL
from gem_screening.well_data.well_classes import FieldOfView, Well


# Set up logging
logger = logging.getLogger(__name__)

def assign_masks_to_fovs(well_list: list[Well]) -> None:
    """
    Assign masks to each FieldOfView based on the mask files in the specified directory. 
    Each mask file should be in the format '<FOVID>_mask_[1-9].tif'. Any other format will be ignored.
    
    Args:
        well_list (list[Well]): List of Well objects containing FOVs to assign masks to.
    """
    # Map all the fov by fov_id
    fov_list = []
    for well in well_list:
        fov_list.extend(well.positive_fovs)
    fov_map = {fov.fov_id: fov for fov in fov_list}

    # Early exit if no FOVs
    if not fov_map:
        logger.info("No positive FOVs found. Skipping mask assignment.")
        return
    
    # Check if masks have already been assigned to all FOVs
    already_assigned = all(fov.tiff_paths.get(MASK_LABEL) for fov in fov_map.values())
    if already_assigned:
        logger.debug("Masks have already been assigned to all FOVs. Skipping mask assignment.")
        return
    
    # Pre-seed grouping dict so zero-mask FOVs show up
    fov_masks: dict[str, list[Path]] = {fov_id: [] for fov_id in fov_map.keys()}
    
    # Batch process mask files
    mask_files = []
    for well in well_list:
        mask_files.extend(well.mask_dir.glob("*.tif"))
    logger.info(f"Processing {len(mask_files)} mask files for {len(fov_map)} FOVs")
    
    # Group masks by FOV identifier
    _group_masks_by_fov(fov_masks, mask_files)
    
    # Check that each key contains the same number of masks
    _log_mask_counts(fov_masks)
    
    # Batch assign masks to the corresponding FOVs
    total_masks_assigned = _assign_masks_to_fovs(fov_map, fov_masks)
    
    logger.info(f"Assigned {total_masks_assigned} masks to {len(fov_masks)} FOVs .")

def _log_mask_counts(fov_masks: dict[str, list[Path]]) -> None:
    counts = {fid: len(paths) for fid, paths in fov_masks.items()}
    unique_counts = set(counts.values())
    if len(unique_counts) == 1:
        logger.info(f"All FOVs have the same number of masks: {unique_counts.pop()}")
    else:
        for n in sorted(unique_counts):
            bad = [fid for fid, count in counts.items() if count == n]
            logger.warning(f"FOVs {bad} have {n} masks, which is different from the others.")

def _assign_masks_to_fovs(fov_map: dict[str, FieldOfView], fov_masks: dict[str, list[Path]]) -> int:
    total_masks_assigned = 0
    for fov_id, paths in fov_masks.items():
        fov = fov_map.get(fov_id)
        if fov is not None and paths:
            # Batch process paths for this FOV
            for path in paths:
                fov.register_existing_tiff(path)
            total_masks_assigned += len(paths)
    return total_masks_assigned

def _group_masks_by_fov(fov_masks: dict[str, list[Path]], mask_files: list[Path]) -> None:
    for mask_path in mask_files:
        try:
            # Extract the FOV identifier from the mask file name
            fov_id, cat, _ = parse_image_filename(mask_path)
            
            # Skip if the category is not MASK_LABEL (faster check first)
            if cat != MASK_LABEL:
                continue
                
            # Check if the FOV identifier is recognized
            if fov_id not in fov_masks:
                logger.warning(f"Mask file {mask_path} has an unrecognized FOV ID: {fov_id}. Skipping.")
                continue
                
            # Append the mask file to the corresponding FOV's list
            fov_masks[fov_id].append(mask_path)
        except Exception as e:
            logger.warning(f"Error processing mask file {mask_path}: {e}. Skipping.")
            continue