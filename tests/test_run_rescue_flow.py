import sys
import types
import pytest
from types import SimpleNamespace

# Stub cp_server and nested modules before importing workflows to satisfy imports
cp_server_stub = types.ModuleType("cp_server")
class _DummyCM:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
cp_server_stub.ComposeManager = _DummyCM

# Create nested submodules: cp_server.tasks_server.utils.redis_com
cp_server_tasks = types.ModuleType("cp_server.tasks_server")
cp_server_utils = types.ModuleType("cp_server.tasks_server.utils")
cp_server_redis = types.ModuleType("cp_server.tasks_server.utils.redis_com")

class _DummyRedis:
    def __getattr__(self, name):
        # Provide no-op callables for any attribute (e.g., set, get, delete)
        def _noop(*args, **kwargs):
            return None
        return _noop

cp_server_redis.redis_client = _DummyRedis()

# Register modules in sys.modules
sys.modules.setdefault("cp_server", cp_server_stub)
sys.modules.setdefault("cp_server.tasks_server", cp_server_tasks)
sys.modules.setdefault("cp_server.tasks_server.utils", cp_server_utils)
sys.modules.setdefault("cp_server.tasks_server.utils.redis_com", cp_server_redis)

# Now import the module under test
import gem_screening.tasks.workflows as wf


class DummyWell:
    def __init__(self, well_id: str = "W1"):
        self.well_id = well_id


def make_settings(threshold: float = 0.75):
    return SimpleNamespace(server_settings=SimpleNamespace(track_stitch_threshold=threshold))


@pytest.fixture()
def call_spy(monkeypatch):
    calls = {
        "register": [],
        "scan_round1": [],
        "scan_round2": [],
        "cell_selection": [],
        "illuminate": [],
        "assess_rescue": [],
    }

    def reg_mock(well_id, masks, total_fovs, track_stitch_threshold=None):
        calls["register"].append((well_id, list(masks), total_fovs, track_stitch_threshold))

    def s1_mock(a1_manager, settings, well_obj, fov_ids=None):
        calls["scan_round1"].append((well_obj.well_id, fov_ids))

    def s2_mock(a1_manager, settings, well_obj, fov_ids=None):
        calls["scan_round2"].append((well_obj.well_id, fov_ids))

    def cs_mock(settings, well_obj):
        calls["cell_selection"].append(well_obj.well_id)

    def il_mock(a1_manager, settings, well_obj):
        calls["illuminate"].append(well_obj.well_id)

    # Patch in the workflows module namespace
    monkeypatch.setattr(wf, "register_masks_batch_client", reg_mock)
    monkeypatch.setattr(wf, "scan_round1", s1_mock)
    monkeypatch.setattr(wf, "scan_round2", s2_mock)
    monkeypatch.setattr(wf, "cell_selection", cs_mock)
    monkeypatch.setattr(wf, "illuminate", il_mock)

    return calls


def test_run_rescue_flow_round1(monkeypatch, call_spy):
    # Arrange: assess_rescue returns case round1
    plan = {
        "case": "round1",
        "masks_to_register": ["/m/A1P1_mask_1.tif", "/m/A1P2_mask_1.tif"],
        "fovs_to_process": ["A1P3", "A1P4"],
        "total_fovs": 4,
    }

    monkeypatch.setattr(wf, "assess_rescue", lambda well: plan)

    # Act
    wf.run_rescue_flow(a1_manager=object(), settings=make_settings(), well_objs=[DummyWell("WELL1")])

    # Assert
    # One registration without threshold (round1)
    assert call_spy["register"] == [("WELL1", plan["masks_to_register"], plan["total_fovs"], None)]
    # scan_round1 called with provided fovs
    assert call_spy["scan_round1"] == [("WELL1", plan["fovs_to_process"])]
    # scan_round2 called after scan_round1, with fov_ids reset to None in _from_scan
    assert call_spy["scan_round2"] == [("WELL1", None)]
    # Post-analysis steps always run
    assert call_spy["cell_selection"] == ["WELL1"]
    assert call_spy["illuminate"] == ["WELL1"]


def test_run_rescue_flow_round2(monkeypatch, call_spy):
    # Arrange: assess_rescue returns case round2
    plan = {
        "case": "round2",
        "masks_to_register": ["/m/A1P1_mask_1.tif", "/m/A1P1_mask_2.tif"],
        "fovs_to_process": ["A1P3", "A1P4"],
        "total_fovs": 4,
    }

    monkeypatch.setattr(wf, "assess_rescue", lambda well: plan)

    # Act
    settings = make_settings(threshold=0.9)
    wf.run_rescue_flow(a1_manager=object(), settings=settings, well_objs=[DummyWell("WELL2")])

    # Assert
    # One registration with threshold (round2)
    assert call_spy["register"] == [("WELL2", plan["masks_to_register"], plan["total_fovs"], 0.9)]
    # scan_round1 should NOT be called
    assert call_spy["scan_round1"] == []
    # scan_round2 called with the provided fovs_to_process
    assert call_spy["scan_round2"] == [("WELL2", plan["fovs_to_process"])]
    # Post-analysis steps always run
    assert call_spy["cell_selection"] == ["WELL2"]
    assert call_spy["illuminate"] == ["WELL2"]


def test_run_rescue_flow_celltinder(monkeypatch, call_spy):
    # Arrange: assess_rescue returns celltinder
    plan = {
        "case": "celltinder",
        "masks_to_register": [],
        "fovs_to_process": [],
        "total_fovs": 0,
    }

    monkeypatch.setattr(wf, "assess_rescue", lambda well: plan)

    # Act
    wf.run_rescue_flow(a1_manager=object(), settings=make_settings(), well_objs=[DummyWell("WELL3")])

    # Assert
    # No registration
    assert call_spy["register"] == []
    # No scanning in _after_scan
    assert call_spy["scan_round1"] == []
    assert call_spy["scan_round2"] == []
    # Only post-analysis steps run
    assert call_spy["cell_selection"] == ["WELL3"]
    assert call_spy["illuminate"] == ["WELL3"]
