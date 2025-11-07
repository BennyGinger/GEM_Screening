
import random

from numpy.typing import NDArray
from a1_manager import A1Manager, StageCoord

from gem_screening.settings.models import PipelineSettings
from gem_screening.tasks.image_capture import snap_image


class ImageCollector:
    """ 
    Class to collect images from a dish grid for segmentation tuning.
    It keeps track of the history of coordinates already imaged to avoid duplicates."""
    def __init__(self, dish_grid: dict[str, dict[int, StageCoord]], a1_manager: A1Manager, settings: PipelineSettings, well: str | None = None):
        
        # Store history as dict: {'P3F4': StageCoord} to preserve order and prevent duplicates
        self.history: dict[str, StageCoord] = {}
        
        self.dish_grid = dish_grid
        self.get_well(well)
        
        self.a1_manager = a1_manager
        self.preset = settings.measure_settings.preset_refseg if settings.measure_settings.do_refseg else settings.measure_settings.preset_measure
        
        self.well_coords = list(dish_grid[self.well].values())
    
    def get_well(self, well: str | None) -> None:
        if well is None:
            well = random.choice(list(self.dish_grid.keys()))
        
        self.well = well
        self.well_coords = list(self.dish_grid[self.well].values())
    
    def get_image(self, coord: StageCoord | None = None) -> NDArray:
        if coord is None:
            coord = random.choice(self.well_coords)
            self.well_coords.remove(coord)
        
        # Find the instance number for this coordinate in the current well
        instance = None
        for inst, stored_coord in self.dish_grid[self.well].items():
            if stored_coord == coord:
                instance = inst
                break
        
        # Use a fallback instance number if lookup fails
        if instance is None:
            # If we can't find the exact match, use the next available instance number
            instance = len(self.history) + 1
        
        # Create the FOV ID as key: 'P3F4' format
        fov_id = f"P{instance}{self.well}"
        
        # Add to history dict (preserving insertion order, preventing duplicates)
        self.history[fov_id] = coord
        
        return snap_image(coord, self.preset, self.a1_manager)