from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog

from gem_screening.gui.settings.startup_panel import ExperimentStartupDialog
from gem_screening.settings.models import PipelineSettings


APP = QApplication.instance() or QApplication([])


def test_new_experiment_accepts_without_a_project_path():
    dialog = ExperimentStartupDialog()

    dialog._new_experiment()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.project_path is None


def test_existing_experiment_requires_pipeline_settings(tmp_path):
    dialog = ExperimentStartupDialog()
    dialog.path_edit.setText(str(tmp_path))

    dialog._open_experiment()

    assert dialog.result() != QDialog.DialogCode.Accepted
    assert "pipeline_settings.json" in dialog.error_label.text()


def test_existing_experiment_with_valid_settings_is_accepted(tmp_path):
    settings = PipelineSettings()
    settings.savedir = str(tmp_path)
    settings.savedir_name = "existing"
    settings_path = tmp_path / "20261001_existing" / "config" / "pipeline_settings.json"
    settings_path.parent.mkdir(parents=True)
    settings.to_json(settings_path)
    dialog = ExperimentStartupDialog()
    dialog.path_edit.setText(str(settings_path.parent.parent))

    dialog._open_experiment()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.project_path == settings_path


def test_existing_experiment_rejects_invalid_pipeline_settings(tmp_path):
    settings_path = tmp_path / "config" / "pipeline_settings.json"
    settings_path.parent.mkdir()
    settings_path.write_text("{not valid json")
    dialog = ExperimentStartupDialog()
    dialog.path_edit.setText(str(tmp_path))

    dialog._open_experiment()

    assert dialog.result() != QDialog.DialogCode.Accepted
    assert dialog.error_label.text()


def test_browse_populates_existing_experiment_path(tmp_path, monkeypatch):
    dialog = ExperimentStartupDialog()
    monkeypatch.setattr(
        QFileDialog,
        "getExistingDirectory",
        lambda *args: str(tmp_path),
    )

    dialog._browse()

    assert dialog.path_edit.text() == str(tmp_path)
