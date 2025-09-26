from PyQt6.QtWidgets import QWidget, QFormLayout, QGroupBox, QVBoxLayout, QCheckBox, QComboBox, QSpinBox, QLabel, QSlider, QHBoxLayout
from PyQt6.QtCore import Qt

from gem_screening.settings.models import PipelineSettings

class MeasurePage(QWidget):
    def __init__(self, pipeline_settings: PipelineSettings):
        super().__init__()
        self.pipeline_settings = pipeline_settings
        main_layout = QVBoxLayout(self)

        # Preset Measure group
        preset_group = QGroupBox("Measurement Preset")
        preset_layout = QFormLayout(preset_group)
        self.optical_config = QComboBox()
        self.optical_config.addItems(["GFP", "iRed", "BFP", "RFP"])
        optical_label = QLabel("Optical Config")
        optical_label.setToolTip("Optical configuration for the preset, e.g., 'GFP', 'iRed', 'BFP', or 'RFP'. Defaults to 'GFP'.")
        self.intensity_slider = QSlider()
        self.intensity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 100)
        self.intensity_value_label = QLabel("25")
        intensity_label = QLabel("Intensity")
        intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 25.")
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(self.intensity_slider)
        intensity_layout.addWidget(self.intensity_value_label)
        self.intensity_slider.valueChanged.connect(lambda v: self.intensity_value_label.setText(str(v)))
        self.exposure = QSpinBox()
        self.exposure.setRange(1, 10000)
        self.exposure.setSingleStep(10)
        exposure_label = QLabel("Exposure (ms)")
        exposure_label.setToolTip("Exposure time in milliseconds for the preset. Defaults to 100.")
        preset_layout.addRow(optical_label, self.optical_config)
        preset_layout.addRow(intensity_label, intensity_layout)
        preset_layout.addRow(exposure_label, self.exposure)
        main_layout.addWidget(preset_group)


        # Preset Refseg group with checkbox as title
        self.refseg_group = QGroupBox()
        self.do_refseg = QCheckBox("Do Reference Segmentation")
        self.do_refseg.setChecked(True)
        self.do_refseg.setToolTip("If True, will perform reference segmentation. Defaults to True.")
        # Place checkbox as groupbox title using layout
        refseg_title_layout = QHBoxLayout()
        refseg_title_layout.addWidget(self.do_refseg)
        refseg_title_layout.addStretch(1)
        refseg_main_layout = QVBoxLayout(self.refseg_group)
        refseg_main_layout.addLayout(refseg_title_layout)
        refseg_layout = QFormLayout()
        self.ref_optical_config = QComboBox()
        self.ref_optical_config.addItems(["iRed", "GFP", "BFP", "RFP"])
        ref_optical_label = QLabel("Optical Config")
        ref_optical_label.setToolTip("Optical configuration for the preset, e.g., 'iRed'. Defaults to 'iRed'.")
        self.ref_intensity_slider = QSlider()
        self.ref_intensity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.ref_intensity_slider.setRange(0, 100)
        self.ref_intensity_value_label = QLabel("5")
        ref_intensity_label = QLabel("Intensity")
        ref_intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 5.")
        ref_intensity_layout = QHBoxLayout()
        ref_intensity_layout.addWidget(self.ref_intensity_slider)
        ref_intensity_layout.addWidget(self.ref_intensity_value_label)
        self.ref_intensity_slider.valueChanged.connect(lambda v: self.ref_intensity_value_label.setText(str(v)))
        self.ref_exposure = QSpinBox()
        self.ref_exposure.setRange(1, 10000)
        self.ref_exposure.setSingleStep(10)
        ref_exposure_label = QLabel("Exposure (ms)")
        ref_exposure_label.setToolTip("Exposure time in milliseconds for the preset. Defaults to 100.")
        refseg_layout.addRow(ref_optical_label, self.ref_optical_config)
        refseg_layout.addRow(ref_intensity_label, ref_intensity_layout)
        refseg_layout.addRow(ref_exposure_label, self.ref_exposure)
        refseg_main_layout.addLayout(refseg_layout)
        main_layout.addWidget(self.refseg_group)
        # Enable/disable controls based on checkbox, but keep group visible
        # Control Imaging Loop group (like refseg)
        self.control_group = QGroupBox()
        self.do_control = QCheckBox("Do Control Imaging Loop")
        self.do_control.setChecked(True)
        self.do_control.setToolTip("If True, will perform a control imaging loop before and after light stimulation. Defaults to True.")
        control_title_layout = QHBoxLayout()
        control_title_layout.addWidget(self.do_control)
        control_title_layout.addStretch(1)
        control_main_layout = QVBoxLayout(self.control_group)
        control_main_layout.addLayout(control_title_layout)
        control_layout = QFormLayout()
        self.control_optical_config = QComboBox()
        self.control_optical_config.addItems(["RFP", "GFP", "iRed", "BFP"])
        control_optical_label = QLabel("Optical Config")
        control_optical_label.setToolTip("Optical configuration for the preset, e.g., 'RFP'. Defaults to 'RFP'.")
        self.control_intensity_slider = QSlider()
        self.control_intensity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.control_intensity_slider.setRange(0, 100)
        self.control_intensity_value_label = QLabel("40")
        control_intensity_label = QLabel("Intensity")
        control_intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 40.")
        control_intensity_layout = QHBoxLayout()
        control_intensity_layout.addWidget(self.control_intensity_slider)
        control_intensity_layout.addWidget(self.control_intensity_value_label)
        self.control_intensity_slider.valueChanged.connect(lambda v: self.control_intensity_value_label.setText(str(v)))
        self.control_exposure = QSpinBox()
        self.control_exposure.setRange(1, 10000)
        control_exposure_label = QLabel("Exposure (ms)")
        control_exposure_label.setToolTip("Exposure time in milliseconds for the preset. Defaults to 100.")
        control_layout.addRow(control_optical_label, self.control_optical_config)
        control_layout.addRow(control_intensity_label, control_intensity_layout)
        control_layout.addRow(control_exposure_label, self.control_exposure)
        control_main_layout.addLayout(control_layout)
        main_layout.addWidget(self.control_group)
        # Enable/disable controls based on checkbox, but keep group visible
        def set_control_enabled(enabled):
            for widget in [
                self.control_optical_config,
                self.control_intensity_slider,
                self.control_intensity_value_label,
                self.control_exposure
            ]:
                widget.setEnabled(enabled)
        self.do_control.toggled.connect(set_control_enabled)
        set_control_enabled(self.do_control.isChecked())
        
        # Enable/disable controls based on checkbox, but keep group visible
        def set_refseg_enabled(enabled):
            for widget in [
                self.ref_optical_config,
                self.ref_intensity_slider,
                self.ref_intensity_value_label,
                self.ref_exposure
            ]:
                widget.setEnabled(enabled)
        self.do_refseg.toggled.connect(set_refseg_enabled)
        set_refseg_enabled(self.do_refseg.isChecked())
        
        # Connect signals to update pipeline_settings
        self.optical_config.currentTextChanged.connect(self.update_measure_optical)
        self.intensity_slider.valueChanged.connect(self.update_measure_intensity)
        self.exposure.valueChanged.connect(self.update_measure_exposure)
        self.do_refseg.toggled.connect(self.update_do_refseg)
        self.ref_optical_config.currentTextChanged.connect(self.update_refseg_optical)
        self.ref_intensity_slider.valueChanged.connect(self.update_refseg_intensity)
        self.ref_exposure.valueChanged.connect(self.update_refseg_exposure)
        self.do_control.toggled.connect(self.update_do_control)
        self.control_optical_config.currentTextChanged.connect(self.update_control_optical)
        self.control_intensity_slider.valueChanged.connect(self.update_control_intensity)
        self.control_exposure.valueChanged.connect(self.update_control_exposure)
    
        # Initialize from pipeline_settings if available
        if self.pipeline_settings is not None:
            ms = self.pipeline_settings.measure_settings
            self.optical_config.setCurrentText(ms.preset_measure.optical_configuration)
            self.intensity_slider.setValue(ms.preset_measure.intensity)
            self.intensity_value_label.setText(str(ms.preset_measure.intensity))
            self.exposure.setValue(ms.preset_measure.exposure_ms)
            self.do_refseg.setChecked(ms.do_refseg)
            self.ref_optical_config.setCurrentText(ms.preset_refseg.optical_configuration)
            self.ref_intensity_slider.setValue(ms.preset_refseg.intensity)
            self.ref_intensity_value_label.setText(str(ms.preset_refseg.intensity))
            self.ref_exposure.setValue(ms.preset_refseg.exposure_ms)
            cs = self.pipeline_settings.control_settings
            self.do_control.setChecked(cs.control_loop)
            self.control_optical_config.setCurrentText(cs.preset.optical_configuration)
            self.control_intensity_slider.setValue(cs.preset.intensity)
            self.control_intensity_value_label.setText(str(cs.preset.intensity))
            self.control_exposure.setValue(cs.preset.exposure_ms)

    def update_measure_optical(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_measure.optical_configuration = value

    def update_measure_intensity(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_measure.intensity = value

    def update_measure_exposure(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_measure.exposure_ms = value

    def update_do_refseg(self, checked: bool):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.do_refseg = checked

    def update_refseg_optical(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_refseg.optical_configuration = value

    def update_refseg_intensity(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_refseg.intensity = value

    def update_refseg_exposure(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_refseg.exposure_ms = value

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
        
        
