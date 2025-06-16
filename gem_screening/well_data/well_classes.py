from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
import json
from pathlib import Path
import shutil

from a1_manager import StageCoord
import numpy as np
import tifffile as tiff

from gem_screening.utils.identifiers import parse_image_filename, parse_category_instance
from gem_screening.utils.serializers import CustomJSONEncoder, custom_decoder


IMG_FOLDER = "images"
MASK_FOLDER = "masks"
IMG_CAT = ['measure', 'refseg', 'control']
MASK_CAT = ['mask', 'stim']
DEFAULT_CATEGORIES = IMG_CAT + MASK_CAT


@dataclass(slots=True)
class FieldOfView:
    """
    Class to store the information of a field of view. Contains the coordinates of the field of view and all the paths to the different images and masks. Also, hold a state to know if the field of view contains positive cells or not.
    Attributes:
        well_dir (Path): Path to the well directory.
        fov_coord (StageCoord): Coordinates of the field of view.
        instance (int): Instance number of the field of view.
        contain_positive_cell (bool): Flag to indicate if the field of view contains positive cells.
        fov_ID (str): ID of the field of view. Format is "<well_name>P<instance-number>".
        images_path (dict[str, Path]): Dictionary mapping image file names to their paths.
        masks_path (dict[str, Path]): Dictionary mapping mask file names to their paths.
    """
    well_dir: Path
    fov_coord: StageCoord
    instance: int
    contain_positive_cell: bool = True
    fov_id: str = field(init=False)
    # Images and masks files mapping
    tiff_paths: dict[str, list[Path]] = field(init=False,
                                                default_factory=lambda: defaultdict(list))
    
    def __post_init__(self)-> None:
        self.fov_id = f"{self.well}P{self.instance}"
    
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
        if cat not in IMG_CAT:
            raise ValueError(f"Invalid category '{cat}' in file name '{file_name}'. Expected one of {IMG_CAT}")
        
        return self.img_dir.joinpath(f"{self.fov_id}_{file_name}.tif")
    
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
        self.tiff_paths[category].append(path)
    
    def load_images(self, category: str) -> list[np.ndarray]:
        """
        Load all images of a specific category for this field of view. 
        Args:
            category (str): The category of images to load. Should be one of the categories defined in `DEFAULT_CATEGORIES`.
        Returns:
            list[np.ndarray]: List of images loaded from the TIFF files in the specified category.
        Raises:
            ValueError: If the category is not valid or if no images are found for the specified category.
        """
        if category not in DEFAULT_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Expected one of {DEFAULT_CATEGORIES}")
        return [tiff.imread(p) for p in sorted(self.tiff_paths.get(category, []))]

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
        return self.well_dir.joinpath(IMG_FOLDER)

    @property
    def mask_dir(self) -> Path:
        """
        Get the path to the masks directory of this FOV.
        """
        return self.well_dir.joinpath(MASK_FOLDER)
    
    @classmethod
    def from_dict(cls: "FieldOfView", data: dict) -> "FieldOfView":
        """
        Create a FieldOfView object from a dictionary.
        Args:
            data (dict): Dictionary containing the field of view data.
        Returns:
            FieldOfView: The created FieldOfView object.
        """
        # exactly the same “bypass __init__” logic as you had in from_json
        obj = object.__new__(cls)
        obj.__dict__.update(data)
        # recompute the ID, just in case it was not set
        obj.fov_ID = f"{obj.well}P{obj.instance}"
        # always wrap the loaded dict so we regain defaultdict(list) behavior. Will preserve all previous inserted paths.
        obj.tiff_paths = defaultdict(list, obj.tiff_paths)
        return obj

   
@dataclass(slots=True)
class Well:
    """
    Class to store the information of a well. Contains the paths to the different images and masks folders, as well as the list of field of views objects, which contains the coordinates of all field of views in the well, as well as the paths of all the image/mask files associated with each field of view.
    Attributes:
        run_dir (Path): Path to the main run directory.
        run_id (str): Unique identifier for the run, composed of the hostname and an uuid.
        well_grid (dict[int, StageCoord]): Dictionary mapping field of view instance numbers to their coordinates.
        well (str): Well name.
        well_dir (Path): Path to the well directory.
        config_dir (Path): Path to the configuration directory.
        img_dir (Path): Path to the images directory.
        mask_dir (Path): Path to the masks directory.
        csv_path (Path): Path to the CSV file containing cell data.
        positive_fovs (list[FieldOfView]): List of FieldOfView objects associated with the well.
        well_obj_path (Path): Path to the JSON file where the well object is saved.
    """
    run_dir: Path
    run_id: str
    well_grid: dict[int, StageCoord]
    well: str
    well_dir: Path = field(init=False)
    config_dir: Path = field(init=False)
    img_dir: Path = field(init=False)
    mask_dir: Path = field(init=False)
    csv_path: Path = field(init=False)
    _fov_obj_list: list[FieldOfView] = field(init=False)
    
    def __post_init__(self)-> None:
        # Setup the main well directory
        self.well_dir = self._setup_dir(self.run_dir, 'Well')
        self._reset_folder()
        # Setup the configuration directory.
        self.config_dir = self._setup_dir(self.well_dir, 'config')
        # Setup fresh images and masks directories.
        self.img_dir = self._setup_dir(self.well_dir, 'images')
        self.mask_dir = self._setup_dir(self.well_dir, 'masks')
        # Setup the CSV file path for cell data.
        self.csv_path = self.well_dir.joinpath(f"{self.well}_cell_data.csv")
        
        # Unpack the field of view objects
        self._fov_obj_list = self._unpack_fov()
            
        # Save the well object to a JSON file
        self.to_json()

    def _setup_dir(self, root_path: Path, new_dir_name: str) -> Path:
        """
        Setup new directory.
        Args:
            root_path (Path): Path to the root directory where the well folder will be created.
            new_dir_name (str): Name of the new directory to be created.
        """
        new_dir = root_path.joinpath(f"{self.well}_{new_dir_name}")
        new_dir.mkdir(parents=True, exist_ok=True)
        return new_dir
        
    def _reset_folder(self)-> None:
        """
        Remove all folders and files in the well folder.
        """
        to_remove = {
            f"{self.well}_config",
            f"{self.well}_images",
            f"{self.well}_masks",
            f"{self.well}_cell_data.csv",}
        
        for child in self.well_dir.iterdir():
            # Skip if not the right folder or csv file
            if child.name in to_remove:
                # Remove the images and masks folders
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
    
    def _unpack_fov(self)-> list[FieldOfView]:
        """
        Unpack the field of view objects from the well grid.
        """
        return [FieldOfView(self.well_dir, coord, i) for i, coord in sorted(self.well_grid.items())]
    
    @property
    def positive_fovs(self)-> list[FieldOfView]:
        """
        Get the list of field of views that contain positive cells.
        """
        return [fov for fov in self._fov_obj_list if fov.contain_positive_cell]
    
    @property
    def well_obj_path(self)-> Path:
        return self.config_dir.joinpath(f"{self.well}_obj.json")
    
    def to_json(self)-> None:
        """
        Save the well object to a JSON file.
        """
        with open(self.well_obj_path, 'w') as fp:
            json.dump(self, fp, cls=CustomJSONEncoder, indent=2)
    
    @classmethod
    def from_json(cls: 'Well', file_path: Path)-> 'Well':
        """
        Load a well object from a JSON file.
        Args:
            file_path (Path): Path to the JSON file.
        Returns:
            Well: The loaded well object.
        """
        # Read the raw dist
        with open(file_path, 'r') as f:
            data: dict = json.loads(f.read(), object_hook=custom_decoder)
        # Re-convert the well_grid keys to int
        data["well_grid"] = {int(k): v for k,v in data["well_grid"].items()}
        
        # Bypass the __init__ and __post_init__ methods
        obj = object.__new__(cls)
        obj.__dict__.update(data)
        return obj
    


