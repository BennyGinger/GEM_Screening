from PyQt6.QtWidgets import QWidget, QFormLayout, QComboBox, QLabel

from gem_screening.settings.models import PipelineSettings

class AcquisitionPage(QWidget):
    def __init__(self, pipeline_settings: PipelineSettings):
        super().__init__()
        layout = QFormLayout(self)
        self.pipeline_settings = pipeline_settings

        # Objective
        self.objective = QComboBox()
        self.objective.addItems(["10x", "20x"])
        objective_label = QLabel("Objective")
        objective_label.setToolTip("The objective lens used for imaging, e.g., '10x' or '20x'. Defaults to '20x'.")
        layout.addRow(objective_label, self.objective)

        # Lamp Name
        self.lamp = QComboBox()
        self.lamp.addItems(["pE-800", "pE-4000", "DiaLamp"])
        lamp_label = QLabel("Lamp Name")
        lamp_label.setToolTip("The name of the lamp used for illumination, e.g., 'pE-800', 'pE-4000', or 'DiaLamp'. Defaults to 'pE-800'.")
        layout.addRow(lamp_label, self.lamp)

        # Focus Device
        self.focus = QComboBox()
        self.focus.addItems(["PFSOffset", "ZDrive"])
        focus_label = QLabel("Focus Device")
        focus_label.setToolTip("The device used for focusing, e.g., 'PFSOffset' or 'ZDrive'. Defaults to 'PFSOffset'.")
        layout.addRow(focus_label, self.focus)

        # Connect signals to update pipeline_settings
        self.objective.currentTextChanged.connect(self.update_objective)
        self.lamp.currentTextChanged.connect(self.update_lamp)
        self.focus.currentTextChanged.connect(self.update_focus)

        # Initialize from pipeline_settings if available
        if self.pipeline_settings is not None:
            acq = self.pipeline_settings.acquisition_settings
            self.objective.setCurrentText(acq.objective)
            self.lamp.setCurrentText(acq.lamp_name)
            self.focus.setCurrentText(acq.focus_device)

    def update_objective(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.acquisition_settings.objective = value

    def update_lamp(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.acquisition_settings.lamp_name = value

    def update_focus(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.acquisition_settings.focus_device = value
