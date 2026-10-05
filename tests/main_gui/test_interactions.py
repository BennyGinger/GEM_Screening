import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget

from gem_screening.gui.main_window import MainGui
from gem_screening.runtime.prompts import prompt_to_continue
from gem_screening.settings.models import ServerSettings


APP = QApplication.instance() or QApplication([])


def wait_until(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        APP.processEvents()
        time.sleep(0.01)
    assert predicate()


def start_mock_run(window, tmp_path):
    window._new_experiment()
    project = window.settings_window.project_settings_panel
    project.savedir_edit.setText(str(tmp_path))
    project.experiment_name_edit.setText("interaction_test")
    window.start_button.click()


def test_worker_uses_embedded_tasks_and_independent_prompt(tmp_path, monkeypatch):
    import gem_screening.gui.segmentation_tuning as tuner_module
    import gem_screening.gui.main_window as main_module

    events = []

    class FakeTuner(QWidget):
        result_signal = pyqtSignal(str)

        def __init__(self, **context):
            super().__init__()
            self.quit_btn = QPushButton("Quit")
            assert QThread.currentThread() is APP.thread()
            events.append(("tuner", context["dish_grid"]))

        def get_settings(self):
            return ServerSettings(size=11)

    class FakeCellTinder(QWidget):
        finished = pyqtSignal()

        def __init__(self, csv_path, n_frames, crop_size):
            super().__init__()
            assert QThread.currentThread() is APP.thread()
            events.append(("celltinder", csv_path, n_frames, crop_size))

    monkeypatch.setattr(tuner_module, "TuneSegWidget", FakeTuner)
    monkeypatch.setattr(main_module, "CellTinderWidget", FakeCellTinder)

    def runner(settings, interaction, _cancellation):
        tuned = interaction.tune_segmentation(settings, dish_grid={"A1": {}})
        events.append(("tuned_size", tuned.size))
        prompt_to_continue("Add ligand", interaction)
        events.append(("prompt_done",))
        interaction.select_cells(Path("cells.csv"), crop_size=251)
        events.append(("done",))

    window = MainGui(runner_factory=lambda _path, _rescue: runner)
    start_mock_run(window, tmp_path)
    wait_until(lambda: window.workspace_tabs.count() == 2)
    assert window.workspace_tabs.tabText(1) == "Segmentation tuning"
    assert window.task_widget.quit_btn.text() == "Use settings and continue"
    assert not window.settings_window.project_settings_panel.savedir_edit.isEnabled()
    assert window.workspace_tabs.currentWidget() is window.task_widget

    window.task_widget.result_signal.emit("quit")
    wait_until(lambda: window._prompt_window is not None)
    assert window._prompt_window.prompt_text == "Add ligand"
    assert window.workspace_tabs.count() == 1

    window._prompt_window.continue_btn.click()
    wait_until(lambda: window.workspace_tabs.count() == 2)
    assert window.workspace_tabs.tabText(1) == "CellTinder"
    window.task_widget.finished.emit()
    wait_until(lambda: not window.run_started)

    assert events == [
        ("tuner", {"A1": {}}),
        ("tuned_size", 11),
        ("prompt_done",),
        ("celltinder", Path("cells.csv"), 2, 251),
        ("done",),
    ]
    assert window.workspace_tabs.count() == 1
    assert window.settings_window.project_settings_panel.savedir_edit.isEnabled()
    assert window.pipeline_settings.server_settings.size == 11
    window.close()


def test_closing_embedded_task_cancels_waiting_worker(tmp_path, monkeypatch):
    import gem_screening.gui.main_window as main_module

    class FakeCellTinder(QWidget):
        finished = pyqtSignal()

        def __init__(self, **_payload):
            super().__init__()

    monkeypatch.setattr(main_module, "CellTinderWidget", FakeCellTinder)
    window = MainGui(
        runner_factory=lambda _path, _rescue: (
            lambda _settings, interaction, _cancel: interaction.select_cells(
                Path("cells.csv"), crop_size=251
            )
        )
    )
    start_mock_run(window, tmp_path)
    wait_until(lambda: window.workspace_tabs.count() == 2)

    window.close_current_task()
    wait_until(lambda: not window.run_started)

    assert window._pipeline_outcome == "cancelled"
    assert window.workspace_tabs.count() == 1
    window.close()


def test_dismissed_prompt_cancels_waiting_worker(tmp_path):
    window = MainGui(
        runner_factory=lambda _path, _rescue: (
            lambda _settings, interaction, _cancel: prompt_to_continue(
                "Add ligand", interaction
            )
        )
    )
    start_mock_run(window, tmp_path)
    wait_until(lambda: window._prompt_window is not None)

    window._prompt_window.close()
    wait_until(lambda: not window.run_started)

    assert window._pipeline_outcome == "cancelled"
    window.close()


def test_tuner_construction_failure_releases_worker(tmp_path, monkeypatch):
    import gem_screening.gui.segmentation_tuning as tuner_module

    class BrokenTuner(QWidget):
        def __init__(self, **_payload):
            raise RuntimeError("tuner could not open")

    monkeypatch.setattr(tuner_module, "TuneSegWidget", BrokenTuner)
    window = MainGui(
        runner_factory=lambda _path, _rescue: (
            lambda settings, interaction, _cancel: interaction.tune_segmentation(
                settings
            )
        )
    )
    start_mock_run(window, tmp_path)
    wait_until(lambda: not window.run_started)

    assert window._pipeline_outcome == "failed"
    assert "tuner could not open" in window.terminal_widget.toPlainText()
    assert window.workspace_tabs.count() == 1
    window.close()


def test_cancel_button_releases_worker_waiting_at_prompt(tmp_path):
    window = MainGui(
        runner_factory=lambda _path, _rescue: (
            lambda _settings, interaction, _cancel: prompt_to_continue(
                "Add ligand", interaction
            )
        )
    )
    start_mock_run(window, tmp_path)
    wait_until(lambda: window._prompt_window is not None)

    window.cancel_button.click()
    wait_until(lambda: not window.run_started)

    assert window._pipeline_outcome == "cancelled"
    assert window._prompt_window is None
    window.close()
