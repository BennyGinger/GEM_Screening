"""Unified GEM Screening application window."""

import logging
import os
import sys
from collections.abc import Callable
from functools import partial
from pathlib import Path

from PyQt6.QtCore import QThread, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from celltinder.cell_tinder import CellTinderWidget

from gem_screening.infrastructure.filesystem import timestamped_dir_path
from gem_screening.gui.settings.editor import MainWindow as SettingsWindow
from gem_screening.gui.settings.pages.acquisition_page import AcquisitionPage
from gem_screening.gui.settings.pages.injection_page import InjectionPage
from gem_screening.gui.settings.pages.logging_page import LoggingPage
from gem_screening.gui.settings.pages.server_page import ServerPage
from gem_screening.gui.settings.pages.stim_page import StimPage
from gem_screening.settings.models import PipelineSettings
from gem_screening.settings.storage import load_gui_settings
from gem_screening.runtime import (
    CancellationToken,
    PipelineCancelled,
    PipelineInteraction,
    PipelineRunner,
    PipelineWorker,
)
from gem_screening.runtime.interaction import InteractionRequest
from gem_screening.runtime.logging import QtLogHandler
from gem_screening.runtime.prompt_gui import PipelineQuit, PromptWindow


logger = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

CELLTINDER_TEST_CSV = Path(
    "/media/ben/Analysis/Python/Repos/GEM_suite/CellTinder/ImagesTest/"
    "20260417_lib66-5KETE-red-Selection/cell_data.csv"
)


def _run_complete_pipeline(
    settings: PipelineSettings,
    interaction: PipelineInteraction,
    cancellation: CancellationToken,
    *,
    run_dir: Path,
) -> None:
    """Worker-compatible adapter for a new pipeline run."""
    cancellation.raise_if_requested()
    from gem_screening.workflows.complete import complete_pipeline

    complete_pipeline(settings, run_dir=run_dir, interaction=interaction)
    cancellation.raise_if_requested()


def _run_rescue_pipeline(
    settings: PipelineSettings,
    interaction: PipelineInteraction,
    cancellation: CancellationToken,
    *,
    run_dir: Path,
) -> None:
    """Worker-compatible adapter for an existing pipeline run."""
    cancellation.raise_if_requested()
    from gem_screening.workflows.rescue import rescue_pipeline

    rescue_pipeline(run_dir, settings=settings, interaction=interaction)
    cancellation.raise_if_requested()


class MainGui(QMainWindow):
    """Unified GEM Screening shell and pipeline controls."""

    def __init__(
        self,
        pipeline_settings: PipelineSettings | None = None,
        runner_factory: Callable[[Path, bool], PipelineRunner] | None = None,
    ):
        super().__init__()
        self.setWindowTitle("GEM Screening")
        self.resize(1400, 900)

        self.pipeline_settings: PipelineSettings | None = None
        self.settings_path: Path | None = None
        self.settings_window: SettingsWindow | None = None
        self.task_widget: QWidget | None = None
        self.run_started = False
        self.is_existing_experiment = False
        self.runner_factory = runner_factory or self._default_runner
        self.pipeline_thread: QThread | None = None
        self.pipeline_worker: PipelineWorker | None = None
        self.pipeline_interaction: PipelineInteraction | None = None
        self.cancellation: CancellationToken | None = None
        self._pipeline_outcome: str | None = None
        self._active_request: InteractionRequest | None = None
        self._prompt_request: InteractionRequest | None = None
        self._prompt_window: PromptWindow | None = None

        root = QWidget()
        root_layout = QVBoxLayout(root)
        self.setCentralWidget(root)

        self.header_stack = QStackedWidget()
        self.header_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        self.header_stack.setMaximumHeight(150)
        self.header_stack.addWidget(self._build_experiment_selector())
        self.header_stack.addWidget(self._build_experiment_identity())
        root_layout.addWidget(self.header_stack)

        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.setDocumentMode(True)
        self.workspace_tabs.setVisible(False)
        root_layout.addWidget(self.workspace_tabs, 1)

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.terminal_widget = QPlainTextEdit()
        self.terminal_widget.setReadOnly(True)
        self.terminal_widget.setMaximumBlockCount(20000)
        self.terminal_widget.setPlaceholderText("Pipeline console")
        self.terminal_widget.setStyleSheet(
            "background-color: #23272e; color: #f8f8f2;"
        )
        bottom_splitter.addWidget(self.terminal_widget)
        bottom_splitter.addWidget(self._build_action_panel())
        bottom_splitter.setStretchFactor(0, 1)
        bottom_splitter.setSizes([1100, 220])
        bottom_splitter.setMinimumHeight(260)
        root_layout.addWidget(bottom_splitter)

        self.terminal_handler = QtLogHandler(self)
        self.terminal_handler.setLevel(LOG_LEVEL)
        self.terminal_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        self.terminal_handler.emitter.message.connect(self.append_terminal)
        logging.getLogger().addHandler(self.terminal_handler)

        if pipeline_settings is not None:
            self._load_experiment(pipeline_settings, None)

    def _build_experiment_selector(self) -> QWidget:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("Start a new experiment or open an existing experiment."))

        new_button = QPushButton("New Experiment")
        new_button.clicked.connect(self._new_experiment)
        layout.addWidget(new_button)

        existing_row = QHBoxLayout()
        existing_row.addWidget(QLabel("Existing experiment"))
        self.experiment_path_edit = QLineEdit()
        self.experiment_path_edit.setPlaceholderText("Path to an experiment folder")
        existing_row.addWidget(self.experiment_path_edit, 1)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_experiment)
        existing_row.addWidget(browse_button)
        open_button = QPushButton("Open Experiment")
        open_button.clicked.connect(self._open_experiment)
        existing_row.addWidget(open_button)
        layout.addLayout(existing_row)

        self.experiment_error = QLabel()
        self.experiment_error.setStyleSheet("color: #b00020;")
        self.experiment_error.setWordWrap(True)
        layout.addWidget(self.experiment_error)
        return panel

    def _build_experiment_identity(self) -> QWidget:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        self.user_folder_label = QLabel()
        self.experiment_name_label = QLabel()
        layout.addWidget(self.user_folder_label)
        layout.addWidget(self.experiment_name_label)
        change_button = QPushButton("Change Experiment")
        change_button.clicked.connect(self._show_experiment_selector)
        layout.addWidget(change_button)
        return panel

    def _build_action_panel(self) -> QWidget:
        panel = QFrame()
        panel.setMinimumWidth(200)
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("Controls"))

        self.start_button = QPushButton("Run")
        self.start_button.setEnabled(False)
        self.start_button.setToolTip("Save the edited settings and run the full pipeline.")
        self.start_button.setStyleSheet(
            "QPushButton { background: #24883a; color: white; font-weight: bold; "
            "padding: 10px 18px; }"
            "QPushButton:hover { background: #1c7130; }"
            "QPushButton:disabled { background: #9aaf9d; color: #e9e9e9; }"
        )
        self.start_button.clicked.connect(self.prepare_pipeline_start)
        layout.addWidget(self.start_button)

        self.rescue_button = QPushButton("Rescue run")
        self.rescue_button.setEnabled(False)
        self.rescue_button.setToolTip(
            "Resume an existing run using its saved settings; GUI edits are ignored."
        )
        self.rescue_button.setStyleSheet(
            "QPushButton { background: #70a878; color: #172b1c; padding: 7px 14px; }"
            "QPushButton:hover { background: #5b9465; }"
            "QPushButton:disabled { background: #c8d6ca; color: #6a776c; }"
        )
        self.rescue_button.clicked.connect(self.prepare_rescue_start)
        layout.addWidget(self.rescue_button)

        self.cancel_button = QPushButton("Cancel Pipeline")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setToolTip(
            "Request cancellation at the next safe pipeline checkpoint."
        )
        self.cancel_button.clicked.connect(self.request_pipeline_cancel)
        layout.addWidget(self.cancel_button)

        self.celltinder_button = QPushButton("Open CellTinder Test")
        self.celltinder_button.setEnabled(False)
        self.celltinder_button.clicked.connect(self.open_celltinder_test)
        layout.addWidget(self.celltinder_button)

        self.close_task_button = QPushButton("Close Current Task")
        self.close_task_button.setVisible(False)
        self.close_task_button.clicked.connect(self.close_current_task)
        layout.addWidget(self.close_task_button)

        layout.addStretch(1)
        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.close)
        layout.addWidget(quit_button)
        return panel

    def _new_experiment(self) -> None:
        try:
            settings, settings_path = load_gui_settings()
        except (OSError, TypeError, ValueError) as error:
            self.experiment_error.setText(str(error))
            return
        self._load_experiment(settings, settings_path)

    def _browse_experiment(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select experiment folder",
            self.experiment_path_edit.text(),
        )
        if selected:
            self.experiment_path_edit.setText(selected)
            self.experiment_error.clear()

    def _open_experiment(self) -> None:
        selected = self.experiment_path_edit.text().strip()
        if not selected:
            self.experiment_error.setText("Select an experiment folder first.")
            return
        try:
            settings, settings_path = load_gui_settings(selected)
        except (OSError, TypeError, ValueError) as error:
            self.experiment_error.setText(str(error))
            return
        self._load_experiment(settings, settings_path)

    def _load_experiment(
        self,
        settings: PipelineSettings,
        settings_path: Path | None,
    ) -> None:
        self.pipeline_settings = settings
        self.settings_path = settings_path
        self.is_existing_experiment = settings_path is not None
        self.close_current_task()
        self.workspace_tabs.clear()

        pages = [
            ("Logging", LoggingPage(settings)),
            ("Microscope", AcquisitionPage(settings)),
            ("Injection", InjectionPage(settings)),
            ("Server", ServerPage(settings)),
            ("Light-Stimulation", StimPage(settings)),
        ]
        self.settings_window = SettingsWindow(
            pages,
            settings,
            settings_path,
            show_proceed_button=False,
        )
        self.workspace_tabs.addTab(self.settings_window, "Settings")
        self.workspace_tabs.setVisible(True)
        self.header_stack.setCurrentIndex(1)
        self._update_run_buttons()
        self.celltinder_button.setEnabled(True)
        self.run_started = False
        self._pipeline_outcome = None
        self.experiment_error.clear()

        project_panel = self.settings_window.project_settings_panel
        if project_panel is not None:
            project_panel.savedir_edit.textChanged.connect(self._update_identity)
            project_panel.experiment_name_edit.textChanged.connect(self._update_identity)
        self._update_identity()
        self.append_terminal("[GUI] Experiment settings loaded.")

    def prepare_pipeline_start(self) -> None:
        """Confirm any replacement, save edits, then run the full pipeline."""
        if self.settings_window is None or self.pipeline_settings is None or self.run_started:
            return
        if self.is_existing_experiment:
            if self.settings_path is None:
                return
            run_dir = self.settings_path.parent.parent
            try:
                original, _ = load_gui_settings(self.settings_path)
            except (OSError, TypeError, ValueError) as error:
                QMessageBox.warning(self, "Cannot rerun", str(error))
                return
            if (
                self.pipeline_settings.savedir != original.savedir
                or self.pipeline_settings.savedir_name != original.savedir_name
            ):
                QMessageBox.warning(
                    self,
                    "Experiment folder changed",
                    "Rerun uses the opened experiment folder. Restore its original "
                    "User folder and Experiment name, or start a new experiment.",
                )
                return
            warning = (
                f"Rerun the experiment in:\n{run_dir}\n\n"
                "Existing images, masks, and analysis results in this folder "
                "will be removed or replaced. Continue?"
            )
        else:
            if not self.pipeline_settings.savedir.strip() or not self.pipeline_settings.savedir_name.strip():
                QMessageBox.warning(
                    self, "Cannot run", "User folder and Experiment name are required."
                )
                return
            run_dir = timestamped_dir_path(
                self.pipeline_settings.savedir, self.pipeline_settings.savedir_name
            )
            warning = (
                f"The experiment folder already contains files:\n{run_dir}\n\n"
                "A full run may remove or replace existing images, masks, "
                "and analysis results. Continue?"
            )

        if (self.is_existing_experiment or
            (run_dir.is_dir() and any(run_dir.iterdir()))):
            answer = QMessageBox.warning(
                self,
                "Replace experiment data",
                warning,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        settings_path = self.settings_window.save_settings()
        if settings_path is None:
            self.append_terminal("[Settings] Settings were not saved; pipeline not started.")
            return

        self.settings_path = settings_path
        self.is_existing_experiment = True
        run_dir = settings_path.parent.parent
        self.append_terminal(f"[Settings] Saved and validated: {settings_path}")
        self._start_pipeline_worker(run_dir, self.pipeline_settings, rescue=False)

    def prepare_rescue_start(self) -> None:
        """Resume using only the settings saved with the opened experiment."""
        if self.run_started or not self.is_existing_experiment or self.settings_path is None:
            return
        run_dir = self.settings_path.parent.parent
        if not self._has_saved_plate(run_dir):
            QMessageBox.warning(
                self, "Cannot rescue", f"No saved plate was found in {run_dir / 'config'}."
            )
            return
        try:
            saved_settings, _ = load_gui_settings(self.settings_path)
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.warning(self, "Cannot rescue", str(error))
            return
        # The settings tab must show the values the worker will actually use.
        settings_path = self.settings_path
        self._load_experiment(saved_settings, settings_path)
        self.append_terminal(
            f"[Pipeline] Rescuing {run_dir} with its saved settings; "
            "unsaved GUI edits discarded."
        )
        self._start_pipeline_worker(run_dir, saved_settings, rescue=True)

    @staticmethod
    def _default_runner(run_dir: Path, rescue: bool) -> PipelineRunner:
        if rescue:
            return partial(_run_rescue_pipeline, run_dir=run_dir)
        return partial(_run_complete_pipeline, run_dir=run_dir)

    @staticmethod
    def _has_saved_plate(run_dir: Path) -> bool:
        return any((run_dir / "config").glob("*_obj.json"))

    def _update_run_buttons(self) -> None:
        self.start_button.setText("Rerun" if self.is_existing_experiment else "Run")
        self.start_button.setEnabled(
            self.pipeline_settings is not None
            and not self.run_started
            and self.task_widget is None
        )
        has_plate = (
            self.settings_path is not None
            and self._has_saved_plate(self.settings_path.parent.parent)
        )
        self.rescue_button.setEnabled(
            self.is_existing_experiment
            and not self.run_started
            and self.task_widget is None
            and has_plate
        )
        self.rescue_button.setToolTip(
            "Resume with the settings saved in this experiment; GUI edits are discarded."
            if has_plate
            else "Rescue becomes available once this experiment has a saved plate."
        )

    def _start_pipeline_worker(
        self,
        run_dir: Path,
        settings: PipelineSettings,
        *,
        rescue: bool,
    ) -> None:
        """Start the selected workflow without blocking the Qt main thread."""
        if self.pipeline_thread is not None:
            raise RuntimeError("A pipeline worker is already active.")

        settings_snapshot = settings.model_copy(deep=True)
        self.cancellation = CancellationToken()
        self.pipeline_interaction = PipelineInteraction(self.cancellation)
        self.pipeline_interaction.confirmation_requested.connect(
            self._handle_confirmation_request
        )
        self.pipeline_interaction.autofocus_requested.connect(
            self._handle_autofocus_request
        )
        self.pipeline_interaction.segmentation_requested.connect(
            self._handle_segmentation_request
        )
        self.pipeline_interaction.celltinder_requested.connect(
            self._handle_celltinder_request
        )
        runner = self.runner_factory(run_dir, rescue)

        thread = QThread(self)
        worker = PipelineWorker(
            settings_snapshot,
            self.pipeline_interaction,
            runner,
            self.cancellation,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._pipeline_completed)
        worker.failed.connect(self._pipeline_failed)
        worker.cancelled.connect(self._pipeline_cancelled)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._pipeline_thread_finished)
        thread.finished.connect(thread.deleteLater)

        self.pipeline_thread = thread
        self.pipeline_worker = worker
        self.terminal_handler.setLevel(settings_snapshot.logging_settings.log_level.upper())
        self.settings_window.save_status.clear()
        self.settings_window.set_read_only(True)
        self.run_started = True
        self._update_run_buttons()
        self.cancel_button.setEnabled(True)
        self.celltinder_button.setEnabled(False)
        self.append_terminal(
            f"[Pipeline] Starting {'rescue' if rescue else 'full'} workflow for: {run_dir}"
        )
        thread.start()

    def _pipeline_completed(self, _result: object) -> None:
        self._pipeline_outcome = "completed"
        self.append_terminal("[Pipeline] Completed successfully.")

    def _pipeline_failed(self, traceback_text: str) -> None:
        self._pipeline_outcome = "failed"
        self.append_terminal("[Pipeline] Failed with an unexpected error:")
        self.append_terminal(traceback_text.rstrip())

    def _pipeline_cancelled(self) -> None:
        self._pipeline_outcome = "cancelled"
        self.append_terminal("[Pipeline] Cancelled.")

    def _pipeline_thread_finished(self) -> None:
        """Restore editable state only after worker execution has stopped."""
        self.close_current_task()
        if self._prompt_window is not None:
            self._prompt_window.close()
        if self._pipeline_outcome is None:
            self._pipeline_outcome = "finished"
            self.append_terminal("[Pipeline] Worker stopped.")
        if self.settings_window is not None:
            self.settings_window.set_read_only(False)
        self.run_started = False
        self._update_run_buttons()
        self.cancel_button.setEnabled(False)
        self.celltinder_button.setEnabled(self.pipeline_settings is not None)
        self.pipeline_thread = None
        self.pipeline_worker = None
        self.pipeline_interaction = None
        self.cancellation = None

    def request_pipeline_cancel(self) -> None:
        if self.cancellation is None:
            return
        self.cancellation.request()
        if self._active_request is not None:
            self.close_current_task()
        if self._prompt_request is not None:
            self._prompt_request.reject(PipelineQuit("Pipeline cancelled"))
            self._prompt_request = None
            if self._prompt_window is not None:
                self._prompt_window.close()
        self.cancel_button.setEnabled(False)
        self.append_terminal(
            "[Pipeline] Cancellation requested; waiting for a safe checkpoint."
        )

    def _handle_confirmation_request(self, request: InteractionRequest) -> None:
        """Display a standalone prompt owned by the GUI thread."""
        try:
            if self.cancellation is not None:
                self.cancellation.raise_if_requested()
            if self._prompt_window is not None:
                raise RuntimeError("A pipeline prompt is already open.")
            window = PromptWindow(request.payload["message"])
            self._prompt_request = request
            self._prompt_window = window
            window.result_selected.connect(self._finish_confirmation)
            window.show()
            self.append_terminal(f"[Pipeline] Waiting for confirmation: {request.payload['message']}")
        except Exception as error:
            self._prompt_request = None
            self._prompt_window = None
            request.reject(error)

    def _finish_confirmation(self, result: str) -> None:
        request = self._prompt_request
        window = self._prompt_window
        self._prompt_request = None
        self._prompt_window = None
        if request is not None:
            request.resolve(result == "continue")
        if window is not None:
            window.deleteLater()

    def _show_pipeline_task(
        self, widget: QWidget, title: str, request: InteractionRequest
    ) -> None:
        if self.task_widget is not None:
            raise RuntimeError("Another pipeline task is already open.")
        self._active_request = request
        self.task_widget = widget
        index = self.workspace_tabs.addTab(widget, title)
        self.workspace_tabs.setCurrentIndex(index)
        self.close_task_button.setVisible(True)
        self.close_task_button.setText("Cancel current task")
        self._update_run_buttons()

    def _handle_autofocus_request(self, request: InteractionRequest) -> None:
        try:
            if self.cancellation is not None:
                self.cancellation.raise_if_requested()
            from a1_manager.autofocus.autofocus_gui import AutofocusWidget

            widget = AutofocusWidget(request.payload["image"])
            if self.cancellation is not None and self.cancellation.is_requested():
                widget.deleteLater()
                raise PipelineCancelled()
            widget.result_signal.connect(
                lambda result: self._autofocus_finished(widget, result)
            )
            self._show_pipeline_task(widget, "Autofocus review", request)
            self.append_terminal("[Pipeline] Waiting for autofocus review.")
        except Exception as error:
            request.reject(error)
            self.append_terminal(f"[Autofocus] Failed to open: {error}")

    def _autofocus_finished(self, widget: QWidget, result: str) -> None:
        if widget is not self.task_widget or self._active_request is None:
            return
        request = self._active_request
        self._active_request = None
        request.resolve(result)
        self.append_terminal(f"[Autofocus] User selected: {result}.")
        self.close_current_task()

    def _handle_segmentation_request(self, request: InteractionRequest) -> None:
        try:
            if self.cancellation is not None:
                self.cancellation.raise_if_requested()
            from gem_screening.gui.segmentation_tuning import TuneSegWidget

            widget = TuneSegWidget(**request.payload)
            if self.cancellation is not None and self.cancellation.is_requested():
                widget.deleteLater()
                raise PipelineCancelled()
            widget.quit_btn.setText("Use settings and continue")
            widget.result_signal.connect(
                lambda result: self._segmentation_finished(widget, result)
            )
            self._show_pipeline_task(widget, "Segmentation tuning", request)
            self.append_terminal("[Pipeline] Waiting for segmentation tuning.")
        except Exception as error:
            request.reject(error)
            self.append_terminal(f"[Segmentation] Failed to open: {error}")

    def _segmentation_finished(self, widget: QWidget, result: str) -> None:
        if widget is not self.task_widget or self._active_request is None:
            return
        request = self._active_request
        self._active_request = None
        try:
            if result != "quit":
                raise PipelineQuit("Segmentation tuning was closed.")
            tuned_settings = widget.get_settings()
            if self.pipeline_settings is not None and self.settings_window is not None:
                self.pipeline_settings.server_settings = tuned_settings.model_copy(deep=True)
                for title, page in self.settings_window.all_pages:
                    if title == "Server":
                        page.load_settings()
                        break
            request.resolve(tuned_settings)
        except Exception as error:
            request.reject(error)
        self.close_current_task()

    def _handle_celltinder_request(self, request: InteractionRequest) -> None:
        try:
            if self.cancellation is not None:
                self.cancellation.raise_if_requested()
            widget = CellTinderWidget(**request.payload)
            if self.cancellation is not None and self.cancellation.is_requested():
                widget.deleteLater()
                raise PipelineCancelled()
            widget.finished.connect(self._celltinder_finished)
            self._show_pipeline_task(widget, "CellTinder", request)
            self.append_terminal(f"[CellTinder] Opened: {request.payload['csv_path']}")
        except Exception as error:
            request.reject(error)
            self.append_terminal(f"[CellTinder] Failed to open: {error}")

    def _update_identity(self, *_args) -> None:
        if self.pipeline_settings is None:
            return
        folder = self.pipeline_settings.savedir.strip() or "Not selected"
        name = self.pipeline_settings.savedir_name.strip() or "Not named"
        self.user_folder_label.setText(f"User folder: {folder}")
        self.experiment_name_label.setText(f"Experiment: {name}")

    def _show_experiment_selector(self) -> None:
        if self.run_started:
            QMessageBox.information(
                self,
                "Pipeline configured",
                "The experiment cannot be changed after the run has started.",
            )
            return
        if self.task_widget is not None:
            QMessageBox.information(
                self,
                "Task open",
                "Close the current task before changing experiment.",
            )
            return
        self.header_stack.setCurrentIndex(0)

    def open_celltinder_test(self) -> None:
        if self.pipeline_settings is None:
            return
        if not CELLTINDER_TEST_CSV.is_file():
            QMessageBox.warning(
                self,
                "CellTinder test data missing",
                f"The test CSV does not exist:\n{CELLTINDER_TEST_CSV}",
            )
            return

        self.close_current_task()
        try:
            celltinder = CellTinderWidget(
                CELLTINDER_TEST_CSV,
                n_frames=2,
                crop_size=self.pipeline_settings.stim_settings.crop_size,
            )
        except Exception as error:
            QMessageBox.critical(self, "Cannot open CellTinder", str(error))
            self.append_terminal(f"[CellTinder] Failed to open: {error}")
            return

        celltinder.finished.connect(self._celltinder_finished)
        self.task_widget = celltinder
        task_index = self.workspace_tabs.addTab(celltinder, "CellTinder")
        self.workspace_tabs.setCurrentIndex(task_index)
        self.close_task_button.setVisible(True)
        self._update_run_buttons()
        self.append_terminal(f"[CellTinder] Opened test data: {CELLTINDER_TEST_CSV}")

    def _celltinder_finished(self) -> None:
        if self._active_request is not None:
            request = self._active_request
            self._active_request = None
            request.resolve()
        self.append_terminal("[CellTinder] Cell selection completed.")
        self.close_current_task()

    def close_current_task(self) -> None:
        if self._active_request is not None:
            request = self._active_request
            self._active_request = None
            request.reject(PipelineQuit("Interactive task was closed before completion"))
        if self.task_widget is None:
            return
        index = self.workspace_tabs.indexOf(self.task_widget)
        if index >= 0:
            self.workspace_tabs.removeTab(index)
        self.task_widget.deleteLater()
        self.task_widget = None
        self.close_task_button.setVisible(False)
        self.close_task_button.setText("Close Current Task")
        self._update_run_buttons()
        if self.workspace_tabs.count():
            self.workspace_tabs.setCurrentIndex(0)

    def append_terminal(self, message: str) -> None:
        scrollbar = self.terminal_widget.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 2
        previous_position = scrollbar.value()
        self.terminal_widget.appendPlainText(message)
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(previous_position)

    def closeEvent(self, event) -> None:
        if self.pipeline_thread is not None and self.pipeline_thread.isRunning():
            self.request_pipeline_cancel()
            QMessageBox.information(
                self,
                "Pipeline still running",
                "Cancellation was requested. Wait for the pipeline to stop before closing.",
            )
            event.ignore()
            return
        logging.getLogger().removeHandler(self.terminal_handler)
        super().closeEvent(event)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainGui()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
