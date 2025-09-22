from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton, QFileDialog
from PyQt6.QtCore import QDateTime, Qt

class ControlsPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Experiment folder path
        path_layout = QHBoxLayout()
        path_label = QLabel("Experiment folder:")
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Paste or write folder path...")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # Timestamp + suffix
        ts_layout = QHBoxLayout()
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_")
        self.timestamp_label = QLabel(timestamp)
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText("Optional suffix (e.g. test_run)")
        ts_layout.addWidget(QLabel("Folder name:"))
        ts_layout.addWidget(self.timestamp_label)
        ts_layout.addWidget(self.suffix_edit)
        layout.addLayout(ts_layout)

        # Checkboxes
        self.cb_overwrite_calib = QCheckBox("Restart calibration")
        self.cb_overwrite_af = QCheckBox("Restart autofocus")
        layout.addWidget(self.cb_overwrite_calib)
        layout.addWidget(self.cb_overwrite_af)

        # Buttons (Settings at top, Process at bottom)
        self.settings_btn = QPushButton("Settings")
        self.process_btn = QPushButton("Process")
        self.process_btn.setStyleSheet("background-color: #c0392b; color: white;")
        layout.addWidget(self.settings_btn)
        layout.addStretch(1)  # Pushes the next widget(s) to the bottom
        layout.addWidget(self.process_btn)

    def browse_folder(self):
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        if dlg.exec():
            selected = dlg.selectedFiles()
            if selected:
                self.path_edit.setText(selected[0])
