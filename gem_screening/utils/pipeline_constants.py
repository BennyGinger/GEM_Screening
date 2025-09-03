# Define constants for the image labels
MEASURE_LABEL = 'measure'
CONTROL_LABEL = 'control'
REFSEG_LABEL = 'refseg'
MASK_LABEL = 'mask'
STIM_LABEL = 'stim'

# Define constants for image and mask folders and categories
IMG_FOLDER = "images"
MASK_FOLDER = "masks"
WELL_FOLDER = "well"
CONFIG_FOLDER = "config"
DF_FILENAME = "cell_data.csv"
WELL_OBJ_FILENAME = "obj.json"
IMG_CAT = [MEASURE_LABEL, REFSEG_LABEL, CONTROL_LABEL]
MASK_CAT = [MASK_LABEL, STIM_LABEL]
DEFAULT_CATEGORIES = IMG_CAT + MASK_CAT

# Define constants for column names
RATIO = 'ratio'
BEFORE_STIM = 'before_stim'
AFTER_STIM = 'after_stim'
CENTROID_X = 'centroid_x'
CENTROID_Y = 'centroid_y'
CELL_LABEL = 'cell_numb'
FOV_ID = 'fov_ID'
CELL_ID = 'cell_id'
FOV_Y = 'fov_y'
FOV_X = 'fov_x'
PRE_ILLUMINATION = 'before_light'
POST_ILLUMINATION = 'after_light'
PROCESS = 'process'

# FIXME: For consistency, change the column names: 'before_stim' -> 'mean_pre_stim
    # and 'after_stim' -> 'mean_post_stim'; 'cell_numb' -> 'cell_label'; 'fov_ID' -> 'fov_id'

# Define constants for cellpose settings
# FIXME: Move these constant to the cp_server module
BG_SETS = {"sigma": 0.0,
           "size": 7,}

CP_SETS = {"do_denoise": True,
               "model_type": "cyto2",
               "restore_type": "denoise_cyto2",
               "gpu": True,
               "channels": None,
               "diameter": 60,
               "flow_threshold": 0.4,
               "cellprob_threshold": 0.0,
               "z_axis": None,
               "do_3D": False,
               "stitch_threshold_3D": 0,}