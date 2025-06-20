from pathlib import Path
from typing import TypeVar

import numpy as np
from numpy.typing import NDArray
import pandas as pd

from gem_screening.tasks.data_intensity import PROCESS
from gem_screening.well_data.well_classes import FieldOfView

# a TypeVar for “any numpy scalar type”
T = TypeVar("T", bound=np.generic)


def create_stim_mask(csv_path: Path, fovs: list[FieldOfView], erosion_factor: int) -> None:
    # FIXME: Change to parquet
    data = pd.read_csv(csv_path)
    raise NotImplementedError(
        "create_stim_mask is not implemented yet. "
        "Please implement this function to create a stimulation mask.")


def _filter_labels(mask: NDArray[T], process: list[bool]) -> NDArray[T]:
    """
    Zero out any label i where process[i-1] is False.
    Args:
        mask: 2D integer array, labels in 1…n (as well as 0 for background)
        process: length-n bool list; True=>keep, False=>zero out
    """
    max_label = int(mask.max())
    if max_label > len(process):
        raise ValueError(
            f"process list too short ({len(process)}) "
            f"for max label {max_label}")
    # Build LUT of size max_label+1
    lut = np.zeros(max_label + 1, dtype=mask.dtype)
    # process[i] corresponds to label i+1, so:
    lut[1:] = np.arange(1, max_label + 1) * np.array(process, dtype=mask.dtype)
    return lut[mask]