import sys
from typing import Optional
import colorsys
import ast
import os

from tifffile import imread
from numpy.typing import NDArray
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QFileDialog, QPushButton, QSizePolicy, QFrame, QSlider, QCheckBox, QLineEdit, QTextEdit, QGroupBox, QGridLayout, QComboBox, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage, QDoubleValidator, QIntValidator, QKeyEvent, QFocusEvent

from a1_manager import A1Manager, StageCoord
from gem_screening.utils.client.service import cellpose_metadata_client, optimise_segmentation
from gem_screening.settings.models import ServerSettings, PipelineSettings
from gem_screening.tasks.tune_segmentation import ImageCollector



class ExtraParamsTextEdit(QTextEdit):
    """Custom QTextEdit that only processes text on focus out or Ctrl+Enter"""
    params_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def focusOutEvent(self, e: Optional[QFocusEvent]):
        """Process text when focus is lost"""
        super().focusOutEvent(e)
        self.params_changed.emit()

    def keyPressEvent(self, e: Optional[QKeyEvent]):
        """Process text on Ctrl+Enter"""
        super().keyPressEvent(e)
        if e and e.key() == Qt.Key.Key_Return and e.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.params_changed.emit()


class TuneSegWidget(QWidget):
    
    result_signal = pyqtSignal(str)
    def __init__(self, settings: PipelineSettings, img: Optional[NDArray] = None, mask: Optional[NDArray] = None, dish_grid=None, a1_manager=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.image = img
        self.seg_mask = mask
        self.original_pixmap = None
        self.mask_overlay_rgb = None  # Pre-computed mask overlay
        self.show_mask_overlay = True
        # Display parameters (like ImageJ/Fiji) for 16-bit images
        self.display_min = 0
        self.display_max = 65535
        self.brightness = 50  # 0-100
        self.contrast = 50    # 0-100

        # Extract ServerSettings from PipelineSettings
        self.pipeline_settings = settings
        self.settings = settings.server_settings
        self.settings_path = None  # Not used anymore

        # ImageCollector setup
        self.image_collector = None
        if dish_grid is not None and a1_manager is not None:
            self.image_collector = ImageCollector(dish_grid, a1_manager, settings)

        # Initialize Cellpose metadata
        self.cellpose_metadata = self._get_cellpose_metadata()

        self._setup_ui()
        
        # Priority: dish_grid over img
        if self.image_collector is not None:
            self._load_random_image()
        elif img is not None:
            self.image = img
            self._auto_scale()
            if mask is not None:
                self._create_mask_overlay()
            else:
                self._run_segmentation_with_current_settings()

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        if self.original_pixmap and hasattr(self, 'image_label'):
            available_size = self.image_label.size()
            scaled_pixmap = self.original_pixmap.scaled(
                available_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def showEvent(self, a0):
        super().showEvent(a0)
        QTimer.singleShot(50, self._update_image_scale)

    def _update_image_scale(self):
        if self.original_pixmap and hasattr(self, 'image_label'):
            available_size = self.image_label.size()
            scaled_pixmap = self.original_pixmap.scaled(
                available_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def _setup_ui(self):
        self.setMinimumSize(600, 400)
        self.resize(1800, 1400)

        layout = QHBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Control panel (left)
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.Shape.StyledPanel)
        control_layout = QVBoxLayout(control_panel)
        control_layout.setSpacing(10)
        control_layout.setContentsMargins(10, 10, 10, 10)

        # View Controls Group
        view_group = QGroupBox("View Controls")
        view_layout = QGridLayout(view_group)
        view_layout.setSpacing(5)
        
        # View Controls
        view_group = QGroupBox("View Controls")
        view_layout = QGridLayout(view_group)
        
        # Min slider
        view_layout.addWidget(QLabel("Min:"), 0, 0)
        self.min_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_slider.setRange(0, 65535)
        self.min_slider.setValue(0)
        self.min_slider.valueChanged.connect(self._on_display_change)
        view_layout.addWidget(self.min_slider, 0, 1)
        self.min_label = QLabel("0")
        view_layout.addWidget(self.min_label, 0, 2)
        
        # Max slider
        view_layout.addWidget(QLabel("Max:"), 1, 0)
        self.max_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_slider.setRange(0, 65535)
        self.max_slider.setValue(65535)
        self.max_slider.valueChanged.connect(self._on_display_change)
        view_layout.addWidget(self.max_slider, 1, 1)
        self.max_label = QLabel("65535")
        view_layout.addWidget(self.max_label, 1, 2)
        
        # Brightness slider
        view_layout.addWidget(QLabel("Brightness:"), 2, 0)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(50)
        self.brightness_slider.valueChanged.connect(self._on_display_change)
        view_layout.addWidget(self.brightness_slider, 2, 1)
        self.brightness_label = QLabel("50")
        view_layout.addWidget(self.brightness_label, 2, 2)
        
        # Contrast slider
        view_layout.addWidget(QLabel("Contrast:"), 3, 0)
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(0, 100)
        self.contrast_slider.setValue(50)
        self.contrast_slider.valueChanged.connect(self._on_display_change)
        view_layout.addWidget(self.contrast_slider, 3, 1)
        self.contrast_label = QLabel("50")
        view_layout.addWidget(self.contrast_label, 3, 2)
        
        # Auto-scale button
        self.auto_scale_btn = QPushButton("Auto-scale")
        self.auto_scale_btn.clicked.connect(self._auto_scale)
        view_layout.addWidget(self.auto_scale_btn, 4, 0, 1, 3)
        
        # Mask overlay toggle
        self.mask_overlay_cb = QCheckBox("Show mask overlay        (key shortcut 'x')")
        self.mask_overlay_cb.setChecked(True)
        self.mask_overlay_cb.toggled.connect(self._toggle_mask_overlay)
        view_layout.addWidget(self.mask_overlay_cb, 5, 0, 1, 3)
        
        control_layout.addWidget(view_group)
        
        # Title with Cellpose version
        version = self.cellpose_metadata.get("version", "unknown")
        title_label = QLabel(f"Cellpose {version}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px 0;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(title_label)
        
        # Load Image Group
        load_group = QGroupBox("Load Image")
        load_layout = QVBoxLayout(load_group)

        # File loading section
        file_section = QHBoxLayout()
        
        # Image path text area
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText("Paste image path and press Enter")
        self.image_path_edit.setMinimumWidth(250)
        self.image_path_edit.returnPressed.connect(self._on_image_path_entered)
        file_section.addWidget(self.image_path_edit)

        # Browse button
        self.load_image_btn = QPushButton("Browse for Image...")
        self.load_image_btn.clicked.connect(self._on_load_image)
        file_section.addWidget(self.load_image_btn)

        # Status label
        self.loaded_image_path_label = QLabel("")
        self.loaded_image_path_label.setWordWrap(True)
        self.loaded_image_path_label.setStyleSheet("font-size: 10px; color: gray;")
        file_section.addWidget(self.loaded_image_path_label)
        
        load_layout.addLayout(file_section)

        # Coordinate history section (only shown if ImageCollector is available)
        if self.image_collector is not None:
            # History display
            history_label = QLabel("Coordinate History:")
            load_layout.addWidget(history_label)
            
            self.history_list = QListWidget()
            self.history_list.setMaximumHeight(80)
            load_layout.addWidget(self.history_list)
            
            # Buttons
            buttons_layout = QHBoxLayout()
            
            self.load_selected_btn = QPushButton("Load Selected Coord")
            self.load_selected_btn.clicked.connect(self._on_load_selected_coord)
            buttons_layout.addWidget(self.load_selected_btn)
            
            self.random_img_btn = QPushButton("Random Image")
            self.random_img_btn.clicked.connect(self._load_random_image)
            buttons_layout.addWidget(self.random_img_btn)
            
            load_layout.addLayout(buttons_layout)

        control_layout.addWidget(load_group)
    
        # Segmentation Parameters Group
        seg_group = QGroupBox("Segmentation Parameters")
        seg_layout = QGridLayout(seg_group)
        seg_layout.setSpacing(5)
        
        # Model selection dropdown
        model_label = QLabel("Model:")
        seg_layout.addWidget(model_label, 0, 0)
        self.model_combo = QComboBox()
        model_names = self.cellpose_metadata.get("model_names", ["cyto3"])
        self.model_combo.addItems(model_names)
        # Set from settings or default to 'cyto3' if available
        if self.settings.model_type in model_names:
            self.model_combo.setCurrentText(self.settings.model_type)
        elif "cyto3" in model_names:
            self.model_combo.setCurrentText("cyto3")
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        seg_layout.addWidget(self.model_combo, 0, 1)
        
        # Diameter
        diameter_label = QLabel("Diameter:")
        seg_layout.addWidget(diameter_label, 1, 0)
        self.diameter_edit = QLineEdit(str(self.settings.diameter))
        self.diameter_edit.setValidator(QIntValidator(1, 1000))
        self.diameter_edit.setFixedWidth(60)
        self.diameter_edit.textChanged.connect(self._on_diameter_changed)
        seg_layout.addWidget(self.diameter_edit, 1, 1)
        
        # Flow threshold
        flow_label = QLabel("Flow Threshold:")
        seg_layout.addWidget(flow_label, 2, 0)
        self.flow_threshold_edit = QLineEdit(str(self.settings.flow_threshold))
        self.flow_threshold_edit.setValidator(QDoubleValidator(0.0, 10.0, 2))
        self.flow_threshold_edit.setFixedWidth(60)
        self.flow_threshold_edit.textChanged.connect(self._on_flow_threshold_changed)
        seg_layout.addWidget(self.flow_threshold_edit, 2, 1)
        
        # Cellprob threshold
        cellprob_label = QLabel("Cellprob Threshold:")
        seg_layout.addWidget(cellprob_label, 3, 0)
        self.cellprob_threshold_edit = QLineEdit(str(self.settings.cellprob_threshold))
        self.cellprob_threshold_edit.setValidator(QDoubleValidator(-10.0, 10.0, 2))
        self.cellprob_threshold_edit.setFixedWidth(60)
        self.cellprob_threshold_edit.textChanged.connect(self._on_cellprob_threshold_changed)
        seg_layout.addWidget(self.cellprob_threshold_edit, 3, 1)
        
        # Extra parameters
        extra_label = QLabel("Extra Parameters:")
        seg_layout.addWidget(extra_label, 4, 0, 1, 2)
        
        self.extra_params_edit = ExtraParamsTextEdit()
        self.extra_params_edit.setPlaceholderText("Enter key=value pairs, one per line\nSupports: bool, int, float, str, dict, list\nExamples:\ndo_3D=True\nmin_size=15\nnorm={'a': 2, 'b': 6}\nchannels=[0, 1, 2]\nPress Ctrl+Enter or click elsewhere to save")
        self.extra_params_edit.setMaximumHeight(80)
        self.extra_params_edit.params_changed.connect(self._on_extra_params_changed)
        seg_layout.addWidget(self.extra_params_edit, 5, 0, 1, 2)
        
        control_layout.addWidget(seg_group)
        
        # Populate extra parameters text area with existing settings
        self._populate_extra_params()
        
        # Run button
        self.run_btn = QPushButton("Run Segmentation")
        self.run_btn.clicked.connect(self._on_run_segmentation)
        control_layout.addWidget(self.run_btn)

        # Log display area
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMinimumHeight(60)
        self.log_display.setStyleSheet("font-size: 11px; background: #f7f7f7; color: #333; border: 1px solid #ccc;")
        control_layout.addWidget(self.log_display)

        # Quit button
        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(lambda: self.result_signal.emit("quit"))
        control_layout.addWidget(self.quit_btn)

        control_layout.addStretch()

        # Image display (right)
        image_panel = QFrame()
        image_panel.setFrameShape(QFrame.Shape.StyledPanel)
        image_layout = QVBoxLayout(image_panel)
        image_layout.setSpacing(10)
        image_layout.setContentsMargins(10, 10, 10, 10)

        self.image_label = QLabel("Image will appear here", self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setScaledContents(False)
        image_layout.addWidget(self.image_label)

        layout.addWidget(control_panel, 1)
        layout.addWidget(image_panel, 3)

    def _log(self, message: str) -> None:
        """Append a message to the log display area."""
        self.log_display.append(message)

    def _update_history_display(self) -> None:
        """Update the coordinate history display."""
        if self.image_collector is None or not hasattr(self, 'history_list'):
            return
            
        self.history_list.clear()
        # Display coordinates as they come (not sorted)
        for coord in self.image_collector.history:
            # Display as xy tuple but keep full StageCoord
            x, y = coord.xy
            coord_text = f"({x:.1f}, {y:.1f})" if x is not None and y is not None else "Unknown"
            item_widget = QListWidgetItem(coord_text)
            item_widget.setData(1, coord)  # Store the full StageCoord as item data
            self.history_list.addItem(item_widget)
        
        # Select the last entry by default
        if self.history_list.count() > 0:
            self.history_list.setCurrentRow(self.history_list.count() - 1)

    def _load_random_image(self) -> None:
        """Load a random image using ImageCollector."""
        if self.image_collector is None:
            self._log("No ImageCollector available")
            return
            
        try:
            self.image = self.image_collector.get_image()
            self._update_history_display()
            self._auto_scale()
            self._run_segmentation_with_current_settings()
            self._log("Random image loaded successfully")
        except Exception as e:
            self._log(f"Failed to load random image: {str(e)}")

    def _on_load_selected_coord(self) -> None:
        """Load image from selected coordinate."""
        if self.image_collector is None or not hasattr(self, 'history_list'):
            self._log("No ImageCollector or history available")
            return
            
        current_item = self.history_list.currentItem()
        if current_item is None:
            self._log("No coordinate selected")
            return
            
        try:
            coord = current_item.data(1)  # Get the stored StageCoord
            self.image = self.image_collector.get_image(coord)
            self._update_history_display()
            self._auto_scale()
            self._run_segmentation_with_current_settings()
            x, y = coord.xy
            self._log(f"Loaded image from coordinate ({x:.1f}, {y:.1f})")
        except Exception as e:
            self._log(f"Failed to load selected coordinate: {str(e)}")

    def _get_cellpose_metadata(self):
        """Retrieve Cellpose metadata from server"""
        try:
            metadata = cellpose_metadata_client()
            return metadata
        except Exception as e:
            print(f"Warning: Could not retrieve Cellpose metadata: {e}")
            # Fallback metadata
            return {
                "model_names": ["cyto3", "cyto2", "cyto", "nuclei"],
                "version": "unknown"
            }

    def _create_mask_overlay(self):
        """Create a colorized mask overlay with distinct colors for each mask"""
        if self.seg_mask is None:
            self.mask_overlay_rgb = None
            return
            
        # Create a colormap for different masks
        unique_masks = np.unique(self.seg_mask)
        unique_masks = unique_masks[unique_masks > 0]  # Remove background
        
        if len(unique_masks) == 0:
            self.mask_overlay_rgb = None
            return
            
        # Create RGB overlay
        h, w = self.seg_mask.shape
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Generate distinct colors using HSV color space
        colors = []
        for i in range(len(unique_masks)):
            hue = (i * 137.5) % 360  # Golden angle for good distribution
            sat = 0.8  # High saturation for distinct colors
            val = 0.9  # High value for bright colors
            rgb = colorsys.hsv_to_rgb(hue/360, sat, val)
            colors.append([int(c * 255) for c in rgb])
        
        # Apply colors to masks
        for i, mask_id in enumerate(unique_masks):
            mask_pixels = self.seg_mask == mask_id
            overlay[mask_pixels] = colors[i % len(colors)]
            
        self.mask_overlay_rgb = overlay

    def keyPressEvent(self, a0: QKeyEvent | None):
        """Handle keyboard shortcuts"""
        if a0 and a0.key() == Qt.Key.Key_X:
            # Toggle mask overlay with 'X' key
            current_state = self.mask_overlay_cb.isChecked()
            self.mask_overlay_cb.setChecked(not current_state)
        else:
            super().keyPressEvent(a0)

    def _on_display_change(self):
        """Handle display parameter changes (min, max, brightness, contrast)"""
        # Update display parameters
        self.display_min = self.min_slider.value()
        self.display_max = self.max_slider.value()
        self.brightness = self.brightness_slider.value()
        self.contrast = self.contrast_slider.value()
        
        # Update labels
        self.min_label.setText(str(self.display_min))
        self.max_label.setText(str(self.display_max))
        self.brightness_label.setText(str(self.brightness))
        self.contrast_label.setText(str(self.contrast))
        
        # Update display
        self._update_image_display()
    
    def _on_image_path_entered(self):
        """Load image when user pastes path and presses Enter"""
        img_path = self.image_path_edit.text().strip()
        if not img_path:
            self._log("No path entered.")
            self.loaded_image_path_label.setText("")
            return
        if not os.path.exists(img_path):
            self._log(f"File not found: {os.path.basename(img_path)}")
            self.loaded_image_path_label.setText("")
            return
        try:
            img = imread(img_path)
            self.image = img
            self.seg_mask = None
            self.mask_overlay_rgb = None
            self._create_mask_overlay()
            self._auto_scale()
            self._log(f"Loaded: {os.path.basename(img_path)}")
            self.loaded_image_path_label.setText("")
            self.image_path_edit.setText(img_path)
            self._run_segmentation_with_current_settings()
        except Exception as e:
            self._log(f"Error loading image: {str(e)}")
            self.loaded_image_path_label.setText("")
    
    def _auto_scale(self):
        """Auto-scale display based on image percentiles (like ImageJ auto-scale)"""
        if self.image is not None:
            # Find 0.1% and 99.9% percentiles for robust auto-scaling
            vmin = np.percentile(self.image, 0.1)
            vmax = np.percentile(self.image, 99.9)
            
            # Update sliders
            self.min_slider.setRange(0, int(vmax))
            self.max_slider.setRange(int(vmin), 65535)
            self.min_slider.setValue(int(vmin))
            self.max_slider.setValue(int(vmax))
            
            # Reset brightness and contrast to neutral
            self.brightness_slider.setValue(50)
            self.contrast_slider.setValue(50)
            
            # Update display
            self._on_display_change()
    
    def _toggle_mask_overlay(self, checked):
        """Toggle mask overlay display"""
        self.show_mask_overlay = checked
        self._update_image_display()
    
    def _on_model_changed(self, text):
        """Handle model selection change"""
        self.settings.model_type = text
        self._save_settings()
    
    def _on_diameter_changed(self, text):
        """Handle diameter change"""
        if text:
            try:
                self.settings.diameter = int(text)
                self._save_settings()
            except ValueError:
                pass  # Keep previous value if invalid
    
    def _on_flow_threshold_changed(self, text):
        """Handle flow threshold change"""
        if text:
            try:
                self.settings.flow_threshold = float(text)
                self._save_settings()
            except ValueError:
                pass  # Keep previous value if invalid
    
    def _on_cellprob_threshold_changed(self, text):
        """Handle cellprob threshold change"""
        if text:
            try:
                self.settings.cellprob_threshold = float(text)
                self._save_settings()
            except ValueError:
                pass  # Keep previous value if invalid
    
    def _on_extra_params_changed(self):
        """Handle extra parameters change"""
        self._parse_and_save_extra_params()
    
    def _populate_extra_params(self):
        """Populate the extra parameters text area with existing settings"""
        if self.settings.extra_settings:
            lines = []
            for key, value in self.settings.extra_settings.items():
                # Format complex types properly
                if isinstance(value, (dict, list, tuple)):
                    # Use repr() to get proper Python representation
                    formatted_value = repr(value)
                else:
                    formatted_value = str(value)
                lines.append(f"{key}={formatted_value}")
            self.extra_params_edit.setPlainText("\n".join(lines))
    
    def _parse_and_save_extra_params(self):
        """Parse extra parameters from text area and save to settings"""
        extra_text = self.extra_params_edit.toPlainText().strip()
        extra_params = {}
        
        if extra_text:
            for _, line in enumerate(extra_text.split('\n'), 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                    
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if not key:  # Skip lines with empty keys
                        continue
                    
                    # Try to evaluate as Python literal first (handles dict, list, tuple, etc.)
                    try:
                        # Use ast.literal_eval for safe evaluation of Python literals
                        parsed_value = ast.literal_eval(value)
                        extra_params[key] = parsed_value
                    except (ValueError, SyntaxError):
                        # If literal_eval fails, try simple type conversions
                        try:
                            if value.lower() in ('true', 'false'):
                                extra_params[key] = value.lower() == 'true'
                            elif value.replace('.', '').replace('-', '').isdigit():
                                if '.' in value:
                                    extra_params[key] = float(value)
                                else:
                                    extra_params[key] = int(value)
                            else:
                                extra_params[key] = value  # Keep as string
                        except ValueError:
                            extra_params[key] = value  # Keep as string if all conversions fail
        
        self.settings.extra_settings = extra_params
        self._save_settings()
    
    def _save_settings(self) -> None:
        pass  # No file saving, settings object is updated in-place
    
    def _run_segmentation_with_current_settings(self) -> None:
        """Run segmentation on self.image using current settings and update mask/display."""
        if self.image is None:
            self._log("No image loaded! Please load an image first.")
            return
        try:
            # Ensure extra parameters are up to date
            self._parse_and_save_extra_params()
            cellpose_settings = self.settings.to_backend_dict()
            mask = optimise_segmentation(self.image, cellpose_settings)
            self.seg_mask = mask
            self._create_mask_overlay()
            self._update_image_display()
            self._log("Segmentation completed successfully!")
        except Exception as e:
            self._log(f"Segmentation failed: {str(e)}")
            print(f"Segmentation error: {e}")
    
    def _on_run_segmentation(self):
        """Run segmentation on the current image using current settings"""
        # Update the run button to show it's processing
        self.run_btn.setText("Running...")
        self.run_btn.setEnabled(False)
        QApplication.processEvents()
        self._run_segmentation_with_current_settings()
        # Reset the run button
        self.run_btn.setText("Run Segmentation")
        self.run_btn.setEnabled(True)
    
    def _on_load_image(self):
        """Handle loading an image from the file system"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilters([
            "Image files (*.tif *.tiff *.png *.jpg *.jpeg *.bmp *.nd2)",
            "TIFF files (*.tif *.tiff)",
            "ND2 files (*.nd2)",
            "All files (*)"
        ])
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                img_path = selected_files[0]
                self._log(f"Loading: {os.path.basename(img_path)}")
                self.loaded_image_path_label.setText("")
                self.image_path_edit.setText(img_path)
                try:
                    img = imread(img_path)
                    self.image = img
                    self.seg_mask = None  # Clear any existing mask
                    self.mask_overlay_rgb = None  # Clear overlay
                    self._create_mask_overlay()
                    self._auto_scale()
                    self._log(f"Loaded: {os.path.basename(img_path)}")
                    self._run_segmentation_with_current_settings()
                except Exception as e:
                    try:
                        # Fallback to QImage for standard formats
                        qimg = QImage(img_path)
                        if not qimg.isNull():
                            img = self._qimage_to_numpy(qimg)
                            self.image = img
                            self.seg_mask = None
                            self.mask_overlay_rgb = None
                            self._create_mask_overlay()
                            self._auto_scale()
                            self._log(f"Loaded: {os.path.basename(img_path)}")
                            self._run_segmentation_with_current_settings()
                        else:
                            self._log(f"Failed to load: {os.path.basename(img_path)}")
                    except Exception as e2:
                        self._log(f"Error: {str(e)}")
    
    def _qimage_to_numpy(self, qimg):
        """Convert QImage to numpy array (for fallback image loading)"""
        # Convert to RGB format
        qimg = qimg.convertToFormat(QImage.Format.Format_RGB888)
        width = qimg.width()
        height = qimg.height()
        ptr = qimg.bits()
        ptr.setsize(qimg.byteCount())
        arr = np.array(ptr, dtype=np.uint8).reshape((height, width, 3))
        # Convert to grayscale for consistency with typical microscopy images
        gray = np.dot(arr[...,:3], [0.2989, 0.5870, 0.1140])
        return gray.astype(np.uint16) * 257  # Scale to 16-bit range
    
    def get_segmentation_params(self):
        """Get segmentation parameters from the control panel (legacy method)"""
        params = {
            'model_type': self.settings.model_type,
            'diameter': self.settings.diameter,
            'flow_threshold': self.settings.flow_threshold,
            'cellprob_threshold': self.settings.cellprob_threshold
        }
        
        # Parse extra parameters
        extra_text = self.extra_params_edit.toPlainText().strip()
        if extra_text:
            for line in extra_text.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Try to convert to appropriate type
                    try:
                        if value.lower() in ('true', 'false'):
                            params[key] = value.lower() == 'true'
                        elif '.' in value:
                            params[key] = float(value)
                        else:
                            params[key] = int(value)
                    except ValueError:
                        params[key] = value  # Keep as string if conversion fails
        
        return params
    
    def get_settings(self):
        """Get the ServerSettings object with current values"""
        # Extra parameters are already parsed and saved in real-time
        # Just ensure they're up to date
        self._parse_and_save_extra_params()
        return self.settings

    def _convert_to_pixmap(self, img_array):
        """Convert numpy array to QPixmap"""
        if len(img_array.shape) == 2:  # Grayscale
            if img_array.dtype == np.uint16:
                # Convert 16-bit to 8-bit for Qt display
                img_8bit = (img_array / 65535 * 255).astype(np.uint8)
                height, width = img_8bit.shape
                bytes_per_line = width
                q_image = QImage(img_8bit.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
            else:  # uint8
                height, width = img_array.shape
                bytes_per_line = width
                q_image = QImage(img_array.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
        else:  # RGB
            height, width, channel = img_array.shape
            bytes_per_line = 3 * width
            q_image = QImage(img_array.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(q_image)
        
    def _update_image_display(self):
        if hasattr(self, 'image_label'):
            if self.image is not None:
                # Apply display adjustments (min/max, brightness, contrast) to original image
                img = self.image.astype(np.float32)
                
                # Apply min/max scaling
                vmin = self.display_min
                vmax = self.display_max
                if vmax > vmin:
                    img = np.clip((img - vmin) / (vmax - vmin), 0, 1)
                else:
                    img = np.clip(img / 65535, 0, 1)
                
                # Apply brightness (shift)
                brightness_factor = (self.brightness - 50) / 50  # -1 to 1
                img = np.clip(img + brightness_factor * 0.3, 0, 1)
                
                # Apply contrast (scale around 0.5)
                contrast_factor = self.contrast / 50  # 0 to 2
                img = np.clip((img - 0.5) * contrast_factor + 0.5, 0, 1)
                
                # Keep in 16-bit for better quality
                img_display = (img * 65535).astype(np.uint16)
                
                # Apply mask overlay if enabled (using pre-computed overlay)
                if self.mask_overlay_rgb is not None and getattr(self, 'show_mask_overlay', True):
                    # Convert 16-bit image to 8-bit for blending
                    img_8bit = (img * 255).astype(np.uint8)
                    
                    # Create alpha blending: 70% original image + 30% mask overlay
                    alpha = 0.3
                    if len(img_8bit.shape) == 2:  # Grayscale
                        # Convert grayscale to RGB for blending
                        img_rgb = np.stack([img_8bit, img_8bit, img_8bit], axis=2)
                    else:
                        img_rgb = img_8bit
                        
                    # Only blend where masks exist (non-zero overlay)
                    mask_exists = np.any(self.mask_overlay_rgb > 0, axis=2)
                    blended = img_rgb.copy()
                    blended[mask_exists] = ((1 - alpha) * img_rgb[mask_exists] + 
                                          alpha * self.mask_overlay_rgb[mask_exists]).astype(np.uint8)
                    
                    pixmap = self._convert_to_pixmap(blended)
                else:
                    pixmap = self._convert_to_pixmap(img_display)
                
                self.original_pixmap = pixmap
                self._update_image_scale()
            else:
                self.image_label.setText("No image available")

class TuneSegWindow(QMainWindow):
    def __init__(self, settings: PipelineSettings, img: Optional[NDArray] = None, mask: Optional[NDArray] = None, dish_grid=None, a1_manager=None):
        super().__init__()
        self.widget = TuneSegWidget(settings, img, mask, dish_grid, a1_manager)
        self.setCentralWidget(self.widget)
        self.setWindowTitle("Segmentation Tuning")
        self.setMinimumSize(600, 400)
        self.resize(1800, 1400)
        self.widget.result_signal.connect(self._handle_result)
        self.result = None
        self.settings = None

    def _handle_result(self, result: str) -> None:
        self.result = result
        if result == "quit":
            # Get the updated server settings when quit is pressed
            self.settings = self.widget.get_settings()
        self.close()

    def closeEvent(self, a0) -> None:
        if a0 is not None:
            a0.accept()


def launch_tune_seg_gui(settings: PipelineSettings, img: Optional[NDArray] = None, mask: Optional[NDArray] = None, dish_grid: dict[str, dict[int, StageCoord]] | None =None, a1_manager: A1Manager | None = None) -> ServerSettings | None:
    """
    Launch the segmentation tuning GUI.
    
    Args:
        settings: PipelineSettings object containing ServerSettings to be updated
        img: Optional numpy array of the image
        mask: Optional numpy array of the mask
        dish_grid: Optional dish grid for ImageCollector
        a1_manager: Optional A1Manager for ImageCollector
    Returns:
        Updated ServerSettings object
    """
    app = QApplication(sys.argv)
    window = TuneSegWindow(settings, img, mask, dish_grid, a1_manager)
    window.show()
    app.exec()
    return window.settings


# Example usage for testing GUI frame
if __name__ == "__main__":
    from pathlib import Path
    from gem_screening.settings.models import LoggingSettings, AcquisitionSettings, DishSettings, MeasureSettings, ControlSettings, StimSettings
    
    # Create a default PipelineSettings object for testing
    pipeline_settings = PipelineSettings(
        savedir="/tmp",
        savedir_name="test",
        logging_settings=LoggingSettings(),
        acquisition_settings=AcquisitionSettings(),
        dish_settings=DishSettings(),
        measure_settings=MeasureSettings(),
        server_settings=ServerSettings(),
        control_settings=ControlSettings(),
        stim_settings=StimSettings()
    )
    
    print("\nOriginal Server Settings:")
    print(pipeline_settings.server_settings.model_dump())
    
    img_path = Path("/media/ben/Analysis/Python/CellTinder/ImagesTest/A1/A1_images/A1_P4_refseg_1.tif")
    img = imread(img_path) if img_path.exists() else None

    updated_settings = launch_tune_seg_gui(pipeline_settings, img=img)
    if updated_settings:
        print("\nUpdated Server Settings:")
        print(updated_settings.model_dump())
