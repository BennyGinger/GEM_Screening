from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from a1_manager import StageCoord
import numpy as np
from numpy.typing import NDArray
import tifffile as tiff

from gem_screening.infrastructure.constants import (
    DEFAULT_CATEGORIES,
    IMG_CAT,
    IMG_FOLDER,
    MASK_FOLDER,
)
from gem_screening.infrastructure.identifiers import (
    parse_category_instance,
    parse_image_filename,
)


@dataclass(slots=True)
class FieldOfView:
    """Coordinates, image paths, and processing state for one field of view."""

    well_dir: Path
    fov_coord: StageCoord
    instance: int
    contain_positive_cells: bool = True
    fov_id: str = field(init=False)
    tiff_paths: dict[str, list[Path]] = field(
        init=False, default_factory=lambda: defaultdict(list)
    )

    def __post_init__(self) -> None:
        self.fov_id = f"{self.well}P{self.instance}"
        self.tiff_paths = defaultdict(list, self.tiff_paths)

    def _bild_img_path(self, file_name: str) -> Path:
        cat = parse_category_instance(file_name)[0]
        if cat not in DEFAULT_CATEGORIES:
            raise ValueError(
                f"Invalid category '{cat}' in file name '{file_name}'. "
                f"Expected one of {DEFAULT_CATEGORIES}"
            )
        if cat in IMG_CAT:
            return self.img_dir / f"{self.fov_id}_{file_name}.tif"
        return self.mask_dir / f"{self.fov_id}_{file_name}.tif"

    def register_img_file(self, file_name: str) -> Path:
        file_path = self._bild_img_path(file_name)
        category = parse_image_filename(file_path)[1]
        self.tiff_paths[category].append(file_path)
        return file_path

    def register_existing_tiff(self, path: Path) -> None:
        category = parse_image_filename(path)[1]
        if path not in self.tiff_paths[category]:
            self.tiff_paths[category].append(path)

    def load_images(self, category: str) -> list[NDArray[np.uint16]]:
        if category not in DEFAULT_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. Expected one of {DEFAULT_CATEGORIES}"
            )
        return [
            tiff.imread(path).astype(np.uint16)
            for path in sorted(self.tiff_paths.get(category, []))
        ]

    @property
    def well(self) -> str:
        return self.well_dir.name.split("_")[0]

    @property
    def img_dir(self) -> Path:
        return self.well_dir / f"{self.well}_{IMG_FOLDER}"

    @property
    def mask_dir(self) -> Path:
        return self.well_dir / f"{self.well}_{MASK_FOLDER}"

    @classmethod
    def from_dict(cls: type[FieldOfView], data: dict) -> FieldOfView:
        obj = object.__new__(cls)
        for key, value in data.items():
            setattr(obj, key, value)
        obj.tiff_paths = defaultdict(list, obj.tiff_paths)
        return obj
