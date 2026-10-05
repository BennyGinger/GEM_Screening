from __future__ import annotations

import traceback
from collections.abc import Callable
from threading import Event
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from gem_screening.runtime.interaction import PipelineInteraction
from gem_screening.runtime.prompt_gui import PipelineQuit
from gem_screening.settings.models import PipelineSettings


class PipelineCancelled(Exception):
    """Raised at a safe checkpoint after cancellation was requested."""


class CancellationToken:
    """Thread-safe cooperative cancellation flag."""

    def __init__(self) -> None:
        self._requested = Event()

    def request(self) -> None:
        self._requested.set()

    def is_requested(self) -> bool:
        return self._requested.is_set()

    def raise_if_requested(self) -> None:
        if self.is_requested():
            raise PipelineCancelled()


PipelineRunner = Callable[
    [PipelineSettings, PipelineInteraction, CancellationToken],
    Any,
]


class PipelineWorker(QObject):
    """Execute a sequential pipeline runner outside the Qt main thread."""

    completed = pyqtSignal(object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()
    finished = pyqtSignal()

    def __init__(
        self,
        settings: PipelineSettings,
        interaction: PipelineInteraction,
        runner: PipelineRunner,
        cancellation: CancellationToken | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.interaction = interaction
        self.runner = runner
        self.cancellation = cancellation or CancellationToken()

    @pyqtSlot()
    def run(self) -> None:
        try:
            self.cancellation.raise_if_requested()
            result = self.runner(
                self.settings,
                self.interaction,
                self.cancellation,
            )
        except (PipelineCancelled, PipelineQuit):
            self.cancelled.emit()
        except Exception:
            self.failed.emit(traceback.format_exc())
        else:
            self.completed.emit(result)
        finally:
            self.finished.emit()

    def request_cancel(self) -> None:
        """May be called safely from the GUI thread while ``run`` is active."""
        self.cancellation.request()
