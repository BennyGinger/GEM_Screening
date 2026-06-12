from typing import Callable
from pathlib import Path

from numpy.typing import NDArray
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt

from gem_screening.settings.models import PipelineSettings
from gem_screening.main_gui.controls.experiment_folder_selector import ExperimentFolderSelector
from gem_screening.main_gui.controls.timestamp_suffix_editor import TimestampSuffixEditor
from gem_screening.main_gui.controls.calib_af_checkboxes import CalibrationAutofocusCheckboxes
from gem_screening.main_gui.controls.settings_process_buttons import SettingsProcessButtons
from gem_screening.main_gui.mock_pipeline_runner import MockPipelineRunner


# TODO: Check all the append_terminal calls and see if any need to be removed
class ControlsPanel(QWidget):
    mock_output_signal = pyqtSignal(str)
    process_finished = pyqtSignal()

    def __init__(self, pipeline_settings: PipelineSettings, autofocus_callback: Callable[[NDArray], None], celltinder_callback: Callable[[Path, int, int], None]):
        super().__init__()
        self.pipeline_settings = pipeline_settings
        self.autofocus_callback = autofocus_callback
        self.celltinder_callback = celltinder_callback

        # Set up mock pipeline runner
        self.pipeline_runner = MockPipelineRunner(
            self.pipeline_settings,
            autofocus_callback=self.handle_autofocus_request,
            celltinder_callback=self.celltinder_callback
        )
        self.pipeline_runner.output_signal.connect(self.mock_output_signal.emit)
        self.pipeline_runner.finished_signal.connect(self.process_finished.emit)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Experiment folder selector
        initial_path = str(getattr(self.pipeline_settings, 'savedir', '')) if self.pipeline_settings else ''
        self.folder_selector = ExperimentFolderSelector(
            initial_path=initial_path,
            on_path_changed=self.update_savedir
        )
        main_layout.addWidget(self.folder_selector)

        # Timestamp and suffix editor
        initial_suffix = str(getattr(self.pipeline_settings, 'savedir_name', '')) if self.pipeline_settings else ''
        self.suffix_editor = TimestampSuffixEditor(
            initial_suffix=initial_suffix,
            on_suffix_changed=self.update_savedir_name
        )
        main_layout.addWidget(self.suffix_editor)

        # Calibration/autofocus checkboxes
        overwrite_calib = False
        overwrite_af = False
        if self.pipeline_settings and hasattr(self.pipeline_settings, 'dish_settings'):
            overwrite_calib = getattr(self.pipeline_settings.dish_settings, 'overwrite_calib', False)
            overwrite_af = getattr(self.pipeline_settings.dish_settings, 'overwrite_autofocus', False)
        self.checkboxes = CalibrationAutofocusCheckboxes(
            overwrite_calib=overwrite_calib,
            overwrite_af=overwrite_af,
            on_calib_changed=self.update_overwrite_calib,
            on_af_changed=self.update_overwrite_autofocus
        )
        main_layout.addWidget(self.checkboxes)

        # Settings and process buttons
        self.buttons = SettingsProcessButtons(
            on_settings_clicked=self.on_settings_clicked,
            on_process_clicked=self.lock_and_run_process
        )
        main_layout.addWidget(self.buttons)

        self.process_finished.connect(self.unlock_controls)



    def lock_and_run_process(self):
        self.setEnabled(False)
        self.pipeline_runner.run()

    def unlock_controls(self):
        self.setEnabled(True)

    def handle_autofocus_request(self, dummy_img):
        self.autofocus_callback(dummy_img)



    def set_autofocus_result(self, result: str):
        self.pipeline_runner.set_autofocus_result(result)

    def update_savedir(self, path):
        if self.pipeline_settings is not None:
            self.pipeline_settings.savedir = path

    def update_savedir_name(self, suffix):
        if self.pipeline_settings is not None:
            self.pipeline_settings.savedir_name = suffix

    def update_overwrite_calib(self, checked):
        if self.pipeline_settings is not None and hasattr(self.pipeline_settings, 'dish_settings'):
            self.pipeline_settings.dish_settings.overwrite_calib = checked

    def update_overwrite_autofocus(self, checked):
        if self.pipeline_settings is not None and hasattr(self.pipeline_settings, 'dish_settings'):
            self.pipeline_settings.dish_settings.overwrite_autofocus = checked

    def on_settings_clicked(self):
        # Placeholder for settings button logic
        pass
