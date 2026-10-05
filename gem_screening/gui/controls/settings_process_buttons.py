from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton


class SettingsProcessButtons(QWidget):
    def __init__(self, parent=None, on_settings_clicked=None, on_process_clicked=None):
        super().__init__(parent)
        self.on_settings_clicked = on_settings_clicked
        self.on_process_clicked = on_process_clicked
        layout = QVBoxLayout(self)
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self._emit_settings_clicked)
        layout.addWidget(self.settings_btn)
        layout.addStretch(1)
        self.process_btn = QPushButton("Process")
        self.process_btn.setStyleSheet("background-color: #c0392b; color: white;")
        self.process_btn.clicked.connect(self._emit_process_clicked)
        layout.addWidget(self.process_btn)

    def _emit_settings_clicked(self):
        if self.on_settings_clicked:
            self.on_settings_clicked()

    def _emit_process_clicked(self):
        if self.on_process_clicked:
            self.on_process_clicked()

    def set_enabled(self, enabled: bool):
        self.settings_btn.setEnabled(enabled)
        self.process_btn.setEnabled(enabled)
