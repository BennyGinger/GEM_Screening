from __future__ import annotations
from dataclasses import dataclass, field
import json
from os import sep
from threading import Lock

from pathlib import Path
import numpy as np
import pandas as pd
import cv2
from tifffile import imread, imwrite
from skimage.morphology import disk
# TODO: Remove cellpose from here
from cellpose import models
from cellpose.utils import stitch3D

from microscope_software.aquisition import Aquisition
from utils.utils import create_savedir, get_centroid, apply_background_correction, progress_bar, run_multithread


# Custom JSON Encoder
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: object)-> object:
        if isinstance(obj, Well):
            return obj.__dict__
        
        if isinstance(obj, FieldOfView):
            return obj.__dict__ 
        
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)

# Custom Decoder Function
def custom_decoder(dct: dict)-> dict:
    for key, value in dct.items():
        if isinstance(value, str) and value.__contains__(sep):
            dct[key] = Path(value)
        if isinstance(value, list) and isinstance(value[0], dict):
            value = [custom_decoder(fov) for fov in value]
            dct[key] = [FieldOfView.from_json(fov) for fov in value]
    return dct


@dataclass 
class Well():
    well: str
    well_dir: Path = field(default_factory=Path)
    img_dir: Path = field(default_factory=Path)
    mask_dir: Path = field(default_factory=Path)
    csv_path: Path = field(default_factory=Path)
    fov_obj_list: list['FieldOfView'] = field(default_factory=list)
    size: int = field(default_factory=int)
    
    def create_dirs(self, well_dir: Path)-> None:
        # Create directories
        self.well_dir = well_dir
        self.img_dir = create_savedir(self.well_dir,f"{self.well}_images")
        self.mask_dir = create_savedir(self.well_dir,f"{self.well}_masks")
        self.csv_path = self.well_dir.joinpath(f"{self.well}_cell_data.csv")
        
    def create_list_fov(self, well_grid: dict[int,dict])-> None:
        for i, fov_coord in enumerate(well_grid.values()):
            self.fov_obj_list.append(FieldOfView(fov_coord, well=self.well, instance=i+1))
        self.size = len(self.fov_obj_list)

    def image_all_fov(self, aquisition: Aquisition, settings: dict, imaging_loop: str)-> None:
        print(f"\nStart imaging for loop {imaging_loop}")
        
        refseg: bool = settings['refseg']
        # Settup imaging preset
        if imaging_loop.__contains__('measure'):
            input_preset = settings['preset_measure']
            
        elif imaging_loop.__contains__('control'):
            input_preset = settings['preset_control']
            refseg = False
        
        if refseg:
            input_preset_refseg = settings['preset_refseg']
            imaging_loop_refseg = f"refseg_{imaging_loop.split('_')[-1]}"
        

        # Filter fov that contain positive cell
        fov_lst = [fov for fov in self.fov_obj_list if fov.contain_poisitive_cell]
        
        # Go trhough all positive fov
        for fov_obj in progress_bar(fov_lst,
                            desc=f"Imaging {imaging_loop}",
                            total=len(fov_lst)):
            fov_obj.take_image_fov(aquisition,input_preset,self.img_dir,imaging_loop)
            if refseg:
                fov_obj.take_image_fov(aquisition,input_preset_refseg,self.img_dir,imaging_loop_refseg)
    
    def segment_all_fov(self, settings: dict)-> None:
        print("\nStart segmentation")
        # Initalise cellpose model
        model = models.CellposeModel(gpu=True,model_type='cyto2')
        for fov_obj in progress_bar(self.fov_obj_list,
                            desc="Segmenting field of view",
                            total=self.size):
            if settings['refseg']:
                fov_obj.segment_fov_refseg(model,settings,self.mask_dir)
                continue
            fov_obj.segment_fov(model,settings,self.mask_dir)
    
    def track_all_fov(self)-> None:
        print("\nStart tracking")
        
        for fov_obj in progress_bar(self.fov_obj_list,
                            desc="Tracking field of view",
                            total=self.size):
            fov_obj.track_fov()
    
    def extract_measure_ratio(self, settings: dict)-> pd.DataFrame: 
        print("\nStart extracting cell ratio")
        if settings['refseg']:
            dfs = run_multithread('get_measure_ratio_refseg',self.fov_obj_list,"measure_ratio",refseg_threshold=settings['refseg_threshold'])
        else:
            dfs = run_multithread('get_measure_ratio',self.fov_obj_list,"measure_ratio")
        
        cell_data_df = pd.concat(dfs)
        cell_data_df.to_csv(self.csv_path)
        return cell_data_df
    
    @staticmethod
    def update_cell_data(cell_data_path: Path, threshold: float, upper_threshold: float)-> pd.DataFrame:
        cell_data_df = pd.read_csv(cell_data_path)
        ratios = cell_data_df['ratio'].to_numpy()
        ratios_bool = (ratios >= threshold) & (ratios <= upper_threshold)
        cell_data_df[f'{threshold}<x<{upper_threshold}'] = ratios_bool
        return cell_data_df

    def create_all_stimmask(self, erosion_factor: int)-> None:
        # Load cell data and update it
        cell_data_df = pd.read_csv(self.csv_path)
        
        print("\nStart creating stimmask")
        run_multithread('create_stimmask',
                        self.fov_obj_list,
                        "stimmask",
                        cell_data_df=cell_data_df,
                        erosion_factor=erosion_factor,
                        lock=Lock())
         
    def stimulate_all_fov(self, aquisition: Aquisition, settings: dict)-> None:
        print("\nStart light stimulation")
        # Set lamp settings
        lamp_settings = {k:v for k,v in settings['preset_stim'].items() if k in ['optical_configuration','intensity']}
        aquisition.oc_settings(**lamp_settings)
        
        stim_lst = [fov for fov in self.fov_obj_list if fov.contain_poisitive_cell]
        
        # Go trhough all fov
        for fov_obj in progress_bar(stim_lst,
                                    desc="Stimulating field of view",
                                    total=len(stim_lst)):
            # Move to point
            aquisition.nikon.set_stage_position(fov_obj.fov_coord)
            
            # Stimulate
            aquisition.load_dmd_mask(fov_obj.stimmask_path)
            aquisition.light_stimulate(settings['preset_stim']['exposure_sec'])
    
    def extract_control_ratio(self)-> None:
        cell_data_df = pd.read_csv(self.csv_path)
        cell_data_df['Pre_illumination'] = np.nan
        cell_data_df['Post_illumination'] = np.nan
            
        stim_lst = [fov for fov in self.fov_obj_list if fov.contain_poisitive_cell]
        
        print("\nStart extracting control ratio")
        dfs = run_multithread('get_control_ratio',
                              stim_lst,
                              "control_ratio",
                              cell_data_df=cell_data_df,
                              lock=Lock())
        
        
        cell_data_df = pd.concat(dfs)
        cell_data_df.to_csv(self.csv_path)

    @property
    def config_dir(self)-> Path:
        config_dir = self.well_dir.joinpath(f"{self.well}_config")
        config_dir.mkdir(exist_ok=True)
        return config_dir
    
    @property
    def well_obj_path(self)-> Path:
        return self.config_dir.joinpath(f"{self.well}_obj.json")
    
    @classmethod
    def from_json(cls: 'Well', file_path: Path)-> 'Well':
        with open(file_path, 'r') as f:
            data: dict = json.loads(f.read(), object_hook=custom_decoder)
        return cls(**data)
    
    def to_json(self)-> None:
        with open(self.well_obj_path, 'w') as fp:
            json.dump(self, fp, cls=CustomJSONEncoder, indent=4)

@dataclass
class FieldOfView():
    fov_coord: dict # dict keys = xy, ZDrive, PFSOffset
    well: str
    instance: int
    contain_poisitive_cell: bool = True
    fov_ID: str = field(default_factory=str)
    measure_1_path: Path = field(default_factory=Path)
    measure_2_path: Path = field(default_factory=Path)
    refseg_1_path: Path = field(default_factory=Path)
    refseg_2_path: Path = field(default_factory=Path)
    control_1_path: Path = field(default_factory=Path)
    control_2_path: Path = field(default_factory=Path)
    mask_path_1: Path = field(default_factory=Path)
    mask_path_2: Path = field(default_factory=Path)
    stimmask_path: Path = field(default_factory=Path)
    cell_number: int = field(default_factory=int)

    def __post_init__(self)-> None:
        self.fov_ID = f"{self.well}_P{self.instance}"
    
    def take_image_fov(self, aquisition: Aquisition, input_preset: dict, img_dir: Path, imaging_loop: str)-> None:
        # Position stage
        aquisition.nikon.set_stage_position(self.fov_coord)
        
        # Change oc settings
        aquisition.oc_settings(**input_preset)
        aquisition.load_dmd_mask() # Load the fullON mask
        
        # Take image and do background correction
        img = aquisition.snap_image()
        bgimg = apply_background_correction(img)
        
        # Save image
        img_path = img_dir.joinpath(f"{self.fov_ID}_{imaging_loop}.tif")
        imwrite(img_path,data=bgimg.astype('uint16'))
        setattr(self,f"{imaging_loop}_path",img_path)
    
    def segment_fov(self, model: models.CellposeModel, settings: dict, mask_dir: Path)-> np.ndarray:
        
        mask_cp,_,_, = model.eval(imread(self.measure_2_path),**settings['cellpose'])
    
        mask_path = mask_dir.joinpath(f"{self.fov_ID}_mask.tif")
        imwrite(mask_path,data=mask_cp.astype('uint16'))
        setattr(self,'mask_path_2',mask_path)
        return mask_cp.astype('uint16')
    
    def segment_fov_refseg(self, model: models.CellposeModel, settings: dict, mask_dir: Path)-> None:
        # Before stim mask
        mask_cp = model.eval(imread(self.refseg_1_path),**settings['cellpose'])[0]
    
        mask_path = mask_dir.joinpath(f"{self.fov_ID}_mask_1.tif")
        imwrite(mask_path,data=mask_cp.astype('uint16'))
        setattr(self,'mask_path_1',mask_path)
        
        # After stim mask
        mask_cp = model.eval(imread(self.refseg_2_path),**settings['cellpose'])[0]
        
        mask_path = mask_dir.joinpath(f"{self.fov_ID}_mask_2.tif")
        imwrite(mask_path,data=mask_cp.astype('uint16'))
        setattr(self,'mask_path_2',mask_path)
        
    def track_fov(self)-> None:
        masks = np.array([imread(self.mask_path_1),imread(self.mask_path_2)])
        
        stitched_masks = np.array(stitch3D(masks, stitch_threshold=0.75))
        
        # Remove non-tracked cells
        trim_incomplete_track(stitched_masks)
        
        # Save stitched mask
        imwrite(self.mask_path_1, data=stitched_masks[0].astype('uint16'))
        imwrite(self.mask_path_2, data=stitched_masks[1].astype('uint16'))
    
    def get_measure_ratio(self)-> pd.DataFrame:
        img1 = imread(self.measure_1_path)
        img2 = imread(self.measure_2_path)
        mask = imread(self.mask_path_2)
        centroid_lst = get_centroid(mask)
        
        keys = ['cell_ID','cell_numb','centroid_x','centroid_y','before_stim','after_stim','ratio','fov_y','fov_x']
        df_dict = {k:[] for k in keys}
        
        
        # Else extract data
        for cell_numb in list(np.unique(mask))[1:]:
            df_dict['cell_ID'].append(f"{self.fov_ID}_C{cell_numb}")
            df_dict['cell_numb'].append(cell_numb)
            y,x = centroid_lst[cell_numb-1]
            mx,my = self.fov_coord['xy']
            df_dict['centroid_x'].append(x)
            df_dict['centroid_y'].append(y)
            df_dict['fov_y'].append(my)
            df_dict['fov_x'].append(mx)
            df_dict['before_stim'].append(np.nanmean(a=img1,where=mask==cell_numb))
            df_dict['after_stim'].append(np.nanmean(a=img2,where=mask==cell_numb))
            df_dict['ratio'].append(df_dict['after_stim'][-1]/df_dict['before_stim'][-1])
            
        df_analysis = pd.DataFrame.from_dict(df_dict)
        df_analysis['fov_ID'] = self.fov_ID
        self.cell_number = len(df_analysis)
        return df_analysis
    
    def get_measure_ratio_refseg(self, refseg_threshold: float)-> pd.DataFrame:
        img1 = imread(self.measure_1_path)
        img2 = imread(self.measure_2_path)
        mask1 = imread(self.mask_path_1)
        mask2 = imread(self.mask_path_2)
        centroid_lst = get_centroid(mask2)
        
        keys = ['cell_ID','cell_numb','centroid_x','centroid_y','before_stim','after_stim','ratio','fov_y','fov_x']
        
        df_dict = {k:[] for k in keys}
        
        # Else extract data
        for index, cell_numb in enumerate(list(np.unique(mask2))[1:]):
            
            df_dict['cell_ID'].append(f"{self.fov_ID}_C{cell_numb}")
            df_dict['cell_numb'].append(cell_numb)
            y,x = centroid_lst[index]
            mx,my = self.fov_coord['xy']
            df_dict['centroid_x'].append(x)
            df_dict['centroid_y'].append(y)
            df_dict['fov_y'].append(my)
            df_dict['fov_x'].append(mx)
            df_dict['before_stim'].append(np.nanmean(a=img1,where=mask1==cell_numb))
            after_stim = np.nanmean(a=img2,where=mask2==cell_numb)
            if after_stim < refseg_threshold:
                df_dict['after_stim'].append(0)
            else:
                df_dict['after_stim'].append(after_stim)
            df_dict['ratio'].append(df_dict['after_stim'][-1]/df_dict['before_stim'][-1])
            
        df_analysis = pd.DataFrame.from_dict(df_dict)
        df_analysis['fov_ID'] = self.fov_ID
        self.cell_number = len(df_analysis)
        return df_analysis
    
    def create_stimmask(self, cell_data_df: pd.DataFrame, erosion_factor: int, lock: Lock)-> None:
        # Load mask and df_analysis
        mask = imread(self.mask_path_2).astype('uint16')
        
        with lock:
            subdf = cell_data_df.loc[cell_data_df['fov_ID']==self.fov_ID]
            cell_IDs = subdf['cell_numb'].to_numpy()
            to_process = subdf['process'].to_numpy()
        
        for cell, process_cell in zip(cell_IDs, to_process):
            if not process_cell:
                mask[mask==cell] = 0
        
        # Check if mask is empty
        if np.all(mask==0):
            self.stimmask_path = None
            self.contain_poisitive_cell = False
            return 
        
        # Erode mask to reduce non-specific stimulation
        pat_ero = disk(erosion_factor)
        mask = cv2.erode(mask,pat_ero)

        # Save mask
        mask_dir = self.mask_path_2.parent
        self.stimmask_path = mask_dir.joinpath(f"{self.fov_ID}_stimmask.tif")
        self.contain_poisitive_cell = True
        imwrite(self.stimmask_path,mask)
    
    def get_control_ratio(self, cell_data_df: pd.DataFrame, lock: Lock) -> pd.DataFrame:
        # load your images/mask once
        img1 = imread(self.control_1_path)
        img2 = imread(self.control_2_path)
        mask = imread(self.stimmask_path)

        # pre-fill the two new columns on every row
        cell_data_df['Pre_illumination']  = np.nan
        cell_data_df['Post_illumination'] = np.nan

        # lock around the work that reads/writes shared state
        with lock:
            # boolean mask for just this FOV
            fov_mask = cell_data_df['fov_ID'] == self.fov_ID
            subdf = cell_data_df.loc[fov_mask]

            # for each cell in this FOV, compute mean and assign back
            for cell, process_cell in zip(subdf['cell_numb'], subdf['process']):
                idx = (mask == cell)
                if process_cell and np.any(idx):
                    m1 = np.nanmean(img1, where=idx)
                    m2 = np.nanmean(img2, where=idx)
                else:
                    m1 = np.nan
                    m2 = np.nan

                # Fill the new columns for this cell
                sel = (cell_data_df['fov_ID'] == self.fov_ID) & (cell_data_df['cell_numb'] == cell)
                cell_data_df.loc[sel, 'Pre_illumination'] = m1
                cell_data_df.loc[sel, 'Post_illumination'] = m2

        return cell_data_df


    @classmethod
    def from_json(cls: 'FieldOfView', data: dict)-> 'FieldOfView':
        return cls(**data)

def trim_incomplete_track(array: np.ndarray)-> np.ndarray:
    """Function to trim the incomplete tracks from the mask stack.
    Modifies the input array in place.
    
    Args:
        array (np.ndarray): 3D Mask array in tyx format.
    Returns:
        np.ndarray: The list of objects removed."""
    # Make a list of unique objects
    lst_obj = [np.unique(frame) for frame in array]
    lst_obj = np.concatenate(lst_obj) # Flatten the list
    # Count the number of occurences of each object
    obj,cnt = np.unique(lst_obj,return_counts=True)
    # Create a list of obj to remove
    obj_to_remove = obj[cnt!=array.shape[0]]
    array_to_remove = np.isin(array,obj_to_remove)
    array[array_to_remove] = 0
    return obj_to_remove

if __name__ == '__main__':
    
    well_grid = {1:  {"xy": [5455.451989428573,23923.975939215685],
                    "ZDrive": None,
                    "PFSOffset": 9340.0},
                2:   {"xy": [5538.205189428573,24449.053918954247],
                    "ZDrive": None,
                    "PFSOffset": 9340.0}}
    
    # well = 'A1'
    # path = Path("D:\Boldi\LTB4_lib\\20240724\\")
    # well_obj = Well(well)
    # well_obj.create_dirs(path)
    # well_obj.create_list_fov(well_grid)
    
    # path_lst = ["D:\\Boldi\\LTB4_lib\\20240725\\A1\\A1_images\\A1_P1127_measure_1.tif",
    #             "D:\\Boldi\\LTB4_lib\\20240725\\A1\\A1_images\\A1_P1128_measure_1.tif"]
    # for i,fov in enumerate(well_obj.fov_obj_list):
    #     fov.measure_1_path = path_lst[i]
    # well_obj.to_json()
    
    well_obj = Well.from_json("D:\\Boldi\\LTB4_lib\\20240724\\A1_well_obj.json")
    print(type(well_obj.fov_obj_list[0].measure_1_path))

    