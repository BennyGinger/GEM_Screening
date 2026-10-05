"""Standalone experiment selection dialog retained for compatibility."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gem_screening.settings.storage import load_gui_settings


class ExperimentStartupDialog(QDialog):
    """Choose between creating a new experiment and opening an existing one."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("GEM Screening")
        self.setMinimumWidth(560)
        self.project_path: Path | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Start a new experiment or open an existing experiment folder."))

        new_button = QPushButton("New Experiment")
        new_button.setToolTip("Open the settings template for a new experiment.")
        new_button.clicked.connect(self._new_experiment)
        layout.addWidget(new_button)

        layout.addWidget(QLabel("Open existing experiment"))
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Path to an experiment folder")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse)
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        open_button = QPushButton("Open Experiment")
        open_button.clicked.connect(self._open_experiment)
        layout.addWidget(open_button)

        cancel_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        cancel_buttons.rejected.connect(self.reject)
        layout.addWidget(cancel_buttons)

    def _new_experiment(self) -> None:
        self.project_path = None
        self.accept()

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select experiment folder",
            self.path_edit.text(),
        )
        if selected:
            self.path_edit.setText(selected)
            self.error_label.clear()

    def _open_experiment(self) -> None:
        selected = self.path_edit.text().strip()
        if not selected:
            self.error_label.setText("Select an experiment folder first.")
            return

        try:
            _, settings_path = load_gui_settings(selected)
        except (OSError, TypeError, ValueError) as error:
            self.error_label.setText(str(error))
            return

        if settings_path is None:
            self.error_label.setText("The selected folder does not contain project settings.")
            return
        self.project_path = settings_path
        self.accept()
