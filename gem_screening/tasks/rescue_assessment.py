"""
Functions to assess the current state of a pipeline run for rescue operations.
"""
from pathlib import Path
from typing import Dict, Any

import pandas as pd

from gem_screening.utils.pipeline_constants import MASK_LABEL, FOV_ID
from gem_screening.well_data.well_classes import Plate


def assess_rescue(plate_obj: Plate) -> Dict[str, Any]:
    """
    Simplified rescue assessment with 3 main cases.
    
    Args:
        well_obj: The Well object to assess
        
    Returns:
        Dictionary with:
        - case: "round1", "round2", or "celltinder" 
        - masks_to_register: list of mask file paths to register (both R1 and R2)
        - fovs_to_process: list of FOV IDs that need processing
        - total_fovs: total number of FOVs for processing (adjusted for edge cases)
    """
    expected_fov_ids = {fov.fov_id for fov in plate_obj.positive_fovs}
    
    # Check which FOVs need processing for data extraction
    fovs_to_process_extraction = []
    existing_df = None
    
    if plate_obj.csv_path.exists():
        try:
            existing_df = pd.read_csv(plate_obj.csv_path)
            existing_fov_ids = set(existing_df[FOV_ID].unique()) if FOV_ID in existing_df.columns else set()
            
            # Filter out FOVs that are already processed for data extraction
            fovs_to_process_extraction = [fov for fov in plate_obj.positive_fovs if fov.fov_id not in existing_fov_ids]
            
            if not fovs_to_process_extraction:
                # All FOVs already exist in CSV - go to celltinder
                return {
                    "case": "celltinder",
                    "masks_to_register": [],
                    "fovs_to_process": [],
                    "total_fovs": len(expected_fov_ids)
                }
            
        except Exception as e:
            # Error reading CSV, continue with assessment
            fovs_to_process_extraction = list(plate_obj.positive_fovs)
    else:
        fovs_to_process_extraction = list(plate_obj.positive_fovs)
    
    # Define helper function first
    def extract_fov_id(file_path: Path) -> str:
        """Extract FOV ID from mask filename like 'A1P1_mask_1.tif' -> 'A1P1'"""
        return file_path.stem.split(f'_{MASK_LABEL}_')[0]

    def get_tracked_masks(mask_dirs: list[Path]) -> set[str]:
        """Get set of already tracked mask file names from tracked_files.txt.
        We compare by file name only to avoid host/container path mismatches."""
        tracked_names = set()
        for mask_dir in mask_dirs:
            track_log_file = mask_dir / "tracked_files.txt"
            if not track_log_file.exists():
                continue
            with open(track_log_file, 'r') as f:
                tracked_names.update(Path(line.strip()).name for line in f if line.strip())
        return tracked_names
    
    # Check for R1 mask files first - this determines our starting point
    r1_mask_files = list(plate_obj.mask_dir_glob(f"*_{MASK_LABEL}_1.tif"))
    r1_mask_fovs = {extract_fov_id(f) for f in r1_mask_files}
    
    # Find R2 mask files
    r2_mask_files = list(plate_obj.mask_dir_glob(f"*_{MASK_LABEL}_2.tif"))

    # Case 1: No R2 masks found - start from round1 (regardless of R1 status)
    if not r2_mask_files:
        # Get the FOV IDs for any existing R1 mask files
        fovs_to_process = list(expected_fov_ids - r1_mask_fovs)
        
        return {
            "case": "round1",
            "masks_to_register": r1_mask_files,
            "fovs_to_process": fovs_to_process,
            "total_fovs": len(expected_fov_ids)
        }
    
    # Case 2: R2 masks found - start from round2
    # Now we know r2_mask_files is not empty, so create the set
    r2_mask_fovs = {extract_fov_id(f) for f in r2_mask_files}
    
    # Get already tracked masks to subtract from registration lists
    tracked_mask_names = get_tracked_masks(plate_obj.mask_dirs)
    
    # Check if R1 is complete
    r1_complete = r1_mask_fovs.issuperset(expected_fov_ids)
    
    if r1_complete:
        # R1 complete, check if R2 is also complete
        r2_complete = r2_mask_fovs.issuperset(expected_fov_ids)
        
        # R1 complete, R2 complete or incomplete - subtract already tracked masks
        untracked_r1_masks = [mask for mask in r1_mask_files if mask.name not in tracked_mask_names]
        untracked_r2_masks = [mask for mask in r2_mask_files if mask.name not in tracked_mask_names]
        
        # Combine all untracked masks for registration
        all_untracked_masks = untracked_r1_masks + untracked_r2_masks
        
        if r2_complete:
            # R2 complete but tracking incomplete - no FOVs to image
            fovs_to_process = []
        else:
            # R2 incomplete - continue imaging
            fovs_to_process = list(expected_fov_ids - r2_mask_fovs)
        
        total_fovs = len(expected_fov_ids)
    else:
        # R1 incomplete, only process FOVs that have R1 masks
        valid_fovs = r1_mask_fovs
        fovs_to_process = list(valid_fovs - r2_mask_fovs)
        # Edge case: total FOVs should be based on actual R1 masks, not expected
        total_fovs = len(r1_mask_fovs)
        
    # Subtract already tracked masks for incomplete R1 case too
    untracked_r1_masks = [mask for mask in r1_mask_files if mask.name not in tracked_mask_names]
    untracked_r2_masks = [mask for mask in r2_mask_files if mask.name not in tracked_mask_names]
        
    # Combine all untracked masks for registration
    all_untracked_masks = untracked_r1_masks + untracked_r2_masks
    
    # Final check: If no masks need registration, go to celltinder (regardless of missing FOVs)
    if not all_untracked_masks:
        return {
            "case": "celltinder",
            "masks_to_register": [],
            "fovs_to_process": [],
            "total_fovs": total_fovs
        }
    
    return {
        "case": "round2",
        "masks_to_register": all_untracked_masks,
        "fovs_to_process": fovs_to_process,
        "total_fovs": total_fovs
    }


if __name__ == "__main__":
    # Example usage showing the 3 simplified cases with tracking optimization:
    # 
    # Case 1 - Round 1: No r2 masks found
    # {"case": "round1", "masks_to_register": [Path("A1P1_mask_1.tif"), Path("A1P2_mask_1.tif")], 
    #  "fovs_to_process": ["A1P3", "A1P4"], "total_fovs": 4}
    #
    # Case 2 - Round 2: R2 masks found, only untracked masks registered (sorted automatically by server)
    # {"case": "round2", "masks_to_register": [Path("A1P2_mask_1.tif"), Path("A1P1_mask_2.tif")],  # Mixed R1/R2, server sorts
    #  "fovs_to_process": ["A1P3", "A1P4"], "total_fovs": 4}  # Only masks not in tracked_files.txt
    #
    # Case 3 - CellTinder: CSV file exists OR (R1+R2 complete AND all tracking complete)
    # {"case": "celltinder", "masks_to_register": [], "fovs_to_process": [], "total_fovs": 4}
    pass
