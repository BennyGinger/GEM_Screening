from dataclasses import fields, is_dataclass
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel
    
       
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
        
        # Encode any Pydantic BaseModel as a dictionary with a type identifier
        if isinstance(o, BaseModel):
            type_name = type(o).__name__
            return { f"__{type_name}__": o.model_dump() }
                  
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
        Any: The decoded object, which could be a Well, FieldOfView, StageCoord, Path, tuple, or any Pydantic model.
    """
    # Look for any tagged object (e.g. __Well__, "__FieldOfView__", __StageCoord__, __Path__, __tuple__)
    for key in list(dct):
        if key.startswith("__") and key.endswith("__"):
            type_name = key.strip("__")
            data = dct[key]
            # 0) Plate
            if type_name == "Plate":
                from gem_screening.well_data.well_classes import Plate
                return Plate.from_dict(data)
            
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

            # 4) Pydantic Settings Models
            if type_name == "PipelineSettings":
                from gem_screening.settings.models import PipelineSettings
                return PipelineSettings(**data)
            
            if type_name == "LoggingSettings":
                from gem_screening.settings.models import LoggingSettings
                return LoggingSettings(**data)
            
            if type_name == "AcquisitionSettings":
                from gem_screening.settings.models import AcquisitionSettings
                return AcquisitionSettings(**data)
            
            if type_name == "DishSettings":
                from gem_screening.settings.models import DishSettings
                return DishSettings(**data)
            
            if type_name == "PresetMeasure":
                from gem_screening.settings.models import PresetMeasure
                return PresetMeasure(**data)
            
            if type_name == "PresetRefseg":
                from gem_screening.settings.models import PresetRefseg
                return PresetRefseg(**data)
            
            if type_name == "PresetControl":
                from gem_screening.settings.models import PresetControl
                return PresetControl(**data)
            
            if type_name == "PresetStim":
                from gem_screening.settings.models import PresetStim
                return PresetStim(**data)
            
            if type_name == "MeasureSettings":
                from gem_screening.settings.models import MeasureSettings
                return MeasureSettings(**data)
            
            if type_name == "ControlSettings":
                from gem_screening.settings.models import ControlSettings
                return ControlSettings(**data)
            
            if type_name == "StimSettings":
                from gem_screening.settings.models import StimSettings
                return StimSettings(**data)
            
            if type_name == "ServerSettings":
                from gem_screening.settings.models import ServerSettings
                return ServerSettings(**data)

            # 5) Path  
            if type_name == "Path":
                return Path(data["path"])

            # 6) tuple  
            if type_name == "tuple":
                return tuple(data)

    # fallback
    return dct