from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from a1_manager import StageCoord, WellCircleCoord, WellSquareCoord, load_config_file

from gem_screening.experiment._directories import setup_dir
from gem_screening.experiment.field_of_view import FieldOfView
from gem_screening.experiment.well import Well
from gem_screening.infrastructure.constants import (
    CONFIG_FOLDER,
    DF_FILENAME,
    OBJ_FILENAME,
    WELL_FOLDER,
)
from gem_screening.infrastructure.serialization import CustomJSONEncoder, custom_json_decoder


@dataclass(slots=True)
class Plate:
    """
    Class to store the information of a plate. Contains the paths to the different wells and a list of well objects.
    Attributes:
        run_dir (Path): Path to the run directory.
        run_id (str): Run ID of the experiment.
        dish_grid (dict[str, dict[int, StageCoord]]): Dictionary mapping well names to their field of view grids.
        csv_path (Path): Path to the CSV file containing cell data
        well_list (list[Well]): List of well objects contained in the plate.
    """
    run_dir: Path
    run_id: str
    dish_grid: dict[str, dict[int, StageCoord]]
    csv_path: Path = field(init=False)
    _well_list: list[Well] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """
        Initialize the plate object. This method is called after the dataclass is created to set up the CSV path.
        """
        # Create a Well folder
        well_dir = setup_dir(self.run_dir, WELL_FOLDER)
        # build the well_list
        for well, well_grid in self.dish_grid.items():
            well_obj = Well(well_dir=setup_dir(well_dir, well),
                            well_grid=well_grid,
                            well=well,
                            run_id=self.run_id)
            self._well_list.append(well_obj)

        # Set up the CSV path
        self.csv_path = self.run_dir.joinpath(f"{DF_FILENAME}")
        if self.csv_path.exists():
            self.csv_path.unlink()
        
        self.to_json()
    
    @property
    def well_list(self) -> list[Well]:
        """
        Get all wells that contain positive FOVs, sorted in snake order for minimal stage movement.
        Returns:
            list[Well]: List of all Well objects that contain positive FOVs, sorted by stage position.
        """
        wells = [w for w in self._well_list if w.process_well]
        return self._snake_sort_wells(wells)
    
    @property
    def positive_fovs(self) -> list[FieldOfView]:
        """
        Get all positive FOVs across all wells in the plate.
        Returns:
            list[FieldOfView]: List of all positive FieldOfView objects in the plate.
        """
        pos_fovs = []
        for well in self.well_list:
            pos_fovs.extend(well.positive_fovs)
        return pos_fovs

    @property
    def wells(self) -> list[str]:
        """
        Get a list of all well names in the plate.
        Returns:
            list[str]: List of all well names in the plate.
        """
        return [w.well for w in self.well_list]

    @property
    def mask_dirs(self) -> list[Path]:
        """
        Get a list of all mask directories across all wells in the plate.
        Returns:
            list[Path]: List of all mask directory paths in the plate.
        """
        return [w.mask_dir for w in self.well_list]
    
    @property
    def plate_obj_path(self)-> Path:
        return self.run_dir.joinpath(CONFIG_FOLDER, f"{self.run_id}_{OBJ_FILENAME}")
    
    def select_wells(self, well_names: list[str]) -> None:
        """
        Select wells to process based on a list of well names. Only wells with names in the provided list will be marked for processing.
        Args:
            well_names (list[str]): List of well names to select for processing.
        """
        for well in self._well_list:
            well.process_well = True if well.well in well_names else False
    
    def well_sublists(self, grouping_method: str = 'col') -> list[list[Well]]:
        """
        Create sublists of wells grouped by column or row.
        Args:
            grouping_method (str): The type of grouping for the wells (e.g., 'row', 'col', 'well').
        Returns:
            list[list[Well]]: Sublists of Well objects grouped accordingly.
        """
        if grouping_method not in ('col', 'row', 'well', 'all'):
            raise ValueError("list_type must be 'col', 'row', 'well', or 'all'")

        # If 'all', return the entire well list as a single sublist
        if grouping_method == 'all':
            return [self.well_list]
        
        if grouping_method == 'well':
            # Each well in its own sublist
            return [[well] for well in self.well_list]
        
        groups = defaultdict(list)
        for well in self._well_list:
            match = re.match(r"([A-Za-z]+)([0-9]+)", well.well)
            if not match:
                continue
            row, col = match.groups()
            key = col if grouping_method == 'col' else row.upper()
            groups[key].append(well)
        # Sort groups by key (col as int, row as letter)
        if grouping_method == 'col':
            sorted_keys = sorted(groups.keys(), key=lambda x: int(x))
        else:
            sorted_keys = sorted(groups.keys())
        return [groups[k] for k in sorted_keys]
    
    def mask_dir_glob(self, pattern: str) -> list[Path]:
        """
        Get a list of all mask files across all wells in the plate.
        Returns:
            list[Path]: List of all mask file paths in the plate.
        """
        mask_files = []
        for well in self.well_list:
            mask_files.extend(well.mask_dir.glob(pattern))
        return mask_files

    def to_json(self) -> None:
        """
        Save the wells object to a JSON file.
        """
        if self.plate_obj_path.exists():
            # Load the existing plate object to extend the wells
            with open(self.plate_obj_path, 'r') as fp:
                old_data = json.load(fp, object_hook=custom_json_decoder)
            if isinstance(old_data, Plate):
                old_plate = old_data
            elif isinstance(old_data, dict):
                old_plate = Plate.from_dict(old_data)
            else:
                raise ValueError("Invalid data in plate JSON file.")
            
            # Extend the wells and dish grid
            self._extend_wells(old_plate.well_list)
            self.dish_grid.update(old_plate.dish_grid)
        
        # Save the plate object to a JSON file
        with open(self.plate_obj_path, 'w') as fp:
            json.dump(self, fp, cls=CustomJSONEncoder, indent=2)
    
    @classmethod
    def from_dict(cls: type[Plate], data: dict[str, Any]) -> Plate:
        """
        Reconstruct a Plate from its serialized dict, replaying the same
        initialization logic so that all folders, CSV path, and FOVs are set up.
        """
        obj = object.__new__(cls)
        for key, value in data.items():
            setattr(obj, key, value)
        # Optionally restore computed fields
        if not hasattr(obj, "csv_path") or obj.csv_path is None:
            obj.csv_path = obj.run_dir.joinpath(f"{DF_FILENAME}")
        return obj
    
    @classmethod
    def from_json(cls: type["Plate"], file_path: Path) -> "Plate":
        """
        Load a Plate object from a JSON file.
        """
        with open(file_path, 'r') as f:
            data = json.load(f, object_hook=custom_json_decoder)
        return data if isinstance(data, Plate) else cls.from_dict(data)
    
    def _extend_wells(self, new_wells: list[Well]) -> None:
        """
        Extend the well_list with only new wells (no duplicates by well_id).
        """
        existing_ids = {w.well_id for w in self.well_list}
        for well in new_wells:
            if well.well_id not in existing_ids:
                self.well_list.append(well)
                existing_ids.add(well.well_id)
        self.well_list.sort(key=lambda w: w.well)  # sort by well name
    
    def _snake_sort_wells(self, wells: list[Well]) -> list[Well]:
        """
        Sort wells in a snake pattern to minimize stage movement.
        Uses calibration data for accurate well centers, falls back to FOV coordinates if unavailable.
        
        Snake pattern:
        Row 1: A1 → A2 → A3 → A4 (left to right, x decreasing)
        Row 2: B4 ← B3 ← B2 ← B1 (right to left, x increasing)  
        Row 3: C1 → C2 → C3 → C4 (left to right, x decreasing)
        """
        if not wells:
            return wells
        
        # Try to get well centers from calibration file
        well_centers = self._get_well_centers_from_calibration()
        
        # Get wells with their coordinates
        wells_with_coords = []
        for well in wells:
            if well_centers and well.well in well_centers:
                # Use calibration data for accurate center
                calib_coord = well_centers[well.well]
                if hasattr(calib_coord, 'center') and calib_coord.center is not None:
                    wells_with_coords.append((well, calib_coord.center))
                else:
                    wells_with_coords.append((well, (float('inf'), float('inf'))))
            elif well.positive_fovs:
                # Fallback to first positive FOV coordinate
                coord = well.positive_fovs[0].fov_coord.xy
                if coord is not None:
                    wells_with_coords.append((well, coord))
                else:
                    wells_with_coords.append((well, (float('inf'), float('inf'))))
            else:
                wells_with_coords.append((well, (float('inf'), float('inf'))))
        
        # Sort by y coordinate (rows) - increasing y means top to bottom
        wells_with_coords.sort(key=lambda item: item[1][1])
        
        # Group by y coordinate (rows) with some tolerance for floating point differences
        tolerance = 1000  # 1000 microns tolerance for grouping wells in same row
        rows = []
        current_row = []
        current_y = None
        
        for well, coord in wells_with_coords:
            if current_y is None or abs(coord[1] - current_y) <= tolerance:
                current_row.append((well, coord))
                current_y = coord[1] if current_y is None else current_y
            else:
                if current_row:
                    rows.append(current_row)
                current_row = [(well, coord)]
                current_y = coord[1]
        
        if current_row:  # Don't forget the last row
            rows.append(current_row)
        
        # Sort each row alternating direction (snake pattern)
        sorted_wells = []
        for i, row in enumerate(rows):
            if i % 2 == 0:
                # Even rows (0, 2, 4...): left to right (x decreasing, so reverse=True)
                row_sorted = sorted(row, key=lambda item: item[1][0], reverse=True)
            else:
                # Odd rows (1, 3, 5...): right to left (x increasing, so reverse=False)  
                row_sorted = sorted(row, key=lambda item: item[1][0], reverse=False)
            
            sorted_wells.extend([well for well, _ in row_sorted])
        
        return sorted_wells

    def _get_well_centers_from_calibration(self) -> dict[str, WellCircleCoord | WellSquareCoord] | None:
        """
        Load well centers from calibration file if available.
        
        Returns:
            dict mapping well names to coordinate objects, or None if not available
        """
        # Look for calibration file in config directory
        config_dir = self.run_dir / CONFIG_FOLDER
        if not config_dir.exists():
            return None
        
        # Try common calibration file names
        calib_files = [
            "calib_35mm.json",
            "calib_96well.json",
            'calib_384well.json',
        ]
        
        for calib_name in calib_files:
            calib_path = config_dir / calib_name
            if calib_path.exists():
                try:
                    return load_config_file(calib_path)
                except Exception:
                    continue
        
        return None
    
    
    def __len__(self) -> int:
        """
        Return the number of wells in the plate.
        """
        return len(self.well_list)
