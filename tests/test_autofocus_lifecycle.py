from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication

from a1_manager import A1Manager
from a1_manager.autofocus.af_utils import QuitAutofocus
from a1_manager.autofocus.live_focus import LiveFocusWidget
from a1_manager.autofocus_main import _autofocus_review, run_autofocus
from a1_manager.dish_manager.main_dish_manager import DishManager
from a1_manager.utils.json_utils import save_config_file
from a1_manager.utils.utility_classes import StageCoord, WellCircleCoord

APP = QApplication.instance() or QApplication([])


def make_manager(running: bool = False) -> Any:
    """
    Provide a stateful camera and focus device without microscope hardware.
    """
    manager = MagicMock()
    manager.dmd = None
    core = manager.core
    core.is_sequence_running.return_value = running
    core.start_continuous_sequence_acquisition.side_effect = lambda _interval: setattr(core.is_sequence_running, "return_value", True)
    core.stop_sequence_acquisition.side_effect = lambda: setattr(core.is_sequence_running, "return_value", False)
    core.get_auto_shutter.return_value = True
    core.get_shutter_open.return_value = False
    core.get_property.return_value = "PFSOffset"
    core.get_position.return_value = 100.0
    core.get_remaining_image_count.return_value = 1
    core.get_last_tagged_image.return_value = MagicMock(
        tags={"Width": 8, "Height": 8, "PixelType": "GRAY16"},
        pix=np.arange(64, dtype=np.uint16),
    )
    return manager


def test_quit_review_stops_pipeline() -> None:
    """
    Quit must propagate without accepting a focus position.
    """
    with pytest.raises(QuitAutofocus):
        _autofocus_review(make_manager(), lambda _manager: "quit")


@pytest.mark.parametrize("choice", ["continue", "close"])
def test_live_focus_restores_camera_and_illumination(choice: str) -> None:
    """
    All review exits clean up the stream before reporting the choice.
    """
    manager = make_manager()
    manager.dmd = object()
    manager.core.get_property.return_value = "0"
    widget = LiveFocusWidget(manager)
    widget._update_frame()
    assert widget.continue_button.isEnabled()
    results: list[str] = []
    widget.result_signal.connect(results.append)
    if choice == "close":
        widget.close()
    else:
        widget.continue_button.click()
    assert results == ["continue" if choice == "continue" else "quit"]
    assert not widget.timer.isActive()
    manager.core.stop_sequence_acquisition.assert_called_once()
    manager.core.set_shutter_open.assert_called_with(False)
    manager.core.set_auto_shutter.assert_called_with(True)
    manager.core.set_property.assert_called_with("LappMainBranch1", "State", "0")
    manager.core.get_position.assert_not_called()
    widget.close()
    manager.core.stop_sequence_acquisition.assert_called_once()


def test_live_focus_preserves_existing_sequence() -> None:
    """
    A borrowed acquisition is not stopped or reconfigured.
    """
    manager = make_manager(running=True)
    widget = LiveFocusWidget(manager)
    widget.close()
    manager.core.start_continuous_sequence_acquisition.assert_not_called()
    manager.core.stop_sequence_acquisition.assert_not_called()
    manager.core.set_shutter_open.assert_not_called()


@pytest.mark.parametrize("pixel_type", ["GRAY8", "GRAY16"])
def test_live_focus_autoscales_raw_pixels_and_holds_levels(pixel_type: str) -> None:
    """
    First-frame scaling must expose low signal and stay fixed across later frames.
    """
    manager = make_manager()
    offset = 1000 if pixel_type == "GRAY16" else 0
    dtype = np.uint16 if pixel_type == "GRAY16" else np.uint8
    raw = np.arange(offset, offset + 64, dtype=dtype)
    manager.core.get_last_tagged_image.return_value = MagicMock(
        tags={"Width": 8, "Height": 8, "PixelType": pixel_type}, pix=raw,
    )
    widget = LiveFocusWidget(manager)
    widget._update_frame()
    controls = widget.display_controls
    assert (controls.min_value.value(), controls.max_value.value()) == (offset, offset + 63)
    assert widget._pixmap is not None
    image = widget._pixmap.toImage()
    assert image.pixelColor(0, 0).red() == 0
    assert image.pixelColor(7, 7).red() == 255
    manager.core.get_last_tagged_image.return_value.pix = raw + 10
    widget._update_frame()
    assert (controls.min_value.value(), controls.max_value.value()) == (offset, offset + 63)
    controls.auto_scale_button.click()
    assert (controls.min_value.value(), controls.max_value.value()) == (offset + 10, offset + 73)
    widget.close()


def test_live_focus_manual_lut_updates_without_another_capture() -> None:
    """
    Numeric levels and brightness update the cached frame without touching acquisition.
    """
    manager = make_manager()
    raw = np.full(64, 1024, dtype=np.uint16)
    manager.core.get_last_tagged_image.return_value.pix = raw
    widget = LiveFocusWidget(manager)
    widget._update_frame()
    controls = widget.display_controls
    controls.min_value.setValue(0)
    controls.max_value.setValue(2048)
    assert widget._pixmap is not None
    assert widget._pixmap.toImage().pixelColor(0, 0).red() == 127
    controls.brightness_value.setValue(100)
    assert widget._pixmap.toImage().pixelColor(0, 0).red() == 204
    controls.auto_scale_button.click()
    assert controls.brightness_value.value() == 50
    assert controls.contrast_value.value() == 50
    manager.core.get_last_tagged_image.assert_called_once()
    np.testing.assert_array_equal(raw, np.full(64, 1024, dtype=np.uint16))
    widget.close()


@pytest.mark.parametrize("intensity", [0, 65535])
def test_live_focus_constant_frame_has_valid_lut(intensity: int) -> None:
    """
    Auto-scale remains usable for blank and saturated frames.
    """
    manager = make_manager()
    manager.core.get_last_tagged_image.return_value.pix = np.full(64, intensity, dtype=np.uint16)
    widget = LiveFocusWidget(manager)
    widget._update_frame()
    controls = widget.display_controls
    assert 0 <= controls.min_value.value() < controls.max_value.value() <= 65535
    assert widget.continue_button.isEnabled()
    widget.close()


def test_live_focus_start_failure_restores_illumination() -> None:
    """
    Failed acquisition startup restores shutter configuration.
    """
    manager = make_manager()
    manager.core.start_continuous_sequence_acquisition.side_effect = RuntimeError("camera failed")
    with pytest.raises(RuntimeError, match="camera failed"):
        LiveFocusWidget(manager)
    manager.core.set_shutter_open.assert_called_with(False)
    manager.core.set_auto_shutter.assert_called_with(True)


def test_live_focus_camera_failure_quits_and_cleans_up() -> None:
    """
    A failed frame read cannot leave the pipeline waiting with illumination on.
    """
    manager = make_manager()
    widget = LiveFocusWidget(manager)
    manager.core.get_last_tagged_image.side_effect = RuntimeError("camera disconnected")
    results: list[str] = []
    widget.result_signal.connect(results.append)
    widget._update_frame()
    assert results == ["quit"]
    assert not widget.timer.isActive()
    manager.core.stop_sequence_acquisition.assert_called_once()
    manager.core.set_shutter_open.assert_called_with(False)
    widget.close()


def test_live_focus_cleanup_failure_cannot_accept_focus() -> None:
    """
    Continue becomes Quit if acquisition cannot be stopped cleanly.
    """
    manager = make_manager()
    widget = LiveFocusWidget(manager)
    widget._update_frame()
    manager.core.stop_sequence_acquisition.side_effect = RuntimeError("stop failed")
    results: list[str] = []
    widget.result_signal.connect(results.append)
    widget.continue_button.click()
    assert results == ["quit"]
    manager.core.set_shutter_open.assert_called_with(False)
    manager.core.set_auto_shutter.assert_called_with(True)
    widget.close()


@pytest.mark.parametrize("method", ["Manual", "sq_grad"])
@pytest.mark.parametrize("cached", [False, True])
def test_focus_saved_after_continue(method: str, cached: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Both modes review cached values and save the user's adjusted focus.
    """
    import a1_manager.autofocus_main as module

    manager = make_manager()
    measurements = {
        "A1": WellCircleCoord(center=(1.0, 0.0), PFSOffset=50.0 if cached else None),
        "A2": WellCircleCoord(center=(0.0, 0.0), PFSOffset=50.0 if cached else None),
    }
    save = MagicMock()
    autofocus = MagicMock(a1_manager=manager, method=method)
    monkeypatch.setattr(module, "load_config_file", lambda _path: measurements)
    monkeypatch.setattr(module, "save_config_file", save)
    monkeypatch.setattr(module, "AutoFocusManager", lambda *_args: autofocus)

    def review(review_manager: A1Manager) -> str:
        """
        Simulate the user adjusting focus before pressing Continue.
        """
        assert review_manager is manager
        save.assert_not_called()
        assert measurements["A1"].PFSOffset == (50.0 if cached else None)
        manager.core.get_position.return_value = 321.0
        return "continue"

    run_autofocus(method, manager, tmp_path / "calib.json", "all", False, review_callback=review)
    assert measurements["A1"].PFSOffset == 321.0
    assert measurements["A2"].PFSOffset == (50.0 if method == "sq_grad" and cached else 321.0)
    assert autofocus.find_focus.call_count == (2 if method == "sq_grad" and not cached else 0)
    save.assert_called_once()


def test_quit_does_not_save_focus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Rejecting the first well leaves its calibration unchanged.
    """
    import a1_manager.autofocus_main as module

    measurements = {"A1": WellCircleCoord(center=(0.0, 0.0), PFSOffset=50.0)}
    save = MagicMock()
    monkeypatch.setattr(module, "load_config_file", lambda _path: measurements)
    monkeypatch.setattr(module, "save_config_file", save)
    with pytest.raises(QuitAutofocus):
        run_autofocus("Manual", make_manager(), tmp_path / "calib.json", "all", False,
                      review_callback=lambda _manager: "quit",
                      )
    assert measurements["A1"].PFSOffset == 50.0
    save.assert_not_called()


def test_accepted_focus_reaches_grid_calibration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Grid generation must use the newly accepted calibration instead of stale values.
    """
    manager = make_manager()
    dish = DishManager("96well", tmp_path, manager)
    dish.dish_calibration = {"A1": WellCircleCoord(center=(0.0, 0.0), PFSOffset=50.0)}
    save_config_file(dish.calib_path, dish.dish_calibration)

    def review(_manager: A1Manager) -> str:
        """
        Accept a manually adjusted position.
        """
        manager.core.get_position.return_value = 321.0
        return "continue"

    dish.autofocus_dish("Manual", False, "all", review_callback=review)
    assert dish.dish_calibration["A1"].PFSOffset == 321.0

    grid_manager = MagicMock()

    def create_grid(measurement: WellCircleCoord, *_args: Any) -> dict[int, StageCoord]:
        """
        Model the grid builder's use of the refreshed calibration.
        """
        return {0: measurement.get_template_point_coord()}

    grid_manager.create_well_grid.side_effect = create_grid
    monkeypatch.setattr("a1_manager.dish_manager.main_dish_manager.WellGridManager.load_subclass_instance",
                        lambda *_args: grid_manager,
                        )
    grid = dish.create_well_grids(False, numb_field_view=1, well_selection="A1")
    assert len(grid["A1"]) == 2
    assert all(point.PFSOffset == 321.0 for point in grid["A1"].values())
    assert all(point.ZDrive is None for point in grid["A1"].values())
