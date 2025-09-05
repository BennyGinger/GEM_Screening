"""
Functions to assess the current state of a pipeline run for rescue operations.
"""
from pathlib import Path
from typing import Dict, Any

from gem_screening.well_data.well_classes import Well


def _count_expected_images(well_obj: Well) -> int:
    """
    Count the total number of images expected based on the well grid.
    
    Args:
        well_obj: The Well object containing FOV information
        
    Returns:
        Total number of expected images (number of FOVs)
    """
    return len(well_obj.positive_fovs)


def _count_actual_images_in_directory(well_obj: Well) -> Dict[str, Any]:
    """
    Count the actual number of image files in the img directory.
    Identifies missing FOVs and provides detailed analysis of what's missing.
    
    Args:
        well_obj: The Well object containing directory information
        
    Returns:
        Dictionary with detailed counts and missing FOV analysis
    """
    img_dir = well_obj.img_dir
    
    # Get all expected FOV IDs from the well object
    expected_fov_ids = {fov.fov_id for fov in well_obj.positive_fovs}
    
    if not img_dir.exists():
        return {
            "total": 0,
            "refseg_1": 0, "refseg_2": 0,
            "measure_1": 0, "measure_2": 0,
            "round_1_complete_pairs": 0,
            "round_2_complete_pairs": 0,
            "missing_round1": list(expected_fov_ids),
            "missing_round2": [],
            "complete_r1_r2_pairs": [],
            "fov_ids": {
                "refseg_1": set(), "refseg_2": set(),
                "measure_1": set(), "measure_2": set()
            }
        }
    
    # Count files by type and round
    refseg_1_files = list(img_dir.glob("*_refseg_1.tif"))
    refseg_2_files = list(img_dir.glob("*_refseg_2.tif"))
    measure_1_files = list(img_dir.glob("*_measure_1.tif"))
    measure_2_files = list(img_dir.glob("*_measure_2.tif"))
    
    # Extract FOV IDs from filenames
    def extract_fov_id(file_path: Path) -> str:
        """Extract FOV ID from filename like 'A1P1_refseg_1.tif' -> 'A1P1'"""
        return file_path.stem.split('_')[0]
    
    # Get sets of FOV IDs for each type
    refseg_1_fovs = {extract_fov_id(f) for f in refseg_1_files}
    refseg_2_fovs = {extract_fov_id(f) for f in refseg_2_files}
    measure_1_fovs = {extract_fov_id(f) for f in measure_1_files}
    measure_2_fovs = {extract_fov_id(f) for f in measure_2_files}
    
    # Find complete pairs for each round
    round_1_complete_fovs = refseg_1_fovs.intersection(measure_1_fovs)
    round_2_complete_fovs = refseg_2_fovs.intersection(measure_2_fovs)
    
    # Find missing FOVs for round 1 (expected but not complete pairs)
    missing_round1 = list(expected_fov_ids - round_1_complete_fovs)
    
    # Missing round 2 logic depends on round 1 status
    if len(round_1_complete_fovs) == len(expected_fov_ids):
        # Round 1 is complete, check what's missing from round 2
        missing_round2 = list(round_1_complete_fovs - round_2_complete_fovs)
    else:
        # Round 1 incomplete, missing_round2 not relevant
        missing_round2 = []
    
    # Find FOVs that have complete pairs for BOTH rounds (2x2 complete)
    complete_r1_r2_pairs = list(round_1_complete_fovs.intersection(round_2_complete_fovs))
    
    return {
        "total": len(refseg_1_files) + len(refseg_2_files) + len(measure_1_files) + len(measure_2_files),
        "refseg_1": len(refseg_1_files),
        "refseg_2": len(refseg_2_files), 
        "measure_1": len(measure_1_files),
        "measure_2": len(measure_2_files),
        "round_1_complete_pairs": len(round_1_complete_fovs),
        "round_2_complete_pairs": len(round_2_complete_fovs),
        "missing_round1": missing_round1,
        "missing_round2": missing_round2,
        "complete_r1_r2_pairs": complete_r1_r2_pairs,
        "fov_ids": {
            "refseg_1": refseg_1_fovs,
            "refseg_2": refseg_2_fovs,
            "measure_1": measure_1_fovs,
            "measure_2": measure_2_fovs,
            "round_1_complete": round_1_complete_fovs,
            "round_2_complete": round_2_complete_fovs
        }
    }


def _assess_image_scanning_state(well_obj: Well) -> Dict[str, Any]:
    """
    Assess the current state of image scanning for a well.
    Simplified logic based on biological constraints.
    
    Args:
        well_obj: The Well object to assess
        
    Returns:
        Dictionary containing assessment information
    """
    expected_fovs = _count_expected_images(well_obj)
    actual_images = _count_actual_images_in_directory(well_obj)
    
    # Check if stimulation has occurred (any round 2 files exist)
    has_round_2_files = (actual_images["refseg_2"] > 0 or actual_images["measure_2"] > 0)
    
    assessment = {
        "expected_fovs": expected_fovs,
        "actual_images": actual_images,
        "stimulation_occurred": has_round_2_files,
        "round_1_complete": actual_images["round_1_complete_pairs"] == expected_fovs,
        "round_2_complete": actual_images["round_2_complete_pairs"] == expected_fovs,
        "status": "unknown"
    }
    
    # Simplified status determination
    if not has_round_2_files:
        # No stimulation yet
        if assessment["round_1_complete"]:
            assessment["status"] = "ready_for_round2"
        else:
            assessment["status"] = "continue_round1"
    else:
        # Stimulation occurred
        if assessment["round_1_complete"]:
            if assessment["round_2_complete"]:
                assessment["status"] = "complete"
            else:
                assessment["status"] = "continue_round2"
        else:
            assessment["status"] = "analyze_complete_pairs_only"
    
    return assessment


def assess_rescue(well_obj: Well) -> Dict[str, Any]:
    """
    Assess rescue feasibility with simplified logic.
    
    Args:
        well_obj: The Well object to assess
        
    Returns:
        Dictionary containing rescue action plan
    """
    scanning_state = _assess_image_scanning_state(well_obj)
    actual_images = scanning_state["actual_images"]
    status = scanning_state["status"]
    
    rescue_plan = {
        "action": status,
        "details": {},
        "scanning_state": scanning_state
    }
    
    if status == "ready_for_round2":
        rescue_plan["details"] = {
            "message": "Round 1 complete, proceed with stimulation and round 2",
            "action": "Run normal round 2 workflow"
        }
        
    elif status == "continue_round1":
        missing_round1 = actual_images["missing_round1"]
        rescue_plan["details"] = {
            "message": f"Round 1 incomplete: {len(missing_round1)} FOVs need imaging",
            "missing_fovs": missing_round1,
            "action": "Image missing/mismatched FOVs for round 1 (may overwrite existing)"
        }
        
    elif status == "continue_round2":
        missing_round2 = actual_images["missing_round2"]
        rescue_plan["details"] = {
            "message": f"Round 2 incomplete: {len(missing_round2)} FOVs need imaging",
            "missing_fovs": missing_round2,
            "action": "Image missing/mismatched FOVs for round 2 (may overwrite existing)"
        }
        
    elif status == "analyze_complete_pairs_only":
        complete_2x2_pairs = actual_images["complete_r1_r2_pairs"]
        rescue_plan["details"] = {
            "message": f"Cannot rescue incomplete round 1 after stimulation",
            "complete_pairs": len(complete_2x2_pairs),
            "total_expected": scanning_state["expected_fovs"],
            "fov_list": complete_2x2_pairs,
            "action": "Analyze only the complete 2x2 paired FOVs, ignore missing ones"
        }
        
    elif status == "complete":
        rescue_plan["details"] = {
            "message": "All imaging complete",
            "action": "Proceed to analysis workflow"
        }
    
    return rescue_plan


if __name__ == "__main__":
    # Example usage - would need actual well object
    pass
