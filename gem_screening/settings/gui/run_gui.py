import sys
from PyQt6.QtWidgets import QApplication

from gem_screening.settings.gui.main_window import MainWindow
from gem_screening.settings.gui.pages.logging_page import LoggingPage
from gem_screening.settings.gui.pages.acquisition_page import AcquisitionPage
from gem_screening.settings.gui.pages.server_page import ServerPage
from gem_screening.settings.gui.pages.stim_page import StimPage
from gem_screening.settings.settings import full_settings

def main():
    app = QApplication(sys.argv)
    # Logging is considered advanced, so it should be first in the list for easier logic
    
    pages = [
        ("Logging", LoggingPage(full_settings)),
        ("Microscope", AcquisitionPage(full_settings)),
        ("Server", ServerPage(full_settings)),
        ("Light-Stimulation", StimPage(full_settings)),
    ]
    window = MainWindow(pages)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
