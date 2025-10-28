from gem_screening.settings.models import AcquisitionSettings, DishSettings, PresetMeasure, PresetControl, PresetStim, ServerSettings, PresetRefseg, MeasureSettings, ControlSettings, StimSettings, PipelineSettings, LoggingSettings

# Folder where the experiment folder will be created
savedir = r'D:\Ben'

# Name for the experiment folder, timestamp will be added as prefix
savedir_name = 'test_pipeline'
# Aquisition settings for the microscope
aqui_sets = AcquisitionSettings(
                    objective='20x',)

# Settings for the dish used in the imaging process
dish_sets = DishSettings(
                    dish_name='96well',
                    # well_selection=['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1',],
                    # well_selection=['B2', 'C2', 'D2', 'E2', 'F2', 'G2',],
                    # well_selection=['B3', 'C3', 'D3', 'E3', 'F3', 'G3'],
                    # well_selection=['B4', 'C4', 'D4', 'E4', 'F4', 'G4'],
                    well_selection=['A5', 'B5', 'C5', 'D5', 'E5', 'F5', 'G5', 'H5',],
                    # well_selection=['A6', 'B6', 'C6', 'D6', 'E6', 'F6', 'G6', 'H6',],
                    # well_selection=['A7', 'B7', 'C7', 'D7', 'E7', 'F7', 'G7', 'H7',],
                    # well_selection=['A8', 'B8', 'C8', 'D8', 'E8', 'F8', 'G8', 'H8',],
                    # well_selection=['A9', 'B9', 'C9', 'D9', 'E9', 'F9', 'G9', 'H9',],
                    # well_selection=['A10', 'B10', 'C10', 'D10', 'E10', 'F10', 'G10', 'H10',],
                    # well_selection=['A11', 'B11', 'C11', 'D11', 'E11', 'F11', 'G11', 'H11',],
                    # well_selection=['A12', 'B12', 'C12', 'D12', 'E12', 'F12', 'G12', 'H12',],
                    af_method='Manual',
                    overwrite_autofocus=True,
                    overwrite_calib=False,
                    numb_field_view=None,
                    dmd_window_only=False,
                    )

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
                    flow_threshold=0.5,
                    cellprob_threshold=-0.4,
                    track_stitch_threshold=0.65)

# Preset settings for control imaging before and after light stimulation
control_sets = ControlSettings(
                    control_loop=True,
                    preset=PresetControl(
                                    optical_configuration='RFP',
                                    intensity=40))

# Preset settings for light stimulation
stim_sets = StimSettings(
                    true_cell_threshold=50,
                    preset=PresetStim(
                                    optical_configuration='BFP',
                                    intensity=100,
                                    exposure_sec=10))

#######################################################################
##################### Do Not Edit Below This Line #####################
#######################################################################
# Combine all settings into a PipelineSettings object
full_settings = PipelineSettings(
    savedir=savedir,
    savedir_name=savedir_name,
    dev_mode=False,
    base_url='localhost',
    logging_settings=LoggingSettings(log_level='INFO',),
    acquisition_settings=aqui_sets,
    dish_settings=dish_sets,
    measure_settings=measure_sets,
    server_settings=server_sets,
    control_settings=control_sets,
    stim_settings=stim_sets)

