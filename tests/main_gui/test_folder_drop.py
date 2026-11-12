from pathlib import Path

import pytest
from PyQt6.QtCore import QMimeData, QPointF, Qt, QUrl
from PyQt6.QtGui import QDropEvent
from PyQt6.QtWidgets import QApplication, QMessageBox

from gem_screening.gui.main_window import MainGui
from gem_screening.settings.models import PipelineSettings


APP = QApplication.instance() or QApplication([])


def drop(window, paths):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    window.dropEvent(event)
    return event.isAccepted()


@pytest.mark.parametrize("config_folder", [False, True])
def test_drop_loads_saved_run(tmp_path, config_folder):
    marker = tmp_path / "config" / "pipeline_settings.json"
    marker.parent.mkdir()
    PipelineSettings(savedir=str(tmp_path.parent), savedir_name="saved run").to_json(marker)
    window = MainGui()
    assert drop(window, [marker.parent if config_folder else tmp_path])
    assert window.is_existing_experiment
    assert window.settings_path == marker
    assert window.pipeline_settings.savedir_name == "saved run"
    assert window.start_button.text() == "Rerun"
    window.close()


def test_drop_new_user_folder_does_not_write_files(tmp_path):
    (tmp_path / "config").mkdir()  # A config directory alone is not a run.
    window = MainGui()
    assert drop(window, [tmp_path])
    assert not window.is_existing_experiment
    assert window.settings_path is None
    assert Path(window.pipeline_settings.savedir) == tmp_path
    assert window.start_button.text() == "Run"
    assert list((tmp_path / "config").iterdir()) == []
    assert not window.settings_window.project_settings_panel.savedir_edit.acceptDrops()
    window.close()


def test_drop_image_folder_loads_nearest_ancestor_run(tmp_path):
    outer = tmp_path / "config" / "pipeline_settings.json"
    outer.parent.mkdir()
    PipelineSettings(savedir_name="outer").to_json(outer)
    run = tmp_path / "nested_run"
    marker = run / "config" / "pipeline_settings.json"
    marker.parent.mkdir(parents=True)
    PipelineSettings(savedir_name="nearest run").to_json(marker)
    images = run / "Images" / "A1"
    images.mkdir(parents=True)
    window = MainGui()
    assert drop(window, [images])
    assert window.settings_path == marker
    assert window.pipeline_settings.savedir_name == "nearest run"
    assert window.experiment_path_edit.text() == str(run)
    window.close()


def test_drop_nested_folder_without_run_keeps_original_folder(tmp_path):
    images = tmp_path / "unrelated" / "Images"
    images.mkdir(parents=True)
    window = MainGui()
    assert drop(window, [images])
    assert window.settings_path is None
    assert Path(window.pipeline_settings.savedir) == images
    window.close()


def test_invalid_saved_settings_preserve_current_experiment(tmp_path, monkeypatch):
    marker = tmp_path / "config" / "pipeline_settings.json"
    marker.parent.mkdir()
    marker.write_text("invalid json")
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args))
    settings = PipelineSettings(savedir_name="keep me")
    window = MainGui(settings)
    assert not drop(window, [tmp_path])
    assert window.pipeline_settings is settings
    assert warnings
    window.close()


def test_drop_rejected_during_run_or_task_and_for_multiple_folders(tmp_path):
    window = MainGui()
    window.run_started = True
    assert not drop(window, [tmp_path])
    window.run_started = False
    assert not drop(window, [tmp_path, tmp_path])
    file = tmp_path / "file.txt"
    file.touch()
    assert not drop(window, [file])
    assert window.pipeline_settings is None
    window.close()
