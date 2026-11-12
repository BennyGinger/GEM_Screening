from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
import tifffile
from a1_manager import StageCoord
from celltinder.backend.data_loader import DataLoader

from gem_screening.experiment import FieldOfView
from gem_screening.tasks.data_intensity import extract_measure_intensities
from gem_screening.settings.models import PipelineSettings
from gem_screening.workflows.complete import run_complete_flow


def _make_fov(tmp_path: Path, *, with_reference: bool) -> FieldOfView:
    """
    Save two measurement frames and tracked masks with optional reference frames.
    """
    well_dir = tmp_path / "well" / "A1"
    fov = FieldOfView(well_dir, StageCoord(xy=(10.0, 20.0)), 0)
    fov.img_dir.mkdir(parents=True)
    fov.mask_dir.mkdir()
    for frame in (1, 2):
        measure = np.full((8, 8), 100 * frame, dtype=np.uint16)
        mask = np.zeros((8, 8), dtype=np.uint16)
        mask[2:6, 2:6] = 1
        tifffile.imwrite(fov.register_img_file(f"measure_{frame}"), measure)
        tifffile.imwrite(fov.register_img_file(f"mask_{frame}"), mask)
        if with_reference:
            reference = np.full((8, 8), 10 * frame, dtype=np.uint16)
            tifffile.imwrite(fov.register_img_file(f"refseg_{frame}"), reference)
    return fov


@pytest.mark.parametrize(("do_refseg", "with_reference"), [(False, False), (False, True), (True, True)])
def test_extract_measurements_respects_channel_mode(tmp_path: Path, do_refseg: bool, with_reference: bool) -> None:
    """
    Produce cell measurements in either channel mode without fabricating references.
    """
    fov = _make_fov(tmp_path, with_reference=with_reference)
    csv_path = tmp_path / "cell_data.csv"

    extract_measure_intensities([fov], true_cell_threshold=50, csv_path=csv_path,
                                do_refseg=do_refseg, max_workers=1,
                                )

    df = pd.read_csv(csv_path)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["before_stim"] == 100
    assert row["after_stim"] == 200
    assert row["ratio"] == 2
    assert row["centroid_x"] == 3.5
    assert row["centroid_y"] == 3.5
    assert row["fov_ID"] == "A1P0"
    if do_refseg:
        assert row["before_ref"] == 10
        assert row["after_ref"] == 20
        assert row["ref_label"] == "refseg"
    else:
        assert pd.isna(row["before_ref"])
        assert pd.isna(row["after_ref"])
        assert pd.isna(row["ref_label"])


def test_reference_mode_still_requires_reference_images(tmp_path: Path) -> None:
    """
    Keep missing reference images from silently producing two-channel results.
    """
    fov = _make_fov(tmp_path, with_reference=False)
    csv_path = tmp_path / "cell_data.csv"

    extract_measure_intensities([fov], true_cell_threshold=50, csv_path=csv_path)

    assert not csv_path.exists()


def test_single_channel_csv_loads_in_celltinder(tmp_path: Path) -> None:
    """
    Load single-channel measurements and cell crops through CellTinder's fallback.
    """
    fov = _make_fov(tmp_path, with_reference=False)
    csv_path = tmp_path / "cell_data.csv"
    extract_measure_intensities([fov], true_cell_threshold=50, csv_path=csv_path,
                                do_refseg=False, max_workers=1,
                                )

    loader = DataLoader(csv_path, n_frames=2, crop_size=5)
    loader.df["valid_cell"] = True
    cell = loader.loads_arrays(0)

    assert loader.df["F-F0"].iloc[0] == 100
    assert len(cell.imgs) == 2
    assert len(cell.masks) == 2
    for frame in cell.imgs:
        np.testing.assert_array_equal(cell.refsegs[frame], cell.imgs[frame])


@pytest.mark.parametrize("do_refseg", [False, True])
def test_complete_flow_reaches_cell_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, do_refseg: bool) -> None:
    """
    Reach cell selection with real measurement output in either channel mode.
    """
    fov = _make_fov(tmp_path, with_reference=do_refseg)
    csv_path = tmp_path / "cell_data.csv"
    well = MagicMock(well="A1", positive_fovs=[fov])
    plate = MagicMock(csv_path=csv_path)
    plate.well_sublists.return_value = [[well]]
    interaction = MagicMock()
    interaction.tune_segmentation.return_value = None
    settings = PipelineSettings()
    settings.measure_settings.do_refseg = do_refseg

    monkeypatch.setattr("cp_server.ComposeManager", MagicMock())
    monkeypatch.setattr("gem_screening.client.cleanup.cleanup_stale", MagicMock())
    monkeypatch.setattr("gem_screening.experiment.Plate", MagicMock(return_value=plate))
    monkeypatch.setattr("gem_screening.tasks.injection.setup_injection_device", MagicMock(return_value=None))
    monkeypatch.setattr("gem_screening.workflows.steps.scan_round1", MagicMock())
    monkeypatch.setattr("gem_screening.workflows.steps.scan_round2", MagicMock())
    monkeypatch.setattr("gem_screening.workflows.steps.stimulate_dish", MagicMock())

    run_complete_flow({}, MagicMock(), tmp_path, "test-run", settings, interaction=interaction)

    assert len(pd.read_csv(csv_path)) == 1
    interaction.select_cells.assert_called_once_with(csv_path, crop_size=settings.stim_settings.crop_size)
