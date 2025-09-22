from PyQt6.QtWidgets import QWidget, QFormLayout, QComboBox, QCheckBox,  QLabel, QPushButton, QSlider, QHBoxLayout, QGroupBox, QLineEdit, QSizePolicy
from .well_selection_widget import WellSelectionWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator

class DishPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        self.setMinimumWidth(700)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Preferred)
        layout.setVerticalSpacing(8)  # Reduce vertical spacing for compactness
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Keep content at top

        # Dish Name
        self.dish_name = QComboBox()
        self.dish_name.addItems(["35mm", "ibidi-8well", "96well"])
        self.dish_name.setCurrentText("35mm")  # Default
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
        self.af_method.setCurrentText("sq_grad")  # Default
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
        self.dmd_window_only.setChecked(True)
        dmd_label = QLabel("DMD Window Only")
        dmd_label.setToolTip("If True, will only use the DMD window for measurement. Defaults to True.")
        adv_layout.addRow(dmd_label, self.dmd_window_only)

        # Overlap % (QSlider 0-100) with value label
        self.overlap_percent = QSlider(Qt.Orientation.Horizontal)
        self.overlap_percent.setRange(0, 100)
        self.overlap_percent.setValue(0)
        self.overlap_percent.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.overlap_percent.setMinimumWidth(500)
        # Match slider width to measure page (no explicit minimum width)
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
        self.n_corners_in.setCurrentText("4")
        n_corners_label = QLabel("N Corners In")
        n_corners_label.setToolTip("Number of corners of each fov that should be contained within a round well at the edges. Must be 1, 2, 3, or 4. Defaults to 4.")
        adv_layout.addRow(n_corners_label, self.n_corners_in)

        self.advanced_box.setLayout(adv_layout)

        # (Advanced settings toggle button and box will be added after Overwrite Calib below)

        # Num Field View (QLineEdit + 'All' QCheckBox)
        self.numb_field_view_input = QLineEdit()
        self.numb_field_view_input.setValidator(QIntValidator(1, 99999999, self))
        self.numb_field_view_input.setPlaceholderText("")
        self.numb_field_view_input.setFixedWidth(90)
        self.numb_field_view_all = QCheckBox("All")
        self.numb_field_view_all.setChecked(True)
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



    def on_dish_changed(self, dish):
        self.well_selection_widget.set_dish(dish)


    # Removed update_well_selection_btn and open_well_dialog (now handled by WellSelectionWidget)


        