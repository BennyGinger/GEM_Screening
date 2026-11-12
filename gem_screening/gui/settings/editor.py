
"""Editable and read-only settings workspace."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QAbstractSpinBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTabBar,
    QMainWindow,
    QMessageBox,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from gem_screening.gui.settings.project_panel import ProjectSettingsPanel
from gem_screening.settings.storage import save_project_settings
from gem_screening.gui.wheel_focus import FocusedNumericWheelFilter, install_parameter_wheel_filter


class MainWindow(QMainWindow):
    def __init__(
        self,
        pages,
        pipeline_settings=None,
        settings_path: Path | None = None,
        show_proceed_button: bool = True,
        project_settings_panel: ProjectSettingsPanel | None = None,
    ):
        self.pipeline_settings = pipeline_settings
        self.settings_path = settings_path
        self._read_only_states: dict[QWidget, bool] = {}
        super().__init__()
        install_parameter_wheel_filter()
        self.setWindowTitle("Settings GUI")
        self.resize(900, 600)

        # Store all pages and advanced info
        self.all_pages = pages
        self.advanced_pages = [i for i, (name, _) in enumerate(pages) if name.lower() == "logging"]

        # Main layout: project-level settings stay visible above every page.
        main_widget = QWidget()
        root_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        self.project_settings_panel = project_settings_panel
        if self.pipeline_settings is not None and project_settings_panel is None:
            self.project_settings_panel = ProjectSettingsPanel(self.pipeline_settings)
            root_layout.addWidget(self.project_settings_panel)

        page_layout = QVBoxLayout()
        root_layout.addLayout(page_layout, 1)

        # Advanced settings checkbox
        self.advanced_checkbox = QCheckBox("Advanced Settings")
        self.advanced_checkbox.stateChanged.connect(self.update_nav)
        self.advanced_checkbox.setVisible(bool(self.advanced_pages))
        page_layout.addWidget(self.advanced_checkbox)

        # Navigation list
        self.nav_tabs = QTabBar()
        self.nav_tabs.setObjectName("settingsTabs")
        self.nav_tabs.setExpanding(False)
        self.nav_tabs.setDrawBase(True)
        for name, _ in pages:
            self.nav_tabs.addTab(name)
        page_layout.addWidget(self.nav_tabs)

        # Stacked widget for pages
        self.stack = QStackedWidget()
        for _, page in pages:
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll_area.setWidget(page)
            self.stack.addWidget(scroll_area)
        page_layout.addWidget(self.stack, 1)

        for _, page in pages:
            wheel_editable_widgets = (
                page.findChildren(QAbstractSpinBox)
                + page.findChildren(QSlider)
                + page.findChildren(QComboBox)
            )
            for widget in wheel_editable_widgets:
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.nav_tabs.currentChanged.connect(self.stack.setCurrentIndex)
        self.update_nav()

        action_layout = QHBoxLayout()
        action_layout.addStretch(1)
        self.save_status = QLabel()
        action_layout.addWidget(self.save_status)
        self.proceed_button = QPushButton("Proceed")
        self.proceed_button.clicked.connect(self._save_settings)
        self.proceed_button.setVisible(show_proceed_button)
        action_layout.addWidget(self.proceed_button)
        root_layout.addLayout(action_layout)

    def set_read_only(self, read_only: bool) -> None:
        """Lock setting values while leaving page navigation and scrolling usable."""
        editable_types = (
            QAbstractButton,
            QAbstractSpinBox,
            QComboBox,
            QLineEdit,
            QPlainTextEdit,
            QSlider,
        )
        setting_widgets = self.findChildren(QWidget)
        if self.project_settings_panel is not None:
            setting_widgets += self.project_settings_panel.findChildren(QWidget)
        editable_widgets = [
            widget
            for widget in setting_widgets
            if isinstance(widget, editable_types)
        ]

        if read_only:
            if self._read_only_states:
                return
            self._read_only_states = {
                widget: widget.isEnabled() for widget in editable_widgets
            }
            for widget in editable_widgets:
                widget.setEnabled(False)
            return

        for widget, was_enabled in self._read_only_states.items():
            widget.setEnabled(was_enabled)
        self._read_only_states.clear()

    def save_settings(self) -> Path | None:
        if self.pipeline_settings is None:
            return None
        try:
            self.settings_path = save_project_settings(
                self.pipeline_settings,
                self.settings_path,
            )
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot save settings", str(error))
            return None
        self.save_status.setText(f"Saved to {self.settings_path}")
        return self.settings_path

    def _save_settings(self) -> None:
        self.save_settings()

    def update_nav(self):
        show_advanced = self.advanced_checkbox.isChecked()
        for i in range(len(self.all_pages)):
            self.nav_tabs.setTabVisible(i, i not in self.advanced_pages or show_advanced)
        self.stack.setCurrentIndex(self.nav_tabs.currentIndex())
