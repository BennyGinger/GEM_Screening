import io
import logging
import subprocess

import pytest

from cp_server import docker_manager


class FakeProcess:
    def __init__(self, lines, returncode=0):
        self.stdout = io.StringIO(lines)
        self.returncode = returncode

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.stdout.close()

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode


def test_compose_build_output_is_logged_live(monkeypatch, caplog):
    captured = []

    def popen(command, **kwargs):
        captured.append((command, kwargs))
        return FakeProcess("Building image\nStarting celery\n")

    monkeypatch.setattr(docker_manager, "_get_base_cmd", lambda: ["docker", "compose"])
    monkeypatch.setattr(docker_manager.subprocess, "Popen", popen)
    with caplog.at_level(logging.INFO, logger="cp_server.compose_manager"):
        docker_manager._run_compose_command(["up", "-d"], check=True)

    assert captured[0][0] == ["docker", "compose", "up", "-d"]
    assert captured[0][1]["env"]["COMPOSE_PROGRESS"] == "plain"
    assert "[Docker] Building image" in caplog.text
    assert "[Docker] Starting celery" in caplog.text


def test_compose_failure_reports_exit_code(monkeypatch, caplog):
    monkeypatch.setattr(docker_manager, "_get_base_cmd", lambda: ["docker", "compose"])
    monkeypatch.setattr(
        docker_manager.subprocess,
        "Popen",
        lambda *_args, **_kwargs: FakeProcess("build failed\n", returncode=2),
    )
    with pytest.raises(subprocess.CalledProcessError):
        docker_manager._run_compose_command(["up", "-d"], check=True)
    assert "exited with code 2" in caplog.text


def test_server_log_follower_relays_to_python_logging(monkeypatch, caplog):
    monkeypatch.setattr(docker_manager, "_get_base_cmd", lambda: ["docker", "compose"])
    monkeypatch.setattr(
        docker_manager.subprocess,
        "Popen",
        lambda *_args, **_kwargs: FakeProcess("fastapi | Server ready\n"),
    )
    with caplog.at_level(logging.INFO, logger="cp_server.compose_manager"):
        follower = docker_manager.ComposeLogFollower()
        follower.start()
        follower.stop()

    assert "[Server] fastapi | Server ready" in caplog.text
