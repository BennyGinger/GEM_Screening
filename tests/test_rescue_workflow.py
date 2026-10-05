from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gem_screening.workflows.rescue.flow import run_rescue_flow
from gem_screening.workflows.rescue.assessment import assess_rescue


def _settings(*, dev_mode: bool = False):
    return SimpleNamespace(
        dev_mode=dev_mode,
        stim_settings=SimpleNamespace(true_cell_threshold=42, crop_size=251),
        server_settings=SimpleNamespace(
            track_stitch_threshold=0.8,
            server_timeout_sec=123,
        ),
    )


def _plate(tmp_path: Path):
    well = SimpleNamespace(well_id="run-1_A1")
    return SimpleNamespace(
        run_id="run-1",
        wells=["A1"],
        well_list=[well],
        positive_fovs=[SimpleNamespace(fov_id="A1P1")],
        csv_path=tmp_path / "cell_data.csv",
    )


@patch("gem_screening.workflows.rescue.flow.illuminate")
@patch("gem_screening.workflows.rescue.flow.run_celltinder")
@patch("gem_screening.workflows.rescue.flow.extract_measure_intensities")
@patch("gem_screening.workflows.rescue.flow.ComposeManager")
@patch("gem_screening.workflows.rescue.flow.assess_rescue")
def test_analysis_only_rescue_does_not_start_docker(
    assess_rescue, compose_manager, extract, celltinder, illuminate, tmp_path
):
    plate = _plate(tmp_path)
    settings = _settings()
    manager = MagicMock()
    assess_rescue.return_value = {
        "case": "celltinder", "masks_to_register": [],
        "fovs_to_process": [], "total_fovs": 1,
    }

    run_rescue_flow(manager, settings, plate)

    compose_manager.assert_not_called()
    extract.assert_called_once_with(
        plate.positive_fovs, true_cell_threshold=42, csv_path=plate.csv_path)
    celltinder.assert_called_once_with(plate.csv_path, crop_size=251)
    illuminate.assert_called_once_with(manager, settings, plate)


@patch("gem_screening.workflows.rescue.flow.illuminate")
@patch("gem_screening.workflows.rescue.flow.run_celltinder")
@patch("gem_screening.workflows.rescue.flow.extract_measure_intensities")
@patch("gem_screening.workflows.rescue.flow.assess_rescue")
def test_analysis_only_rescue_uses_embedded_cell_selection(
    assess_rescue, extract, standalone_celltinder, illuminate, tmp_path
):
    plate = _plate(tmp_path)
    settings = _settings()
    manager = MagicMock()
    interaction = MagicMock()
    assess_rescue.return_value = {
        "case": "celltinder", "masks_to_register": [],
        "fovs_to_process": [], "total_fovs": 1,
    }

    run_rescue_flow(manager, settings, plate, interaction=interaction)

    interaction.select_cells.assert_called_once_with(
        plate.csv_path, crop_size=251
    )
    standalone_celltinder.assert_not_called()
    extract.assert_called_once()
    illuminate.assert_called_once_with(manager, settings, plate)


@patch("gem_screening.workflows.rescue.flow._run_analysis")
@patch("gem_screening.workflows.rescue.flow._from_scan")
@patch("gem_screening.workflows.rescue.flow.wait_for_completion")
@patch("gem_screening.workflows.rescue.flow.register_masks_batch_client")
@patch("gem_screening.workflows.rescue.flow.cleanup_stale")
@patch("gem_screening.workflows.rescue.flow.ComposeManager")
@patch("gem_screening.workflows.rescue.flow.assess_rescue")
def test_completed_images_are_registered_then_analyzed_without_reacquisition(
    assess_rescue, compose_manager, cleanup, register, wait, from_scan,
    run_analysis, tmp_path
):
    plate = _plate(tmp_path)
    settings = _settings(dev_mode=True)
    manager = MagicMock()
    masks = [tmp_path / "A1P1_mask_1.tif", tmp_path / "A1P1_mask_2.tif"]
    assess_rescue.return_value = {
        "case": "round2", "masks_to_register": masks,
        "fovs_to_process": [], "total_fovs": 1,
    }

    run_rescue_flow(manager, settings, plate)

    compose_manager.assert_called_once_with(dev_mode=True)
    cleanup.assert_called_once_with()
    register.assert_called_once_with(
        run_id="run-1", mask_paths=masks, total_fovs=1,
        track_stitch_threshold=0.8)
    wait.assert_called_once_with(["run-1_A1"], timeout=123)
    from_scan.assert_not_called()
    run_analysis.assert_called_once_with(manager, settings, plate, interaction=None)


def test_partial_round2_is_not_mistaken_for_analysis_only(tmp_path):
    mask_dir = tmp_path / "masks"
    mask_dir.mkdir()
    for name in ("A1P1_mask_1.tif", "A1P2_mask_1.tif", "A1P1_mask_2.tif"):
        (mask_dir / name).touch()
    (mask_dir / "tracked_files.txt").write_text(
        "A1P1_mask_1.tif\nA1P2_mask_1.tif\nA1P1_mask_2.tif\n"
    )
    plate = SimpleNamespace(
        positive_fovs=[
            SimpleNamespace(fov_id="A1P1"),
            SimpleNamespace(fov_id="A1P2"),
        ],
        csv_path=tmp_path / "cell_data.csv",
        mask_dirs=[mask_dir],
        mask_dir_glob=mask_dir.glob,
    )

    plan = assess_rescue(plate)

    assert plan["case"] == "round2"
    assert plan["fovs_to_process"] == ["A1P2"]
    assert plan["masks_to_register"] == []
