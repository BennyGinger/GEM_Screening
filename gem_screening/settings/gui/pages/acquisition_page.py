from PyQt6.QtWidgets import QWidget, QFormLayout, QComboBox, QLabel

class AcquisitionPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        # Objective
        self.objective = QComboBox()
        self.objective.addItems(["10x", "20x"])
        self.objective.setCurrentText("20x")
        objective_label = QLabel("Objective")
        objective_label.setToolTip("The objective lens used for imaging, e.g., '10x' or '20x'. Defaults to '20x'.")
        layout.addRow(objective_label, self.objective)
        # Lamp Name
        self.lamp = QComboBox()
        self.lamp.addItems(["pE-800", "pE-4000", "DiaLamp"])
        self.lamp.setCurrentText("pE-800")
        lamp_label = QLabel("Lamp Name")
        lamp_label.setToolTip("The name of the lamp used for illumination, e.g., 'pE-800', 'pE-4000', or 'DiaLamp'. Defaults to 'pE-800'.")
        layout.addRow(lamp_label, self.lamp)
        # Focus Device
        self.focus = QComboBox()
        self.focus.addItems(["PFSOffset", "ZDrive"])
        self.focus.setCurrentText("PFSOffset")
        focus_label = QLabel("Focus Device")
        focus_label.setToolTip("The device used for focusing, e.g., 'PFSOffset' or 'ZDrive'. Defaults to 'PFSOffset'.")
        layout.addRow(focus_label, self.focus)
