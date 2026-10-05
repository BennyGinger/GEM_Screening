from gem_screening.settings.models import (
    AcquisitionSettings,
    ControlSettings,
    DishSettings,
    InjectionSettings,
    LoggingSettings,
    MeasureSettings,
    PipelineSettings,
    ServerSettings,
    StimSettings,
)
from gem_screening.settings.storage import (
    load_gui_settings,
    load_settings,
    resolve_project_settings_path,
    save_project_settings,
)


def expected_default_settings() -> PipelineSettings:
    return PipelineSettings(
        savedir="",
        savedir_name="",
        logging_settings=LoggingSettings(),
        acquisition_settings=AcquisitionSettings(),
        dish_settings=DishSettings(),
        measure_settings=MeasureSettings(),
        injection_settings=InjectionSettings(),
        server_settings=ServerSettings(),
        control_settings=ControlSettings(),
        stim_settings=StimSettings(),
    )


def test_pipeline_settings_constructs_with_model_defaults():
    assert PipelineSettings() == expected_default_settings()


def test_loader_accepts_a_specific_settings_path(tmp_path):
    settings_path = tmp_path / "custom.json"
    PipelineSettings(savedir="C:/data", savedir_name="experiment").to_json(
        settings_path
    )

    settings = load_settings(settings_path)

    assert settings.savedir == "C:/data"
    assert settings.savedir_name == "experiment"


def test_well_grouping_is_preserved_in_saved_project_settings(tmp_path):
    settings = expected_default_settings()
    settings.dish_settings.well_grouping = "well"
    settings_path = tmp_path / "pipeline_settings.json"

    settings.to_json(settings_path)
    restored = PipelineSettings.from_json(settings_path)

    assert restored.dish_settings.well_grouping == "well"


def test_well_grouping_can_be_omitted_from_a1_manager_arguments():
    dish_settings = DishSettings(well_grouping="row")

    a1_manager_arguments = dish_settings.model_dump(exclude={"well_grouping"})

    assert "well_grouping" in dish_settings.model_dump()
    assert "well_grouping" not in a1_manager_arguments


def test_new_gui_project_uses_model_defaults_and_has_no_output_path():
    settings, output_path = load_gui_settings()

    assert settings == expected_default_settings()
    assert output_path is None


def test_project_can_be_loaded_from_run_config_or_json_path(tmp_path):
    settings = expected_default_settings()
    settings.savedir = str(tmp_path)
    settings.savedir_name = "existing"
    json_path = tmp_path / "run" / "config" / "pipeline_settings.json"
    json_path.parent.mkdir(parents=True)
    settings.to_json(json_path)

    assert resolve_project_settings_path(tmp_path / "run") == json_path
    assert resolve_project_settings_path(json_path.parent) == json_path
    loaded, output_path = load_gui_settings(json_path)
    assert loaded == settings
    assert output_path == json_path


def test_new_project_settings_are_saved_in_timestamped_run_directory(tmp_path):
    settings = expected_default_settings()
    settings.savedir = str(tmp_path)
    settings.savedir_name = "new_exp"

    settings_path = save_project_settings(settings)

    assert settings_path.parent.name == "config"
    assert settings_path.parent.parent.name.endswith("_new_exp")
    assert PipelineSettings.from_json(settings_path) == settings
