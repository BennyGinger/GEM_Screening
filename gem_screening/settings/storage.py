"""Load, resolve, and save pipeline settings."""

from pathlib import Path

from gem_screening.settings.models import PipelineSettings
from gem_screening.infrastructure.filesystem import create_timestamped_dir
from gem_screening.infrastructure.constants import CONFIG_FOLDER


def load_settings(file_path: str | Path) -> PipelineSettings:
    """Load saved pipeline settings from JSON."""
    return PipelineSettings.from_json(Path(file_path))


def resolve_project_settings_path(project_path: str | Path) -> Path:
    """Resolve a project directory, config directory, or JSON file."""
    project_path = Path(project_path)
    if project_path.is_file():
        if project_path.suffix.lower() != ".json":
            raise ValueError(f"Expected a JSON settings file, got: {project_path}")
        return project_path

    candidates = (
        project_path / CONFIG_FOLDER / "pipeline_settings.json",
        project_path / "pipeline_settings.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"No pipeline_settings.json found in project path: {project_path}"
    )


def load_gui_settings(project_path: str | Path | None = None) -> tuple[PipelineSettings, Path | None]:
    """Load the template for a new project or JSON settings for an existing one."""
    if project_path is None:
        return PipelineSettings(), None

    settings_path = resolve_project_settings_path(project_path)
    settings = PipelineSettings.from_json(settings_path)
    if not isinstance(settings, PipelineSettings):
        settings = PipelineSettings.model_validate(settings)
    return settings, settings_path


def save_project_settings(
    settings: PipelineSettings,
    settings_path: Path | None = None,
) -> Path:
    """Save settings to an existing project or create/reuse its run directory."""
    if settings_path is None:
        if not settings.savedir.strip():
            raise ValueError("User folder is required.")
        if not settings.savedir_name.strip():
            raise ValueError("Experiment name is required.")
        run_dir = create_timestamped_dir(settings.savedir, settings.savedir_name)
        settings_path = run_dir / CONFIG_FOLDER / "pipeline_settings.json"

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings.to_json(settings_path)
    return settings_path
