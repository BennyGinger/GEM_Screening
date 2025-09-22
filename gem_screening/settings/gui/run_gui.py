import sys
from PyQt6.QtWidgets import QApplication

from gem_screening.settings.gui.main_window import MainWindow
from gem_screening.settings.gui.pages.logging_page import LoggingPage
from gem_screening.settings.gui.pages.acquisition_page import AcquisitionPage
from gem_screening.settings.gui.pages.dish_page import DishPage
from gem_screening.settings.gui.pages.measure_page import MeasurePage
from gem_screening.settings.gui.pages.server_page import ServerPage
from gem_screening.settings.gui.pages.stim_page import StimPage


def main():
    app = QApplication(sys.argv)
    # Logging is considered advanced, so it should be first in the list for easier logic
    pages = [
        ("Logging", LoggingPage()),
        ("Microscope", AcquisitionPage()),
        ("Dish", DishPage()),
        ("Optics", MeasurePage()),
        ("Server", ServerPage()),
        ("Light-Stimulation", StimPage()),
    ]
    window = MainWindow(pages)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
