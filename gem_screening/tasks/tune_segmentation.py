
import random
from typing import TypeVar
import colorsys

from numpy.typing import NDArray
import numpy as np
from a1_manager import A1Manager, StageCoord

from gem_screening.settings.models import PipelineSettings
from gem_screening.tasks.image_capture import snap_image

T = TypeVar("T", bound=np.generic)

def generate_random_image(dish_grid: dict[str, dict[int, StageCoord]], a1_manager: A1Manager, settings: PipelineSettings, well: str | None = None) -> NDArray:
    """
    Generate a random image from the dish grid for segmentation tuning.
    Args:
        dish_grid (dict[str, dict[int, StageCoord]]): The dish grid containing well coordinates.
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
        well (str | None): The specific well to tune. If None, the well will be chosen at random.
    Returns:
        NDArray: The captured image used for segmentation tuning.
    """
    # Choose a well at random if not specified
    if well is None:
        well = random.choice(list(dish_grid.keys()))

    # Get the presets
    preset = settings.measure_settings.preset_refseg if settings.measure_settings.do_refseg else settings.measure_settings.preset_measure
    
    # Get random coordinates from the well
    well_coords = list(dish_grid[well].values())
    coord = random.choice(well_coords)
    
    # snap image
    return snap_image(coord, preset, a1_manager)

class ImageCollector:
    """ 
    Class to collect images from a dish grid for segmentation tuning.
    It keeps track of the history of coordinates already imaged to avoid duplicates."""
    def __init__(self, dish_grid: dict[str, dict[int, StageCoord]], a1_manager: A1Manager, settings: PipelineSettings, well: str | None = None):
        
        self.history: set[StageCoord] = set()
        
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
        
        self.history.add(coord)
        return snap_image(coord, self.preset, self.a1_manager)