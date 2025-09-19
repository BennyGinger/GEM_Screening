from PyQt6.QtWidgets import QWidget, QFormLayout, QSpinBox, QComboBox, QLabel

class StimPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        # True Cell Threshold
        self.true_cell_threshold = QSpinBox()
        self.true_cell_threshold.setRange(0, 1000)
        true_cell_label = QLabel("True Cell Threshold")
        true_cell_label.setToolTip("Mean intensity threshold for true cell detection. Below this value, cells are considered noise and set to 0 in the output. Defaults to 50.")
        layout.addRow(true_cell_label, self.true_cell_threshold)
        # Crop Size
        self.crop_size = QSpinBox()
        self.crop_size.setRange(1, 10000)
        crop_label = QLabel("Crop Size")
        crop_label.setToolTip("Size of the crop for the display of the ROI, for the CellTinder GUI, to select positive cells. Defaults to 251.")
        layout.addRow(crop_label, self.crop_size)
        # Erosion Factor
        self.erosion_factor = QSpinBox()
        self.erosion_factor.setRange(0, 100)
        erosion_label = QLabel("Erosion Factor")
        erosion_label.setToolTip("Erosion factor for the stimulation masks to avoid stimulation of neighboring cells. Defaults to 3.")
        layout.addRow(erosion_label, self.erosion_factor)
        # Optical Config
        self.optical_config = QComboBox()
        self.optical_config.addItems(["BFP", "RFP", "GFP", "iRed"])
        optical_label = QLabel("Optical Config")
        optical_label.setToolTip("Optical configuration for the preset, e.g., 'BFP' or 'RFP'. Defaults to 'BFP'.")
        layout.addRow(optical_label, self.optical_config)
        # Intensity
        self.intensity = QSpinBox()
        self.intensity.setRange(0, 100)
        intensity_label = QLabel("Intensity")
        intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 100.")
        layout.addRow(intensity_label, self.intensity)
        # Exposure (sec)
        self.exposure_sec = QSpinBox()
        self.exposure_sec.setRange(1, 10000)
        exposure_label = QLabel("Exposure (sec)")
        exposure_label.setToolTip("Exposure time in seconds for the preset. Defaults to 10.")
        layout.addRow(exposure_label, self.exposure_sec)
