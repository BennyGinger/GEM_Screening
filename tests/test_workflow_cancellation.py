from types import SimpleNamespace

import pytest

from gem_screening.runtime import CancellationToken, PipelineCancelled, PipelineInteraction
from gem_screening.tasks import image_capture


def test_imaging_stops_before_next_snap(monkeypatch):
    token = CancellationToken()
    interaction = PipelineInteraction(token)
    fovs = [
        SimpleNamespace(well="A1", fov_id="A1P1"),
        SimpleNamespace(well="A1", fov_id="A1P2"),
    ]
    snapped = []

    def snap(fov, **_kwargs):
        snapped.append(fov)
        token.request()
        return None

    monkeypatch.setattr(image_capture, "_process_single_fov", snap)
    with pytest.raises(PipelineCancelled):
        image_capture._process_fovs(
            "measure_1", fovs, object(),
            [("measure_1", object(), lambda _paths: None)],
            cancel_check=interaction.check_cancelled,
        )

    assert snapped == [fovs[0]]


def test_server_wait_checks_cancellation_before_poll(monkeypatch):
    from gem_screening.client import progress

    token = CancellationToken()
    token.request()
    monkeypatch.setattr(
        progress, "_initialize_progress",
        lambda _well_ids: pytest.fail("Server should not be polled"),
    )
    with pytest.raises(PipelineCancelled):
        progress.wait_for_completion("A1", cancel_check=token.raise_if_requested)
