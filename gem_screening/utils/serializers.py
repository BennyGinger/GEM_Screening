from dataclasses import asdict
import json
from pathlib import Path
from typing import TYPE_CHECKING

from a1_manager import StageCoord


if TYPE_CHECKING:
    # these lines are invisible at runtime, but IDEs index them
    from gem_screening.well_manager.well_classes import Well
    from gem_screening.well_manager.well_classes import FieldOfView
    
       
class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle specific types during serialization.
    Args:
        json.JSONEncoder: The base JSON encoder class.
    """
    def default(self, obj: object) -> dict:
        if isinstance(obj, Well):
            return {"__Well__": {
                "run_dir":     obj.run_dir,
                "well_grid":   obj.well_grid,
                "well":        obj.well,
                "fov_obj_list": obj.fov_obj_list,
                "well_dir":    obj.well_dir,
                "config_dir":  obj.config_dir,
                "img_dir":     obj.img_dir,
                "mask_dir":    obj.mask_dir,
                "csv_path":    obj.csv_path,}}
                  
        if isinstance(obj, Path):
            return {"__Path__": True, "path": str(obj)}
        
        if isinstance(obj, StageCoord):
            return { "__StageCoord__": asdict(obj) }
        
        if isinstance(obj, FieldOfView):
            return {"__FieldOfView__": {
                "fov_coord":            obj.fov_coord,      # still a StageCoord
                "well":                 obj.well,
                "instance":             obj.instance,
                "contain_positive_cell":obj.contain_positive_cell,
                "fov_ID":               obj.fov_ID,
                "images_path":          obj.images_path,    # dict[str, Path]
                "masks_path":           obj.masks_path}}

        # Let the base class raise TypeError for anything else
        return super().default(obj)
    
def custom_decoder(dct: dict) -> dict:
    """
    Custom JSON decoder to handle specific types during deserialization.
    Args:
        dct (dict): The dictionary to decode.
    Returns:
        dict: The decoded dictionary.
    """
    if "__Well__" in dct:
        return dct["__Well__"]
    if "__Path__" in dct:
        return Path(dct["path"])
    if "__StageCoord__" in dct:
        return StageCoord(**dct["__StageCoord__"])
    if "__FieldOfView__" in dct:
        return FieldOfView.from_dict(dct["__FieldOfView__"])
    return dct