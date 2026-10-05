"""Processing server settings page."""

import json

from PyQt6.QtWidgets import QWidget, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QLabel, QGroupBox, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy, QLineEdit, QPlainTextEdit
from PyQt6.QtGui import QIntValidator

from gem_screening.settings.models import PipelineSettings

class ServerPage(QWidget):
    def __init__(self, pipeline_settings: PipelineSettings):
        super().__init__()
        self.pipeline_settings = pipeline_settings
        layout = QFormLayout(self)
        # Model Type
        self.model_type = QComboBox()
        self.model_type.addItems(["cpsam", "cyto2", "cyto3", "custom"])
        self.model_type.setCurrentText("cpsam")
        model_label = QLabel("Model Type")
        model_label.setToolTip("Type of the Cellpose model, e.g., 'cyto2', 'cyto3'. Defaults to 'cpsam'.")
        layout.addRow(model_label, self.model_type)
        # Pretrained model path (for custom model)
        self.pretrained_model_row_widget = QWidget()
        self.pretrained_model_row_layout = QHBoxLayout(self.pretrained_model_row_widget)
        self.pretrained_model_row_layout.setContentsMargins(0, 0, 0, 0)
        pretrained_label = QLabel("Pretrained Model Path")
        pretrained_label.setToolTip("Path to a custom pretrained model. Only used if model type is 'custom'.")
        self.pretrained_model_input = QLineEdit()
        self.pretrained_model_input.setPlaceholderText("/path/to/model.pth")
        self.pretrained_model_input.setMinimumWidth(505)
        self.pretrained_model_row_layout.addWidget(pretrained_label)
        self.pretrained_model_row_layout.addSpacerItem(QSpacerItem(5, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))
        self.pretrained_model_row_layout.addWidget(self.pretrained_model_input)
        self.pretrained_model_row_layout.addStretch(1)
        layout.addRow(self.pretrained_model_row_widget)
        self.pretrained_model_row_widget.hide()

        # Denoise and Restore Type (dynamic row)
        self.do_denoise = QCheckBox()
        self.do_denoise.setChecked(True)
        denoise_label = QLabel("Denoise")
        denoise_label.setToolTip("If True, will use the denoising model. Defaults to True. Deprecated in cellpose>=4.0, parameter will be ignored.")
        self.restore_type = QComboBox()
        self.restore_type.addItems(["denoise_cyto3", "denoise_cyto2"])
        self.restore_type.setCurrentText("denoise_cyto3")
        restore_label = QLabel("Restore Type")
        restore_label.setToolTip("Type of restoration for the Cellpose model, e.g., 'denoise_cyto2', 'denoise_cyto3'. Defaults to 'denoise_cyto3'. Deprecated in cellpose>=4.0, parameter will be ignored.")
        self.denoise_row_widget = QWidget()
        self.denoise_row_layout = QHBoxLayout(self.denoise_row_widget)
        self.denoise_row_layout.setContentsMargins(0, 0, 0, 0)
        self.denoise_row_layout.addWidget(self.do_denoise)
        self.denoise_row_layout.addSpacing(150)  # Increased spacing for better separation
        self.denoise_row_layout.addWidget(restore_label)
        self.denoise_row_layout.addSpacing(8)   # Small space between label and combobox
        self.denoise_row_layout.addWidget(self.restore_type)
        self.denoise_row_layout.addStretch(1)
        layout.addRow(denoise_label, self.denoise_row_widget)
        restore_label.setVisible(False)
        self.restore_type.setVisible(False)

        def update_denoise_restore_visibility():
            model = self.model_type.currentText()
            denoise_checked = self.do_denoise.isChecked()
            if model == "cpsam":
                denoise_label.setVisible(False)
                self.denoise_row_widget.setVisible(False)
                self.pretrained_model_row_widget.hide()
            elif model in ("cyto2", "cyto3"):
                denoise_label.setVisible(True)
                self.denoise_row_widget.setVisible(True)
                self.pretrained_model_row_widget.hide()
                restore_label.setVisible(denoise_checked)
                self.restore_type.setVisible(denoise_checked)
            elif model == "custom":
                denoise_label.setVisible(False)
                self.denoise_row_widget.setVisible(False)
                self.pretrained_model_row_widget.show()
        
        self.model_type.currentTextChanged.connect(update_denoise_restore_visibility)
        self.do_denoise.toggled.connect(update_denoise_restore_visibility)
        update_denoise_restore_visibility()
        
        # Diameter
        self.diameter = QSpinBox()
        self.diameter.setRange(1, 200)
        self.diameter.setValue(40)
        diameter_label = QLabel("Diameter")
        diameter_label.setToolTip("Diameter for segmentation, e.g., 40 or 60. Defaults to 40. Deprecated in cellpose>=4.0, parameter will be ignored.")
        layout.addRow(diameter_label, self.diameter)
        
        # Flow Threshold
        self.flow_threshold = QDoubleSpinBox()
        self.flow_threshold.setRange(0, 10)
        self.flow_threshold.setValue(0.4)
        flow_label = QLabel("Flow Threshold")
        flow_label.setToolTip("Flow threshold for segmentation. Increase this threshold if cellpose is not returning as many ROIs as you’d expect. Similarly, decrease this threshold if cellpose is returning too many ill-shaped ROIs. Defaults to 0.4")
        layout.addRow(flow_label, self.flow_threshold)
        
        # Cellprob Threshold
        self.cellprob_threshold = QDoubleSpinBox()
        self.cellprob_threshold.setRange(-6, 6)
        self.cellprob_threshold.setValue(0)
        cellprob_label = QLabel("Cellprob Threshold")
        cellprob_label.setToolTip("Cell probability threshold for segmentation. Comprised between -6 and 6. Decrease this threshold if cellpose is not returning as many ROIs as you'd expect. Similarly, increase this threshold if cellpose is returning too many ROIs particularly from dim areas. Defaults to 0.")
        layout.addRow(cellprob_label, self.cellprob_threshold)
        
        # Track Stitch Threshold
        self.track_stitch_threshold = QDoubleSpinBox()
        self.track_stitch_threshold.setRange(0, 1)
        self.track_stitch_threshold.setValue(0.75)
        trackstitch_label = QLabel("Track Threshold")
        trackstitch_label.setToolTip("Percentage overlap between masks that will be considered as 'same' cells during tracking (using IoU). Defaults to 0.75.")
        layout.addRow(trackstitch_label, self.track_stitch_threshold)
        
        ##########################################################
        # Advanced settings box (hidden by default)
        self.advanced_box = QGroupBox()
        self.advanced_box.setTitle("")
        self.advanced_box.setVisible(False)
        adv_layout = QFormLayout(self.advanced_box)
        
        # Sigma
        self.sigma = QDoubleSpinBox()
        self.sigma.setRange(0, 100)
        self.sigma.setValue(0)
        sigma_label = QLabel("Sigma")
        sigma_label.setToolTip("Sigma value for background subtraction. Defaults to 0.")
        adv_layout.addRow(sigma_label, self.sigma)
        
        # Size
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setRange(1, 100)
        self.size_spinbox.setValue(7)
        size_label = QLabel("Size")
        size_label.setToolTip("Size parameter for background subtraction. Defaults to 7.")
        adv_layout.addRow(size_label, self.size_spinbox)
        
        # GPU option
        self.gpu = QCheckBox()
        self.gpu.setChecked(True)
        gpu_label = QLabel("Use GPU")
        gpu_label.setToolTip("If checked, will use GPU for processing. Defaults to True.")
        adv_layout.addRow(gpu_label, self.gpu)
        
        # 3D Segmentation (move to advanced)
        self.do_3D = QCheckBox()
        self.do_3D.setChecked(False)
        do3d_label = QLabel("3D Segmentation")
        do3d_label.setToolTip("If True, will perform 3D segmentation. Defaults to False.")
        adv_layout.addRow(do3d_label, self.do_3D)
        
        # Stitch Threshold 3D (move to advanced)
        self.stitch_threshold_3D = QDoubleSpinBox()
        self.stitch_threshold_3D.setRange(0, 1)
        self.stitch_threshold_3D.setValue(0)
        stitch3d_label = QLabel("Stitch Threshold 3D")
        stitch3d_label.setToolTip("Stitch threshold used for alternative 3D segmentation using IoU. `do_3D` needs and will be turn to False. Defaults to 0.")
        adv_layout.addRow(stitch3d_label, self.stitch_threshold_3D)

        self.server_timeout = QDoubleSpinBox()
        self.server_timeout.setRange(1.0, 86_400.0)
        self.server_timeout.setDecimals(1)
        timeout_label = QLabel("Server timeout (sec)")
        timeout_label.setToolTip("Maximum time to wait for server processing to finish.")
        adv_layout.addRow(timeout_label, self.server_timeout)

        self.channels_input = QLineEdit()
        self.channels_input.setPlaceholderText("None, or comma-separated indexes such as 0, 1")
        channels_label = QLabel("Channels")
        channels_label.setToolTip(
            "Optional Cellpose channel indexes. Leave empty for None; deprecated in Cellpose 4."
        )
        adv_layout.addRow(channels_label, self.channels_input)

        self.z_axis_input = QLineEdit()
        self.z_axis_input.setValidator(QIntValidator(0, 99, self))
        self.z_axis_input.setPlaceholderText("None")
        z_axis_label = QLabel("Z axis")
        z_axis_label.setToolTip("Optional array axis used as Z for 3D segmentation.")
        adv_layout.addRow(z_axis_label, self.z_axis_input)

        self.extra_settings_input = QPlainTextEdit()
        self.extra_settings_input.setPlaceholderText('{"backend_option": "value"}')
        self.extra_settings_input.setMaximumHeight(90)
        extra_label = QLabel("Extra server settings")
        extra_label.setToolTip("Optional backend-specific settings as a JSON object.")
        adv_layout.addRow(extra_label, self.extra_settings_input)
        self.extra_settings_error = QLabel()
        self.extra_settings_error.setStyleSheet("color: #b00020;")
        adv_layout.addRow("", self.extra_settings_error)

        self.advanced_btn = QPushButton("Show Advanced Settings")
        self.advanced_btn.setCheckable(True)
        def toggle_advanced():
            show = self.advanced_btn.isChecked()
            self.advanced_box.setVisible(show)
            self.advanced_btn.setText("Hide Advanced Settings" if show else "Show Advanced Settings")
        self.advanced_btn.clicked.connect(toggle_advanced)
        layout.addRow(self.advanced_btn)
        layout.addRow(self.advanced_box)
        
        # Connect signals to update pipeline_settings
        self.model_type.currentTextChanged.connect(self.update_model_type)
        self.pretrained_model_input.textChanged.connect(self.update_pretrained_model)
        self.do_denoise.toggled.connect(self.update_do_denoise)
        self.restore_type.currentTextChanged.connect(self.update_restore_type)
        self.diameter.valueChanged.connect(self.update_diameter)
        self.flow_threshold.valueChanged.connect(self.update_flow_threshold)
        self.cellprob_threshold.valueChanged.connect(self.update_cellprob_threshold)
        self.do_3D.toggled.connect(self.update_do_3D)
        self.stitch_threshold_3D.valueChanged.connect(self.update_stitch_threshold_3D)
        self.track_stitch_threshold.valueChanged.connect(self.update_track_stitch_threshold)
        self.sigma.valueChanged.connect(self.update_sigma)
        self.size_spinbox.valueChanged.connect(self.update_size)
        self.gpu.toggled.connect(self.update_gpu)
        self.server_timeout.valueChanged.connect(self.update_server_timeout)
        self.channels_input.textChanged.connect(self.update_channels)
        self.z_axis_input.textChanged.connect(self.update_z_axis)
        self.extra_settings_input.textChanged.connect(self.update_extra_settings)

        # Initialize from pipeline_settings if available
        if self.pipeline_settings is not None:
            self.load_settings()

    def load_settings(self) -> None:
        """Refresh controls after the segmentation tuner changes server settings."""
        ss = self.pipeline_settings.server_settings
        self.model_type.setCurrentText(ss.model_type)
        self.pretrained_model_input.setText(getattr(ss, 'pretrained_model', ''))
        self.do_denoise.setChecked(ss.do_denoise)
        self.restore_type.setCurrentText(ss.restore_type)
        self.diameter.setValue(ss.diameter)
        self.flow_threshold.setValue(ss.flow_threshold)
        self.cellprob_threshold.setValue(ss.cellprob_threshold)
        self.do_3D.setChecked(ss.do_3D)
        self.stitch_threshold_3D.setValue(ss.stitch_threshold_3D)
        self.track_stitch_threshold.setValue(ss.track_stitch_threshold)
        self.sigma.setValue(ss.sigma)
        self.size_spinbox.setValue(ss.size)
        self.gpu.setChecked(ss.gpu)
        self.server_timeout.setValue(ss.server_timeout_sec)
        self.channels_input.setText(
            ", ".join(str(channel) for channel in ss.channels) if ss.channels else ""
        )
        self.z_axis_input.setText(str(ss.z_axis) if ss.z_axis is not None else "")
        self.extra_settings_input.setPlainText(
            json.dumps(ss.extra_settings, indent=2) if ss.extra_settings else ""
        )

    def update_model_type(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.model_type = value

    def update_pretrained_model(self, value):
        if self.pipeline_settings is not None:
            setattr(self.pipeline_settings.server_settings, 'pretrained_model', value)

    def update_do_denoise(self, checked):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.do_denoise = checked

    def update_restore_type(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.restore_type = value

    def update_diameter(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.diameter = value

    def update_flow_threshold(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.flow_threshold = value

    def update_cellprob_threshold(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.cellprob_threshold = value

    def update_do_3D(self, checked):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.do_3D = checked

    def update_stitch_threshold_3D(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.stitch_threshold_3D = value

    def update_track_stitch_threshold(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.track_stitch_threshold = value

    def update_sigma(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.sigma = value

    def update_size(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.size = value

    def update_gpu(self, checked):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.gpu = checked

    def update_server_timeout(self, value: float) -> None:
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.server_timeout_sec = value

    def update_channels(self, value: str) -> None:
        if self.pipeline_settings is None:
            return
        text = value.strip()
        if not text:
            self.pipeline_settings.server_settings.channels = None
            return
        try:
            channels = [int(item.strip()) for item in text.split(",")]
        except ValueError:
            return
        self.pipeline_settings.server_settings.channels = channels

    def update_z_axis(self, value: str) -> None:
        if self.pipeline_settings is not None:
            text = value.strip()
            self.pipeline_settings.server_settings.z_axis = int(text) if text else None

    def update_extra_settings(self) -> None:
        if self.pipeline_settings is None:
            return
        text = self.extra_settings_input.toPlainText().strip()
        if not text:
            self.pipeline_settings.server_settings.extra_settings = {}
            self.extra_settings_error.clear()
            return
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            self.extra_settings_error.setText("Enter a valid JSON object.")
            return
        if not isinstance(value, dict):
            self.extra_settings_error.setText("Extra settings must be a JSON object.")
            return
        self.pipeline_settings.server_settings.extra_settings = value
        self.extra_settings_error.clear()
