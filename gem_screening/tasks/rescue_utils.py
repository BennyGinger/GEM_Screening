
from pathlib import Path

from gem_screening.tasks.initialization import CONFIG_FOLDER
from gem_screening.settings.models import PipelineSettings
from gem_screening.well_data.well_classes import Well, Plate


WELL_OBJ_PATTERN = "*_obj.json"

def load_saved_plate(run_dir: Path, well_selection: str | list[str] | None = None) -> Plate:
    """
    Load saved well objects from a given run directory, with an optional filter for specific wells.
    Args:
        run_dir (Path): The directory containing the saved well objects.
        well_selection (str | list[str] | None): Specific well(s) to filter. If None, all wells are loaded.
    Returns:
        Plate: The loaded Plate object containing all well objects.
    """
    # Load the plate object
    config_dir = run_dir.joinpath(CONFIG_FOLDER)
    if not config_dir.exists():
        raise FileNotFoundError(f"No configuration folder found at {config_dir}")
    plate_path = _find_obj_json_file(config_dir)
    if plate_path is None:
        raise FileNotFoundError(f"No *_obj.json file found in {config_dir}")
    plate = Plate.from_json(plate_path)
    
    # Filter wells if a selection is provided
    if well_selection is not None:
        if isinstance(well_selection, str):
            well_selection = [well_selection]

        plate.select_wells(well_selection)

    return plate

def load_saved_settings(run_dir: Path) -> PipelineSettings:
    """
    Load pipeline settings from a given run directory.
    Args:
        run_dir (Path): The directory containing the saved pipeline settings.
    Returns:
        PipelineSettings: The loaded pipeline settings.
    """
    settings_path = run_dir.joinpath(CONFIG_FOLDER, "pipeline_settings.json")
    if not settings_path.exists():
        raise FileNotFoundError(f"No pipeline settings found at {settings_path}")
    return PipelineSettings.from_json(settings_path)

def _find_obj_json_file(run_dir: Path) -> Path | None:
    """
    Find the first file in run_dir that ends with 'obj.json'.
    Returns the Path if found, else None.
    """
    for file in run_dir.glob("*_obj.json"):
        return file
    return None