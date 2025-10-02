from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal


class MockPipelineRunner(QObject):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    autofocus_request = pyqtSignal(object)  # NDArray
    celltinder_request = pyqtSignal(Path, int, int)

    def __init__(self, pipeline_settings, autofocus_callback, celltinder_callback):
        super().__init__()
        self.pipeline_settings = pipeline_settings
        self.autofocus_callback = autofocus_callback
        self.celltinder_callback = celltinder_callback
        self.autofocus_result = None
        self.autofocus_waiting = False

    def run(self):
        msg = f"[MOCK] Pipeline starting with settings: {list(self.pipeline_settings.__dict__.keys())}"
        self.output_signal.emit(msg)
        try:
            from tifffile import imread
            from PyQt6.QtCore import QCoreApplication
            # Step 1: Autofocus loop until user decides
            while True:
                dummy_img = imread('/media/ben/Analysis/Python/Docker_mount/Test_images/nd2/Run3/c3z1t1v3_s1/Images/C1_s01_f0001_z0001.tif')
                self.autofocus_waiting = True
                self.autofocus_result = None
                self.autofocus_callback(dummy_img)
                while self.autofocus_waiting:
                    QCoreApplication.processEvents()
                if self.autofocus_result == "continue":
                    self.output_signal.emit("[MOCK] Autofocus accepted, continuing...")
                    break
                elif self.autofocus_result == "quit":
                    self.output_signal.emit("[MOCK] Pipeline quit by user")
                    self.finished_signal.emit()
                    return
                elif self.autofocus_result == "restart":
                    self.output_signal.emit("[MOCK] Restarting autofocus...")
                    continue
            # Step 2: Simulate pipeline processing
            self.output_signal.emit("[MOCK] Processing acquisition data...")
            self.output_signal.emit("[MOCK] Analyzing cell positions...")
            # Step 3: Call CellTinder
            csv_path = Path('/media/ben/Analysis/Python/CellTinder/ImagesTest/A1/A1_cell_data.csv')
            n_frames = 2
            crop_size = 151
            self.celltinder_callback(csv_path, n_frames, crop_size)
        except Exception as e:
            self.output_signal.emit(f"[MOCK] Could not start pipeline: {e}")
            self.finished_signal.emit()
        else:
            self.finished_signal.emit()

    def set_autofocus_result(self, result: str):
        self.autofocus_result = result
        self.autofocus_waiting = False
