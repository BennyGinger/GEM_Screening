from PyQt6.QtWidgets import QWidget, QVBoxLayout, QCheckBox


class CalibrationAutofocusCheckboxes(QWidget):
    def __init__(self, parent=None, overwrite_calib=False, overwrite_af=False, on_calib_changed=None, on_af_changed=None):
        super().__init__(parent)
        self.on_calib_changed = on_calib_changed
        self.on_af_changed = on_af_changed
        layout = QVBoxLayout(self)
        self.cb_overwrite_calib = QCheckBox("Restart calibration")
        self.cb_overwrite_calib.setToolTip("If checked, the calibration will be restarted.")
        self.cb_overwrite_calib.setChecked(overwrite_calib)
        self.cb_overwrite_calib.toggled.connect(self._emit_calib_changed)
        layout.addWidget(self.cb_overwrite_calib)
        self.cb_overwrite_af = QCheckBox("Restart autofocus")
        self.cb_overwrite_af.setToolTip("If checked, the autofocus will be restarted.")
        self.cb_overwrite_af.setChecked(overwrite_af)
        self.cb_overwrite_af.toggled.connect(self._emit_af_changed)
        layout.addWidget(self.cb_overwrite_af)

    def _emit_calib_changed(self, checked):
        if self.on_calib_changed:
            self.on_calib_changed(checked)

    def _emit_af_changed(self, checked):
        if self.on_af_changed:
            self.on_af_changed(checked)

    def set_calib(self, checked):
        self.cb_overwrite_calib.setChecked(checked)

    def set_af(self, checked):
        self.cb_overwrite_af.setChecked(checked)
