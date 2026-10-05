"""Injection settings page."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QWidget,
)

from gem_screening.settings.models import PipelineSettings


class InjectionPage(QWidget):
    """Settings for optional automated ligand injection."""

    def __init__(self, pipeline_settings: PipelineSettings) -> None:
        super().__init__()
        self.pipeline_settings = pipeline_settings
        settings = pipeline_settings.injection_settings
        layout = QFormLayout(self)
        self.form_layout = layout

        self.do_inject = QCheckBox("Do inject")
        self.do_inject.setToolTip(
            "Whether to perform automated injection. When disabled, ligand addition is manual."
        )
        self.do_inject.setChecked(settings.enabled)
        layout.addRow(self.do_inject)

        self.injection_device = QComboBox()
        self.injection_device.addItem("QuickPick", "quickpick")
        self.injection_device.addItem("NanoPick", "nanopick")
        self.injection_device.setCurrentIndex(
            max(0, self.injection_device.findData(settings.injection_device))
        )
        device_label = QLabel("Injection device")
        device_label.setToolTip(
            "Injection device: NanoPick for NanoPick head control or QuickPick for QuickPick valve control."
        )
        self.injection_device.setToolTip(device_label.toolTip())
        layout.addRow(device_label, self.injection_device)

        self.needle_size = QComboBox()
        for size in (30, 50, 70):
            self.needle_size.addItem(f"{size} µm", size)
        self.needle_size.setCurrentIndex(
            max(0, self.needle_size.findData(settings.needle_size))
        )
        needle_label = QLabel("Needle size")
        needle_label.setToolTip(
            "Needle size in micrometres for QuickPick valve control; normally 30, 50 or 70."
        )
        self.needle_size.setToolTip(needle_label.toolTip())
        layout.addRow(needle_label, self.needle_size)

        self.pressure = QDoubleSpinBox()
        self.pressure.setRange(0.0, 10.0)
        self.pressure.setDecimals(2)
        self.pressure.setSingleStep(0.05)
        self.pressure.setValue(settings.pressure or 0.0)
        pressure_label = QLabel("Pressure (bar)")
        pressure_label.setToolTip("Pressure in bar for QuickPick valve control.")
        self.pressure.setToolTip(pressure_label.toolTip())
        layout.addRow(pressure_label, self.pressure)

        self.inject_time_ms = QDoubleSpinBox()
        self.inject_time_ms.setRange(0.0, 1_000_000.0)
        self.inject_time_ms.setDecimals(1)
        self.inject_time_ms.setValue(settings.inject_time_ms or 0.0)
        time_label = QLabel("Injection time (ms)")
        time_label.setToolTip("Injection time in milliseconds for NanoPick head control.")
        self.inject_time_ms.setToolTip(time_label.toolTip())
        layout.addRow(time_label, self.inject_time_ms)

        self.inject_vol_ul = QDoubleSpinBox()
        self.inject_vol_ul.setRange(0.0, 10_000.0)
        self.inject_vol_ul.setDecimals(2)
        self.inject_vol_ul.setValue(settings.inject_vol_ul)
        self.mixing_cycles = QSpinBox()
        self.mixing_cycles.setRange(1, 100)
        self.mixing_cycles.setValue(settings.mixing_cycles)
        self.mixing_cycles.setToolTip(
            "Number of mixing cycles during injection; 1 means there is no extra mixing."
        )

        volume_label = QLabel("Injection volume (µL)")
        volume_label.setToolTip("Total volume to inject into each well, in microlitres.")
        self.inject_vol_ul.setToolTip(volume_label.toolTip())
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.inject_vol_ul)
        volume_layout.addSpacing(32)
        mixing_label = QLabel("Mixing cycles")
        mixing_label.setToolTip(self.mixing_cycles.toolTip())
        volume_layout.addWidget(mixing_label)
        volume_layout.addWidget(self.mixing_cycles)
        volume_layout.addSpacing(32)
        self.volume_per_injection = QLabel()
        self.volume_per_injection.setToolTip(
            "Injection volume divided by the number of mixing cycles."
        )
        volume_layout.addWidget(self.volume_per_injection)
        volume_layout.addStretch(1)
        layout.addRow(volume_label, volume_layout)

        self._setting_widgets = (
            self.injection_device,
            self.needle_size,
            self.pressure,
            self.inject_time_ms,
            self.inject_vol_ul,
            self.mixing_cycles,
        )

        self.do_inject.toggled.connect(self._update_enabled)
        self.injection_device.currentIndexChanged.connect(self._update_device)
        self.needle_size.currentIndexChanged.connect(self._update_needle_size)
        self.pressure.valueChanged.connect(self._update_pressure)
        self.inject_time_ms.valueChanged.connect(self._update_inject_time)
        self.inject_vol_ul.valueChanged.connect(self._update_volume)
        self.mixing_cycles.valueChanged.connect(self._update_mixing_cycles)

        self._set_device_fields(settings.injection_device)
        self._set_controls_enabled(settings.enabled)
        self._update_volume_per_injection()

    def _set_controls_enabled(self, enabled: bool) -> None:
        for widget in self._setting_widgets:
            widget.setEnabled(enabled)

    def _set_device_fields(self, device: str) -> None:
        is_quickpick = device == "quickpick"
        self.form_layout.setRowVisible(self.needle_size, is_quickpick)
        self.form_layout.setRowVisible(self.pressure, is_quickpick)
        self.form_layout.setRowVisible(self.inject_time_ms, not is_quickpick)

    def _update_enabled(self, enabled: bool) -> None:
        self.pipeline_settings.injection_settings.enabled = enabled
        self._set_controls_enabled(enabled)

    def _update_device(self) -> None:
        device = str(self.injection_device.currentData())
        self.pipeline_settings.injection_settings.injection_device = device
        self._set_device_fields(device)

    def _update_needle_size(self) -> None:
        self.pipeline_settings.injection_settings.needle_size = int(
            self.needle_size.currentData()
        )

    def _update_pressure(self, value: float) -> None:
        self.pipeline_settings.injection_settings.pressure = value

    def _update_inject_time(self, value: float) -> None:
        self.pipeline_settings.injection_settings.inject_time_ms = value

    def _update_volume(self, value: float) -> None:
        self.pipeline_settings.injection_settings.inject_vol_ul = value
        self._update_volume_per_injection()

    def _update_mixing_cycles(self, value: int) -> None:
        self.pipeline_settings.injection_settings.mixing_cycles = value
        self._update_volume_per_injection()

    def _update_volume_per_injection(self) -> None:
        cycles = max(1, self.mixing_cycles.value())
        volume = self.inject_vol_ul.value() / cycles
        self.volume_per_injection.setText(f"Volume per injection: {volume:.2f} µL")
