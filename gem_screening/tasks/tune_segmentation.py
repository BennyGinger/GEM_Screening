
import random
from typing import TypeVar
import colorsys

from numpy.typing import NDArray
import numpy as np
from a1_manager import A1Manager, StageCoord

from gem_screening.settings.models import PipelineSettings
from gem_screening.tasks.image_capture import snap_image
from gem_screening.utils.client.service import optimise_segmentation

T = TypeVar("T", bound=np.generic)

def run_tunning(dish_grid: dict[str, dict[int, StageCoord]], a1_manager: A1Manager, settings: PipelineSettings, well: str | None = None) -> tuple[NDArray[T], NDArray[T]]:
    """
    Run the segmentation tuning process for the specified well or all wells in the dish grid.
    Args:
        dish_grid (dict[str, dict[int, StageCoord]]): The dish grid containing well coordinates.
        a1_manager (A1Manager): The A1Manager instance to control the microscope hardware.
        settings (PipelineSettings): The settings for the pipeline, including acquisition settings, dish settings, and save directory.
        well (str | None): The specific well to tune. If None, the well will be chosen at random.
    Returns:
        tuple[NDArray[T], NDArray[T]]: A tuple containing the captured image and the optimized segmentation mask.
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
    img: NDArray = snap_image(coord, preset, a1_manager)
    
    # Send to server for optimisation
    mask = optimise_segmentation(img, settings.server_settings.to_backend_dict())
    
    return img, mask


##################################################################
################# Copied from cellpose.plot ######################
##################################################################
def mask_overlay(img, masks, colors=None):
    """Overlay masks on image (set image to grayscale).

    Args:
        img (int or float, 2D or 3D array): Image of size [Ly x Lx (x nchan)].
        masks (int, 2D array): Masks where 0=NO masks; 1,2,...=mask labels.
        colors (int, 2D array, optional): Size [nmasks x 3], each entry is a color in 0-255 range.

    Returns:
        RGB (uint8, 3D array): Array of masks overlaid on grayscale image.
    """
    if colors is not None:
        if colors.max() > 1:
            colors = np.float32(colors)
            colors /= 255
        colors = rgb_to_hsv(colors)
    if img.ndim > 2:
        img = img.astype(np.float32).mean(axis=-1)
    else:
        img = img.astype(np.float32)

    HSV = np.zeros((img.shape[0], img.shape[1], 3), np.float32)
    HSV[:, :, 2] = np.clip((img / 255. if img.max() > 1 else img) * 1.5, 0, 1)
    hues = np.linspace(0, 1, masks.max() + 1)[np.random.permutation(masks.max())]
    for n in range(int(masks.max())):
        ipix = (masks == n + 1).nonzero()
        if colors is None:
            HSV[ipix[0], ipix[1], 0] = hues[n]
        else:
            HSV[ipix[0], ipix[1], 0] = colors[n, 0]
        HSV[ipix[0], ipix[1], 1] = 1.0
    RGB = (hsv_to_rgb(HSV) * 255).astype(np.uint8)
    return RGB

def rgb_to_hsv(arr):
    rgb_to_hsv_channels = np.vectorize(colorsys.rgb_to_hsv)
    r, g, b = np.rollaxis(arr, axis=-1)
    h, s, v = rgb_to_hsv_channels(r, g, b)
    hsv = np.stack((h, s, v), axis=-1)
    return hsv

def hsv_to_rgb(arr):
    hsv_to_rgb_channels = np.vectorize(colorsys.hsv_to_rgb)
    h, s, v = np.rollaxis(arr, axis=-1)
    r, g, b = hsv_to_rgb_channels(h, s, v)
    rgb = np.stack((r, g, b), axis=-1)
    return rgb