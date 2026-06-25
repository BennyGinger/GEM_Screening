from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from collections import defaultdict
import re
import json
from pathlib import Path
import shutil
from typing import Any

from a1_manager import StageCoord, load_config_file, WellCircleCoord, WellSquareCoord
import numpy as np
from numpy.typing import NDArray
import tifffile as tiff

from gem_screening.utils.identifiers import parse_image_filename, parse_category_instance
from gem_screening.utils.pipeline_constants import CONFIG_FOLDER, DEFAULT_CATEGORIES, DF_FILENAME, IMG_CAT, IMG_FOLDER, MASK_FOLDER, WELL_FOLDER, OBJ_FILENAME
from gem_screening.utils.serializers import CustomJSONEncoder, custom_json_decoder




@dataclass(slots=True)
class FieldOfView:
    """
    Class to store the information of a field of view. Contains the coordinates of the field of view and all the paths to the different images and masks. Also, hold a state to know if the field of view contains positive cells or not.
    Attributes:
        well_dir (Path): Path to the well directory.
        fov_coord (StageCoord): Coordinates of the field of view.
        instance (int): Instance number of the field of view.
        contain_positive_cells (bool): Flag to indicate if the field of view contains positive cells.
        fov_id (str): ID of the field of view. Format is "<well_name>P<instance-number>".
        tiff_paths (dict[str, list[Path]]): Dictionary mapping image categories to lists of file paths for TIFF images.
    """
    well_dir: Path
    fov_coord: StageCoord
    instance: int
    contain_positive_cells: bool = True
    fov_id: str = field(init=False)
    # Images and masks files mapping
    tiff_paths: dict[str, list[Path]] = field(init=False,
                                                default_factory=lambda: defaultdict(list))
    
    def __post_init__(self)-> None:
        """
        Initialize the field of view object. This method is called after the dataclass is created to set up the fov_id and tiff_paths to always wrap the loaded dict so it regain defaultdict(list) behavior. Will preserve all previous inserted paths during reconstruction (e.g. from JSON).
        """
        self.fov_id = f"{self.well}P{self.instance}"
        self.tiff_paths = defaultdict(list, self.tiff_paths)
    
    def _bild_img_path(self, file_name: str) -> Path:
        """
        Build the file path for the image based on the file name.
        Args:
            file_name (str): Name of the file. It should be in the format `"<category>_<instance-number>"`.
        Returns:
            Path: The complete path to the file.
        Raises:
            ValueError: If the file name does not match the expected format or if the category is invalid.
        """
        cat = parse_category_instance(file_name)[0]
        if cat not in DEFAULT_CATEGORIES:
            raise ValueError(f"Invalid category '{cat}' in file name '{file_name}'. Expected one of {DEFAULT_CATEGORIES}")
        
        if cat in IMG_CAT:
            # If the category is an image category, we save it in the images folder
            return self.img_dir.joinpath(f"{self.fov_id}_{file_name}.tif")
        return self.mask_dir.joinpath(f"{self.fov_id}_{file_name}.tif")
    
    def register_img_file(self, file_name: str)-> Path:
        """
        Register an image file path to the field of view object. The file will be registered as a TIFF file in the appropriate directory based on its category.
        Args:
            file_name (str): Name of the image file. It should be in the format `"<category>_<instance-number>"`.
        Returns:
            Path: The complete path of the registered file.
        """
        file_path = self._bild_img_path(file_name)
        category = parse_image_filename(file_path)[1]
        self.tiff_paths[category].append(file_path)
        return file_path
    
    def register_existing_tiff(self, path: Path) -> None:
        """
        Register an existing TIFF file path to the field of view object. The file will be registered based on its category extracted from the file name.
        Args:
            path (Path): Path to the existing TIFF file.
        """
        category = parse_image_filename(path)[1]
        if path not in self.tiff_paths[category]:
            self.tiff_paths[category].append(path)
    
    def load_images(self, category: str) -> list[NDArray[np.uint16]]:
        """
        Load all images of a specific category for this field of view. 
        Args:
            category (str): The category of images to load. Should be one of the categories defined in `DEFAULT_CATEGORIES`.
        Returns:
            list[NDArray[np.uint16]]: List of images loaded from the TIFF files in the specified category.
        Raises:
            ValueError: If the category is not valid or if no images are found for the specified category.
        """
        if category not in DEFAULT_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Expected one of {DEFAULT_CATEGORIES}")
        return [tiff.imread(p).astype(np.uint16) for p in sorted(self.tiff_paths.get(category, []))]

    @property
    def well(self) -> str:
        """
        Get the well name.
        Returns:
            str: The well name.
        """
        return self.well_dir.name.split('_')[0]
    
    @property
    def img_dir(self) -> Path:
        """
        Get the path to the images directory of this FOV.
        """
        return self.well_dir.joinpath(f"{self.well}_{IMG_FOLDER}")

    @property
    def mask_dir(self) -> Path:
        """
        Get the path to the masks directory of this FOV.
        """
        return self.well_dir.joinpath(f"{self.well}_{MASK_FOLDER}")
    
    @classmethod
    def from_dict(cls: type[FieldOfView], data: dict) -> FieldOfView:
        """
        Create a FieldOfView object from a dictionary.
        Args:
            data (dict): Dictionary containing the field of view data.
        Returns:
            FieldOfView: The created FieldOfView object.
        """
        obj = object.__new__(cls)
        for key, value in data.items():
            setattr(obj, key, value)
        # restore defaultdict behavior, allowing to automatically create lists for new keys
        obj.tiff_paths = defaultdict(list, obj.tiff_paths)
        return obj


@dataclass(slots=True)
class Well:
    """
    Class to store the information of a well. Contains the paths to the different images and masks folders, as well as the list of field of views objects, which contains the coordinates of all field of views in the well, as well as the paths of all the image/mask files associated with each field of view.
    Attributes:
        well_dir (Path): Path to the well directory.
        well_grid (dict[int, StageCoord]): Dictionary mapping field of view instance numbers to their coordinates.
        well (str): Well name.
        run_id (str): Run ID of the experiment.
        img_dir (Path): Path to the images directory.
        mask_dir (Path): Path to the masks directory.
        positive_fovs (list[FieldOfView]): List of field of views that contain positive cells.
    """
    well_dir: Path
    well_grid: dict[int, StageCoord]
    well: str
    run_id: str
    # Filled after __post_init__
    img_dir: Path = field(init=False)
    mask_dir: Path = field(init=False)
    _center_fov: FieldOfView = field(init=False)
    _process_well: bool = field(default=True)
    _fov_obj_list: list[FieldOfView] = field(init=False)
    
    def __post_init__(self)-> None:
        """
        Initialize the well object. This method is called after the dataclass is created to set up the directories and field of view objects.
        """
        self._reset_folder()
        # Setup fresh images and masks directories.
        self.img_dir = _setup_dir(self.well_dir, IMG_FOLDER, self.well)
        self.mask_dir = _setup_dir(self.well_dir, MASK_FOLDER, self.well)

        # Unpack the field of view objects
        self._fov_obj_list, self._center_fov = self._unpack_fov()

    @property
    def center(self) -> StageCoord:
        """
        Get the center field of view of the well.
        Returns:
            FieldOfView: The center field of view object.
        """
        return self._center_fov.fov_coord
    
    def _reset_folder(self)-> None:
        """
        Remove all folders and files in the well folder.
        """
        to_remove = {
            f"{self.well}_{CONFIG_FOLDER}",
            f"{self.well}_{IMG_FOLDER}",
            f"{self.well}_{MASK_FOLDER}",}
        
        for child in self.well_dir.iterdir():
            # Skip if not the right folder or csv file
            if child.name in to_remove:
                # Remove the images and masks folders
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
    
    def _unpack_fov(self)-> tuple[list[FieldOfView], FieldOfView]:
        """
        Unpack the field of view objects from the well grid.
        """
        list_fov = [FieldOfView(self.well_dir, coord, i) for i, coord in sorted(self.well_grid.items())]
        center_fov = list_fov.pop(-1)
        return list_fov, center_fov
    
    @property
    def positive_fovs(self)-> list[FieldOfView]:
        """
        Get the list of field of views that contain positive cells.
        """
        return [fov for fov in self._fov_obj_list if fov.contain_positive_cells]
    
    @property
    def well_id(self)-> str:
        """
        Construct the well ID from the run ID and well name.
        Returns:
            str: The well ID in the format "<run_id>_<well_name>".
        """
        return f"{self.run_id}_{self.well}"
    
    @property
    def process_well(self) -> bool:
        """
        Returns True if the well should be processed (user flag True and positive FOVs). False otherwise.
        """
        return self._process_well and bool(self.positive_fovs)
    
    @process_well.setter
    def process_well(self, value: bool) -> None:
        """
        Set the user flag to process the well.
        Args:
            value (bool): True to process the well, False otherwise.
        """
        self._process_well = value
    
    @classmethod
    def from_dict(cls: type[Well], data: dict[str, Any]) -> Well:
        """
        Reconstruct a Well from its serialized dict, replaying the same
        initialization logic so that all folders, CSV path, and FOVs are set up.
        """
        # Convert well_grid keys from string to int (JSON serialization converts int keys to strings)
        if "well_grid" in data:
            data["well_grid"] = {int(k): v for k, v in data["well_grid"].items()}
        
        obj = object.__new__(cls)
        for key, value in data.items():
            setattr(obj, key, value)
        return obj


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
        well_dir = _setup_dir(self.run_dir, WELL_FOLDER)
        # build the well_list
        for well, well_grid in self.dish_grid.items():
            well_obj = Well(well_dir=_setup_dir(well_dir, well),
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
        
def _setup_dir(root_path: Path, new_dir_name: str, prefix: str | None = None) -> Path:
    """
    Setup new directory.
    Args:
        root_path (Path): Path to the root directory where the well folder will be created.
        new_dir_name (str): Name of the new directory to be created.
        prefix (str | None): Optional prefix to add before the new directory name. For example, the well name.
    Returns:
        Path: The path to the newly created directory.
    """
    fprefix = f"{prefix}_" if prefix is not None else ""
    new_dir = root_path.joinpath(f"{fprefix}{new_dir_name}")
    new_dir.mkdir(parents=True, exist_ok=True)
    return new_dir