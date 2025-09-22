
from pathlib import Path

from gem_screening.tasks.initialization import CONFIG_FOLDER
from gem_screening.settings.models import PipelineSettings
from gem_screening.well_data.well_classes import Well


WELL_OBJ_PATTERN = "*_obj.json"

def load_saved_well_obj(run_dir: Path, well_selection: str | list[str] | None = None) -> list[Well]:
    """
    Load saved well objects from a given run directory, with an optional filter for specific wells.
    Args:
        run_dir (Path): The directory containing the saved well objects.
        well_selection (str | list[str] | None): Specific well(s) to filter. If None, all wells are loaded.
    Returns:
        list[Well]: A list of loaded Well objects.
    """
    
    # Load the well_obj
    wells_paths = list(run_dir.rglob(WELL_OBJ_PATTERN))
    if not wells_paths:
        raise FileNotFoundError(f"No well objects found in {run_dir}")
    wells_list = [Well.from_json(p) for p in wells_paths]
    
    # Filter wells if a selection is provided
    if well_selection is not None:
        if isinstance(well_selection, str):
            well_selection = [well_selection]
        filtered_wells = [w for w in wells_list if w.well in well_selection]
        if not filtered_wells:
            raise ValueError(f"No wells match the selection {well_selection} in {run_dir}")
        return filtered_wells
    else:
        return wells_list
    
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