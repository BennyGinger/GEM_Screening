from dataclasses import fields, is_dataclass
import json
from pathlib import Path
from typing import Any
    
       
class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle specific types during serialization.
    Args:
        json.JSONEncoder: The base JSON encoder class.
    """
    def default(self, o: object) -> object:
        # Encode any dataclass as a dictionary with a type identifier
        if is_dataclass(o):
            type_name = type(o).__name__
            d = {f.name: getattr(o, f.name) for f in fields(o)}
            return { f"__{type_name}__": d }
                  
        if isinstance(o, Path):
            return {"__Path__": {"path": str(o)}}
        
        if isinstance(o, tuple):
            return {"__tuple__": list(o)}
        
        # Fall back to the default JSON encoder for other types
        return super().default(o)
    
def custom_json_decoder(dct: dict[str, Any]) -> Any:
    """
    Custom JSON decoder to handle specific types during deserialization.
    Args:
        dct (dict): The dictionary to decode.
    Returns:
        Any: The decoded object, which could be a Well, FieldOfView, StageCoord, Path, or tuple.
    """
    # Look for any tagged object (e.g. __Well__, "__FieldOfView__", __StageCoord__, __Path__, __tuple__)
    for key in list(dct):
        if key.startswith("__") and key.endswith("__"):
            type_name = key.strip("__")
            data = dct[key]

            # 1) Well  
            if type_name == "Well":
                from gem_screening.well_data.well_classes import Well
                return Well.from_dict(data)

            # 2) FieldOfView  
            if type_name == "FieldOfView":
                from gem_screening.well_data.well_classes import FieldOfView
                return FieldOfView.from_dict(data)
            
            # 3) StageCoord (or any other dataclass)  
            if type_name == "StageCoord":
                from a1_manager import StageCoord
                return StageCoord(**data)

            # 3) Path  
            if type_name == "Path":
                return Path(data["path"])

            # 4) tuple  
            if type_name == "tuple":
                return tuple(data)

    # fallback
    return dct