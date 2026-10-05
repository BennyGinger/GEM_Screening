"""Light stimulation and control imaging settings page."""

from PyQt6.QtWidgets import QWidget, QFormLayout, QSpinBox, QComboBox, QLabel, QGroupBox, QPushButton, QSlider, QHBoxLayout, QCheckBox, QVBoxLayout
from PyQt6.QtCore import Qt

from gem_screening.settings.models import PipelineSettings



class StimPage(QWidget):

    def __init__(self, pipeline_settings: PipelineSettings):
        super().__init__()
        self.pipeline_settings = pipeline_settings
        layout = QFormLayout(self)

        # Do Illumination Checkbox
        self.do_illumination = QCheckBox("Do Illumination")
        self.do_illumination.setChecked(False)
        self.do_illumination.setToolTip("If unchecked, all illumination settings below are disabled.")
        layout.addRow(self.do_illumination)


        # Optical Config
        self.optical_config = QComboBox()
        self.optical_config.addItems(["BFP", "RFP", "GFP", "iRed"])
        optical_label = QLabel("Optical Config")
        optical_label.setToolTip("Optical configuration for the preset, e.g., 'BFP' or 'RFP'. Defaults to 'BFP'.")
        layout.addRow(optical_label, self.optical_config)


        # Intensity (Slider)
        self.intensity_slider = QSlider()
        self.intensity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 100)
        self.intensity_slider.setValue(100)
        self.intensity_value_label = QLabel("100")
        intensity_label = QLabel("Intensity")
        intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 100.")
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(self.intensity_slider)
        intensity_layout.addWidget(self.intensity_value_label)
        self.intensity_slider.valueChanged.connect(lambda v: self.intensity_value_label.setText(str(v)))
        layout.addRow(intensity_label, intensity_layout)


        # Exposure (sec)
        self.exposure_sec = QSpinBox()
        self.exposure_sec.setRange(1, 10000)
        self.exposure_sec.setValue(10)
        exposure_label = QLabel("Exposure (sec)")
        exposure_label.setToolTip("Exposure time in seconds for the preset. Defaults to 10.")
        layout.addRow(exposure_label, self.exposure_sec)


        # Advanced settings box (hidden by default)
        self.advanced_box = QGroupBox()
        self.advanced_box.setTitle("")
        self.advanced_box.setVisible(False)
        adv_layout = QFormLayout(self.advanced_box)

        # True Cell Threshold
        self.true_cell_threshold = QSpinBox()
        self.true_cell_threshold.setRange(0, 1000)
        self.true_cell_threshold.setValue(50)
        true_cell_label = QLabel("True Cell Threshold")
        true_cell_label.setToolTip("Mean intensity threshold for true cell detection. Below this value, cells are considered noise and set to 0 in the output. Defaults to 50.")
        adv_layout.addRow(true_cell_label, self.true_cell_threshold)

        # Crop Size
        self.crop_size = QSpinBox()
        self.crop_size.setRange(1, 10000)
        self.crop_size.setValue(251)
        crop_label = QLabel("Crop Size")
        crop_label.setToolTip("Size of the crop for the display of the ROI, for the CellTinder GUI, to select positive cells. Defaults to 251.")
        adv_layout.addRow(crop_label, self.crop_size)

        # Erosion Factor
        self.erosion_factor = QSpinBox()
        self.erosion_factor.setRange(0, 100)
        self.erosion_factor.setValue(3)
        erosion_label = QLabel("Erosion Factor")
        erosion_label.setToolTip("Erosion factor (pixels) for the stimulation masks to avoid stimulation of neighboring cells. Defaults to 3.")
        adv_layout.addRow(erosion_label, self.erosion_factor)

        # Advanced toggle button
        self.advanced_btn = QPushButton("Show Advanced Settings")
        self.advanced_btn.setCheckable(True)
        def toggle_advanced():
            show = self.advanced_btn.isChecked()
            self.advanced_box.setVisible(show)
            self.advanced_btn.setText("Hide Advanced Settings" if show else "Show Advanced Settings")
        self.advanced_btn.clicked.connect(toggle_advanced)
        layout.addRow(self.advanced_btn)
        layout.addRow(self.advanced_box)

        # Control imaging is part of the light-stimulation workflow. Keep its
        # values in ControlSettings, but present it alongside stimulation.
        self.control_group = QGroupBox()
        self.control_group.setTitle("")
        control_main_layout = QVBoxLayout(self.control_group)
        self.do_control = QCheckBox("Do Control Imaging Loop")
        self.do_control.setChecked(False)
        self.do_control.setToolTip(
            "If checked, perform control imaging before and after light stimulation. "
            "Defaults to False."
        )
        control_main_layout.addWidget(self.do_control)

        control_layout = QFormLayout()
        self.control_optical_config = QComboBox()
        self.control_optical_config.addItems(["RFP", "GFP", "iRed", "BFP"])
        control_optical_label = QLabel("Optical Config")
        control_optical_label.setToolTip(
            "Optical configuration for control images, e.g. 'RFP'. Defaults to 'RFP'."
        )
        control_layout.addRow(control_optical_label, self.control_optical_config)

        self.control_intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.control_intensity_slider.setRange(0, 100)
        self.control_intensity_value_label = QLabel("40")
        control_intensity_label = QLabel("Intensity")
        control_intensity_label.setToolTip(
            "Illumination intensity for control images, from 0 to 100. Defaults to 40."
        )
        control_intensity_layout = QHBoxLayout()
        control_intensity_layout.addWidget(self.control_intensity_slider)
        control_intensity_layout.addWidget(self.control_intensity_value_label)
        control_layout.addRow(control_intensity_label, control_intensity_layout)

        self.control_exposure = QSpinBox()
        self.control_exposure.setRange(1, 10000)
        control_exposure_label = QLabel("Exposure (ms)")
        control_exposure_label.setToolTip(
            "Exposure time in milliseconds for control images. Defaults to 100."
        )
        control_layout.addRow(control_exposure_label, self.control_exposure)
        control_main_layout.addLayout(control_layout)
        layout.addRow(self.control_group)

        # Connect signals to update pipeline_settings
        self.optical_config.currentTextChanged.connect(self.update_optical_config)
        self.intensity_slider.valueChanged.connect(self.update_intensity)
        self.exposure_sec.valueChanged.connect(self.update_exposure_sec)
        self.true_cell_threshold.valueChanged.connect(self.update_true_cell_threshold)
        self.crop_size.valueChanged.connect(self.update_crop_size)
        self.erosion_factor.valueChanged.connect(self.update_erosion_factor)
        self.control_intensity_slider.valueChanged.connect(
            lambda value: self.control_intensity_value_label.setText(str(value))
        )
        self.do_control.toggled.connect(self.update_do_control)
        self.control_optical_config.currentTextChanged.connect(self.update_control_optical)
        self.control_intensity_slider.valueChanged.connect(self.update_control_intensity)
        self.control_exposure.valueChanged.connect(self.update_control_exposure)

        # Initialize from pipeline_settings if available
        if self.pipeline_settings is not None:
            stim = self.pipeline_settings.stim_settings
            self.optical_config.setCurrentText(stim.preset.optical_configuration)
            self.intensity_slider.setValue(stim.preset.intensity)
            self.intensity_value_label.setText(str(stim.preset.intensity))
            self.exposure_sec.setValue(stim.preset.exposure_sec)
            self.true_cell_threshold.setValue(stim.true_cell_threshold)
            self.crop_size.setValue(stim.crop_size)
            self.erosion_factor.setValue(stim.erosion_factor)
            control = self.pipeline_settings.control_settings
            self.do_control.setChecked(control.control_loop)
            self.control_optical_config.setCurrentText(control.preset.optical_configuration)
            self.control_intensity_slider.setValue(control.preset.intensity)
            self.control_intensity_value_label.setText(str(control.preset.intensity))
            self.control_exposure.setValue(control.preset.exposure_ms)

        # Connect signals to update pipeline_settings (at the end of __init__)
        self.optical_config.currentTextChanged.connect(self.update_optical_config)
        self.intensity_slider.valueChanged.connect(self.update_intensity)
        self.exposure_sec.valueChanged.connect(self.update_exposure_sec)
        self.true_cell_threshold.valueChanged.connect(self.update_true_cell_threshold)
        self.crop_size.valueChanged.connect(self.update_crop_size)
        self.erosion_factor.valueChanged.connect(self.update_erosion_factor)

        # Connect do_illumination to settings and enable/disable widgets
        def set_illumination_enabled(enabled):
            for widget in [
                self.optical_config,
                self.intensity_slider,
                self.intensity_value_label,
                self.exposure_sec,
                self.advanced_btn,
                self.advanced_box
            ]:
                widget.setEnabled(enabled)
        self.do_illumination.toggled.connect(set_illumination_enabled)
        set_illumination_enabled(self.do_illumination.isChecked())
        self.do_illumination.toggled.connect(self.update_do_illumination)

        def set_control_enabled(enabled):
            for widget in [
                self.control_optical_config,
                self.control_intensity_slider,
                self.control_intensity_value_label,
                self.control_exposure,
            ]:
                widget.setEnabled(enabled)

        self.do_control.toggled.connect(set_control_enabled)
        set_control_enabled(self.do_control.isChecked())

        # Initialize from pipeline_settings if available
        if self.pipeline_settings is not None:
            stim = self.pipeline_settings.stim_settings
            # Set do_illumination if present, else default False
            if hasattr(stim, 'do_illuminate'):
                self.do_illumination.setChecked(stim.do_illuminate)
            else:
                self.do_illumination.setChecked(False)
            self.optical_config.setCurrentText(stim.preset.optical_configuration)
            self.intensity_slider.setValue(stim.preset.intensity)
            self.intensity_value_label.setText(str(stim.preset.intensity))
            self.exposure_sec.setValue(stim.preset.exposure_sec)
            self.true_cell_threshold.setValue(stim.true_cell_threshold)
            self.crop_size.setValue(stim.crop_size)
            self.erosion_factor.setValue(stim.erosion_factor)

    def update_do_illumination(self, checked: bool):
        if self.pipeline_settings is not None:
            self.pipeline_settings.stim_settings.do_illuminate = checked

    def update_optical_config(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.stim_settings.preset.optical_configuration = value

    def update_intensity(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.stim_settings.preset.intensity = value

    def update_exposure_sec(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.stim_settings.preset.exposure_sec = value

    def update_true_cell_threshold(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.stim_settings.true_cell_threshold = value

    def update_crop_size(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.stim_settings.crop_size = value

    def update_erosion_factor(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.stim_settings.erosion_factor = value

    def update_do_control(self, checked: bool):
        if self.pipeline_settings is not None:
            self.pipeline_settings.control_settings.control_loop = checked

    def update_control_optical(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.control_settings.preset.optical_configuration = value

    def update_control_intensity(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.control_settings.preset.intensity = value

    def update_control_exposure(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.control_settings.preset.exposure_ms = value

        
