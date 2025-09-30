from typing import Callable

from numpy.typing import NDArray
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton, QFileDialog
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import QDateTime, Qt

from gem_screening.settings.models import PipelineSettings


from PyQt6.QtCore import pyqtSignal

class ControlsPanel(QWidget):
    mock_output_signal = pyqtSignal(str)

    def __init__(self, pipeline_settings: PipelineSettings, autofocus_callback: Callable[[NDArray], None]):
        super().__init__()
        self.pipeline_settings = pipeline_settings
        self.autofocus_callback = autofocus_callback  # Function to call for autofocus requests
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Experiment folder path
        path_layout = QHBoxLayout()
        path_label = QLabel("Experiment folder:")
        self.path_edit = QLineEdit()
        self.path_edit.setToolTip("Path to the main experiment folder where results will be saved.")
        self.path_edit.textChanged.connect(self.update_savedir)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # Timestamp + suffix
        ts_layout = QHBoxLayout()
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_")
        self.timestamp_label = QLabel(timestamp)
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setToolTip("Optional suffix to append to the experiment folder name.")
        self.suffix_edit.textChanged.connect(self.update_savedir_name)

        # If pipeline_settings provided, initialize fields from it
        if self.pipeline_settings is not None:
            if hasattr(self.pipeline_settings, 'savedir') and self.pipeline_settings.savedir:
                self.path_edit.setText(str(self.pipeline_settings.savedir))
            if hasattr(self.pipeline_settings, 'savedir_name') and self.pipeline_settings.savedir_name:
                self.suffix_edit.setText(str(self.pipeline_settings.savedir_name))
        ts_layout.addWidget(QLabel("Folder name:"))
        ts_layout.addWidget(self.timestamp_label)
        ts_layout.addWidget(self.suffix_edit)
        layout.addLayout(ts_layout)

        # Checkboxes
        self.cb_overwrite_calib = QCheckBox("Restart calibration")
        self.cb_overwrite_calib.setToolTip("If checked, the calibration will be restarted.")
        self.cb_overwrite_af = QCheckBox("Restart autofocus")
        self.cb_overwrite_af.setToolTip("If checked, the autofocus will be restarted.")
        layout.addWidget(self.cb_overwrite_calib)
        layout.addWidget(self.cb_overwrite_af)
        self.cb_overwrite_calib.toggled.connect(self.update_overwrite_calib)
        self.cb_overwrite_af.toggled.connect(self.update_overwrite_autofocus)
    
        # Settings
        self.settings_btn = QPushButton("Settings")
        layout.addWidget(self.settings_btn)
        layout.addStretch(1)  # Pushes the next widget(s) to the bottom
        
        # Process
        self.process_btn = QPushButton("Process")
        self.process_btn.setStyleSheet("background-color: #c0392b; color: white;")
        layout.addWidget(self.process_btn)

        # For now, connect to a mock pipeline launcher
        self.process_btn.clicked.connect(self.mock_pipeline)


    def mock_pipeline(self):
        # This function mimics launching the pipeline and can be extended to show pop-up or embedded GUI
        msg = f"[MOCK] Pipeline would launch here with settings: {self.pipeline_settings.__dict__.keys()}"
        self.mock_output_signal.emit(msg)
        # Use the callback if provided, else fallback to signal (for backward compatibility)
        try:
            from tifffile import imread
            dummy_img = imread('/media/ben/Analysis/Python/Docker_mount/Test_images/nd2/Run3/c3z1t1v3_s1/Images/C1_s01_f0001_z0001.tif')
            self.autofocus_callback(dummy_img)
        except Exception as e:
            self.mock_output_signal.emit(f"[MOCK] Could not emit autofocus GUI: {e}")
        
    def update_savedir(self):
        if self.pipeline_settings is not None:
            self.pipeline_settings.savedir = self.path_edit.text()

    def update_savedir_name(self):
        if self.pipeline_settings is not None:
            self.pipeline_settings.savedir_name = self.suffix_edit.text()

    def browse_folder(self):
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        if dlg.exec():
            selected = dlg.selectedFiles()
            if selected:
                self.path_edit.setText(selected[0])
    
    def update_overwrite_calib(self, checked):
        if self.pipeline_settings is not None and hasattr(self.pipeline_settings, 'dish_settings'):
            self.pipeline_settings.dish_settings.overwrite_calib = checked

    def update_overwrite_autofocus(self, checked):
        if self.pipeline_settings is not None and hasattr(self.pipeline_settings, 'dish_settings'):
            self.pipeline_settings.dish_settings.overwrite_autofocus = checked
