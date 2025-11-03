import sys

import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
                             QPushButton, QSizePolicy, QFrame, QSlider, QCheckBox, QLineEdit, 
                             QTextEdit, QGroupBox, QGridLayout, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage, QDoubleValidator, QIntValidator, QKeyEvent

from gem_screening.utils.client.service import cellpose_metadata_client


class TuneSegWidget(QWidget):
    result_signal = pyqtSignal(str)
    def __init__(self, img=None, mask=None, parent=None):
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
        
        # Initialize Cellpose metadata
        self.cellpose_metadata = self._get_cellpose_metadata()
        
        self._setup_ui()
        if img is not None and mask is not None:
            self._create_mask_overlay()  # Pre-compute mask overlay
            self._auto_scale()  # Auto-scale on launch
        elif img is not None:
            self._auto_scale()  # Auto-scale even without mask

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
        self.mask_overlay_cb = QCheckBox("Show mask overlay")
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
        # Set default to 'cyto3' if available
        if "cyto3" in model_names:
            self.model_combo.setCurrentText("cyto3")
        seg_layout.addWidget(self.model_combo, 0, 1)
        
        # Diameter
        diameter_label = QLabel("Diameter:")
        seg_layout.addWidget(diameter_label, 1, 0)
        self.diameter_edit = QLineEdit("40")
        self.diameter_edit.setValidator(QIntValidator(1, 1000))
        self.diameter_edit.setFixedWidth(60)
        seg_layout.addWidget(self.diameter_edit, 1, 1)
        
        # Flow threshold
        flow_label = QLabel("Flow Threshold:")
        seg_layout.addWidget(flow_label, 2, 0)
        self.flow_threshold_edit = QLineEdit("0.4")
        self.flow_threshold_edit.setValidator(QDoubleValidator(0.0, 10.0, 2))
        self.flow_threshold_edit.setFixedWidth(60)
        seg_layout.addWidget(self.flow_threshold_edit, 2, 1)
        
        # Cellprob threshold
        cellprob_label = QLabel("Cellprob Threshold:")
        seg_layout.addWidget(cellprob_label, 3, 0)
        self.cellprob_threshold_edit = QLineEdit("0.0")
        self.cellprob_threshold_edit.setValidator(QDoubleValidator(-10.0, 10.0, 2))
        self.cellprob_threshold_edit.setFixedWidth(60)
        seg_layout.addWidget(self.cellprob_threshold_edit, 3, 1)
        
        # Extra parameters
        extra_label = QLabel("Extra Parameters:")
        seg_layout.addWidget(extra_label, 4, 0, 1, 2)
        
        self.extra_params_edit = QTextEdit()
        self.extra_params_edit.setPlaceholderText("Enter key=value pairs, one per line\nExample:\ndo_3D=True\nmin_size=15")
        self.extra_params_edit.setMaximumHeight(80)
        seg_layout.addWidget(self.extra_params_edit, 5, 0, 1, 2)
        
        control_layout.addWidget(seg_group)
        
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
        import colorsys
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
    
    def get_segmentation_params(self):
        """Get segmentation parameters from the control panel"""
        params = {
            'model_type': self.model_combo.currentText(),
            'diameter': int(self.diameter_edit.text()) if self.diameter_edit.text() else 40,
            'flow_threshold': float(self.flow_threshold_edit.text()),
            'cellprob_threshold': float(self.cellprob_threshold_edit.text())
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
    def __init__(self, img=None, mask=None):
        super().__init__()
        self.widget = TuneSegWidget(img, mask)
        self.setCentralWidget(self.widget)
        self.setWindowTitle("Segmentation Tuning")
        self.setMinimumSize(600, 400)
        self.resize(1800, 1400)
        self.widget.result_signal.connect(self._handle_result)
        self.result = None

    def _handle_result(self, result):
        self.result = result
        self.close()

    def closeEvent(self, a0):
        if a0 is not None:
            a0.accept()


# Example usage for testing GUI frame
if __name__ == "__main__":
    from tifffile import imread
    # Dummy image and mask arrays
    img = imread("/media/ben/Analysis/Python/Docker_mount/Test_images/nd2/Run4/c4z1t91v1_s1/Images_Registered/GFP_s01_f0001_z0001.tif")
    mask = imread("/media/ben/Analysis/Python/Docker_mount/Test_images/nd2/Run4/c4z1t91v1_s1/Masks_Cellpose/GFP_s01_f0001_z0001.tif")
    app = QApplication(sys.argv)
    window = TuneSegWindow(img, mask)
    window.show()
    sys.exit(app.exec())
