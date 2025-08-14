from gem_screening.utils.settings.models import AcquisitionSettings, DishSettings, PresetMeasure, PresetControl, PresetStim, ServerSettings, PresetRefseg, MeasureSettings, ControlSettings, StimSettings, PipelineSettings, LoggingSettings

# Folder where the experiment folder will be created
savedir = r'D:\Ben'

# Name for the experiment folder, timestamp will be added as prefix
savedir_name = 'test_gem_screening'

# base_url for the servers, `localhost` or a remote server (e.g. `10.114.104.21`)
base_url = 'localhost'

# Set up logging settings
logging_sets = LoggingSettings(
                    log_level='DEBUG',
                    logfile_name='gem_screening.log',)

# Aquisition settings for the microscope
aqui_sets = AcquisitionSettings(
                    objective='20x',
                    lamp_name='pE-800',
                    focus_device='PFSOffset')

# Settings for the dish used in the imaging process
dish_sets = DishSettings(
                    dish_name='35mm',
                    well_selection=['A1'],
                    af_method='sq_grad',
                    overwrite_autofocus=False,
                    overwrite_calib=False,
                    numb_field_view=3,)

# Preset settings for imaging for measurement
measure_sets = MeasureSettings(
                    preset_measure=PresetMeasure(
                                    optical_configuration='GFP',
                                    intensity=25),
                    do_refseg=True,
                    preset_refseg=PresetRefseg(
                                    optical_configuration='iRed',
                                    intensity=5))

# Settings for the segmentation and tracking server
server_sets = ServerSettings(
                    diameter=40,
                    flow_threshold=1.0,
                    cellprob_threshold=0.0,)

# Preset settings for control imaging before and after light stimulation
control_sets = ControlSettings(
                    control_loop=True,
                    preset=PresetControl(
                                    optical_configuration='RFP',
                                    intensity=40))

# Preset settings for light stimulation
stim_sets = StimSettings(
                    true_cell_threshold=50,
                    erosion_factor=3,
                    crop_size=251,
                    preset=PresetStim(
                                    optical_configuration='BFP',
                                    intensity=100,
                                    exposure_sec=10))


# Combine all settings into a PipelineSettings object
full_settings = PipelineSettings(
    savedir=savedir,
    savedir_name=savedir_name,
    logging_settings=logging_sets,
    acquisition_settings=aqui_sets,
    dish_settings=dish_sets,
    measure_settings=measure_sets,
    server_settings=server_sets,
    control_settings=control_sets,
    stim_settings=stim_sets)


# settings = {
# # savedir for images
# 'savedir': r'D:\Ben',
# 'savedir_name': 'test_celltinder',

# # Aquisition setting
# 'aquisition_settings': {'objective': '20x', # Only 10x or 20x are calibrated for now
#                         'lamp_name': 'pE-800',  # 'pE-800','pE-4000','DiaLamp'
#                         'focus_device': 'PFSOffset'}, # 'PFSOffset' or 'ZDrive'
# #  Initiate dish
# 'dish_settings': {'dish_name': '35mm', # '35mm' 'ibidi-8well' '96well'
#                     'overwrite_calib': False, # if True, will overwrite the calibration file
#                     'well_selection': ['A1'], # if 'all', will do all possible wells, otherwise enter a list of wells ['A1','A2',...]
#                     'numb_field_view': 3, # if None, will run the whole well --> 35mm dish full coverage has 1418 field of view
#                     'overlap_percent': None}, # in 0-100% Only applicable to complete well coverage (i.e. 'numb_field_view'=None). if None then will use optimal overlap for the dish
                
# # Autofocus settings
# # if Manual, need to focus with the focus device selected above in micromanager
# 'autofocus': {'method': 'sq_grad', # Choose mtd label here, ['sq_grad','Manual']
#                 'overwrite': False}, # If True, will overwrite the autofocus

# # Channel list for measurment
# 'preset_measure': {'optical_configuration': 'GFP', # Channel to seg for analysis
#                 'intensity': 25}, # 0-100%

# # Channel list for refseg
# 'refseg': True, # If True, will do a second imaging loop before and after light stimulation in the target channel 
# 'refseg_threshold': 50, # Minimum pixel intensity to be considered as a cell
# 'preset_refseg': {'optical_configuration': 'iRed', # Channel to seg for analysis
#                 'intensity': 5}, # 0-100%

# # Segmetation settings
# 'server': {'diameter': 40, 
#                 'flow_threshold': 1, 
#                 'cellprob_threshold': 0}, # Cellpose settings 10x: 20-25, 20x: 40-50, tried 20 with 10x and it seemed perfect - Boldi

# # Stimulation masks
# 'stimasks': {'erosion_factor': 3,}, # for the stim masks to avoid stimulation of neibourghing cells, radius size in pixels

# # Stimulation
# 'preset_stim': {'optical_configuration': 'BFP', # Channel for control after light stimulation
#                 'intensity': 100, # 0-100%
#                 'exposure_sec': 10},  # in sec'

# 'control_loop': True, # If True, will do a third imaging loop before and after light stimulation in the target channel
# 'preset_control': {'optical_configuration': 'RFP', # Channel for control after light stimulation
#                     'intensity': 40},
# }