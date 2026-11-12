import io
import logging
import subprocess

import pytest

from cp_server import docker_manager


class FakeProcess:
    def __init__(self, lines: str, returncode: int = 0) -> None:
        """
        Provide captured output and a deterministic process exit status.
        """
        self.stdout = io.StringIO(lines)
        self.returncode = returncode

    def __enter__(self) -> "FakeProcess":
        """
        Return the fake process for use in a context manager.
        """
        return self

    def __exit__(self, *args: object) -> None:
        """
        Close the simulated process output.
        """
        self.stdout.close()

    def poll(self) -> int:
        """
        Return the process exit status.
        """
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        """
        Return the completed process exit status.
        """
        return self.returncode


def test_compose_build_output_is_logged_live(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """
    Relay routine Docker output at DEBUG.
    """
    captured: list[tuple[list[str], dict[str, object]]] = []

    def popen(command: list[str], **kwargs: object) -> FakeProcess:
        """
        Capture the Docker command and supply its output.
        """
        captured.append((command, kwargs))
        return FakeProcess("Building image\nStarting celery\n")

    monkeypatch.setattr(docker_manager, "_get_base_cmd", lambda: ["docker", "compose"])
    monkeypatch.setattr(docker_manager.subprocess, "Popen", popen)
    with caplog.at_level(logging.DEBUG, logger="cp_server.compose_manager"):
        docker_manager._run_compose_command(["up", "-d"], check=True)

    assert captured[0][0] == ["docker", "compose", "up", "-d"]
    env = captured[0][1]["env"]
    assert isinstance(env, dict)
    assert env["COMPOSE_PROGRESS"] == "plain"
    assert "[Docker] Building image" in caplog.text
    assert "[Docker] Starting celery" in caplog.text
    assert all(record.levelno == logging.DEBUG for record in caplog.records)


def test_compose_failure_reports_exit_code(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """
    Keep Docker failures visible and propagate the failed command.
    """
    monkeypatch.setattr(docker_manager, "_get_base_cmd", lambda: ["docker", "compose"])
    monkeypatch.setattr(
        docker_manager.subprocess,
        "Popen",
        lambda *_args, **_kwargs: FakeProcess("build failed\n", returncode=2),
    )
    with pytest.raises(subprocess.CalledProcessError):
        docker_manager._run_compose_command(["up", "-d"], check=True)
    assert "exited with code 2" in caplog.text
    assert caplog.records[-1].levelno == logging.ERROR


def test_server_log_follower_relays_to_python_logging(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """
    Follow routine server logs at DEBUG.
    """
    monkeypatch.setattr(docker_manager, "_get_base_cmd", lambda: ["docker", "compose"])
    monkeypatch.setattr(
        docker_manager.subprocess,
        "Popen",
        lambda *_args, **_kwargs: FakeProcess("fastapi | Server ready\n"),
    )
    with caplog.at_level(logging.DEBUG, logger="cp_server.compose_manager"):
        follower = docker_manager.ComposeLogFollower()
        follower.start()
        follower.stop()

    assert "[Server] fastapi | Server ready" in caplog.text
    assert caplog.records[-1].levelno == logging.DEBUG


def test_server_errors_keep_traceback_severity_per_service(monkeypatch: pytest.MonkeyPatch,
                                                         caplog: pytest.LogCaptureFixture,
                                                         ) -> None:
    """
    Preserve interleaved error tracebacks while hiding routine server output.
    """
    lines = ("fastapi | 2026-11-12 [ERROR] app: Request failed\n"
             "celery | 2026-11-12 [INFO] worker: Task received\n"
             "fastapi | Traceback (most recent call last):\n"
             "fastapi |   File app.py, line 10\n"
             "fastapi | ValueError: invalid input\n"
             "fastapi | INFO: Request completed\n"
             "celery | [CRITICAL/MainProcess] Worker crashed\n")
    monkeypatch.setattr(docker_manager, "_get_base_cmd", lambda: ["docker", "compose"])
    monkeypatch.setattr(docker_manager.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess(lines))

    with caplog.at_level(logging.INFO, logger="cp_server.compose_manager"):
        follower = docker_manager.ComposeLogFollower()
        follower.start()
        follower.stop()

    assert [record.levelno for record in caplog.records] == [logging.ERROR] * 4 + [logging.CRITICAL]
    assert "ValueError: invalid input" in caplog.text
    assert "  File app.py" in caplog.text
    assert "Task received" not in caplog.text
    assert "Request completed" not in caplog.text


def test_compose_manager_propagates_pipeline_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Preserve pipeline exceptions through Docker cleanup.
    """
    monkeypatch.setattr(docker_manager, "compose_up", lambda _stream_log: None)
    monkeypatch.setattr(docker_manager, "compose_down", lambda: None)
    with pytest.raises(ValueError, match="pipeline failed"):
        with docker_manager.ComposeManager():
            raise ValueError("pipeline failed")
