# from PyQt6 imports

from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter, QTextEdit
from PyQt6.QtCore import Qt
from gem_screening.main_gui.controls_panel import ControlsPanel
from gem_screening.main_gui.main_display import MainDisplay
from gem_screening.settings.gui.main_window import MainWindow as SettingsWindow


class MainGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEM Screening Main GUI")
        self.showMaximized()

        # Main horizontal splitter (left 1/3, right 2/3)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(8)
        main_splitter.setStyleSheet("QSplitter::handle { background: #888; border: 1px solid #444; }")

        # Left side (1/3): vertical splitter (top: controls, bottom: terminal)
        left_splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: user controls panel
        self.controls_widget = ControlsPanel()
        self.controls_widget.settings_btn.clicked.connect(self.toggle_settings)

        # Bottom: terminal/progress display
        self.terminal_widget = QTextEdit()
        self.terminal_widget.setReadOnly(True)
        self.terminal_widget.setPlaceholderText("Terminal/Progress Output...")
        self.terminal_widget.setStyleSheet("background-color: #23272e; color: #f8f8f2;")

        left_splitter.addWidget(self.controls_widget)
        left_splitter.addWidget(self.terminal_widget)
        left_splitter.setSizes([300, 200])

        # Right side (2/3): main area with stack for switching
        self.main_display = MainDisplay()
        self.settings_gui = None
        self.settings_visible = False

        # Add widgets to main splitter
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(self.main_display)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        # Prevent right pane from collapsing below its minimum size
        main_splitter.setCollapsible(1, False)

        self.setCentralWidget(main_splitter)

    def toggle_settings(self):
        if not self.settings_visible:
            # Create settings GUI if not already
            if self.settings_gui is None:
                from gem_screening.settings.gui.pages.logging_page import LoggingPage
                from gem_screening.settings.gui.pages.acquisition_page import AcquisitionPage
                from gem_screening.settings.gui.pages.dish_page import DishPage
                from gem_screening.settings.gui.pages.measure_page import MeasurePage
                from gem_screening.settings.gui.pages.server_page import ServerPage
                from gem_screening.settings.gui.pages.stim_page import StimPage
                pages = [
                    ("Logging", LoggingPage()),
                    ("Microscope", AcquisitionPage()),
                    ("Dish", DishPage()),
                    ("Optics", MeasurePage()),
                    ("Server", ServerPage()),
                    ("Light-Stimulation", StimPage()),
                ]
                self.settings_gui = SettingsWindow(pages)
            self.main_display.set_widget(self.settings_gui)
            self.settings_visible = True
        else:
            self.main_display.clear()
            self.settings_visible = False

# For standalone testing (remove or comment out in production)
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainGui()
    window.show()
    sys.exit(app.exec())
