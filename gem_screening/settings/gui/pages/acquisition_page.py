from PyQt6.QtWidgets import QWidget, QFormLayout, QComboBox, QCheckBox,  QLabel, QPushButton, QSlider, QHBoxLayout, QGroupBox, QLineEdit, QSizePolicy, QSpinBox, QVBoxLayout, QSpacerItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator

from gem_screening.settings.gui.pages.well_selection_widget import WellSelectionWidget
from gem_screening.settings.models import PipelineSettings


class AcquisitionPage(QWidget):
    def __init__(self, pipeline_settings: PipelineSettings):
        super().__init__()
        self.pipeline_settings = pipeline_settings
        layout = QFormLayout(self)
        self.setMinimumWidth(700)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Preferred)
        layout.setVerticalSpacing(8)  # Reduce vertical spacing for compactness
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Keep content at top

        # Objective
        self.objective = QComboBox()
        self.objective.addItems(["10x", "20x"])
        objective_label = QLabel("Objective")
        objective_label.setToolTip("The objective lens used for imaging, e.g., '10x' or '20x'. Defaults to '20x'.")
        layout.addRow(objective_label, self.objective)

        # Dish Name
        self.dish_name = QComboBox()
        self.dish_name.addItems(["35mm", "ibidi-8well", "96well"])
        dish_label = QLabel("Dish Name")
        dish_label.setToolTip("Name of the dish, e.g., '35mm', 'ibidi-8well', or '96well'. Defaults to '35mm'.")
        layout.addRow(dish_label, self.dish_name)

        # Well Selection Widget (always visible)
        self.well_selection_widget = WellSelectionWidget()
        well_label = QLabel("Well Selection")
        well_label.setToolTip("Select wells to image. For 35mm, only A1 is available. For ibidi-8well and 96well, select wells directly.")
        layout.addRow(well_label, self.well_selection_widget)

        self.dish_name.currentTextChanged.connect(self.on_dish_changed)
        self.on_dish_changed(self.dish_name.currentText())

        # AF Method
        self.af_method = QComboBox()
        self.af_method.addItems(["sq_grad", "Manual"])
        af_label = QLabel("Autofocus Method")
        af_label.setToolTip("Method for autofocus, e.g., 'sq_grad' or 'Manual'. Defaults to 'sq_grad'.")
        layout.addRow(af_label, self.af_method)
        
        # Num Field View (QLineEdit + 'All' QCheckBox)
        self.numb_field_view_input = QLineEdit()
        self.numb_field_view_input.setValidator(QIntValidator(1, 99999999, self))
        self.numb_field_view_input.setPlaceholderText("")
        self.numb_field_view_input.setFixedWidth(90)
        self.numb_field_view_all = QCheckBox("All")
        numfov_label = QLabel("# Field of View")
        numfov_label.setToolTip("Number of field views to image. If None, will run the whole well.")
        numfov_hbox = QHBoxLayout()
        numfov_hbox.addWidget(self.numb_field_view_input)
        numfov_hbox.addSpacing(20)  # Add more space between input and 'All' checkbox
        numfov_hbox.addWidget(self.numb_field_view_all)
        numfov_hbox.addStretch(1)
        layout.addRow(numfov_label, numfov_hbox)

        def on_numfov_text_changed(text):
            if text.strip():
                if self.numb_field_view_all.isChecked():
                    self.numb_field_view_all.setChecked(False)
                # Update pipeline_settings
                if self.pipeline_settings is not None:
                    self.pipeline_settings.dish_settings.numb_field_view = int(text)
            else:
                # If cleared, do not set to None unless 'All' is checked
                if self.pipeline_settings is not None and not self.numb_field_view_all.isChecked():
                    self.numb_field_view_all.setChecked(True)
                    self.pipeline_settings.dish_settings.numb_field_view = None

        def on_numfov_all_changed(state):
            if self.numb_field_view_all.isChecked():
                self.numb_field_view_input.clear()
                # Set to None if 'All' is checked
                if self.pipeline_settings is not None:
                    self.pipeline_settings.dish_settings.numb_field_view = None
            

        self.numb_field_view_input.textChanged.connect(on_numfov_text_changed)
        self.numb_field_view_all.stateChanged.connect(on_numfov_all_changed)

        ##########################################################
        # Advanced settings toggle button (now after Overwrite Calib)
        self.advanced_btn = QPushButton("Show Advanced Settings")
        self.advanced_btn.setCheckable(True)
        
        # --- Advanced settings container ---
        self.advanced_box = QGroupBox("Advanced Settings")
        self.advanced_box.setCheckable(False)
        self.advanced_box.setVisible(False)
        adv_layout = QFormLayout()

        # Lamp Name
        self.lamp = QComboBox()
        self.lamp.addItems(["pE-800", "pE-4000", "DiaLamp"])
        lamp_label = QLabel("Lamp Name")
        lamp_label.setToolTip("The name of the lamp used for illumination, e.g., 'pE-800', 'pE-4000', or 'DiaLamp'. Defaults to 'pE-800'.")
        self.lamp.currentTextChanged.connect(self.update_lamp)
        adv_layout.addRow(lamp_label, self.lamp)

        # Focus Device
        self.focus = QComboBox()
        self.focus.addItems(["PFSOffset", "ZDrive"])
        focus_label = QLabel("Focus Device")
        focus_label.setToolTip("The device used for focusing, e.g., 'PFSOffset' or 'ZDrive'. Defaults to 'PFSOffset'.")
        self.focus.currentTextChanged.connect(self.update_focus)
        adv_layout.addRow(focus_label, self.focus)
        
        # DMD Window Only (default True)
        self.dmd_window_only = QCheckBox()
        dmd_label = QLabel("Use DMD window size")
        dmd_label.setToolTip("If True, will only use the size of the DMD window for measurement. Defaults to True.")
        adv_layout.addRow(dmd_label, self.dmd_window_only)

        # Overlap % (QSlider 0-100) with value label
        self.overlap_percent = QSlider(Qt.Orientation.Horizontal)
        self.overlap_percent.setRange(0, 100)
        self.overlap_percent.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.overlap_percent.setMinimumWidth(500)
        overlap_label = QLabel("Overlap between FOVs %")
        overlap_label.setToolTip("Overlap percentage for field of views. If None, will use optimal overlap for the dish.")
        self.overlap_value_label = QLabel(str(self.overlap_percent.value()))
        overlap_hbox = QHBoxLayout()
        overlap_hbox.addWidget(self.overlap_percent)
        overlap_hbox.addWidget(self.overlap_value_label)
        overlap_hbox.addStretch(1)
        adv_layout.addRow(overlap_label, overlap_hbox)

        def update_overlap_label(val):
            self.overlap_value_label.setText(str(val))
        self.overlap_percent.valueChanged.connect(update_overlap_label)

        # N Corners In (dropdown)
        self.n_corners_in = QComboBox()
        self.n_corners_in.addItems(["1", "2", "3", "4"])
        n_corners_label = QLabel("FOV's Corners Incl.")
        n_corners_label.setToolTip("Number of corners of each FOV that should be contained within a round well at the edges. Must be 1, 2, 3, or 4. Defaults to 4.")
        adv_layout.addRow(n_corners_label, self.n_corners_in)
        self.advanced_box.setLayout(adv_layout)
        
        def toggle_advanced():
            show = self.advanced_btn.isChecked()
            self.advanced_box.setVisible(show)
            self.advanced_btn.setText("Hide Advanced Settings" if show else "Show Advanced Settings")
        self.advanced_btn.clicked.connect(toggle_advanced)
        layout.addRow(self.advanced_btn)
        layout.addRow(self.advanced_box)
        layout.addItem(QSpacerItem(0, 16))

        ##########################################################
        # Optics Settings
        # Measurement Preset group
        preset_group = QGroupBox("Measurement Preset")
        preset_layout = QFormLayout(preset_group)
        self.optical_config = QComboBox()
        self.optical_config.addItems(["GFP", "iRed", "BFP", "RFP"])
        optical_label = QLabel("Optical Config")
        optical_label.setToolTip("Optical configuration for the preset, e.g., 'GFP', 'iRed', 'BFP', or 'RFP'. Defaults to 'GFP'.")
        self.intensity_slider = QSlider()
        self.intensity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 100)
        self.intensity_value_label = QLabel("25")
        intensity_label = QLabel("Intensity")
        intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 25.")
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(self.intensity_slider)
        intensity_layout.addWidget(self.intensity_value_label)
        self.intensity_slider.valueChanged.connect(lambda v: self.intensity_value_label.setText(str(v)))
        self.exposure = QSpinBox()
        self.exposure.setRange(1, 10000)
        self.exposure.setSingleStep(10)
        exposure_label = QLabel("Exposure (ms)")
        exposure_label.setToolTip("Exposure time in milliseconds for the preset. Defaults to 100.")
        preset_layout.addRow(optical_label, self.optical_config)
        preset_layout.addRow(intensity_label, intensity_layout)
        preset_layout.addRow(exposure_label, self.exposure)
        self.optical_config.currentTextChanged.connect(self.update_measure_optical)
        self.intensity_slider.valueChanged.connect(self.update_measure_intensity)
        self.exposure.valueChanged.connect(self.update_measure_exposure)
        layout.addRow(preset_group)

        # Preset Refseg group with checkbox as title
        self.refseg_group = QGroupBox()
        self.do_refseg = QCheckBox("Do Reference Segmentation")
        self.do_refseg.setChecked(True)
        self.do_refseg.setToolTip("If True, will perform reference segmentation. Defaults to True.")
        # Place checkbox as groupbox title using layout
        refseg_title_layout = QHBoxLayout()
        refseg_title_layout.addWidget(self.do_refseg)
        refseg_title_layout.addStretch(1)
        refseg_main_layout = QVBoxLayout(self.refseg_group)
        refseg_main_layout.addLayout(refseg_title_layout)
        refseg_layout = QFormLayout()
        self.ref_optical_config = QComboBox()
        self.ref_optical_config.addItems(["iRed", "GFP", "BFP", "RFP"])
        ref_optical_label = QLabel("Optical Config")
        ref_optical_label.setToolTip("Optical configuration for the preset, e.g., 'iRed'. Defaults to 'iRed'.")
        self.ref_intensity_slider = QSlider()
        self.ref_intensity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.ref_intensity_slider.setRange(0, 100)
        self.ref_intensity_value_label = QLabel("5")
        ref_intensity_label = QLabel("Intensity")
        ref_intensity_label.setToolTip("Intensity level for the preset, ranging from 0 to 100. Defaults to 5.")
        ref_intensity_layout = QHBoxLayout()
        ref_intensity_layout.addWidget(self.ref_intensity_slider)
        ref_intensity_layout.addWidget(self.ref_intensity_value_label)
        self.ref_intensity_slider.valueChanged.connect(lambda v: self.ref_intensity_value_label.setText(str(v)))
        self.ref_exposure = QSpinBox()
        self.ref_exposure.setRange(1, 10000)
        self.ref_exposure.setSingleStep(10)
        ref_exposure_label = QLabel("Exposure (ms)")
        ref_exposure_label.setToolTip("Exposure time in milliseconds for the preset. Defaults to 100.")
        refseg_layout.addRow(ref_optical_label, self.ref_optical_config)
        refseg_layout.addRow(ref_intensity_label, ref_intensity_layout)
        refseg_layout.addRow(ref_exposure_label, self.ref_exposure)
        refseg_main_layout.addLayout(refseg_layout)
        self.do_refseg.toggled.connect(self.update_do_refseg)
        self.ref_optical_config.currentTextChanged.connect(self.update_refseg_optical)
        self.ref_intensity_slider.valueChanged.connect(self.update_refseg_intensity)
        self.ref_exposure.valueChanged.connect(self.update_refseg_exposure)
        layout.addRow(self.refseg_group)
        
        def set_refseg_enabled(enabled):
            for widget in [
                self.ref_optical_config,
                self.ref_intensity_slider,
                self.ref_intensity_value_label,
                self.ref_exposure
            ]:
                widget.setEnabled(enabled)
        self.do_refseg.toggled.connect(set_refseg_enabled)
        set_refseg_enabled(self.do_refseg.isChecked())
        ##########################################################
        # Connect signals to update pipeline_settings
        self.dish_name.currentTextChanged.connect(self.update_dish_name)
        self.af_method.currentTextChanged.connect(self.update_af_method)
        self.dmd_window_only.stateChanged.connect(self.update_dmd_window_only)
        self.overlap_percent.valueChanged.connect(self.update_overlap_percent)
        self.n_corners_in.currentTextChanged.connect(self.update_n_corners_in)
        self.numb_field_view_input.textChanged.connect(self.update_numb_field_view)
        self.numb_field_view_all.stateChanged.connect(self.update_numb_field_view_all)
        self.objective.currentTextChanged.connect(self.update_objective)
        self.lamp.currentTextChanged.connect(self.update_lamp)
        self.focus.currentTextChanged.connect(self.update_focus)
        self.optical_config.currentTextChanged.connect(self.update_measure_optical)
        self.intensity_slider.valueChanged.connect(self.update_measure_intensity)
        self.exposure.valueChanged.connect(self.update_measure_exposure)
        self.do_refseg.toggled.connect(self.update_do_refseg)
        self.ref_optical_config.currentTextChanged.connect(self.update_refseg_optical)
        self.ref_intensity_slider.valueChanged.connect(self.update_refseg_intensity)
        self.ref_exposure.valueChanged.connect(self.update_refseg_exposure)
        # Well selection widget connection (assume it has a signal or method to get selection)
        if hasattr(self.well_selection_widget, 'selectionChanged'):
            self.well_selection_widget.selectionChanged.connect(self.update_well_selection)

        # Initialize from pipeline_settings if available
        if self.pipeline_settings is not None:
            acq = self.pipeline_settings.acquisition_settings
            self.objective.setCurrentText(acq.objective)
            self.lamp.setCurrentText(acq.lamp_name)
            self.focus.setCurrentText(acq.focus_device)
            
            dish = self.pipeline_settings.dish_settings
            self.dish_name.setCurrentText(dish.dish_name)
            self.af_method.setCurrentText(dish.af_method)
            self.dmd_window_only.setChecked(dish.dmd_window_only)
            if dish.overlap_percent is not None:
                self.overlap_percent.setValue(int(dish.overlap_percent))
            self.n_corners_in.setCurrentText(str(dish.n_corners_in))
            if dish.numb_field_view is not None:
                self.numb_field_view_input.setText(str(dish.numb_field_view))
                self.numb_field_view_all.setChecked(False)
            else:
                self.numb_field_view_input.clear()
                self.numb_field_view_all.setChecked(True)
            # Well selection
            if hasattr(self.well_selection_widget, 'set_selection'):
                wells = dish.well_selection
                if isinstance(wells, str):
                    wells = [wells]
                self.well_selection_widget.set_selection(wells)
            ms = self.pipeline_settings.measure_settings
            self.optical_config.setCurrentText(ms.preset_measure.optical_configuration)
            self.intensity_slider.setValue(ms.preset_measure.intensity)
            self.intensity_value_label.setText(str(ms.preset_measure.intensity))
            self.exposure.setValue(ms.preset_measure.exposure_ms)
            self.do_refseg.setChecked(ms.do_refseg)
            self.ref_optical_config.setCurrentText(ms.preset_refseg.optical_configuration)
            self.ref_intensity_slider.setValue(ms.preset_refseg.intensity)
            self.ref_intensity_value_label.setText(str(ms.preset_refseg.intensity))
            self.ref_exposure.setValue(ms.preset_refseg.exposure_ms)

    def update_dish_name(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.dish_settings.dish_name = value

    def update_af_method(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.dish_settings.af_method = value

    def update_dmd_window_only(self, state):
        if self.pipeline_settings is not None:
            self.pipeline_settings.dish_settings.dmd_window_only = bool(state)

    def update_overlap_percent(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.dish_settings.overlap_percent = float(value) if value > 0 else None

    def update_n_corners_in(self, value):
        if self.pipeline_settings is not None:
            self.pipeline_settings.dish_settings.n_corners_in = int(value)

    def update_numb_field_view(self, text):
        if self.pipeline_settings is not None:
            if text.strip():
                self.pipeline_settings.dish_settings.numb_field_view = int(text)
                self.numb_field_view_all.setChecked(False)
            else:
                self.pipeline_settings.dish_settings.numb_field_view = None

    def update_numb_field_view_all(self, state):
        if self.pipeline_settings is not None:
            if self.numb_field_view_all.isChecked():
                self.pipeline_settings.dish_settings.numb_field_view = None
                self.numb_field_view_input.clear()

    def update_well_selection(self, selection):
        if self.pipeline_settings is not None:
            self.pipeline_settings.dish_settings.well_selection = selection

    def on_dish_changed(self, dish):
        self.well_selection_widget.set_dish(dish)

    def update_objective(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.acquisition_settings.objective = value

    def update_lamp(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.acquisition_settings.lamp_name = value

    def update_focus(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.acquisition_settings.focus_device = value
    
    def update_measure_optical(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_measure.optical_configuration = value

    def update_measure_intensity(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_measure.intensity = value

    def update_measure_exposure(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_measure.exposure_ms = value

    def update_do_refseg(self, checked: bool):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.do_refseg = checked

    def update_refseg_optical(self, value: str):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_refseg.optical_configuration = value

    def update_refseg_intensity(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_refseg.intensity = value

    def update_refseg_exposure(self, value: int):
        if self.pipeline_settings is not None:
            self.pipeline_settings.measure_settings.preset_refseg.exposure_ms = value