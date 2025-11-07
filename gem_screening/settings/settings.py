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
                    # well_selection=['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10', 'A11', 'A12'],
                    well_selection='all',
                    well_grouping='col',
                    af_method='Manual',
                    overwrite_autofocus=False,
                    overwrite_calib=False,
                    # numb_field_view=1,
                    numb_field_view=3,
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
    dev_mode=True,
    base_url='localhost',
    logging_settings=LoggingSettings(log_level='INFO',),
    acquisition_settings=aqui_sets,
    dish_settings=dish_sets,
    measure_settings=measure_sets,
    server_settings=server_sets,
    control_settings=control_sets,
    stim_settings=stim_sets)

