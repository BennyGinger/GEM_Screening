from PyQt6.QtWidgets import QWidget, QFormLayout, QComboBox, QCheckBox,  QLabel, QPushButton, QSlider, QHBoxLayout, QGroupBox, QLineEdit, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator

from gem_screening.settings.gui.pages.well_selection_widget import WellSelectionWidget
from gem_screening.settings.models import PipelineSettings
class DishPage(QWidget):
    def __init__(self, pipeline_settings: PipelineSettings):
        super().__init__()
        self.pipeline_settings = pipeline_settings
        layout = QFormLayout(self)
        self.setMinimumWidth(700)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Preferred)
        layout.setVerticalSpacing(8)  # Reduce vertical spacing for compactness
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Keep content at top

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
        af_label = QLabel("AF Method")
        af_label.setToolTip("Method for autofocus, e.g., 'sq_grad' or 'Manual'. Defaults to 'sq_grad'.")
        layout.addRow(af_label, self.af_method)

        # --- Advanced settings container ---
        self.advanced_box = QGroupBox("Advanced Settings")
        self.advanced_box.setCheckable(False)
        self.advanced_box.setVisible(False)
        adv_layout = QFormLayout()

        # DMD Window Only (default True)
        self.dmd_window_only = QCheckBox()
        dmd_label = QLabel("DMD Window Only")
        dmd_label.setToolTip("If True, will only use the DMD window for measurement. Defaults to True.")
        adv_layout.addRow(dmd_label, self.dmd_window_only)

        # Overlap % (QSlider 0-100) with value label
        self.overlap_percent = QSlider(Qt.Orientation.Horizontal)
        self.overlap_percent.setRange(0, 100)
        self.overlap_percent.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.overlap_percent.setMinimumWidth(500)
        overlap_label = QLabel("Overlap %")
        overlap_label.setToolTip("Overlap percentage for field views. If None, will use optimal overlap for the dish.")
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
        n_corners_label = QLabel("N Corners In")
        n_corners_label.setToolTip("Number of corners of each fov that should be contained within a round well at the edges. Must be 1, 2, 3, or 4. Defaults to 4.")
        adv_layout.addRow(n_corners_label, self.n_corners_in)

        # (Advanced settings toggle button and box will be added after Overwrite Calib below)
        self.advanced_box.setLayout(adv_layout)
        # Num Field View (QLineEdit + 'All' QCheckBox)
        self.numb_field_view_input = QLineEdit()
        self.numb_field_view_input.setValidator(QIntValidator(1, 99999999, self))
        self.numb_field_view_input.setPlaceholderText("")
        self.numb_field_view_input.setFixedWidth(90)
        self.numb_field_view_all = QCheckBox("All")
        numfov_label = QLabel("Num Field View")
        numfov_label.setToolTip("Number of field views to image. If None, will run the whole well.")
        numfov_hbox = QHBoxLayout()
        numfov_hbox.addWidget(self.numb_field_view_input)
        numfov_hbox.addWidget(self.numb_field_view_all)
        numfov_hbox.addStretch(1)
        layout.addRow(numfov_label, numfov_hbox)

        def on_numfov_text_changed(text):
            if text.strip():
                if self.numb_field_view_all.isChecked():
                    self.numb_field_view_all.setChecked(False)
            # Do not auto-check if cleared, let user control

        def on_numfov_all_changed(state):
            if self.numb_field_view_all.isChecked():
                self.numb_field_view_input.clear()
            # Do not disable input, always allow typing

        self.numb_field_view_input.textChanged.connect(on_numfov_text_changed)
        self.numb_field_view_all.stateChanged.connect(on_numfov_all_changed)

        # Overwrite Autofocus
        self.overwrite_autofocus = QCheckBox()
        overwrite_af_label = QLabel("Overwrite Autofocus")
        overwrite_af_label.setToolTip("If True, will overwrite the autofocus settings. Defaults to False.")
        layout.addRow(overwrite_af_label, self.overwrite_autofocus)

        # Overwrite Calib
        self.overwrite_calib = QCheckBox()
        overwrite_calib_label = QLabel("Overwrite Calib")
        overwrite_calib_label.setToolTip("If True, will overwrite the calibration file. Defaults to False.")
        layout.addRow(overwrite_calib_label, self.overwrite_calib)

        # Advanced settings toggle button (now after Overwrite Calib)
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
        self.dish_name.currentTextChanged.connect(self.update_dish_name)
        self.af_method.currentTextChanged.connect(self.update_af_method)
        self.dmd_window_only.stateChanged.connect(self.update_dmd_window_only)
        self.overlap_percent.valueChanged.connect(self.update_overlap_percent)
        self.n_corners_in.currentTextChanged.connect(self.update_n_corners_in)
        self.numb_field_view_input.textChanged.connect(self.update_numb_field_view)
        self.numb_field_view_all.stateChanged.connect(self.update_numb_field_view_all)
        self.overwrite_autofocus.stateChanged.connect(self.update_overwrite_autofocus)
        self.overwrite_calib.stateChanged.connect(self.update_overwrite_calib)
        # Well selection widget connection (assume it has a signal or method to get selection)
        if hasattr(self.well_selection_widget, 'selectionChanged'):
            self.well_selection_widget.selectionChanged.connect(self.update_well_selection)

        # Initialize from pipeline_settings if available
        if self.pipeline_settings is not None:
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
            self.overwrite_autofocus.setChecked(dish.overwrite_autofocus)
            self.overwrite_calib.setChecked(dish.overwrite_calib)
            # Well selection
            if hasattr(self.well_selection_widget, 'set_selection'):
                wells = dish.well_selection
                if isinstance(wells, str):
                    wells = [wells]
                self.well_selection_widget.set_selection(wells)

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

    def update_overwrite_autofocus(self, state):
        if self.pipeline_settings is not None:
            self.pipeline_settings.dish_settings.overwrite_autofocus = bool(state)

    def update_overwrite_calib(self, state):
        if self.pipeline_settings is not None:
            self.pipeline_settings.dish_settings.overwrite_calib = bool(state)

    def update_well_selection(self, selection):
        if self.pipeline_settings is not None:
            self.pipeline_settings.dish_settings.well_selection = selection

    def on_dish_changed(self, dish):
        self.well_selection_widget.set_dish(dish)


        