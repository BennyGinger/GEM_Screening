from PyQt6.QtWidgets import QWidget, QFormLayout, QSpinBox, QComboBox, QLabel, QGroupBox, QPushButton, QSlider, QHBoxLayout
from PyQt6.QtCore import Qt

from gem_screening.settings.models import PipelineSettings

class StimPage(QWidget):
    def __init__(self, pipeline_settings: PipelineSettings):
        super().__init__()
        self.pipeline_settings = pipeline_settings
        layout = QFormLayout(self)

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

        # Connect signals to update pipeline_settings (at the end of __init__)
        self.optical_config.currentTextChanged.connect(self.update_optical_config)
        self.intensity_slider.valueChanged.connect(self.update_intensity)
        self.exposure_sec.valueChanged.connect(self.update_exposure_sec)
        self.true_cell_threshold.valueChanged.connect(self.update_true_cell_threshold)
        self.crop_size.valueChanged.connect(self.update_crop_size)
        self.erosion_factor.valueChanged.connect(self.update_erosion_factor)

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

        # Connect signals to update pipeline_settings (at the end of __init__)
        self.optical_config.currentTextChanged.connect(self.update_optical_config)
        self.intensity_slider.valueChanged.connect(self.update_intensity)
        self.exposure_sec.valueChanged.connect(self.update_exposure_sec)
        self.true_cell_threshold.valueChanged.connect(self.update_true_cell_threshold)
        self.crop_size.valueChanged.connect(self.update_crop_size)
        self.erosion_factor.valueChanged.connect(self.update_erosion_factor)

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
        
        