from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QLabel

class ServerPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        # Sigma
        self.sigma = QDoubleSpinBox()
        self.sigma.setRange(0, 100)
        sigma_label = QLabel("Sigma")
        sigma_label.setToolTip("Sigma value for background subtraction. Defaults to 0.")
        layout.addRow(sigma_label, self.sigma)
        # Size
        self.size = QSpinBox()
        self.size.setRange(1, 100)
        size_label = QLabel("Size")
        size_label.setToolTip("Size parameter for background subtraction. Defaults to 7.")
        layout.addRow(size_label, self.size)
        # Denoise
        self.do_denoise = QCheckBox()
        denoise_label = QLabel("Denoise")
        denoise_label.setToolTip("If True, will use the denoising model. Defaults to True. Deprecated in cellpose>=4.0, parameter will be ignored.")
        layout.addRow(denoise_label, self.do_denoise)
        # Model Type
        self.model_type = QComboBox()
        self.model_type.addItems(["cpsam", "cyto2", "cyto3"])
        model_label = QLabel("Model Type")
        model_label.setToolTip("Type of the Cellpose model, e.g., 'cyto2', 'cyto3'. Defaults to 'cpsam'.")
        layout.addRow(model_label, self.model_type)
        # Restore Type
        self.restore_type = QComboBox()
        self.restore_type.addItems(["denoise_cyto3", "denoise_cyto2"])
        restore_label = QLabel("Restore Type")
        restore_label.setToolTip("Type of restoration for the Cellpose model, e.g., 'denoise_cyto2', 'denoise_cyto3'. Defaults to 'denoise_cyto3'. Deprecated in cellpose>=4.0, parameter will be ignored.")
        layout.addRow(restore_label, self.restore_type)
        # GPU
        self.gpu = QCheckBox()
        gpu_label = QLabel("GPU")
        gpu_label.setToolTip("If True, will use GPU for processing. Defaults to True.")
        layout.addRow(gpu_label, self.gpu)
        # Diameter
        self.diameter = QSpinBox()
        self.diameter.setRange(1, 200)
        diameter_label = QLabel("Diameter")
        diameter_label.setToolTip("Diameter for segmentation, e.g., 40 or 60. Defaults to 40. Deprecated in cellpose>=4.0, parameter will be ignored.")
        layout.addRow(diameter_label, self.diameter)
        # Flow Threshold
        self.flow_threshold = QDoubleSpinBox()
        self.flow_threshold.setRange(0, 10)
        flow_label = QLabel("Flow Threshold")
        flow_label.setToolTip("Flow threshold for segmentation. Defaults to 1.")
        layout.addRow(flow_label, self.flow_threshold)
        # Cellprob Threshold
        self.cellprob_threshold = QDoubleSpinBox()
        self.cellprob_threshold.setRange(0, 10)
        cellprob_label = QLabel("Cellprob Threshold")
        cellprob_label.setToolTip("Cell probability threshold for segmentation. Defaults to 0.")
        layout.addRow(cellprob_label, self.cellprob_threshold)
        # 3D Segmentation
        self.do_3D = QCheckBox()
        do3d_label = QLabel("3D Segmentation")
        do3d_label.setToolTip("If True, will perform 3D segmentation. Defaults to False.")
        layout.addRow(do3d_label, self.do_3D)
        # Stitch Threshold 3D
        self.stitch_threshold_3D = QDoubleSpinBox()
        self.stitch_threshold_3D.setRange(0, 1)
        stitch3d_label = QLabel("Stitch Threshold 3D")
        stitch3d_label.setToolTip("Stitch threshold used for alternative 3D segmentation using IoU. `do_3D` needs to be False. Defaults to 0.")
        layout.addRow(stitch3d_label, self.stitch_threshold_3D)
        # Track Stitch Threshold
        self.track_stitch_threshold = QDoubleSpinBox()
        self.track_stitch_threshold.setRange(0, 1)
        trackstitch_label = QLabel("Track Stitch Threshold")
        trackstitch_label.setToolTip("Threshold for stitching masks during tracking. Defaults to 0.75.")
        layout.addRow(trackstitch_label, self.track_stitch_threshold)
