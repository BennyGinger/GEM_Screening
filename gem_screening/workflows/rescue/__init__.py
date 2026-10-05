from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from gem_screening.runtime.prompt_gui import PipelineQuit
from gem_screening.settings.models import PipelineSettings
from gem_screening.workflows.initialization import initialize_rescue_pipeline
from gem_screening.workflows.rescue.loading import load_saved_plate, load_saved_settings

if TYPE_CHECKING:
    from gem_screening.runtime.interaction import PipelineInteraction

def rescue_pipeline(
    run_dir: Path,
    settings: PipelineSettings | None = None,
    well_selection: str | list[str] | None = None,
    *,
    interaction: PipelineInteraction | None = None,
) -> None:
    """Resume processing for an existing GEM Screening run."""
    plate = load_saved_plate(run_dir, well_selection)
    if settings is None:
        settings = load_saved_settings(run_dir)

    a1_manager, logger = initialize_rescue_pipeline(settings, run_dir, plate.run_id)

    # Import after runtime environment and logging have been configured.
    from gem_screening.workflows.rescue.flow import run_rescue_flow

    try:
        run_rescue_flow(a1_manager, settings, plate, interaction=interaction)
    except PipelineQuit:
        logger.info("User chose to quit during pipeline execution. Stopping pipeline.")
        if interaction is not None:
            raise
        return

    logger.info("Pipeline rescue completed successfully.")


__all__ = ["rescue_pipeline"]
