from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import QDateTime, Qt


class TimestampSuffixEditor(QWidget):
    def __init__(self, parent=None, initial_suffix="", on_suffix_changed=None):
        super().__init__(parent)
        self.on_suffix_changed = on_suffix_changed
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QLabel("Folder name:"))
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_")
        self.timestamp_label = QLabel(timestamp)
        layout.addWidget(self.timestamp_label)
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setToolTip("Optional suffix to append to the experiment folder name.")
        self.suffix_edit.setText(initial_suffix)
        self.suffix_edit.textChanged.connect(self._emit_suffix_changed)
        layout.addWidget(self.suffix_edit)

    def _emit_suffix_changed(self):
        if self.on_suffix_changed:
            self.on_suffix_changed(self.suffix_edit.text())

    def get_suffix(self):
        return self.suffix_edit.text()

    def set_suffix(self, suffix):
        self.suffix_edit.setText(suffix)
