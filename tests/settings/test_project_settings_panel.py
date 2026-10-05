from datetime import datetime

from PyQt6.QtWidgets import QApplication, QFileDialog, QWidget

from gem_screening.gui.settings.editor import MainWindow
from gem_screening.gui.settings.project_panel import ProjectSettingsPanel
from gem_screening.settings.models import PipelineSettings


APP = QApplication.instance() or QApplication([])


def test_project_fields_update_pipeline_settings_and_preview():
    settings = PipelineSettings()
    panel = ProjectSettingsPanel(settings)

    panel.savedir_edit.setText("C:/experiments")
    panel.experiment_name_edit.setText("screen_1")
    panel.dev_mode.setChecked(True)
    panel.base_url_edit.setText("analysis-server")

    assert settings.savedir == "C:/experiments"
    assert settings.savedir_name == "screen_1"
    assert settings.dev_mode is True
    assert settings.base_url == "analysis-server"
    assert panel.run_directory_preview.text() == (
        f"{datetime.now():%Y%m%d}_screen_1"
    )


def test_browse_button_result_updates_user_folder(monkeypatch):
    settings = PipelineSettings()
    panel = ProjectSettingsPanel(settings)
    monkeypatch.setattr(
        QFileDialog,
        "getExistingDirectory",
        lambda *args: "C:/selected",
    )

    panel._browse_savedir()

    assert panel.savedir_edit.text() == "C:/selected"
    assert settings.savedir == "C:/selected"


def test_advanced_settings_are_collapsible():
    settings = PipelineSettings()
    panel = ProjectSettingsPanel(settings)

    assert panel.advanced_box.isHidden()
    panel.advanced_button.setChecked(True)
    assert not panel.advanced_box.isHidden()
    assert panel.advanced_button.text() == "Hide Advanced Settings"


def test_proceed_saves_new_project_settings(tmp_path):
    settings = PipelineSettings()
    settings.savedir = str(tmp_path)
    settings.savedir_name = "gui_exp"
    window = MainWindow([("Page", QWidget())], settings)

    window.proceed_button.click()

    assert window.settings_path is not None
    assert window.settings_path.is_file()
    assert "Saved to" in window.save_status.text()
