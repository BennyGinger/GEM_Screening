from PyQt6.QtWidgets import QWidget, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QLabel, QGroupBox, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy, QLineEdit, QVBoxLayout, QSlider
from PyQt6.QtCore import Qt

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

        self.advanced_btn = QPushButton("Show Advanced Settings")
        self.advanced_btn.setCheckable(True)
        def toggle_advanced():
            show = self.advanced_btn.isChecked()
            self.advanced_box.setVisible(show)
            self.advanced_btn.setText("Hide Advanced Settings" if show else "Show Advanced Settings")
        self.advanced_btn.clicked.connect(toggle_advanced)
        layout.addRow(self.advanced_btn)
        layout.addRow(self.advanced_box)
        
        ##########################################################
        # Control Imaging Group
        self.control_group = QGroupBox()
        self.control_group.setTitle("")
        self.do_control = QCheckBox("Do Control Imaging Loop")
        self.do_control.setChecked(True)
        self.do_control.setToolTip("If True, will perform a control imaging loop before and after light stimulation. Defaults to True.")
        control_title_layout = QHBoxLayout()
        control_title_layout.addWidget(self.do_control)
        control_main_layout = QVBoxLayout(self.control_group)
        control_main_layout.addLayout(control_title_layout)
        control_layout = QFormLayout()
        self.control_optical_config = QComboBox()
        self.control_optical_config.addItems(["RFP", "GFP", "iRed", "BFP"])
        control_optical_label = QLabel("Optical Config")
        control_optical_label.setToolTip("Optical configuration for the preset, e.g., 'RFP'. Defaults to 'RFP'.")
        self.control_intensity_slider = QSlider()
        self.control_intensity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.control_intensity_slider.setRange(0, 100)
        self.control_intensity_value_label = QLabel("40")
        control_intensity_label = QLabel("Intensity")
        control_intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 40.")
        control_intensity_layout = QHBoxLayout()
        control_intensity_layout.addWidget(self.control_intensity_slider)
        control_intensity_layout.addWidget(self.control_intensity_value_label)
        self.control_intensity_slider.valueChanged.connect(lambda v: self.control_intensity_value_label.setText(str(v)))
        self.control_exposure = QSpinBox()
        self.control_exposure.setRange(1, 10000)
        control_exposure_label = QLabel("Exposure (ms)")
        control_exposure_label.setToolTip("Exposure time in milliseconds for the preset. Defaults to 100.")
        control_layout.addRow(control_optical_label, self.control_optical_config)
        control_layout.addRow(control_intensity_label, control_intensity_layout)
        control_layout.addRow(control_exposure_label, self.control_exposure)
        control_main_layout.addLayout(control_layout)
        layout.addRow(self.control_group)
        # Enable/disable controls based on checkbox, but keep group visible
        def set_control_enabled(enabled):
            for widget in [
                self.control_optical_config,
                self.control_intensity_slider,
                self.control_intensity_value_label,
                self.control_exposure
            ]:
                widget.setEnabled(enabled)
        self.do_control.toggled.connect(set_control_enabled)
        set_control_enabled(self.do_control.isChecked())
        
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
        self.do_control.toggled.connect(self.update_do_control)
        self.control_optical_config.currentTextChanged.connect(self.update_control_optical)
        self.control_intensity_slider.valueChanged.connect(self.update_control_intensity)
        self.control_exposure.valueChanged.connect(self.update_control_exposure)

        # Initialize from pipeline_settings if available
        if self.pipeline_settings is not None:
            ss = self.pipeline_settings.server_settings
            self.model_type.setCurrentText(ss.model_type)
            if hasattr(self, 'pretrained_model_input'):
                self.pretrained_model_input.setText(getattr(ss, 'pretrained_model_path', ''))
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
            cs = self.pipeline_settings.control_settings
            self.do_control.setChecked(cs.control_loop)
            self.control_optical_config.setCurrentText(cs.preset.optical_configuration)
            self.control_intensity_slider.setValue(cs.preset.intensity)
            self.control_intensity_value_label.setText(str(cs.preset.intensity))
            self.control_exposure.setValue(cs.preset.exposure_ms)

    def update_model_type(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.server_settings.model_type = value

    def update_pretrained_model(self, value):
        if self.pipeline_settings is not None:
            setattr(self.pipeline_settings.server_settings, 'pretrained_model_path', value)

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
    
    def update_do_control(self, checked: bool):
        if self.pipeline_settings is not None:
            self.pipeline_settings.control_settings.control_loop = checked

    def update_control_optical(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.control_settings.preset.optical_configuration = value

    def update_control_intensity(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.control_settings.preset.intensity = value

    def update_control_exposure(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.control_settings.preset.exposure_ms = value
        
