from PyQt6.QtWidgets import QWidget, QFormLayout, QComboBox, QCheckBox,  QDoubleSpinBox, QLabel, QPushButton, QDialog, QVBoxLayout, QTableWidget, QSlider, QTableWidgetItem, QHeaderView, QHBoxLayout, QGroupBox, QLineEdit, QSizePolicy
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor, QIntValidator, QPainter, QPen, QMouseEvent

class DishPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)

        # Dish Name
        self.dish_name = QComboBox()
        self.dish_name.addItems(["35mm", "ibidi-8well", "96well"])
        self.dish_name.setCurrentText("35mm")  # Default
        dish_label = QLabel("Dish Name")
        dish_label.setToolTip("Name of the dish, e.g., '35mm', 'ibidi-8well', or '96well'. Defaults to '35mm'.")
        layout.addRow(dish_label, self.dish_name)

        # Well Selection Button
        self.well_selection_btn = QPushButton()
        self.selected_wells = ["A1"]
        self.update_well_selection_btn()
        self.well_selection_btn.clicked.connect(self.open_well_dialog)
        well_label = QLabel("Well Selection")
        well_label.setToolTip("Well name or list of wells to image, e.g., ['A1', 'A2']. If 'all', will image all possible wells. Defaults to ['A1'].")
        layout.addRow(well_label, self.well_selection_btn)

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
        if dish == "35mm":
            self.selected_wells = ["A1"]
            self.well_selection_btn.setEnabled(True)
        elif dish == "ibidi-8well":
            self.selected_wells = []
            self.well_selection_btn.setEnabled(True)
        elif dish == "96well":
            self.selected_wells = []
            self.well_selection_btn.setEnabled(True)
        self.update_well_selection_btn()

    def update_well_selection_btn(self):
        if self.dish_name.currentText() == "35mm":
            self.well_selection_btn.setText("A1")
        else:
            if self.selected_wells:
                if len(self.selected_wells) < 10:
                    self.well_selection_btn.setText(", ".join(self.selected_wells))
                else:
                    shown = self.selected_wells[:3] + ["..."] + self.selected_wells[-3:]
                    self.well_selection_btn.setText(", ".join(shown))
            else:
                self.well_selection_btn.setText("Select wells...")

    def open_well_dialog(self):
        dish = self.dish_name.currentText()
        if dish == "ibidi-8well":
            rows, cols = 2, 4
            row_labels = ["A", "B"]
            col_labels = [str(i+1) for i in range(4)]
        elif dish == "96well":
            rows, cols = 8, 12
            row_labels = [chr(ord('A')+i) for i in range(8)]
            col_labels = [str(i+1) for i in range(12)]
        else:
            return
        dlg = WellSelectionDialog(self, rows, cols, row_labels, col_labels, self.selected_wells)
        if dlg.exec():
            self.selected_wells = dlg.get_selected_wells()
            self.update_well_selection_btn()

# --- WellSelectionDialog ---


# Custom QTableWidget to draw rubber-band rectangle in foreground
class RubberBandTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_active = False
        self._drag_mode = None
        self._drag_start = None
        self._drag_end = None

    def set_rubberband(self, active, mode, start, end):
        self._drag_active = active
        self._drag_mode = mode
        self._drag_start = start
        self._drag_end = end
        viewport = self.viewport()
        if viewport is not None:
            viewport.update()

    def clear_rubberband(self):
        self._drag_active = False
        self._drag_mode = None
        self._drag_start = None
        self._drag_end = None
        viewport = self.viewport()
        if viewport is not None:
            viewport.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        # Draw the rubber-band rectangle in the foreground
        if self._drag_active and self._drag_start and self._drag_end:
            
            painter = QPainter(self.viewport())
            if self._drag_mode == 'deselect':
                pen = QPen(QColor(220, 50, 50, 180), 2, Qt.PenStyle.DashLine)  # Red-ish
            else:
                pen = QPen(QColor(0, 120, 215, 180), 2, Qt.PenStyle.DashLine)  # Blue-ish
            painter.setPen(pen)
            rect = QRect(self._drag_start, self._drag_end).normalized()
            painter.drawRect(rect)
            painter.end()

class WellSelectionDialog(QDialog):
    def eventFilter(self, a0, a1):
        # Rubber-band rectangle selection logic (mouse events only)
        if a0 == self.table.viewport() and a1 is not None:
            if a1.type() == a1.Type.MouseButtonPress:
                if isinstance(a1, QMouseEvent):
                    pos = a1.pos()
                else:
                    pos = None
                self._drag_start = pos
                self._drag_end = pos
                self._drag_active = True
                
                if isinstance(a1, QMouseEvent):
                    if a1.button() == Qt.MouseButton.LeftButton:
                        self._drag_mode = 'select'
                    elif a1.button() == Qt.MouseButton.RightButton:
                        self._drag_mode = 'deselect'
                    else:
                        self._drag_mode = None
                else:
                    self._drag_mode = None
                self.table.set_rubberband(True, self._drag_mode, self._drag_start, self._drag_end)
                self._highlight_cells_in_rect(self._drag_start, self._drag_end)
                return True
            elif a1.type() == a1.Type.MouseMove and getattr(self, '_drag_active', False):
                if isinstance(a1, QMouseEvent):
                    pos = a1.pos()
                else:
                    pos = None
                self._drag_end = pos
                self.table.set_rubberband(True, self._drag_mode, self._drag_start, self._drag_end)
                self._highlight_cells_in_rect(self._drag_start, self._drag_end)
                return True
            elif a1.type() == a1.Type.MouseButtonRelease and getattr(self, '_drag_active', False):
                self._apply_drag_selection()
                self._clear_highlight()
                self._drag_active = False
                self._drag_mode = None
                self.table.clear_rubberband()
                return True
        return super().eventFilter(a0, a1)

    def _highlight_cells_in_rect(self, start, end):
        # Highlight all cells within the rectangle defined by start and end
        rect = QRect(start, end).normalized()
        for r in range(self.rows):
            for c in range(self.cols):
                item = self.table.item(r, c)
                if item is not None:
                    cell_rect = self.table.visualItemRect(item)
                    if rect.intersects(cell_rect):
                        item.setBackground(QColor(200, 220, 255, 180))
                    else:
                        item.setBackground(QColor(255, 255, 255, 0))

    def _clear_highlight(self):
        for r in range(self.rows):
            for c in range(self.cols):
                item = self.table.item(r, c)
                if item is not None:
                    item.setBackground(QColor(255, 255, 255, 0))

    def _apply_drag_selection(self):
        # Actually select/deselect all highlighted cells
        if self._drag_start is not None and self._drag_end is not None:
            rect = QRect(self._drag_start, self._drag_end).normalized()
            for r in range(self.rows):
                for c in range(self.cols):
                    item = self.table.item(r, c)
                    if item is not None:
                        cell_rect = self.table.visualItemRect(item)
                        if rect.intersects(cell_rect):
                            if self._drag_mode == 'select':
                                item.setSelected(True)
                            elif self._drag_mode == 'deselect':
                                item.setSelected(False)

    def __init__(self, parent, rows, cols, row_labels, col_labels, selected_wells):
        super().__init__(parent)
        self.setWindowTitle("Select Wells")
        self.resize(500, 300)
        self.selected = set(selected_wells)
        self.rows = rows
        self.cols = cols
        self.row_labels = row_labels
        self.col_labels = col_labels

        vbox = QVBoxLayout(self)

        self.table = RubberBandTableWidget(rows, cols)
        self.table.setHorizontalHeaderLabels(col_labels)
        self.table.setVerticalHeaderLabels(row_labels)
        # For 96well, set a fixed size so all cells are visible without scrolling
        if rows == 8 and cols == 12:
            cell_width = 40
            cell_height = 32
            vh = self.table.verticalHeader()
            hh = self.table.horizontalHeader()
            vh_width = vh.width() if vh is not None else 0
            hh_height = hh.height() if hh is not None else 0
            table_width = cell_width * cols + vh_width + 4
            table_height = cell_height * rows + hh_height + 4
            self.table.setMinimumSize(table_width, table_height)
            self.setMinimumSize(table_width + 40, table_height + 100)
            for c in range(cols):
                self.table.setColumnWidth(c, cell_width)
            for r in range(rows):
                self.table.setRowHeight(r, cell_height)
        else:
            hh = self.table.horizontalHeader()
            vh = self.table.verticalHeader()
            if hh is not None:
                hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            if vh is not None:
                vh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        for r in range(rows):
            for c in range(cols):
                well = f"{row_labels[r]}{col_labels[c]}"
                item = QTableWidgetItem()
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(r, c, item)
                if well in self.selected:
                    item = self.table.item(r, c)
                    if item is not None:
                        item.setSelected(True)

        vbox.addWidget(self.table)

        # Install event filter for left/right click and drag selection (must be after self.table is created)
        viewport = self.table.viewport()
        if viewport is not None:
            viewport.installEventFilter(self)
            viewport.setMouseTracking(True)
        self._drag_active = False
        self._drag_mode = None

        # OK and Cancel buttons
        btn_hbox = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_hbox.addStretch(1)
        btn_hbox.addWidget(ok_btn)
        btn_hbox.addWidget(cancel_btn)
        vbox.addLayout(btn_hbox)

    # No select all logic needed

    # No checkboxes, so no itemChanged logic needed

    # No update_select_all_checkbox needed

    def get_selected_wells(self):
        selected = []
        for item in self.table.selectedItems():
            r = item.row()
            c = item.column()
            selected.append(f"{self.row_labels[r]}{self.col_labels[c]}")
        return selected

    def exec(self):
        # Override to update selected wells after dialog closes
        result = super().exec()
        return result

        