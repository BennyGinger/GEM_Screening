from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PyQt6.QtCore import Qt


class ExperimentFolderSelector(QWidget):
    def __init__(self, parent=None, initial_path="", on_path_changed=None):
        super().__init__(parent)
        self.on_path_changed = on_path_changed
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label = QLabel("Experiment folder:")
        self.path_edit = QLineEdit()
        self.path_edit.setToolTip("Path to the main experiment folder where results will be saved.")
        self.path_edit.setText(initial_path)
        self.path_edit.textChanged.connect(self._emit_path_changed)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        layout.addWidget(label)
        layout.addWidget(self.path_edit)
        layout.addWidget(browse_btn)

    def _emit_path_changed(self):
        if self.on_path_changed:
            self.on_path_changed(self.path_edit.text())

    def browse_folder(self):
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        if dlg.exec():
            selected = dlg.selectedFiles()
            if selected:
                self.path_edit.setText(selected[0])

    def get_path(self):
        return self.path_edit.text()

    def set_path(self, path):
        self.path_edit.setText(path)
