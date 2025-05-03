from __future__ import annotations
from pathlib import Path

from celltinder import run_cell_tinder
from a1_manager import A1Manager, launch_dish_workflow

from microscope_software.well_module import Well
from utils.utils import create_date_savedir, timer


################# Main Function #################
def complete_pipeline(settings: dict)-> None:
    # Initialise mm and set up microscope
    aquisition = A1Manager(**settings['aquisition_settings'])
    aquisition.oc_settings(**settings['preset_measure'])
    
    # Initialise pipeline
    run_dir = create_date_savedir(Path(settings['savedir']), settings['savedir_name'])
    
    resp = input("\nDid you focus on the cells? Press enter to continue or 'q' to break: ")
    if resp == 'q':
        return
    
    # Generate the different field of views for each well, autofocus
    _, dish_grids = launch_dish_workflow(**settings['dish_settings'])
    
    # Start imaging
    for well, well_grid in dish_grids.items():
        # Get the well folder path
        well_dir = run_dir.joinpath(well)
        well_dir.mkdir(exist_ok=True)
        
        # Create point_object list
        well_obj = initialize_well_object(well, well_grid, well_dir)
        
        # Scan cells, return True if user wants to quit, else False
        break_loop = scan_cells(well_obj, settings, aquisition)
        if break_loop:
            break
        
        # Stimulate cells
        stimulate_cells(well_obj, settings, aquisition)

def rescue_stimmulation(run_dir: str | Path, settings: dict, well_to_run: str | list[str])-> None:
    # Initialise mm and set up microscope
    aquisition = A1Manager(**settings['aquisition_settings'])
    
    # Get the csv files for the well to run
    if isinstance(well_to_run, str):
        well_to_run = [well_to_run]
    
    if isinstance(run_dir,str):
        run_dir = Path(run_dir)
     
    for well in well_to_run:
        # Find the well object file
        well_dir = run_dir.joinpath(well)
        
        if not well_dir.exists():
            raise FileNotFoundError(f'Well object folder not found: {well}')
        
        # Load the well object
        well_obj_path = well_dir.joinpath(f'{well}_config', f'{well}_obj.json')
        print(f'Loading well object from {well_obj_path}')
        well_obj = Well.from_json(well_obj_path)
        
        # Read the csv file
        stimulate_cells(well_obj, settings, aquisition)

################# Helper functions #################
def scan_cells(well_obj: Well, settings: dict, aquisition: A1Manager)-> bool:
    
    capture_images(settings, aquisition, well_obj, "measure_1")
    
    # Ask user to stimulate cells
    resp = input("\nPlease stimulate the cells and press enter to continue: ")
    if resp == 'q':
        return True
    
    # Second imaging loop, after cell stimulation
    capture_images(settings, aquisition, well_obj, "measure_2")
    
    # Segmentation
    apply_segmentation(settings, well_obj)
    if settings['refseg']:
        apply_tracking(well_obj)
    
    # Get cell ratio and save it for further analysis
    extract_cell_ratio(settings, well_obj)
    
    # Run celltinder
    run_cell_tinder(well_obj.csv_path)
    print('Celltinder done')
    # Create stimulation mask
    generate_stimmask(settings, well_obj)
    
    # Save the well object
    well_obj.to_json()
    return False
    
def stimulate_cells(well_obj: Well, settings: dict, aquisition: A1Manager)-> None:
    
    # Control loop before light stimulation (only if point contains positive cells)
    if settings['control_loop']:
        capture_images(settings, aquisition, well_obj, "control_1")
    
    # Light stimulation of all poisitive points (point containing positive cells)
    stimulate_all_fov(settings, aquisition, well_obj)
    
    # Control loop after light stimulation
    if settings['control_loop']:
        capture_images(settings, aquisition, well_obj, "control_2")
        extract_control_data(well_obj)
    
    # Save the well object
    well_obj.to_json()

def initialize_well_object(well: str, well_grid: dict[int,dict], well_dir: Path)-> Well: 
    
    well_obj = Well(well)
    well_obj.create_dirs(well_dir)
    well_obj.create_list_fov(well_grid)
    well_obj.to_json()
    return well_obj

@timer
def extract_control_data(well_obj: Well)-> None:
    well_obj.extract_control_ratio()
    
@timer
def stimulate_all_fov(settings: dict, aquisition: A1Manager, well_obj: Well)-> None:
    well_obj.stimulate_all_fov(aquisition,settings)

@timer
def generate_stimmask(settings: dict, well_obj: Well):
    well_obj.create_all_stimmask(**settings['stimasks'])

@timer
def extract_cell_ratio(settings: dict, well_obj: Well)-> None:
    # Extract cell ratio
    well_obj.extract_measure_ratio(settings)

@timer
def apply_segmentation(settings: dict, well_obj: Well)-> None:
    well_obj.segment_all_fov(settings)

@timer
def apply_tracking(well_obj: Well)-> None:
    well_obj.track_all_fov()

@timer
def capture_images(settings: dict, aquisition: A1Manager, well_obj: Well, imaging_loop: str)-> None:
    well_obj.image_all_fov(aquisition,settings,imaging_loop)
        

if __name__ == '__main__':
    # Load settings
    settings = {
    # savedir for images
    'savedir': r'D:\Ben',
    'savedir_name': 'test_celltinder',
    
    # A1Manager setting
    'aquisition_settings': {'objective': '20x', # Only 10x or 20x are calibrated for now
                           'lamp_name': 'pE-800',  # 'pE-800','pE-4000','DiaLamp'
                           'focus_device': 'PFSOffset'}, # 'PFSOffset' or 'ZDrive'
    #  Initiate dish
    'dish_settings': {'dish_name': '35mm', # '35mm' 'ibidi-8well' '96well'
                     'overwrite_calib': False, # if True, will overwrite the calibration file
                     'well_selection': ['A1'], # if 'all', will do all possible wells, otherwise enter a list of wells ['A1','A2',...]
                     'numb_field_view': 3, # if None, will run the whole well --> 35mm dish full coverage has 1418 field of view
                     'overlap': None}, # in 0-100% Only applicable to complete well coverage (i.e. 'numb_field_view'=None). if None then will use optimal overlap for the dish
                   
    # Autofocus settings
    # if Manual, need to focus with the focus device selected above in micromanager
    'autofocus': {'method': 'sq_grad', # Choose mtd label here, ['sq_grad','Manual']
                  'overwrite': False}, # If True, will overwrite the autofocus
    
    # Channel list for measurment
    'preset_measure': {'optical_configuration': 'GFP', # Channel to seg for analysis
                  'intensity': 25}, # 0-100%
    
    # Channel list for refseg
    'refseg': True, # If True, will do a second imaging loop before and after light stimulation in the target channel 
    'refseg_threshold': 50, # Minimum pixel intensity to be considered as a cell
    'preset_refseg': {'optical_configuration': 'iRed', # Channel to seg for analysis
                  'intensity': 5}, # 0-100%
    
    # Segmetation settings
    'cellpose': {'diameter': 40, 
                 'flow_threshold': 1, 
                 'cellprob_threshold': 0}, # Cellpose settings 10x: 20-25, 20x: 40-50, tried 20 with 10x and it seemed perfect - Boldi

    # Stimulation masks
    'stimasks': {'erosion_factor': 3,}, # for the stim masks to avoid stimulation of neibourghing cells, radius size in pixels

    # Stimulation
    'preset_stim': {'optical_configuration': 'BFP', # Channel for control after light stimulation
                    'intensity': 100, # 0-100%
                    'exposure_sec': 10},  # in sec'
    
    'control_loop': True, # If True, will do a third imaging loop before and after light stimulation in the target channel
    'preset_control': {'optical_configuration': 'RFP', # Channel for control after light stimulation
                        'intensity': 40},
    } 
    
    
    # complete_pipeline(settings) 
    rescue_stimmulation(r'D:\Ben\20250430_test_celltinder', settings, 'A1')
    

