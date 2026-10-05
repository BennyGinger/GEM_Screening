from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from gem_screening.settings.models import PipelineSettings, ServerSettings
from gem_screening.workflows.complete import run_complete_flow


def test_complete_flow_uses_interaction_and_saves_tuned_settings(tmp_path, monkeypatch):
    import cp_server
    import gem_screening.client.cleanup as cleanup_module
    import gem_screening.runtime.external as external_module
    import gem_screening.tasks.injection as injection_module
    import gem_screening.experiment as experiment_module

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    csv_path = tmp_path / "cell_data.csv"
    plate = SimpleNamespace(well_sublists=lambda grouping_method: [], csv_path=csv_path)
    monkeypatch.setattr(cp_server, "ComposeManager", MagicMock())
    monkeypatch.setattr(cleanup_module, "cleanup_stale", MagicMock())
    monkeypatch.setattr(external_module, "run_celltinder", MagicMock())
    monkeypatch.setattr(injection_module, "setup_injection_device", MagicMock())
    monkeypatch.setattr(experiment_module, "Plate", MagicMock(return_value=plate))

    class Interaction:
        def __init__(self):
            self.tuning_context = None
            self.csv_path = None

        def tune_segmentation(self, settings, **context):
            self.tuning_context = context
            return ServerSettings(size=17)

        def select_cells(self, path: Path, crop_size: int):
            self.csv_path = path

    interaction = Interaction()
    settings = PipelineSettings()
    manager = object()
    grid = {"A1": {1: object()}}

    run_complete_flow(
        grid, manager, tmp_path, "test-run", settings, interaction=interaction
    )

    assert interaction.tuning_context == {
        "dish_grid": grid, "a1_manager": manager
    }
    assert interaction.csv_path == csv_path
    assert settings.server_settings.size == 17
    assert PipelineSettings.from_json(
        config_dir / "pipeline_settings.json"
    ).server_settings.size == 17
    external_module.run_celltinder.assert_not_called()
