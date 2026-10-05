import logging

from PyQt6.QtWidgets import QApplication

from gem_screening.runtime.logging import configure_logging
from gem_screening.runtime import (
    CancellationToken,
    PipelineCancelled,
    PipelineInteraction,
    PipelineWorker,
)
from gem_screening.runtime.logging import QtLogHandler
from gem_screening.settings.models import PipelineSettings


APP = QApplication.instance() or QApplication([])


def test_qt_log_handler_survives_pipeline_logging_configuration(tmp_path):
    root_logger = logging.getLogger()
    handler = QtLogHandler()
    messages = []
    handler.emitter.message.connect(messages.append)
    root_logger.addHandler(handler)

    configure_logging(tmp_path)
    root_logger.warning("visible in GUI console")
    APP.processEvents()

    assert handler in root_logger.handlers
    assert any("visible in GUI console" in message for message in messages)
    root_logger.removeHandler(handler)
    handler.close()


def test_pipeline_worker_emits_completion():
    results = []
    worker = PipelineWorker(
        PipelineSettings(),
        PipelineInteraction(),
        lambda settings, interaction, cancellation: "complete",
    )
    worker.completed.connect(results.append)

    worker.run()

    assert results == ["complete"]


def test_pipeline_worker_reports_failure():
    failures = []

    def fail(settings, interaction, cancellation):
        raise RuntimeError("pipeline failed")

    worker = PipelineWorker(PipelineSettings(), PipelineInteraction(), fail)
    worker.failed.connect(failures.append)

    worker.run()

    assert len(failures) == 1
    assert "RuntimeError: pipeline failed" in failures[0]


def test_cancellation_token_raises_at_checkpoint():
    token = CancellationToken()
    token.request()

    try:
        token.raise_if_requested()
    except PipelineCancelled:
        pass
    else:
        raise AssertionError("Cancellation checkpoint did not raise")
