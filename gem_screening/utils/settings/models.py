from pydantic import BaseModel, ConfigDict


class LoggingSettings(BaseModel):
    """
    Pydantic model for Logging settings.
    
    Attributes:
        log_level (str, optional): The logging level, e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR', or 'CRITICAL'. Defaults to 'INFO'.
        logfile_name (str, optional): The file name where logs will be saved. Defaults to 'gem_screening.log'.
    """
    log_level: str = 'INFO'
    logfile_name: str = 'gem_screening.log'

class AcquisitionSettings(BaseModel):
    """
    Pydantic model for Acquisition settings for the imaging process.
    Attributes:
        objective (str, optional): The objective lens used for imaging, e.g., '10x' or '20x'. Defaults to '20x'.
        lamp_name (str, optional): The name of the lamp used for illumination, e.g., 'pE-800', 'pE-4000', or 'DiaLamp'. Defaults to 'pE-800'.
        focus_device (str, optional): The device used for focusing, e.g., 'PFSOffset' or 'ZDrive'. Defaults to 'PFSOffset'.
    """
    objective: str = '20x'
    lamp_name: str  = 'pE-800'
    focus_device: str  = 'PFSOffset'

class DishSettings(BaseModel):
    """
    Pydantic model for Settings for the dish used in the imaging process.
    Attributes:
        dish_name (str, optional): Name of the dish, e.g., '35mm', 'ibidi-8well', or '96well'. Defaults to '35mm'.
        overwrite_calib (bool, optional): If True, will overwrite the calibration file for the dish. Defaults to False.
        well_selection (list[str], optional): List of wells to image, e.g., ['A1', 'A2']. If 'all', will image all possible wells. Defaults to ['A1'].
        numb_field_view (int, optional): Number of field views to image. If None, will run the whole well.
        overlap_percent (float, optional): Overlap percentage for field views. If None, will use optimal overlap for the dish.
    """
    dish_name: str = '35mm'
    overwrite_calib: bool = False
    well_selection: list[str] = ['A1']
    numb_field_view: int | None = None
    overlap_percent: float | None = None

class AutofocusSettings(BaseModel):
    """
    Pydantic model for Settings for autofocus during the imaging process.
    Attributes:
        method (str, optional): Method for autofocus, e.g., 'sq_grad' or 'Manual'. Defaults to 'sq_grad'.
        overwrite (bool, optional): If True, will overwrite the autofocus settings. Defaults to False.
    """
    method: str = 'sq_grad'
    overwrite: bool = False

class PresetMeasure(BaseModel):
    """
    Pydantic model for Preset settings for imaging.
    Attributes:
        optical_configuration (str, optional): Optical configuration for the preset, e.g., 'GFP', 'iRed', 'BFP', or 'RFP'. Defaults to 'GFP'.
        intensity (int, optional): Intensity level for the preset, ranging from 0 to 100. Defaults to 25.
        exposure_ms (int, optional): Exposure time in milliseconds for the preset. Defaults to 100.
    """
    optical_configuration: str = 'GFP'
    intensity: int = 25
    exposure_ms: int = 100

class PresetRefseg(BaseModel):
    """
    Pydantic model for Preset settings for reference segmentation.
    Attributes:
        optical_configuration (str, optional): Optical configuration for the preset, e.g., 'iRed'. Defaults to 'iRed'.
        intensity (int, optional): Intensity level for the preset, ranging from 0 to 100. Defaults to 5.
        exposure_ms (int, optional): Exposure time in milliseconds for the preset. Defaults to 100.
    """
    optical_configuration: str = 'iRed'
    intensity: int = 5
    exposure_ms: int = 100
    
class PresetControl(BaseModel):
    """
    Pydantic model for Preset settings for control imaging after light stimulation.
    Attributes:
        optical_configuration (str, optional): Optical configuration for the preset, e.g., 'RFP'. Defaults to 'RFP'.
        intensity (int, optional): Intensity level for the preset, ranging from 0 to 100. Defaults to 40.
        exposure_ms (int, optional): Exposure time in milliseconds for the preset. Defaults to 100.
    """
    optical_configuration: str = 'RFP'
    intensity: int = 40
    exposure_ms: int = 100

class PresetStim(BaseModel):
    """
    Pydantic model for Preset settings for stimulation.
    Attributes:
        optical_configuration (str, optional): Optical configuration for the preset, e.g., 'BFP' or 'RFP'. Defaults to 'BFP'.
        intensity (int, optional): Intensity level for the preset, ranging from 0 to 100. Defaults to 100.
        exposure_sec (int, optional): Exposure time in seconds for the preset. Defaults to 10.
    """
    optical_configuration: str = 'BFP'
    intensity: int = 100
    exposure_sec: int = 10

class MeasureSettings(BaseModel):
    """
    Pydantic model for Settings for reference segmentation.
    Attributes:
        preset_measure (PresetMeasure): Preset settings for imaging.
        do_refseg (bool, optional): If True, will perform reference segmentation. Defaults to True.
        preset_refseg (PresetRefseg): Preset settings for reference segmentation.
    
    Notes:
        - `PresetMeasure` and `PresetRefseg` contain the optical configuration (str), intensity (%), and exposure time (ms) for imaging.
    """
    preset_measure: PresetMeasure = PresetMeasure()
    do_refseg: bool = True
    preset_refseg: PresetRefseg = PresetRefseg()

class ControlSettings(BaseModel):
    """
    Pydantic model for Settings for control imaging before and after light stimulation.
    Attributes:
        control_loop (bool, optional): If True, will perform a control imaging loop before and after light stimulation. Defaults to True.
        preset (PresetControl): Preset settings for control imaging.
    Notes:
        - `PresetControl` contains the optical configuration (str), intensity (%), and exposure time (ms) for control imaging.
    """
    control_loop: bool = True
    preset: PresetControl = PresetControl()

class StimSettings(BaseModel):
    """
    Pydantic model for Settings for stimulation masks.
    Attributes:
        true_cell_threshold (int, optional): Threshold for true cell detection. Below this value, cells are considered noise and set to 0 in the output. Defaults to 50.
        crop_size (int, optional): Size of the crop for the display of the ROI, for the CellTinder GUI, to select positive cells. Defaults to 251.
        erosion_factor (int, optional): Erosion factor for the stimulation masks to avoid stimulation of neighboring cells. Defaults to 3.
        preset (PresetStim): Preset settings for light stimulation.
    Notes:
        - `PresetStim` contains the optical configuration (str), intensity (%), and exposure time (sec) for light stimulation.
    """
    true_cell_threshold: int = 50
    crop_size: int = 251
    erosion_factor: int = 3
    preset: PresetStim = PresetStim()

class ServerSettings(BaseModel):
    """
    Pydantic model for Settings for the server used in the imaging process.
    Attributes:
        sigma (float, optional): Sigma value for background subtraction. Defaults to 0.
        size (int, optional): Size parameter for background subtraction. Defaults to 7.
        do_denoise (bool, optional): If True, will use the denoising model. Defaults to True.
        model_type (str, optional): Type of the Cellpose model, e.g., 'cyto2', 'cyto3'. Defaults to 'cyto2'.
        restore_type (str, optional): Type of restoration for the Cellpose model, e.g., 'denoise_cyto2', 'denoise_cyto3'. Defaults to 'denoise_cyto2'.
        gpu (bool, optional): If True, will use GPU for processing. Defaults to True.
        channels (list[int], optional): List of channels to use for segmentation. Defaults to None.
        diameter (int, optional): Diameter for segmentation, e.g., 40 or 60. Defaults to 40.
        flow_threshold (float, optional): Flow threshold for segmentation. Defaults to 1.
        cellprob_threshold (float, optional): Cell probability threshold for segmentation. Defaults to 0.
        z_axis (int, optional): Z-axis index for 3D segmentation. Defaults to None.
        do_3D (bool, optional): If True, will perform 3D segmentation. Defaults to False.
        stitch_threshold_3D (float, optional): Stitch threshold used for alternative 3D segmentation using IoU. `do_3D` needs to be False. Defaults to 0.
        track_stitch_threshold (float, optional): Threshold for stitching masks during tracking. Defaults to 0.75.
        
    Notes:
        - `well_id` (str) is set by the pipeline to identify the well run.
        - `dst_folder` (str) is set by the pipeline to specify the destination folder for results.
        - `total_fovs` (int) is set by the pipeline to specify the total number of fields of view.
    """
    ## Set by user ##
    server_timeout_sec: float = 600.0 # 10 minutes
    sigma: float = 0.0
    size: int = 7
    do_denoise: bool = True
    model_type: str = 'cyto2'
    restore_type: str = 'denoise_cyto2'
    gpu: bool = True
    channels: list[int] = None
    diameter: int = 40
    flow_threshold: float = 1.0
    cellprob_threshold: float = 0.0
    z_axis: int = None
    do_3D: bool = False
    stitch_threshold_3D: float = 0.0
    track_stitch_threshold: float = 0.75
    
    ## Set by pipeline ##
    well_id: str = ''
    dst_folder: str = ''
    total_fovs: int = 0
    
    model_config = ConfigDict(model_dump_exclude={"server_timeout_sec"})
    
class PipelineSettings(BaseModel):
    """
    Pydantic model for Settings for the entire imaging pipeline.
    Attributes:
        savedir (str): Directory where images will be saved.
        savedir_name (str): Name of the directory for saving images.
        base_url (str): Base URL for the servers, defaults to `localhost`.
        logging_settings (LoggingSettings): Settings for logging configuration.
        acquisition_settings (AcquisitionSettings): Settings for the aquisition process.
        dish_settings (DishSettings): Settings for the dish used in the imaging process.
        af_settings (AutofocusSettings): Settings for autofocus during the imaging process.
        measure_settings (MeasureSettings): Settings for measurement and reference segmentation.
        server_settings (ServerSettings): Settings for the segmentation and tracking server.
        control_settings (ControlSettings): Settings for control imaging before and after light stimulation.
        stim_settings (StimSettings): Settings for light stimulation masks.
    """
    savedir: str
    savedir_name: str
    base_url: str = 'localhost'
    logging_settings: LoggingSettings
    acquisition_settings: AcquisitionSettings
    dish_settings: DishSettings
    af_settings: AutofocusSettings
    measure_settings: MeasureSettings
    server_settings: ServerSettings
    control_settings: ControlSettings
    stim_settings: StimSettings