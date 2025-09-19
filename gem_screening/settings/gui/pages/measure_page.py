from PyQt6.QtWidgets import QWidget, QFormLayout, QGroupBox, QVBoxLayout, QCheckBox, QComboBox, QSpinBox, QLabel

class MeasurePage(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)

        # Preset Measure group
        preset_group = QGroupBox("Measurement Preset")
        preset_layout = QFormLayout(preset_group)
        self.optical_config = QComboBox()
        self.optical_config.addItems(["GFP", "iRed", "BFP", "RFP"])
        optical_label = QLabel("Optical Config")
        optical_label.setToolTip("Optical configuration for the preset, e.g., 'GFP', 'iRed', 'BFP', or 'RFP'. Defaults to 'GFP'.")
        self.intensity = QSpinBox()
        self.intensity.setRange(0, 100)
        intensity_label = QLabel("Intensity")
        intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 25.")
        self.exposure = QSpinBox()
        self.exposure.setRange(1, 10000)
        exposure_label = QLabel("Exposure (ms)")
        exposure_label.setToolTip("Exposure time in milliseconds for the preset. Defaults to 100.")
        preset_layout.addRow(optical_label, self.optical_config)
        preset_layout.addRow(intensity_label, self.intensity)
        preset_layout.addRow(exposure_label, self.exposure)
        main_layout.addWidget(preset_group)

        # Do Reference Segmentation
        self.do_refseg = QCheckBox("Do Reference Segmentation")
        self.do_refseg.setToolTip("If True, will perform reference segmentation. Defaults to True.")
        main_layout.addWidget(self.do_refseg)

        # Preset Refseg group
        refseg_group = QGroupBox("Reference Segmentation Preset")
        refseg_layout = QFormLayout(refseg_group)
        self.ref_optical_config = QComboBox()
        self.ref_optical_config.addItems(["iRed", "GFP", "BFP", "RFP"])
        ref_optical_label = QLabel("Optical Config")
        ref_optical_label.setToolTip("Optical configuration for the preset, e.g., 'iRed'. Defaults to 'iRed'.")
        self.ref_intensity = QSpinBox()
        self.ref_intensity.setRange(0, 100)
        ref_intensity_label = QLabel("Intensity")
        ref_intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 5.")
        self.ref_exposure = QSpinBox()
        self.ref_exposure.setRange(1, 10000)
        ref_exposure_label = QLabel("Exposure (ms)")
        ref_exposure_label.setToolTip("Exposure time in milliseconds for the preset. Defaults to 100.")
        refseg_layout.addRow(ref_optical_label, self.ref_optical_config)
        refseg_layout.addRow(ref_intensity_label, self.ref_intensity)
        refseg_layout.addRow(ref_exposure_label, self.ref_exposure)
        main_layout.addWidget(refseg_group)
