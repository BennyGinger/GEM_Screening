from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Any

from a1_manager import StageCoord

from gem_screening.experiment._directories import setup_dir
from gem_screening.experiment.field_of_view import FieldOfView
from gem_screening.infrastructure.constants import CONFIG_FOLDER, IMG_FOLDER, MASK_FOLDER


@dataclass(slots=True)
class Well:
    """Filesystem paths, fields of view, and processing state for one well."""

    well_dir: Path
    well_grid: dict[int, StageCoord]
    well: str
    run_id: str
    img_dir: Path = field(init=False)
    mask_dir: Path = field(init=False)
    _center_fov: FieldOfView = field(init=False)
    _process_well: bool = field(default=True)
    _fov_obj_list: list[FieldOfView] = field(init=False)

    def __post_init__(self) -> None:
        self._reset_folder()
        self.img_dir = setup_dir(self.well_dir, IMG_FOLDER, self.well)
        self.mask_dir = setup_dir(self.well_dir, MASK_FOLDER, self.well)
        self._fov_obj_list, self._center_fov = self._unpack_fov()

    @property
    def center(self) -> StageCoord:
        return self._center_fov.fov_coord

    def _reset_folder(self) -> None:
        to_remove = {
            f"{self.well}_{CONFIG_FOLDER}",
            f"{self.well}_{IMG_FOLDER}",
            f"{self.well}_{MASK_FOLDER}",
        }
        for child in self.well_dir.iterdir():
            if child.name in to_remove:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()

    def _unpack_fov(self) -> tuple[list[FieldOfView], FieldOfView]:
        fovs = [
            FieldOfView(self.well_dir, coord, instance)
            for instance, coord in sorted(self.well_grid.items())
        ]
        center_fov = fovs.pop(-1)
        return fovs, center_fov

    @property
    def positive_fovs(self) -> list[FieldOfView]:
        return [fov for fov in self._fov_obj_list if fov.contain_positive_cells]

    @property
    def well_id(self) -> str:
        return f"{self.run_id}_{self.well}"

    @property
    def process_well(self) -> bool:
        return self._process_well and bool(self.positive_fovs)

    @process_well.setter
    def process_well(self, value: bool) -> None:
        self._process_well = value

    @classmethod
    def from_dict(cls: type[Well], data: dict[str, Any]) -> Well:
        if "well_grid" in data:
            data["well_grid"] = {int(key): value for key, value in data["well_grid"].items()}
        obj = object.__new__(cls)
        for key, value in data.items():
            setattr(obj, key, value)
        return obj
