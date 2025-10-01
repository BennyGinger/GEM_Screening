from typing import Callable
from pathlib import Path

from numpy.typing import NDArray
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton, QFileDialog
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import QDateTime, Qt

from gem_screening.settings.models import PipelineSettings


# TODO: Check all the append_terminal calls and see if any need to be removed

class ControlsPanel(QWidget):
    mock_output_signal = pyqtSignal(str)
    process_finished = pyqtSignal()


    def __init__(self, pipeline_settings: PipelineSettings, autofocus_callback: Callable[[NDArray], None], celltinder_callback: Callable[[Path, int, int], None]):
        super().__init__()
        self.pipeline_settings = pipeline_settings
        self.autofocus_callback = autofocus_callback  # Function to call for autofocus requests
        self.celltinder_callback = celltinder_callback  # Function to call for celltinder launch
        
        # Add autofocus state tracking
        self.autofocus_result = None
        self.autofocus_waiting = False

        # Create a main layout and a content widget for easy disabling
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._content_widget = QWidget(self)
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._main_layout.addWidget(self._content_widget)

        # Experiment folder path
        path_layout = QHBoxLayout()
        path_label = QLabel("Experiment folder:")
        self.path_edit = QLineEdit()
        self.path_edit.setToolTip("Path to the main experiment folder where results will be saved.")
        self.path_edit.textChanged.connect(self.update_savedir)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        self._content_layout.addLayout(path_layout)

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
        self._content_layout.addLayout(ts_layout)

        # Checkboxes
        self.cb_overwrite_calib = QCheckBox("Restart calibration")
        self.cb_overwrite_calib.setToolTip("If checked, the calibration will be restarted.")
        self.cb_overwrite_af = QCheckBox("Restart autofocus")
        self.cb_overwrite_af.setToolTip("If checked, the autofocus will be restarted.")
        self._content_layout.addWidget(self.cb_overwrite_calib)
        self._content_layout.addWidget(self.cb_overwrite_af)
        self.cb_overwrite_calib.toggled.connect(self.update_overwrite_calib)
        self.cb_overwrite_af.toggled.connect(self.update_overwrite_autofocus)

        # Settings
        self.settings_btn = QPushButton("Settings")
        self._content_layout.addWidget(self.settings_btn)
        self._content_layout.addStretch(1)  # Pushes the next widget(s) to the bottom

        # Process
        self.process_btn = QPushButton("Process")
        self.process_btn.setStyleSheet("background-color: #c0392b; color: white;")
        self._content_layout.addWidget(self.process_btn)

        # For now, connect to a mock pipeline launcher
        self.process_btn.clicked.connect(self.lock_and_run_process)
        # Connect process_finished signal to unlock_controls slot
        self.process_finished.connect(self.unlock_controls)

    def lock_and_run_process(self):
        # Disable the entire content widget (all controls)
        self._content_widget.setEnabled(False)
        self.mock_pipeline()

    def unlock_controls(self):
        self._content_widget.setEnabled(True)

    def mock_pipeline(self):
        """
        This function mimics the full pipeline flow:
        1. Start autofocus in a loop until user decides (continue/quit)
        2. Do pipeline processing steps
        3. Call CellTinder
        4. Only unlock controls when entire pipeline is done
        """
        msg = f"[MOCK] Pipeline starting with settings: {list(self.pipeline_settings.__dict__.keys())}"
        self.mock_output_signal.emit(msg)
        try:
            from tifffile import imread
            from pathlib import Path
            from PyQt6.QtCore import QCoreApplication
            
            # Step 1: Autofocus loop until user decides
            while True:
                dummy_img = imread('/media/ben/Analysis/Python/Docker_mount/Test_images/nd2/Run3/c3z1t1v3_s1/Images/C1_s01_f0001_z0001.tif')
                self.autofocus_waiting = True
                self.autofocus_result = None
                self.autofocus_callback(dummy_img)
                
                # Wait for autofocus decision
                while self.autofocus_waiting:
                    QCoreApplication.processEvents()
                
                if self.autofocus_result == "continue":
                    self.mock_output_signal.emit("[MOCK] Autofocus accepted, continuing...")
                    break
                elif self.autofocus_result == "quit":
                    self.mock_output_signal.emit("[MOCK] Pipeline quit by user")
                    self.process_finished.emit()
                    return
                elif self.autofocus_result == "restart":
                    self.mock_output_signal.emit("[MOCK] Restarting autofocus...")
                    continue
            
            # Step 2: Simulate pipeline processing
            self.mock_output_signal.emit("[MOCK] Processing acquisition data...")
            self.mock_output_signal.emit("[MOCK] Analyzing cell positions...")
            
            # Step 3: Call CellTinder
            csv_path = Path('/media/ben/Analysis/Python/CellTinder/ImagesTest/A1/A1_cell_data.csv')
            n_frames = 2
            crop_size = 151
            self.celltinder_callback(csv_path, n_frames, crop_size)
            
        except Exception as e:
            self.mock_output_signal.emit(f"[MOCK] Could not start pipeline: {e}")
            # If error, unlock controls immediately
            self.process_finished.emit()

    def set_autofocus_result(self, result: str):
        """Called by main window to set autofocus result and exit waiting loop"""
        self.autofocus_result = result
        self.autofocus_waiting = False
        
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
