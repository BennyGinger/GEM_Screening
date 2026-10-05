import time
import logging
from threading import Event

from PyQt6.QtWidgets import QApplication, QMessageBox

from gem_screening.gui.main_window import MainGui, _run_complete_pipeline
from gem_screening.runtime import CancellationToken, PipelineInteraction
from gem_screening.settings.models import PipelineSettings


APP = QApplication.instance() or QApplication([])


def wait_until(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        APP.processEvents()
        time.sleep(0.01)
    assert predicate()


def test_main_gui_loads_settings_and_hosts_celltinder_task():
    window = MainGui()

    window._new_experiment()

    assert window.workspace_tabs.count() == 1
    assert window.workspace_tabs.tabText(0) == "Settings"
    assert window.celltinder_button.isEnabled()
    assert window.start_button.text() == "Run"
    assert not window.rescue_button.isEnabled()

    window.open_celltinder_test()

    assert window.workspace_tabs.count() == 2
    assert window.workspace_tabs.tabText(1) == "CellTinder"
    assert window.workspace_tabs.currentWidget() is window.task_widget
    assert not window.close_task_button.isHidden()
    assert not window.start_button.isEnabled()
    assert window.settings_window is not None
    assert window.settings_window.project_settings_panel.savedir_edit.isEnabled()

    window.close_current_task()

    assert window.workspace_tabs.count() == 1
    assert window.workspace_tabs.currentIndex() == 0
    assert window.start_button.isEnabled()
    assert window.settings_window.project_settings_panel.savedir_edit.isEnabled()
    window.close()


def test_start_saves_and_locks_settings_until_pipeline_finishes(tmp_path):
    runner_started = Event()
    release_runner = Event()

    def runner(_settings, _interaction, cancellation):
        runner_started.set()
        while not release_runner.wait(0.01):
            cancellation.raise_if_requested()

    window = MainGui(runner_factory=lambda _run_dir, _rescue: runner)
    window._new_experiment()
    assert window.settings_window is not None
    project_panel = window.settings_window.project_settings_panel
    project_panel.savedir_edit.setText(str(tmp_path))
    project_panel.experiment_name_edit.setText("locked_settings")

    window.start_button.click()
    wait_until(runner_started.is_set)

    assert window.run_started is True
    assert window.settings_path is not None
    assert window.settings_path.is_file()
    assert not project_panel.savedir_edit.isEnabled()
    assert window.settings_window.nav_list.isEnabled()
    assert "Saved and validated" in window.terminal_widget.toPlainText()

    assert not project_panel.savedir_edit.isEnabled()
    release_runner.set()
    wait_until(lambda: not window.run_started)

    assert project_panel.savedir_edit.isEnabled()
    assert window.start_button.isEnabled()
    assert window.start_button.text() == "Rerun"
    assert not window.cancel_button.isEnabled()
    assert "Completed successfully" in window.terminal_widget.toPlainText()
    window.close()


def test_pipeline_failure_is_reported_and_unlocks_settings(tmp_path):
    def fail(_settings, _interaction, _cancellation):
        raise RuntimeError("simulated pipeline failure")

    window = MainGui(runner_factory=lambda _run_dir, _rescue: fail)
    window._new_experiment()
    project_panel = window.settings_window.project_settings_panel
    project_panel.savedir_edit.setText(str(tmp_path))
    project_panel.experiment_name_edit.setText("failed_run")

    window.start_button.click()
    wait_until(lambda: window._pipeline_outcome == "failed")
    wait_until(lambda: not window.run_started)

    output = window.terminal_widget.toPlainText()
    assert "Failed with an unexpected error" in output
    assert "RuntimeError: simulated pipeline failure" in output
    assert project_panel.savedir_edit.isEnabled()
    window.close()


def test_worker_log_reaches_persistent_console(tmp_path):
    def runner(_settings, _interaction, _cancellation):
        logging.getLogger("cp_server.compose_manager").warning(
            "simulated server startup message"
        )

    window = MainGui(runner_factory=lambda _run_dir, _rescue: runner)
    window._new_experiment()
    project_panel = window.settings_window.project_settings_panel
    project_panel.savedir_edit.setText(str(tmp_path))
    project_panel.experiment_name_edit.setText("logging_test")
    window.start_button.click()
    wait_until(lambda: not window.run_started)

    assert "simulated server startup message" in window.terminal_widget.toPlainText()
    window.close()


def test_console_keeps_scroll_position_when_new_logs_arrive():
    window = MainGui()
    window.show()
    for index in range(300):
        window.append_terminal(f"Earlier log line {index}")
    APP.processEvents()

    scrollbar = window.terminal_widget.verticalScrollBar()
    assert scrollbar.maximum() > 0
    scrollbar.setValue(0)
    window.append_terminal("Latest log line")

    assert scrollbar.value() == 0
    assert "Latest log line" in window.terminal_widget.toPlainText()
    window.close()


def test_rescue_uses_saved_settings_and_does_not_save_gui_edits(tmp_path):
    captured = []

    def factory(run_dir, rescue):
        return lambda settings, _interaction, _cancellation: captured.append(
            (run_dir, rescue, settings.dev_mode)
        )

    window = MainGui(runner_factory=factory)
    window._new_experiment()
    window.settings_window.project_settings_panel.savedir_edit.setText(str(tmp_path))
    window.settings_window.project_settings_panel.experiment_name_edit.setText("existing")
    settings_path = window.settings_window.save_settings()
    (settings_path.parent / "saved_obj.json").write_text("{}")
    original_contents = settings_path.read_bytes()
    loaded_settings = PipelineSettings.from_json(settings_path)
    window._load_experiment(loaded_settings, settings_path)
    assert window.start_button.text() == "Rerun"
    assert window.rescue_button.isEnabled()
    window.settings_window.project_settings_panel.dev_mode.setChecked(True)

    window.rescue_button.click()
    wait_until(lambda: not window.run_started)

    assert captured == [(settings_path.parent.parent, True, False)]
    assert settings_path.read_bytes() == original_contents
    assert window.pipeline_settings.dev_mode is False
    window.close()


def test_rerun_cancel_preserves_settings_and_data(tmp_path, monkeypatch):
    called = []
    window = MainGui(runner_factory=lambda *_: called.append(True))
    window._new_experiment()
    window.settings_window.project_settings_panel.savedir_edit.setText(str(tmp_path))
    window.settings_window.project_settings_panel.experiment_name_edit.setText("existing")
    settings_path = window.settings_window.save_settings()
    saved_data = settings_path.parent.parent / "existing_image.tif"
    saved_data.write_bytes(b"original")
    original_settings = settings_path.read_bytes()
    window._load_experiment(PipelineSettings.from_json(settings_path), settings_path)
    window.pipeline_settings.dev_mode = True
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Cancel
    )

    window.start_button.click()

    assert called == []
    assert saved_data.read_bytes() == b"original"
    assert settings_path.read_bytes() == original_settings
    assert not window.run_started
    window.close()


def test_rerun_targets_opened_folder_and_saves_edits(tmp_path, monkeypatch):
    captured = []

    def factory(run_dir, rescue):
        return lambda settings, _interaction, _cancellation: captured.append(
            (run_dir, rescue, settings.dev_mode)
        )

    run_dir = tmp_path / "20200101_existing"
    config_dir = run_dir / "config"
    config_dir.mkdir(parents=True)
    settings_path = config_dir / "pipeline_settings.json"
    PipelineSettings(savedir=str(tmp_path), savedir_name="existing").to_json(
        settings_path
    )
    window = MainGui(runner_factory=factory)
    window._load_experiment(PipelineSettings.from_json(settings_path), settings_path)
    window.settings_window.project_settings_panel.dev_mode.setChecked(True)
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    )

    window.start_button.click()
    wait_until(lambda: not window.run_started)

    assert captured == [(run_dir, False, True)]
    assert PipelineSettings.from_json(settings_path).dev_mode is True
    window.close()


def test_new_run_warns_before_reusing_nonempty_folder(tmp_path, monkeypatch):
    from gem_screening.infrastructure.filesystem import timestamped_dir_path

    called = []
    window = MainGui(runner_factory=lambda *_: called.append(True))
    window._new_experiment()
    window.settings_window.project_settings_panel.savedir_edit.setText(str(tmp_path))
    window.settings_window.project_settings_panel.experiment_name_edit.setText("collision")
    run_dir = timestamped_dir_path(tmp_path, "collision")
    run_dir.mkdir()
    (run_dir / "image.tif").write_bytes(b"original")
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Cancel
    )

    window.start_button.click()

    assert called == []
    assert (run_dir / "image.tif").read_bytes() == b"original"
    assert not (run_dir / "config" / "pipeline_settings.json").exists()
    window.close()


def test_full_runner_passes_existing_folder_to_workflow(tmp_path, monkeypatch):
    from gem_screening.workflows import complete

    captured = []
    monkeypatch.setattr(
        complete,
        "complete_pipeline",
        lambda settings, *, run_dir, interaction: captured.append((run_dir, interaction)),
    )
    old_run_dir = tmp_path / "20200101_existing"

    interaction = PipelineInteraction()
    _run_complete_pipeline(
        PipelineSettings(),
        interaction,
        CancellationToken(),
        run_dir=old_run_dir,
    )

    assert captured == [(old_run_dir, interaction)]
