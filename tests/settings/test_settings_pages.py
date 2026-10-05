from pathlib import Path

from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication, QComboBox, QScrollArea, QSpinBox, QWidget

from gem_screening.gui.settings.editor import FocusedNumericWheelFilter, MainWindow
from gem_screening.gui.settings.pages.acquisition_page import AcquisitionPage
from gem_screening.gui.settings.pages.injection_page import InjectionPage
from gem_screening.gui.settings.pages.server_page import ServerPage
from gem_screening.gui.settings.pages.stim_page import StimPage
from gem_screening.gui.settings.pages.well_selection_widget import WellSelectionWidget
from gem_screening.settings.models import PipelineSettings


APP = QApplication.instance() or QApplication([])


def test_acquisition_page_updates_remaining_dish_settings():
    settings = PipelineSettings()
    page = AcquisitionPage(settings)

    page.well_grouping_checks["well"].setChecked(True)
    page.overwrite_autofocus.setChecked(True)
    page.overwrite_calib.setChecked(True)
    page.af_savedir.setText("C:/autofocus")

    assert settings.dish_settings.well_grouping == "well"
    assert settings.dish_settings.overwrite_autofocus is True
    assert settings.dish_settings.overwrite_calib is True
    assert settings.dish_settings.af_savedir == Path("C:/autofocus")


def test_injection_page_disables_controls_and_switches_device_fields():
    settings = PipelineSettings()
    settings.injection_settings.enabled = False
    page = InjectionPage(settings)

    assert not page.injection_device.isEnabled()
    page.do_inject.setChecked(True)
    page.injection_device.setCurrentIndex(page.injection_device.findData("nanopick"))
    page.inject_time_ms.setValue(125.0)

    assert settings.injection_settings.enabled is True
    assert settings.injection_settings.injection_device == "nanopick"
    assert page.form_layout.isRowVisible(page.inject_time_ms)
    assert not page.form_layout.isRowVisible(page.needle_size)
    assert settings.injection_settings.inject_time_ms == 125.0


def test_injection_volume_per_cycle_updates_live():
    settings = PipelineSettings()
    page = InjectionPage(settings)

    page.inject_vol_ul.setValue(12.0)
    page.mixing_cycles.setValue(3)

    assert page.volume_per_injection.text() == "Volume per injection: 4.00 µL"


def test_server_advanced_fields_and_custom_model_update_settings():
    settings = PipelineSettings()
    page = ServerPage(settings)

    page.server_timeout.setValue(900.0)
    page.channels_input.setText("0, 2")
    page.z_axis_input.setText("1")
    page.extra_settings_input.setPlainText('{"use_nuclear_channel": true}')
    page.pretrained_model_input.setText("C:/models/custom")

    server = settings.server_settings
    assert server.server_timeout_sec == 900.0
    assert server.channels == [0, 2]
    assert server.z_axis == 1
    assert server.extra_settings == {"use_nuclear_channel": True}
    assert getattr(server, "pretrained_model") == "C:/models/custom"
    assert not hasattr(server, "pretrained_model_path")


def test_control_and_illumination_defaults_are_disabled():
    settings = PipelineSettings()
    server_page = ServerPage(settings)
    stim_page = StimPage(settings)

    assert settings.control_settings.control_loop is False
    assert settings.stim_settings.do_illuminate is False
    assert settings.injection_settings.enabled is False
    assert not hasattr(server_page, "do_control")
    assert not stim_page.do_control.isChecked()
    assert not stim_page.do_illumination.isChecked()


def test_control_imaging_settings_are_updated_from_stimulation_page():
    settings = PipelineSettings()
    page = StimPage(settings)

    page.do_control.setChecked(True)
    page.control_optical_config.setCurrentText("GFP")
    page.control_intensity_slider.setValue(55)
    page.control_exposure.setValue(150)

    control = settings.control_settings
    assert control.control_loop is True
    assert control.preset.optical_configuration == "GFP"
    assert control.preset.intensity == 55
    assert control.preset.exposure_ms == 150


def test_well_selection_is_remembered_for_each_dish():
    widget = WellSelectionWidget()
    widget.set_dish("96well")
    widget.set_selection(["A1", "B2"])

    widget.set_dish("384well")
    widget.set_selection(["C3"])
    widget.set_dish("96well")

    assert widget.selected_wells == ["A1", "B2"]


def test_acquisition_page_restores_wells_when_returning_to_a_dish():
    settings = PipelineSettings()
    settings.dish_settings.dish_name = "96well"
    settings.dish_settings.well_selection = ["A1", "B2"]
    page = AcquisitionPage(settings)

    page.dish_name.setCurrentText("384well")
    page.well_selection_widget.set_selection(["C3"])
    page.update_well_selection(["C3"])
    page.dish_name.setCurrentText("96well")

    assert page.well_selection_widget.selected_wells == ["A1", "B2"]
    assert settings.dish_settings.well_selection == ["A1", "B2"]


def test_all_fovs_toggle_restores_previous_number():
    settings = PipelineSettings()
    settings.dish_settings.numb_field_view = 3
    page = AcquisitionPage(settings)

    page.numb_field_view_all.setChecked(True)
    assert page.numb_field_view_input.text() == ""
    assert settings.dish_settings.numb_field_view is None

    page.numb_field_view_all.setChecked(False)
    assert page.numb_field_view_input.text() == "3"
    assert settings.dish_settings.numb_field_view == 3


def test_settings_pages_are_scrollable_and_proceed_stays_outside_scroll_area():
    settings = PipelineSettings()
    page = QWidget()
    window = MainWindow([("Page", page)], settings)

    assert isinstance(window.stack.widget(0), QScrollArea)
    assert window.proceed_button.parentWidget() is window.centralWidget()


def test_numeric_wheel_is_blocked_until_control_has_focus():
    spinbox = QSpinBox()
    wheel_filter = FocusedNumericWheelFilter()
    wheel_event = QEvent(QEvent.Type.Wheel)

    spinbox.clearFocus()

    assert wheel_filter.eventFilter(spinbox, wheel_event) is True


def test_dropdown_wheel_is_blocked_until_control_has_focus():
    dropdown = QComboBox()
    dropdown.addItems(["first", "second"])
    wheel_filter = FocusedNumericWheelFilter()
    wheel_event = QEvent(QEvent.Type.Wheel)

    dropdown.clearFocus()

    assert wheel_filter.eventFilter(dropdown, wheel_event) is True
