from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import logging
import socket
import subprocess
from threading import Event
from unittest.mock import MagicMock, call
import weakref

import pytest
import pycromanager

from gem_screening.runtime import micromanager
from gem_screening.runtime.micromanager import configuration_path, headless_microscope


def test_proxy_cleanup_closes_a_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Close every retained proxy even as closure removes it from the bridge registry.
    """
    from pyjavaz.bridge import Bridge

    bridge = MagicMock()
    first, second = MagicMock(), MagicMock()
    proxies = {first, second}
    bridge._java_objects = proxies

    def close_first() -> None:
        """
        Model a proxy unregistering itself when explicitly closed.
        """
        proxies.remove(first)

    def close_second() -> None:
        """
        Model another proxy unregistering itself when explicitly closed.
        """
        proxies.remove(second)

    first._close.side_effect = close_first
    second._close.side_effect = close_second
    monkeypatch.setitem(Bridge._cached_bridges_by_port, micromanager.BRIDGE_PORT, weakref.ref(bridge))
    micromanager._close_java_proxies(micromanager.BRIDGE_PORT)
    first._close.assert_called_once()
    second._close.assert_called_once()
    assert not proxies


@pytest.mark.parametrize("close_failure", [False, True])
def test_shutdown_releases_proxies_before_stopping_java(monkeypatch: pytest.MonkeyPatch,
                                                       close_failure: bool,
                                                       ) -> None:
    """
    Preserve shutdown ordering and terminate Java even if proxy cleanup fails.
    """
    import pyjavaz

    events = MagicMock()
    process = MagicMock()
    process.poll.return_value = None
    monkeypatch.setattr(micromanager, "_close_java_proxies", events.close)
    monkeypatch.setattr(micromanager, "_terminate_backend", events.terminate)
    monkeypatch.setattr(pyjavaz, "server_terminated", events.notify)
    if close_failure:
        events.close.side_effect = RuntimeError("proxy cleanup failed")
        with pytest.raises(RuntimeError, match="proxy cleanup failed"):
            micromanager._shutdown_backend(process)
    else:
        micromanager._shutdown_backend(process)
    assert events.mock_calls == [call.close(micromanager.BRIDGE_PORT),
                                 call.terminate(process), call.notify(micromanager.BRIDGE_PORT),
                                 ]


def test_timeout_status_is_debug_only(tmp_path: Path,
                                     backend: MagicMock,
                                     caplog: pytest.LogCaptureFixture,
                                     ) -> None:
    """
    Keep the configured timeout out of the normal INFO console output.
    """
    with caplog.at_level(logging.DEBUG, logger=micromanager.__name__):
        with headless_microscope("pE-800", log_dir=tmp_path / "logs",
                                autofocus_method="Manual", mm_app_path=tmp_path,
                                config_dir=tmp_path / "config_files",
                                ):
            pass
    timeout_records = [record for record in caplog.records if "Startup timeout:" in record.message]
    assert len(timeout_records) == 1
    assert timeout_records[0].levelno == logging.DEBUG


def test_legacy_command_uses_only_required_jars(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch,
                                              ) -> None:
    """
    Preserve the installed Core and avoid scanning unrelated plugin libraries.
    """
    plugins = tmp_path / "plugins" / "Micro-Manager"
    plugins.mkdir(parents=True)
    for name in micromanager.LEGACY_BACKEND_JARS:
        (plugins / name).touch()
    popen = MagicMock()
    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(socket, "socket", MagicMock())
    startup_log = tmp_path / "startup.log"
    micromanager._launch_backend(tmp_path, startup_log)
    command = popen.call_args.args[0]
    assert command[0] == str(tmp_path / "jre" / "bin" / "java.exe")
    assert command[2].split(";") == [str(plugins / name) for name in micromanager.LEGACY_BACKEND_JARS]
    assert "*" not in command[2]
    assert command[-1] == str(micromanager.BRIDGE_PORT)
    assert popen.call_args.kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW
    assert popen.call_args.kwargs["stderr"] == subprocess.STDOUT
    assert startup_log.is_file()


def test_occupied_bridge_port_does_not_launch_java(tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch,
                                                 ) -> None:
    """
    Leave an existing backend alone and report its occupied bridge port.
    """
    plugins = tmp_path / "plugins" / "Micro-Manager"
    plugins.mkdir(parents=True)
    for name in micromanager.LEGACY_BACKEND_JARS:
        (plugins / name).touch()
    port_check = MagicMock()
    port_check.return_value.__enter__.return_value.bind.side_effect = OSError("occupied")
    popen = MagicMock()
    monkeypatch.setattr(socket, "socket", port_check)
    monkeypatch.setattr(subprocess, "Popen", popen)
    with pytest.raises(RuntimeError, match="port 4827 is in use"):
        micromanager._launch_backend(tmp_path, tmp_path / "startup.log")
    popen.assert_not_called()


@pytest.mark.parametrize("exited", [False, True])
def test_startup_failure_before_readiness_is_reported(tmp_path: Path,
                                                    backend: MagicMock,
                                                    exited: bool,
                                                    ) -> None:
    """
    Bound a silent startup and surface Java output when it exits early.
    """
    def launch(mm_app_path: Path, startup_log: Path) -> MagicMock:
        """
        Model Java stalling or exiting before reporting readiness.
        """
        startup_log.write_text("java.lang.NoClassDefFoundError" if exited else "")
        backend.process.poll.return_value = 1 if exited else None
        return backend.process

    backend.launch.side_effect = launch
    expected = "NoClassDefFoundError" if exited else "did not become ready within"
    with pytest.raises(RuntimeError, match=expected):
        with headless_microscope("pE-800",
                                log_dir=tmp_path / "logs",
                                autofocus_method="Manual",
                                mm_app_path=tmp_path,
                                config_dir=tmp_path / "config_files",
                                startup_timeout_seconds=0.02,
                                ):
            pytest.fail("Hardware workflow must not run before Java is ready")
    backend.core.load_system_configuration.assert_not_called()


def test_startup_timeout_terminates_blocked_launcher(tmp_path: Path, backend: MagicMock) -> None:
    """
    Simulate Java never reporting readiness and verify timeout releases the worker.
    """
    stopped = Event()

    def blocked_start(filename: str) -> None:
        """
        Model a device initialization call blocked until Java is stopped.
        """
        assert stopped.wait(2.0), "Watchdog did not stop the blocked launcher"
        raise RuntimeError("Java process exited before STARTED")

    backend.start.side_effect = blocked_start
    backend.process.terminate.side_effect = stopped.set
    with pytest.raises(RuntimeError, match="did not become ready within 0.02 seconds"):
        with headless_microscope("pE-800",
                                log_dir=tmp_path / "logs",
                                autofocus_method="Manual",
                                mm_app_path=tmp_path,
                                config_dir=tmp_path / "config_files",
                                startup_timeout_seconds=0.02,
                                ):
            pytest.fail("Workflow must not run after startup timed out")
    backend.process.terminate.assert_called_once()
    backend.core.get_camera_device.assert_not_called()


@pytest.fixture
def backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """
    Replace Java process creation and hardware calls with an owned fake backend.
    """
    config_dir = tmp_path / "config_files"
    config_dir.mkdir()
    for filename in ("v1_Andor_p800.cfg", "v1_Andor_p4000.cfg"):
        (config_dir / filename).touch()
    calls = MagicMock()
    calls.core.get_camera_device.return_value = "Andor sCMOS Camera"
    calls.process.poll.return_value = None
    calls.start = calls.core.load_system_configuration

    def launch(mm_app_path: Path, startup_log: Path) -> MagicMock:
        """
        Model Java emitting the legacy readiness message.
        """
        startup_log.write_text("Headless mode started\n")
        return calls.process

    def wait(timeout: float) -> int:
        """
        Mark the fake process as stopped after termination.
        """
        calls.process.poll.return_value = 0
        return 0

    calls.launch.side_effect = launch
    calls.process.wait.side_effect = wait
    monkeypatch.setattr(micromanager, "_launch_backend", calls.launch)
    monkeypatch.setattr(pycromanager, "Core", lambda: calls.core)
    return calls


@pytest.mark.parametrize("lamp,suffix", [("pE-800", "p800"), ("pE-4000", "p4000")])
def test_selected_config_is_loaded_before_work_and_released_afterwards(tmp_path: Path,
                                                                     backend: MagicMock,
                                                                     lamp: str,
                                                                     suffix: str,
                                                                     ) -> None:
    """
    Load the selected config independently of the backend installation directory.
    """
    installation = tmp_path / "new-runtime"
    installation.mkdir()
    with headless_microscope(lamp,
                             log_dir=tmp_path / "logs",
                             autofocus_method="Manual",
                             mm_app_path=installation,
                             config_dir=tmp_path / "config_files",
                             ):
        backend.launch.assert_called_once_with(installation,
                                               tmp_path / "logs" / "micromanager-startup.log",
                                               )
        backend.core.load_system_configuration.assert_called_once_with(
            str(tmp_path / "config_files" / f"v1_Andor_{suffix}.cfg")
        )
        backend.core.set_primary_log_file.assert_called_once_with(
            str(tmp_path / "logs" / "micromanager.log")
        )
        backend.core.get_device_type.assert_called_once_with(lamp)
        backend.process.terminate.assert_not_called()
    backend.core.set_shutter_open.assert_called_once_with(False)
    backend.core.unload_all_devices.assert_called_once()
    backend.process.terminate.assert_called_once()


@pytest.mark.parametrize("startup_failure", [True, False])
def test_startup_or_workflow_failure_always_stops_backend(
    tmp_path: Path, backend: MagicMock, startup_failure: bool,
) -> None:
    if startup_failure:
        backend.start.side_effect = RuntimeError("driver missing")
    with pytest.raises(RuntimeError, match="driver missing|workflow failed"):
        with headless_microscope(
            "pE-800", log_dir=tmp_path / "logs", autofocus_method="sq_grad",
            mm_app_path=tmp_path,
            config_dir=tmp_path / "config_files",
        ):
            raise RuntimeError("workflow failed")
    backend.process.terminate.assert_called_once()


def test_missing_camera_prevents_workflow(tmp_path: Path, backend: MagicMock) -> None:
    backend.core.get_camera_device.return_value = ""
    with pytest.raises(RuntimeError, match="no default camera"):
        with headless_microscope(
            "pE-800", log_dir=tmp_path / "logs", autofocus_method="Manual",
            mm_app_path=tmp_path,
            config_dir=tmp_path / "config_files",
        ):
            pytest.fail("Workflow must not start without a camera")
    backend.process.terminate.assert_called_once()


def test_invalid_settings_do_not_start_hardware(tmp_path: Path, backend: MagicMock) -> None:
    with pytest.raises(ValueError, match="Select pE-800 or pE-4000"):
        configuration_path("DiaLamp", tmp_path)
    with pytest.raises(FileNotFoundError, match="configuration not found"):
        configuration_path("pE-800", tmp_path / "missing")
    with pytest.raises(ValueError, match="OughtaFocus"):
        with headless_microscope(
            "pE-800", log_dir=tmp_path / "logs", autofocus_method="OughtaFocus",
            mm_app_path=tmp_path,
            config_dir=tmp_path / "config_files",
        ):
            pytest.fail("OughtaFocus must be rejected before startup")
    backend.launch.assert_not_called()
    backend.process.terminate.assert_not_called()


@pytest.mark.parametrize("rescue", [False, True])
@pytest.mark.parametrize("cancel_during_startup", [False, True])
def test_gui_adapters_start_before_workflow_and_stop_on_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    rescue: bool, cancel_during_startup: bool,
) -> None:
    from gem_screening.gui import main_window
    from gem_screening.runtime import CancellationToken, PipelineCancelled, PipelineInteraction
    from gem_screening.settings.models import PipelineSettings
    from gem_screening.workflows import complete
    from gem_screening.workflows import rescue as rescue_module

    settings = PipelineSettings()
    settings.acquisition_settings.lamp_name = "pE-4000"
    cancellation = CancellationToken()
    interaction = PipelineInteraction(cancellation)
    lifecycle: list[str] = []

    @contextmanager
    def managed_backend(
        lamp_name: str, *, log_dir: Path, autofocus_method: str,
    ) -> Iterator[None]:
        assert lamp_name == "pE-4000"
        assert log_dir == tmp_path / "logs"
        assert autofocus_method == "Manual"
        lifecycle.append("started")
        if cancel_during_startup:
            cancellation.request()
        try:
            yield
        finally:
            lifecycle.append("stopped")

    workflow = MagicMock(side_effect=lambda *args, **kwargs: lifecycle.append("workflow"))
    monkeypatch.setattr(main_window, "headless_microscope", managed_backend)
    monkeypatch.setattr(complete, "complete_pipeline", workflow)
    monkeypatch.setattr(rescue_module, "rescue_pipeline", workflow)
    runner = main_window._run_rescue_pipeline if rescue else main_window._run_complete_pipeline
    if cancel_during_startup:
        with pytest.raises(PipelineCancelled):
            runner(settings, interaction, cancellation, run_dir=tmp_path)
        assert lifecycle == ["started", "stopped"]
        workflow.assert_not_called()
    else:
        runner(settings, interaction, cancellation, run_dir=tmp_path)
        assert lifecycle == ["started", "workflow", "stopped"]
        workflow.assert_called_once()
