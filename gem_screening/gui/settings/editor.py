
"""Editable and read-only settings workspace."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QAbstractSpinBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
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
from PyQt6.QtCore import QEvent, QObject, Qt

from gem_screening.gui.settings.project_panel import ProjectSettingsPanel
from gem_screening.settings.storage import save_project_settings


class FocusedNumericWheelFilter(QObject):
    """Prevent wheel changes until an editable control has been clicked/focused."""

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Wheel and not watched.hasFocus():
            event.ignore()
            return True
        return super().eventFilter(watched, event)

class MainWindow(QMainWindow):
    def __init__(
        self,
        pages,
        pipeline_settings=None,
        settings_path: Path | None = None,
        show_proceed_button: bool = True,
    ):
        self.pipeline_settings = pipeline_settings
        self.settings_path = settings_path
        self._read_only_states: dict[QWidget, bool] = {}
        super().__init__()
        self.setWindowTitle("Settings GUI")
        self.resize(900, 600)

        # Store all pages and advanced info
        self.all_pages = pages
        self.advanced_pages = [i for i, (name, _) in enumerate(pages) if name.lower() == "logging"]

        # Main layout: project-level settings stay visible above every page.
        main_widget = QWidget()
        root_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        self.project_settings_panel = None
        if self.pipeline_settings is not None:
            self.project_settings_panel = ProjectSettingsPanel(self.pipeline_settings)
            root_layout.addWidget(self.project_settings_panel)

        page_layout = QHBoxLayout()
        root_layout.addLayout(page_layout, 1)

        # Sidebar layout (vertical)
        sidebar = QVBoxLayout()
        page_layout.addLayout(sidebar)

        # Advanced settings checkbox
        self.advanced_checkbox = QCheckBox("Advanced Settings")
        self.advanced_checkbox.stateChanged.connect(self.update_nav)
        sidebar.addWidget(self.advanced_checkbox)

        # Navigation list
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(180)
        sidebar.addWidget(self.nav_list)

        # Stacked widget for pages
        self.stack = QStackedWidget()
        for _, page in pages:
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll_area.setWidget(page)
            self.stack.addWidget(scroll_area)
        page_layout.addWidget(self.stack, 1)

        self.numeric_wheel_filter = FocusedNumericWheelFilter(self)
        for _, page in pages:
            wheel_editable_widgets = (
                page.findChildren(QAbstractSpinBox)
                + page.findChildren(QSlider)
                + page.findChildren(QComboBox)
            )
            for widget in wheel_editable_widgets:
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                widget.installEventFilter(self.numeric_wheel_filter)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.update_nav()
        self.nav_list.setCurrentRow(0)

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
        editable_widgets = [
            widget
            for widget in self.findChildren(QWidget)
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
        # Remember the currently selected logical page index (in all_pages)
        current_nav_row = self.nav_list.currentRow()
        current_logical_index = self.page_map[current_nav_row] if hasattr(self, 'page_map') and 0 <= current_nav_row < len(self.page_map) else None

        self.nav_list.clear()
        self.page_map = []
        for i, (name, _) in enumerate(self.all_pages):
            if i in self.advanced_pages and not show_advanced:
                continue
            self.nav_list.addItem(name)
            self.page_map.append(i)

        # Try to restore selection to the same logical page if still visible
        new_row = 0
        if current_logical_index is not None:
            try:
                new_row = self.page_map.index(current_logical_index)
            except ValueError:
                # If the previous tab is now hidden, select the next available tab
                if current_nav_row < len(self.page_map):
                    new_row = current_nav_row
                else:
                    new_row = max(0, len(self.page_map) - 1)

        self.nav_list.currentRowChanged.disconnect()
        self.nav_list.currentRowChanged.connect(self._sync_stack)
        self.nav_list.setCurrentRow(new_row)
        self._sync_stack(new_row)

    def _sync_stack(self, nav_row):
        if 0 <= nav_row < len(self.page_map):
            self.stack.setCurrentIndex(self.page_map[nav_row])
