"""Standalone launcher for the settings editor."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from gem_screening.gui.settings.editor import MainWindow
from gem_screening.gui.settings.startup_panel import ExperimentStartupDialog
from gem_screening.gui.settings.pages.logging_page import LoggingPage
from gem_screening.gui.settings.pages.acquisition_page import AcquisitionPage
from gem_screening.gui.settings.pages.server_page import ServerPage
from gem_screening.gui.settings.pages.stim_page import StimPage
from gem_screening.gui.settings.pages.injection_page import InjectionPage
from gem_screening.settings.storage import load_gui_settings

def main(settings_path: str | Path | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    if settings_path is None:
        settings_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if settings_path is None:
        startup_dialog = ExperimentStartupDialog()
        if startup_dialog.exec() != QDialog.DialogCode.Accepted:
            return 0
        settings_path = startup_dialog.project_path

    try:
        pipeline_settings, output_path = load_gui_settings(settings_path)
    except (OSError, TypeError, ValueError) as error:
        QMessageBox.critical(None, "Cannot open experiment", str(error))
        return 1

    # Logging is considered advanced, so it should be first in the list for easier logic
    
    pages = [
        ("Logging", LoggingPage(pipeline_settings)),
        ("Microscope", AcquisitionPage(pipeline_settings)),
        ("Injection", InjectionPage(pipeline_settings)),
        ("Server", ServerPage(pipeline_settings)),
        ("Light-Stimulation", StimPage(pipeline_settings)),
    ]
    window = MainWindow(pages, pipeline_settings, output_path)
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
