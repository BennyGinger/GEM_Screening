"""Experiment location and top-level settings panel."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gem_screening.settings.models import PipelineSettings
from gem_screening.gui.settings.pages.logging_page import LoggingPage
from gem_screening.infrastructure.filesystem import timestamped_dir_path


class ProjectSettingsPanel(QGroupBox):
    """Project location and top-level pipeline settings."""

    def __init__(self, pipeline_settings: PipelineSettings, parent: QWidget | None = None, *, include_logging: bool = False) -> None:
        super().__init__("Experiment", parent)
        self.pipeline_settings = pipeline_settings

        layout = QFormLayout(self)

        self.savedir_edit = QLineEdit(pipeline_settings.savedir)
        self.savedir_edit.setPlaceholderText("Select the parent folder for experiments")
        self.savedir_edit.setToolTip(
            "Parent folder in which the timestamped experiment folder will be created."
        )
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self._browse_savedir)
        self.savedir_row = QHBoxLayout()
        self.savedir_row.addWidget(self.savedir_edit, 3)
        self.savedir_row.addWidget(self.browse_button)
        if include_logging:
            self.savedir_row.insertWidget(0, QLabel("User folder"))
            layout.addRow(self.savedir_row)
        else:
            layout.addRow(QLabel("User folder"), self.savedir_row)

        self.experiment_name_edit = QLineEdit(pipeline_settings.savedir_name)
        self.experiment_name_edit.setPlaceholderText("Enter an experiment name")
        self.experiment_name_edit.setToolTip(
            "Name appended to the date when the experiment folder is created."
        )
        if include_logging:
            self.savedir_row.addWidget(QLabel("Experiment name"))
            self.savedir_row.addWidget(self.experiment_name_edit, 2)
        else:
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
        advanced_layout = QGridLayout(self.advanced_box)
        advanced_layout.setColumnStretch(1, 1)
        advanced_layout.setColumnStretch(3, 1)

        self.dev_mode = QCheckBox()
        self.dev_mode.setChecked(pipeline_settings.dev_mode)
        self.dev_mode.setToolTip(
            "Keep Docker services running after the pipeline finishes."
        )
        advanced_layout.addWidget(QLabel("Development mode"), 0, 0)
        advanced_layout.addWidget(self.dev_mode, 0, 1)

        self.base_url_edit = QLineEdit(pipeline_settings.base_url)
        self.base_url_edit.setToolTip("Hostname or address used for pipeline services.")
        advanced_layout.addWidget(QLabel("Server address"), 0, 2)
        advanced_layout.addWidget(self.base_url_edit, 0, 3)
        if include_logging:
            self.logging_page = LoggingPage(pipeline_settings)
            logging_layout = self.logging_page.layout()
            column = 0
            while logging_layout.rowCount():
                row = logging_layout.takeRow(0)
                advanced_layout.addWidget(row.labelItem.widget(), 1, column)
                advanced_layout.addWidget(row.fieldItem.widget(), 1, column + 1)
                column += 2
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
        self._update_run_directory_preview()

    def _update_experiment_name(self, value: str) -> None:
        self.pipeline_settings.savedir_name = value
        self._update_run_directory_preview()

    def _update_dev_mode(self, checked: bool) -> None:
        self.pipeline_settings.dev_mode = checked

    def _update_base_url(self, value: str) -> None:
        self.pipeline_settings.base_url = value

    def _update_run_directory_preview(self) -> None:
        settings_path = getattr(self, "settings_path", None)
        folder = settings_path.parent.parent if settings_path else timestamped_dir_path(
            self.pipeline_settings.savedir, self.pipeline_settings.savedir_name
        )
        self.run_directory_preview.setText(str(folder))
        self.run_directory_preview.setToolTip(str(folder))
