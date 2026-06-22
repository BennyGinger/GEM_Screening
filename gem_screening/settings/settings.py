from gem_screening.settings.models import AcquisitionSettings, DishSettings, PresetMeasure, PresetControl, PresetStim, ServerSettings, PresetRefseg, MeasureSettings, ControlSettings, StimSettings, PipelineSettings, LoggingSettings, InjectionSettings

# Folder where the experiment folder will be created
savedir = r'D:\Ben'

# Name for the experiment folder, timestamp will be added as prefix
savedir_name = 'troubleshooting'
# Aquisition settings for the microscope
aqui_sets = AcquisitionSettings(
                    objective='20x',)

# Settings for the dish used in the imaging process
dish_sets = DishSettings(
                    dish_name='96well',
                    well_selection=['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1'],
                    # well_selection='all',
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

# Settings for the automated injection
injection_sets = InjectionSettings(
                    enabled=False, # whether to perform automated injection or not, if False, the injection step will be manual 
                    injection_device='quickpick',
                    needle_size=50, # in microns, only needed for quickpick head control
                    pressure=0.3, # in bar, only needed for quickpick head control
                    inject_vol_ul=10, # in microliters, for both injection devices
                    inject_time_ms=None, # in milliseconds, only needed for nanopick head control
                    mixing_cycles=3) # number of mixing cycles during injection

# Settings for the segmentation and tracking server
server_sets = ServerSettings(
                    flow_threshold=0.5,
                    cellprob_threshold=-0.4,
                    track_stitch_threshold=0.65)

# Preset settings for control imaging before and after light stimulation
control_sets = ControlSettings(
                    control_loop=False,
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
    injection_settings=injection_sets,
    server_settings=server_sets,
    control_settings=control_sets,
    stim_settings=stim_sets)

