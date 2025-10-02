import logging
from pathlib import Path
from typing import Callable
import os

from numpy.typing import NDArray
from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter, QTextEdit
from PyQt6.QtCore import Qt


from gem_screening.main_gui.controls_panel import ControlsPanel
from gem_screening.main_gui.main_display import MainDisplay

# Import AutofocusWidget for embedding
from a1_manager.autofocus.autofocus_gui import AutofocusWidget
from celltinder.cell_tinder import CellTinderWidget


from gem_screening.settings.gui.main_window import MainWindow as SettingsWindow
from gem_screening.settings.models import PipelineSettings, LoggingSettings, AcquisitionSettings, DishSettings, MeasureSettings, ServerSettings, ControlSettings, StimSettings


logger = logging.getLogger(__name__)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
# TODO: Check all the append_terminal calls and see if any need to be removed

class TerminalLogHandler(logging.Handler):
    def __init__(self, append_func: Callable[[str], None]):
        super().__init__()
        self.append_func = append_func

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        self.append_func(msg)

class MainGui(QMainWindow):
    def __init__(self, pipeline_settings: PipelineSettings | None = None):
        super().__init__()
        self.setWindowTitle("GEM Screening Main GUI")
        self.showMaximized()

        # Create a shared PipelineSettings object
        if pipeline_settings is not None:
            self.pipeline_settings = pipeline_settings
        else:
            self.pipeline_settings = PipelineSettings(
                savedir="Paste or write folder path...",
                savedir_name="Optional suffix (e.g. test_run)",
                logging_settings=LoggingSettings(),
                acquisition_settings=AcquisitionSettings(),
                dish_settings=DishSettings(),
                measure_settings=MeasureSettings(),
                server_settings=ServerSettings(),
                control_settings=ControlSettings(),
                stim_settings=StimSettings(),
            )

        # Main horizontal splitter (left 1/3, right 2/3)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(8)
        main_splitter.setStyleSheet("QSplitter::handle { background: #888; border: 1px solid #444; }")

        # Left side (1/3): vertical splitter (top: controls, bottom: terminal)
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        # Top: user controls panel
        self.controls_widget = ControlsPanel(
            self.pipeline_settings,
            autofocus_callback=self.show_autofocus_widget,
            celltinder_callback=self.show_celltinder_widget
        )
        self.controls_widget.buttons.settings_btn.clicked.connect(self.toggle_settings)
        self.controls_widget.mock_output_signal.connect(self.append_terminal)
        self.main_display = MainDisplay()
        self.settings_gui = None
        self.settings_visible = False

        # Bottom: terminal/progress display
        self.terminal_widget = QTextEdit()
        self.terminal_widget.setReadOnly(True)
        self.terminal_widget.setPlaceholderText("Terminal/Progress Output...")
        self.terminal_widget.setStyleSheet("background-color: #23272e; color: #f8f8f2;")

        terminal_handler = TerminalLogHandler(self.append_terminal)
        terminal_handler.setLevel(LOG_LEVEL)
        logging.getLogger().addHandler(terminal_handler)

        # Add widgets to left splitter
        left_splitter.addWidget(self.controls_widget)
        left_splitter.addWidget(self.terminal_widget)
        left_splitter.setSizes([300, 200])

        # Right side (2/3): main area with stack for switching
        # Add widgets to main splitter
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(self.main_display)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        # Set initial splitter position: left 1/3, right 2/3
        screen = self.screen()
        screen_width = screen.geometry().width() if screen is not None else 1200
        main_splitter.setSizes([screen_width // 3, screen_width * 2 // 3])
        main_splitter.setCollapsible(1, False)
        self.setCentralWidget(main_splitter)

    def show_autofocus_widget(self, image: NDArray) -> None:
        """
        Display the autofocus GUI in the right panel with the given image (numpy array).
        """
        autofocus_widget = AutofocusWidget(image)
        autofocus_widget.result_signal.connect(self.handle_autofocus_result)
        self.main_display.set_widget(autofocus_widget)
        self.settings_visible = False

    def show_celltinder_widget(self, csv_path: Path, n_frames: int, crop_size: int) -> None:
        """
        Display the CellTinder widget in the right panel with the given parameters.
        """
        celltinder_widget = CellTinderWidget(csv_path, n_frames, crop_size)

        def on_celltinder_done():
            self.append_terminal("[Pipeline] Cell selection completed. Resetting view.")
            # Clear the panel (MainDisplay manages child deletion)
            self.main_display.clear()
            # Notify controls that processing is finished
            self.controls_widget.process_finished.emit()
        celltinder_widget.finished.connect(on_celltinder_done)
        self.main_display.set_widget(celltinder_widget)
        self.settings_visible = False
    
    def handle_autofocus_result(self, result: str) -> None:
        """Handle the result from the autofocus GUI (continue, restart, quit)."""
        self.append_terminal(f"[Autofocus Result] User selected: {result}")
        if result == "restart":
            self.append_terminal("[Autofocus] Restarting autofocus...")
            # Set result to restart the loop
            self.controls_widget.set_autofocus_result("restart")
        elif result == "continue":
            self.append_terminal("[Autofocus] Continuing pipeline...")
            # Set result to exit the loop and continue pipeline
            self.controls_widget.set_autofocus_result("continue")
        elif result == "quit":
            self.append_terminal("[Autofocus] Quitting pipeline...")
            # Set result to exit the loop and quit
            self.controls_widget.set_autofocus_result("quit")
    
    def append_terminal(self, msg: str):
        self.terminal_widget.append(msg)

    def toggle_settings(self):
        if not self.settings_visible:
            # Create settings GUI if not already
            if self.settings_gui is None:
                from gem_screening.settings.gui.pages.logging_page import LoggingPage
                from gem_screening.settings.gui.pages.acquisition_page import AcquisitionPage
                from gem_screening.settings.gui.pages.server_page import ServerPage
                from gem_screening.settings.gui.pages.stim_page import StimPage
                pages = [
                    ("Logging", LoggingPage(self.pipeline_settings)),
                    ("Acquisition", AcquisitionPage(self.pipeline_settings)),
                    ("Server", ServerPage(self.pipeline_settings)),
                    ("Light-Stimulation", StimPage(self.pipeline_settings)),
                ]
                self.settings_gui = SettingsWindow(pages, self.pipeline_settings)
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
