"""Own the headless Micro-Manager backend used by GUI pipeline runs."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
import socket
import subprocess
from threading import Event, Thread
from time import monotonic, sleep
from typing import Final, Protocol, cast


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

MICRO_MANAGER_PATH: Final[Path] = Path(r"C:\Program Files\Micro-Manager-2.0")
HARDWARE_CONFIG_PATH: Final[Path] = Path(r"C:\Program Files\Micro-Manager-2.0\config_files")
STARTUP_TIMEOUT_SECONDS: Final[float] = 60.0
BRIDGE_PORT: Final[int] = 4827
LEGACY_BACKEND_JARS: Final[tuple[str, ...]] = (
    "PycroManagerJava-0.25.0.jar", "AcqEngJ-0.15.0.jar",
    "MMCoreJ.jar", "jeromq-0.5.1.jar",
)
LAMP_CONFIG_FILES: Final[dict[str, str]] = {
    "pE-800": "v1_Andor_p800.cfg",
    "pE-4000": "v1_Andor_p4000.cfg",
}


class _HardwareCore(Protocol):
    """Core methods used here, supplied dynamically by the Java bridge."""

    def get_camera_device(self) -> str:
        """
        Return the default camera label.
        """
        ...

    def get_device_type(self, label: str) -> object:
        """
        Return the type of a loaded device.
        """
        ...

    def set_shutter_open(self, state: bool) -> None:
        """
        Set the active shutter state.
        """
        ...

    def unload_all_devices(self) -> None:
        """
        Release the loaded hardware devices.
        """
        ...

    def set_primary_log_file(self, filename: str) -> None:
        """
        Enable Core logging before device configuration begins.
        """
        ...

    def enable_debug_log(self, enabled: bool) -> None:
        """
        Control detailed device initialization logging.
        """
        ...

    def load_system_configuration(self, filename: str) -> None:
        """
        Load and initialize the selected hardware configuration.
        """
        ...


def configuration_path(lamp_name: str,
                       config_dir: Path = HARDWARE_CONFIG_PATH,
                       ) -> Path:
    """
    Resolve and validate the single-lamp hardware configuration.
    """
    filename = LAMP_CONFIG_FILES.get(lamp_name)
    if filename is None:
        raise ValueError(
            f"Headless startup does not support lamp {lamp_name!r}. "
            "Select pE-800 or pE-4000."
        )
    config_file = config_dir / filename
    if not config_file.is_file():
        raise FileNotFoundError(f"Micro-Manager hardware configuration not found: {config_file}")
    return config_file


def _watch_startup(finished: Event,
                   timed_out: Event,
                   timeout_seconds: float,
                   stop_backend: Callable[[], None],
                   ) -> None:
    """
    Report startup progress and stop a backend that exceeds its deadline.
    """
    started_at = monotonic()
    remaining = timeout_seconds
    while not finished.wait(min(5.0, remaining)):
        elapsed = monotonic() - started_at
        remaining = timeout_seconds - elapsed
        if elapsed >= timeout_seconds:
            timed_out.set()
            logger.error("Micro-Manager startup timed out after %.0f seconds; stopping the backend.",
                         timeout_seconds,
                         )
            try:
                stop_backend()
            except Exception:
                logger.exception("Could not terminate Micro-Manager after the startup timeout.")
            return
        logger.debug("Micro-Manager is still starting (%.0f / %.0f seconds).",
                    elapsed, timeout_seconds,
                    )


def _launch_backend(mm_app_path: Path, startup_log: Path) -> subprocess.Popen[bytes]:
    """
    Launch the installed legacy Java backend with only its required libraries.
    """
    plugins = mm_app_path / "plugins" / "Micro-Manager"
    jars = [plugins / name for name in LEGACY_BACKEND_JARS]
    for jar in jars:
        if not jar.is_file():
            raise FileNotFoundError(f"Required legacy Micro-Manager library not found: {jar}")
    with socket.socket() as port_check:
        try:
            port_check.bind(("127.0.0.1", BRIDGE_PORT))
        except OSError as error:
            raise RuntimeError(f"Micro-Manager bridge port {BRIDGE_PORT} is in use. "
                               "Close the existing Micro-Manager backend first."
                               ) from error
    command = [str(mm_app_path / "jre" / "bin" / "java.exe"),
               "-classpath", ";".join(str(jar) for jar in jars), "-Xmx2000m",
               "org.micromanager.remote.HeadlessLauncher", str(BRIDGE_PORT),
               ]
    with startup_log.open("wb") as output:
        return subprocess.Popen(command, cwd=mm_app_path,
                                stdout=output, stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                )


def _terminate_backend(process: subprocess.Popen[bytes]) -> None:
    """
    Stop only the Java process owned by this run, including a stalled startup.
    """
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5.0)


def _close_java_proxies(port: int) -> None:
    """
    Release this bridge's live proxies before stopping their Java server.

    Pyjavaz 1.2.8 has no safe public close-all operation: Bridge.close iterates
    a set that proxy closure mutates. Closing a snapshot lets the last proxy
    close the now-empty bridge, without deferring destructors to garbage collection.
    """
    from pyjavaz.bridge import Bridge

    cached_bridge = Bridge._cached_bridges_by_port.get(port)
    bridge = cached_bridge() if cached_bridge is not None else None
    if bridge is None:
        return
    for proxy in list(bridge._java_objects):
        proxy._close()


def _shutdown_backend(process: subprocess.Popen[bytes]) -> None:
    """
    Close client proxies before terminating Java, including failed startups.
    """
    from pyjavaz import server_terminated

    if process.poll() is not None:
        server_terminated(BRIDGE_PORT)
    try:
        _close_java_proxies(BRIDGE_PORT)
    finally:
        try:
            _terminate_backend(process)
        finally:
            server_terminated(BRIDGE_PORT)


def _wait_for_backend(process: subprocess.Popen[bytes], startup_log: Path) -> None:
    """
    Recognize the legacy readiness message and surface early Java failures.
    """
    while True:
        output = startup_log.read_text(encoding="utf-8", errors="replace")
        if process.poll() is not None:
            raise RuntimeError(f"Java backend exited before it became ready. "
                               f"Startup log: {startup_log}\n{output[-4000:]}"
                               )
        if "Headless mode started" in output:
            return
        sleep(0.1)


def _start_backend(process: subprocess.Popen[bytes],
                   startup_log: Path,
                   config_file: Path,
                   lamp_name: str,
                   core_log_path: Path,
                   timeout_seconds: float,
                   ) -> _HardwareCore:
    """
    Connect to the legacy Core and load hardware under the startup watchdog.
    """
    from pycromanager import Core
    from pyjavaz.bridge import Bridge

    finished = Event()
    timed_out = Event()
    watcher = Thread(target=_watch_startup,
                     args=(finished, timed_out, timeout_seconds,
                           lambda: _terminate_backend(process)),
                     name="MicroManagerStartupWatchdog",
                     daemon=True,
                     )
    watcher.start()
    try:
        _wait_for_backend(process, startup_log)
        # A new server may reuse the previous run's port.
        Bridge._ports_with_terminated_servers.discard(BRIDGE_PORT)
        core = cast(_HardwareCore, Core())
        core.set_primary_log_file(str(core_log_path))
        core.enable_debug_log(True)
        logger.info("Java backend connected. Loading hardware configuration: %s", config_file)
        core.load_system_configuration(str(config_file))
        if not core.get_camera_device():
            raise RuntimeError("The hardware configuration has no default camera.")
        core.get_device_type(lamp_name)
    except Exception as error:
        if timed_out.is_set():
            raise TimeoutError(f"Micro-Manager did not become ready within {timeout_seconds:g} seconds. "
                               f"Startup log: {startup_log}. Core log: {core_log_path}"
                               ) from error
        raise
    finally:
        finished.set()
        watcher.join()
    if timed_out.is_set():
        raise TimeoutError(f"Micro-Manager startup exceeded {timeout_seconds:g} seconds.")
    return core


@contextmanager
def headless_microscope(lamp_name: str,
                        *,
                        log_dir: Path,
                        autofocus_method: str,
                        mm_app_path: Path = MICRO_MANAGER_PATH,
                        config_dir: Path = HARDWARE_CONFIG_PATH,
                        startup_timeout_seconds: float = STARTUP_TIMEOUT_SECONDS,
                        ) -> Iterator[None]:
    """
    Load hardware before A1Manager is created and release it after the run.

    Called in the pipeline worker. The installed 0.25 Java launcher needs a
    minimal classpath, its legacy readiness message, and explicit config loading.
    """
    if autofocus_method == "OughtaFocus":
        raise ValueError(
            "OughtaFocus requires Micro-Manager Studio and is disabled in headless mode. "
            "Select Manual or sq_grad autofocus."
        )
    config_file = configuration_path(lamp_name, config_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    startup_log = log_dir / "micromanager-startup.log"
    logger.info("Micro-Manager installation: %s", mm_app_path)
    logger.info("Starting Micro-Manager in the background with %s", config_file)
    logger.info("Java startup output: %s", startup_log)
    logger.info("Core log: %s", log_dir / "micromanager.log")
    logger.debug("Startup timeout: %.0f seconds.", startup_timeout_seconds)
    core: _HardwareCore | None = None
    process = _launch_backend(mm_app_path, startup_log)
    try:
        try:
            core = _start_backend(process, startup_log, config_file, lamp_name,
                                  log_dir / "micromanager.log", startup_timeout_seconds,
                                  )
        except Exception as error:
            raise RuntimeError(
                f"Could not initialize Micro-Manager with {config_file}. "
                "Close any open Micro-Manager instance and check the hardware "
                f"connections and configuration. Details: {error}"
            ) from error

        logger.info("Micro-Manager is ready (%s).", lamp_name)
        yield
    finally:
        if core is not None:
            try:
                core.set_shutter_open(False)
                core.unload_all_devices()
            except Exception:
                logger.exception("Could not release Micro-Manager devices cleanly.")
        try:
            _shutdown_backend(process)
        except Exception:
            logger.exception("Could not stop the headless Micro-Manager backend.")
            raise
        logger.info("Headless Micro-Manager stopped.")
