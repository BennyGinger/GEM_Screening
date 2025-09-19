from PyQt6.QtWidgets import QWidget, QFormLayout, QCheckBox, QComboBox, QSpinBox, QLabel

class ControlPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        # Control Loop
        self.control_loop = QCheckBox()
        control_loop_label = QLabel("Control Loop")
        control_loop_label.setToolTip("If True, will perform a control imaging loop before and after light stimulation. Defaults to True.")
        layout.addRow(control_loop_label, self.control_loop)
        # Optical Config
        self.optical_config = QComboBox()
        self.optical_config.addItems(["RFP", "GFP", "iRed", "BFP"])
        optical_label = QLabel("Optical Config")
        optical_label.setToolTip("Optical configuration for the preset, e.g., 'RFP'. Defaults to 'RFP'.")
        layout.addRow(optical_label, self.optical_config)
        # Intensity
        self.intensity = QSpinBox()
        self.intensity.setRange(0, 100)
        intensity_label = QLabel("Intensity")
        intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 40.")
        layout.addRow(intensity_label, self.intensity)
        # Exposure (ms)
        self.exposure = QSpinBox()
        self.exposure.setRange(1, 10000)
        exposure_label = QLabel("Exposure (ms)")
        exposure_label.setToolTip("Exposure time in milliseconds for the preset. Defaults to 100.")
        layout.addRow(exposure_label, self.exposure)
