import logging

from numpy.typing import NDArray
from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter, QTextEdit
from PyQt6.QtCore import Qt


from gem_screening.main_gui.controls_panel import ControlsPanel
from gem_screening.main_gui.main_display import MainDisplay

# Import AutofocusWidget for embedding
try:
    from a1_manager.autofocus.autofocus_gui import AutofocusWidget
except ImportError:
    AutofocusWidget = None

from gem_screening.settings.gui.main_window import MainWindow as SettingsWindow
from gem_screening.settings.models import PipelineSettings, LoggingSettings, AcquisitionSettings, DishSettings, MeasureSettings, ServerSettings, ControlSettings, StimSettings


logger = logging.getLogger(__name__)

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
                stim_settings=StimSettings(),)

        # Main horizontal splitter (left 1/3, right 2/3)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(8)
        main_splitter.setStyleSheet("QSplitter::handle { background: #888; border: 1px solid #444; }")

        # Left side (1/3): vertical splitter (top: controls, bottom: terminal)
        left_splitter = QSplitter(Qt.Orientation.Vertical)



        # Bottom: terminal/progress display
        self.terminal_widget = QTextEdit()
        self.terminal_widget.setReadOnly(True)
        self.terminal_widget.setPlaceholderText("Terminal/Progress Output...")
        self.terminal_widget.setStyleSheet("background-color: #23272e; color: #f8f8f2;")

        # Top: user controls panel

        self.controls_widget = ControlsPanel(self.pipeline_settings, autofocus_callback=self.show_autofocus_widget)
        self.controls_widget.settings_btn.clicked.connect(self.toggle_settings)
        self.controls_widget.mock_output_signal.connect(self.append_terminal)
        # Right side (2/3): main area with stack for switching
        self.main_display = MainDisplay()
        self.settings_gui = None
        self.settings_visible = False

        # Add widgets to left splitter
        left_splitter.addWidget(self.controls_widget)
        left_splitter.addWidget(self.terminal_widget)
        left_splitter.setSizes([300, 200])

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
        """Display the autofocus GUI in the right panel with the given image (numpy array)."""
        self._last_autofocus_image = image  # Store for possible redo
        if AutofocusWidget is not None:
            autofocus_widget = AutofocusWidget(image)
            autofocus_widget.result_signal.connect(self.handle_autofocus_result)
            self.main_display.set_widget(autofocus_widget)
            self.settings_visible = False
        else:
            logger.error("AutofocusWidget not available. Ensure a1_manager is installed.")
            self.append_terminal("[ERROR] AutofocusWidget not available.")

    def handle_autofocus_result(self, result: str) -> None:
        """Handle the result from the autofocus GUI (continue, restart, quit)."""
        self.append_terminal(f"[Autofocus Result] User selected: {result}")
        if result == "restart":
            self.append_terminal("[Autofocus] Restarting autofocus...")
            # In a real pipeline, you would reacquire a new image here
            try:
                from tifffile import imread
                # For demo: alternate between two images for restart
                import random
                img_paths = [
                    '/media/ben/Analysis/Python/Docker_mount/Test_images/nd2/Run3/c3z1t1v3_s1/Images/C1_s01_f0001_z0001.tif',
                    '/media/ben/Analysis/Python/Docker_mount/Test_images/nd2/Run3/c3z1t1v3_s2/Images/C1_s02_f0001_z0001.tif',
                    '/media/ben/Analysis/Python/Docker_mount/Test_images/nd2/Run3/c3z1t1v3_s3/Images/C1_s03_f0001_z0001.tif'
                ]
                new_img = imread(random.choice(img_paths))
                self.show_autofocus_widget(new_img)
            except Exception as e:
                self.append_terminal(f"[Autofocus] Error generating new image: {e}")
        elif result == "continue":
            self.append_terminal("[Autofocus] Continuing pipeline...")
            # Insert next pipeline step here
        elif result == "quit":
            self.append_terminal("[Autofocus] Quitting pipeline...")
            # Insert pipeline cleanup/stop logic here
    
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
