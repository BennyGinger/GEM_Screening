from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QComboBox, QLabel

class LoggingPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)

        # Log Level
        self.level = QComboBox()
        self.level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        log_level_label = QLabel("Log Level")
        log_level_label.setToolTip("The logging level, e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR', or 'CRITICAL'. Defaults to 'INFO'.")
        layout.addRow(log_level_label, self.level)

        # Logfile Name
        self.logfile = QLineEdit()
        self.logfile.setText("gem_screening.log")  # Default value
        logfile_label = QLabel("Logfile Name")
        logfile_label.setToolTip("The file name where logs will be saved. Defaults to 'gem_screening.log'.")
        layout.addRow(logfile_label, self.logfile)
