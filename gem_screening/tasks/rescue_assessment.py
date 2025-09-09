"""
Functions to assess the current state of a pipeline run for rescue operations.
"""
from pathlib import Path
from typing import Dict, Any

from gem_screening.utils.pipeline_constants import REFSEG_LABEL
from gem_screening.well_data.well_classes import Well

# TODO: add case tracking
def assess_rescue(well_obj: Well) -> Dict[str, Any]:
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
    expected_fov_ids = {fov.fov_id for fov in well_obj.positive_fovs}
    
    # Case 3: Check for CSV file (celltinder or illuminate case)
    if well_obj.csv_path.exists():
        return {
            "case": "celltinder",
            "masks_to_register": [],
            "fovs_to_process": [],
            "total_fovs": len(expected_fov_ids)
        }
    
    # Define helper function first
    def extract_fov_id(file_path: Path) -> str:
        """Extract FOV ID from mask filename like 'A1P1_mask_1.tif' -> 'A1P1'"""
        return file_path.stem.split(f'_{REFSEG_LABEL}_')[0]
    
    def get_tracked_masks(mask_dir: Path) -> set[Path]:
        """Get set of already tracked mask paths from tracked_files.txt"""
        track_log_file = mask_dir / "tracked_files.txt"
        if not track_log_file.exists():
            return set()
        
        # Read tracked files from log and convert to Path objects
        with open(track_log_file, 'r') as f:
            tracked_paths = {Path(line.strip()) for line in f if line.strip()}
        
        return tracked_paths
    
    # Check for R1 mask files first - this determines our starting point
    r1_mask_files = list(well_obj.mask_dir.glob(f"*_{REFSEG_LABEL}_1.tif"))
    r1_mask_fovs = {extract_fov_id(f) for f in r1_mask_files}
    
    # Find R2 mask files
    r2_mask_files = list(well_obj.mask_dir.glob(f"*_{REFSEG_LABEL}_2.tif"))
    
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
    tracked_masks = get_tracked_masks(well_obj.mask_dir)
    
    # Check if R1 is complete
    r1_complete = r1_mask_fovs.issuperset(expected_fov_ids)
    
    if r1_complete:
        # R1 complete, check if R2 is also complete
        r2_complete = r2_mask_fovs.issuperset(expected_fov_ids)
        
        # R1 complete, R2 complete or incomplete - subtract already tracked masks
        untracked_r1_masks = [mask for mask in r1_mask_files if mask not in tracked_masks]
        untracked_r2_masks = [mask for mask in r2_mask_files if mask not in tracked_masks]
        
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
        untracked_r1_masks = [mask for mask in r1_mask_files if mask not in tracked_masks]
        untracked_r2_masks = [mask for mask in r2_mask_files if mask not in tracked_masks]
        
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
