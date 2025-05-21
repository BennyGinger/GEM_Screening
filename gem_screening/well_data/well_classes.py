from __future__ import annotations
from dataclasses import dataclass, field
import json
from pathlib import Path
import shutil
from typing import Optional

from a1_manager import StageCoord

from gem_screening.utils.serializers import CustomJSONEncoder, custom_decoder


@dataclass(slots=True)
class FieldOfView:
    """
    Class to store the information of a field of view. Contains the coordinates of the field of view and all the paths to the different images and masks. Also, hold a state to know if the field of view contains positive cells or not.
    Attributes:
        fov_coord (StageCoord): Coordinates of the field of view.
        well (str): Well name.
        instance (int): Instance number of the field of view.
        contain_positive_cell (bool): Flag to indicate if the field of view contains positive cells.
        fov_ID (str): ID of the field of view.
        images_path (dict[str, Path]): Dictionary mapping image file names to their paths.
        masks_path (dict[str, Path]): Dictionary mapping mask file names to their paths.
    """
    fov_coord: StageCoord
    well: str
    instance: int
    contain_positive_cell: bool = True
    fov_ID: str = field(init=False)
    # Images files mapping: file name -> path
    images_path: dict[str, Path] = field(default_factory=dict)
    masks_path: dict[str, Path] = field(default_factory=dict)
    
    def __post_init__(self)-> None:
        self.fov_ID = f"{self.well}_P{self.instance}"
    
    def add_image(self, img_name: str, img_path: Path)-> None:
        """
        Add an image path to the field of view.
        Args:
            img_name (str): Name of the image file.
            img_path (Path): Path to the image file.
        """
        self.images_path[img_name] = img_path
    
    def add_mask(self, mask_name: str, mask_path: Path)-> None:
        """
        Add a mask path to the field of view.
        Args:
            mask_name (str): Name of the mask file.
            mask_path (Path): Path to the mask file.
        """
        self.masks_path[mask_name] = mask_path
    
    def get_image_path(self, img_name: str)-> Optional[Path]:
        """
        Get the path of an image file.
        Args:
            img_name (str): Name of the image file.
        """
        return self.images_path.get(img_name, None)
    
    def get_mask_path(self, mask_name: str)-> Optional[Path]:
        """
        Get the path of a mask file.
        Args:
            mask_name (str): Name of the mask file.
        """
        return self.masks_path.get(mask_name, None)

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
        # recompute the ID if it wasn’t in the payload
        if "fov_ID" not in data:
            obj.fov_ID = f"{obj.well}_P{obj.instance}"
        return obj

   
@dataclass(slots=True)
class Well:
    """
    Class to store the information of a well. Contains the paths to the different images and masks folders, as well as the list of field of views objects, which contains the coordinates of all field of views in the well, as well as the paths of all the image/mask files associated with each field of view.
    Attributes:
        run_dir (Path): Path to the main run directory.
        well_grid (dict[int, StageCoord]): Dictionary mapping field of view instance numbers to their coordinates.
        well (str): Well name.
        well_dir (Path): Path to the well directory.
        config_dir (Path): Path to the configuration directory.
        img_dir (Path): Path to the images directory.
        mask_dir (Path): Path to the masks directory.
        csv_path (Path): Path to the CSV file containing cell data.
        fov_obj_list (list[FieldOfView]): List of FieldOfView objects associated with the well.
    """
    run_dir: Path
    well_grid: dict[int, StageCoord]
    well: str
    well_dir: Path = field(init=False)
    config_dir: Path = field(init=False)
    img_dir: Path = field(init=False)
    mask_dir: Path = field(init=False)
    csv_path: Path = field(init=False)
    fov_obj_list: list[FieldOfView] = field(init=False)
    
    def __post_init__(self)-> None:
        # Setup the main well directory
        self.well_dir = self.run_dir.joinpath(f"{self.well}_Well")
        self.well_dir.mkdir(parents=True, exist_ok=True)
        self._reset_folder()
        
        # Setup fresh images and masks directories.
        self.config_dir = self.well_dir.joinpath(f"{self.well}_config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.img_dir = self.well_dir.joinpath(f"{self.well}_images")
        self.img_dir.mkdir(parents=True, exist_ok=True)
        self.mask_dir = self.well_dir.joinpath(f"{self.well}_masks")
        self.mask_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.well_dir.joinpath(f"{self.well}_cell_data.csv")
        
        # Unpack the field of view objects
        self.fov_obj_list = self._unpack_fov()
            
        # Save the well object to a JSON file
        self.to_json()
        
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
        return [FieldOfView(coord, self.well, i) for i, coord in sorted(self.well_grid.items())]
    
    @property
    def positive_fovs(self)-> list[FieldOfView]:
        """
        Get the list of field of views that contain positive cells.
        """
        return [fov for fov in self.fov_obj_list if fov.contain_positive_cell]
    
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
    


