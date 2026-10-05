from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtSignal

from gem_screening.settings.models import PipelineSettings, ServerSettings

if TYPE_CHECKING:
    from gem_screening.runtime.worker import CancellationToken


@dataclass
class InteractionRequest:
    """A request emitted by the worker and resolved by the GUI thread."""

    payload: dict[str, Any]
    result: Any = None
    error: BaseException | None = None
    _finished: Event = field(default_factory=Event, repr=False)

    def resolve(self, result: Any = None) -> None:
        self.result = result
        self._finished.set()

    def reject(self, error: BaseException) -> None:
        self.error = error
        self._finished.set()

    def wait(self, cancellation: CancellationToken | None = None) -> Any:
        while not self._finished.wait(0.1):
            if cancellation is not None:
                cancellation.raise_if_requested()
        if self.error is not None:
            raise self.error
        return self.result


class PipelineInteraction(QObject):
    """Thread-safe requests from a pipeline worker to the Qt main thread."""

    confirmation_requested = pyqtSignal(object)
    autofocus_requested = pyqtSignal(object)
    segmentation_requested = pyqtSignal(object)
    celltinder_requested = pyqtSignal(object)

    def __init__(self, cancellation: CancellationToken | None = None) -> None:
        super().__init__()
        self.cancellation = cancellation

    def confirm(self, message: str) -> bool:
        request = InteractionRequest({"message": message})
        self.confirmation_requested.emit(request)
        return bool(request.wait(self.cancellation))

    def run_autofocus_check(self, image: Any) -> str:
        request = InteractionRequest({"image": image})
        self.autofocus_requested.emit(request)
        return str(request.wait(self.cancellation))

    def tune_segmentation(
        self,
        settings: PipelineSettings,
        **context: Any,
    ) -> ServerSettings | None:
        request = InteractionRequest({"settings": settings, **context})
        self.segmentation_requested.emit(request)
        return request.wait(self.cancellation)

    def select_cells(
        self,
        csv_path: Path,
        crop_size: int,
        n_frames: int = 2,
    ) -> None:
        request = InteractionRequest(
            {
                "csv_path": csv_path,
                "crop_size": crop_size,
                "n_frames": n_frames,
            }
        )
        self.celltinder_requested.emit(request)
        request.wait(self.cancellation)
