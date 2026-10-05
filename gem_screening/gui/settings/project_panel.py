"""Experiment location and top-level settings panel."""

from datetime import datetime

from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gem_screening.settings.models import PipelineSettings


class ProjectSettingsPanel(QGroupBox):
    """Project location and top-level pipeline settings."""

    def __init__(self, pipeline_settings: PipelineSettings, parent: QWidget | None = None) -> None:
        super().__init__("Experiment", parent)
        self.pipeline_settings = pipeline_settings

        layout = QFormLayout(self)

        self.savedir_edit = QLineEdit(pipeline_settings.savedir)
        self.savedir_edit.setPlaceholderText("Select the parent folder for experiments")
        self.savedir_edit.setToolTip(
            "Parent folder in which the timestamped experiment folder will be created."
        )
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_savedir)
        savedir_row = QHBoxLayout()
        savedir_row.addWidget(self.savedir_edit, 1)
        savedir_row.addWidget(browse_button)
        layout.addRow(QLabel("User folder"), savedir_row)

        self.experiment_name_edit = QLineEdit(pipeline_settings.savedir_name)
        self.experiment_name_edit.setPlaceholderText("Enter an experiment name")
        self.experiment_name_edit.setToolTip(
            "Name appended to the date when the experiment folder is created."
        )
        layout.addRow(QLabel("Experiment name"), self.experiment_name_edit)

        self.run_directory_preview = QLabel()
        self.run_directory_preview.setToolTip("Name of the experiment folder that will be used.")
        layout.addRow(QLabel("Experiment folder"), self.run_directory_preview)

        self.advanced_button = QPushButton("Show Advanced Settings")
        self.advanced_button.setCheckable(True)
        self.advanced_button.toggled.connect(self._toggle_advanced)
        layout.addRow(self.advanced_button)

        self.advanced_box = QGroupBox()
        self.advanced_box.setVisible(False)
        advanced_layout = QFormLayout(self.advanced_box)

        self.dev_mode = QCheckBox()
        self.dev_mode.setChecked(pipeline_settings.dev_mode)
        self.dev_mode.setToolTip(
            "Keep Docker services running after the pipeline finishes."
        )
        advanced_layout.addRow(QLabel("Development mode"), self.dev_mode)

        self.base_url_edit = QLineEdit(pipeline_settings.base_url)
        self.base_url_edit.setToolTip("Hostname or address used for pipeline services.")
        advanced_layout.addRow(QLabel("Server address"), self.base_url_edit)
        layout.addRow(self.advanced_box)

        self.savedir_edit.textChanged.connect(self._update_savedir)
        self.experiment_name_edit.textChanged.connect(self._update_experiment_name)
        self.dev_mode.toggled.connect(self._update_dev_mode)
        self.base_url_edit.textChanged.connect(self._update_base_url)
        self._update_run_directory_preview()

    def _browse_savedir(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select user folder",
            self.savedir_edit.text(),
        )
        if selected:
            self.savedir_edit.setText(selected)

    def _toggle_advanced(self, visible: bool) -> None:
        self.advanced_box.setVisible(visible)
        self.advanced_button.setText(
            "Hide Advanced Settings" if visible else "Show Advanced Settings"
        )

    def _update_savedir(self, value: str) -> None:
        self.pipeline_settings.savedir = value

    def _update_experiment_name(self, value: str) -> None:
        self.pipeline_settings.savedir_name = value
        self._update_run_directory_preview()

    def _update_dev_mode(self, checked: bool) -> None:
        self.pipeline_settings.dev_mode = checked

    def _update_base_url(self, value: str) -> None:
        self.pipeline_settings.base_url = value

    def _update_run_directory_preview(self) -> None:
        date_prefix = datetime.now().strftime("%Y%m%d")
        experiment_name = self.experiment_name_edit.text().strip()
        folder_name = f"{date_prefix}_{experiment_name}" if experiment_name else date_prefix
        self.run_directory_preview.setText(folder_name)
