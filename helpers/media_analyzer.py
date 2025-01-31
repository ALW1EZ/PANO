import sys
import cv2
import numpy as np
from PySide6.QtWidgets import (QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QSlider, QSpinBox, QDoubleSpinBox, QGroupBox,
                             QCheckBox, QScrollArea, QTabWidget, QGridLayout)
from PySide6.QtCore import Qt, QSize, Signal, QTimer, QPoint
from PySide6.QtGui import QImage, QPixmap, QResizeEvent, QPainter, QPen
from .base import BaseHelper

class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(QSize(400, 400))
        self.setAlignment(Qt.AlignCenter)
        self._pixmap = None
        self._original_pixmap = None
        self.draw_mode = False
        self.start_pos = None
        self.current_pos = None
        self.setMouseTracking(True)

    def setPixmap(self, pixmap):
        if isinstance(pixmap, QPixmap):
            self._original_pixmap = pixmap
            self._update_scaled_pixmap()
        else:
            QLabel.setPixmap(self, pixmap)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _convert_pos_to_pixmap(self, pos):
        """Convert mouse position to pixmap coordinates"""
        if not self._pixmap:
            return None
            
        # Get the pixmap and label sizes
        pixmap_size = self._pixmap.size()
        label_size = self.size()
        
        # Calculate scaling
        scale = min(label_size.width() / pixmap_size.width(),
                   label_size.height() / pixmap_size.height())
        
        # Calculate image position within label (centered)
        scaled_width = pixmap_size.width() * scale
        scaled_height = pixmap_size.height() * scale
        x_offset = (label_size.width() - scaled_width) / 2
        y_offset = (label_size.height() - scaled_height) / 2
        
        # Convert position
        x = (pos.x() - x_offset) / scale
        y = (pos.y() - y_offset) / scale
        
        # Check if position is within image bounds
        if 0 <= x < pixmap_size.width() and 0 <= y < pixmap_size.height():
            return QPoint(int(x), int(y))
        return None

    def _update_scaled_pixmap(self):
        if self._original_pixmap:
            # Get the label size
            label_size = self.size()
            
            # Scale the original pixmap
            scaled = self._original_pixmap.scaled(
                label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._pixmap = scaled
            
            if self.draw_mode and self.start_pos and self.current_pos:
                temp_pixmap = scaled.copy()
                painter = QPainter(temp_pixmap)
                painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
                
                # Calculate scaling and offset for drawing
                pixmap_size = scaled.size()
                scale = min(label_size.width() / self._original_pixmap.width(),
                          label_size.height() / self._original_pixmap.height())
                x_offset = (label_size.width() - pixmap_size.width()) / 2
                y_offset = (label_size.height() - pixmap_size.height()) / 2
                
                # Convert points to scaled coordinates
                start_scaled = QPoint(
                    int(self.start_pos.x() * scale + x_offset),
                    int(self.start_pos.y() * scale + y_offset)
                )
                current_scaled = QPoint(
                    int(self.current_pos.x() * scale + x_offset),
                    int(self.current_pos.y() * scale + y_offset)
                )
                
                # Draw line
                painter.drawLine(start_scaled, current_scaled)
                
                # Draw arrow head
                angle = np.arctan2(current_scaled.y() - start_scaled.y(),
                                 current_scaled.x() - start_scaled.x())
                arrow_size = 20
                arrow_angle = np.pi/6
                
                p1 = QPoint(
                    int(current_scaled.x() - arrow_size * np.cos(angle + arrow_angle)),
                    int(current_scaled.y() - arrow_size * np.sin(angle + arrow_angle))
                )
                p2 = QPoint(
                    int(current_scaled.x() - arrow_size * np.cos(angle - arrow_angle)),
                    int(current_scaled.y() - arrow_size * np.sin(angle - arrow_angle))
                )
                
                painter.drawLine(current_scaled, p1)
                painter.drawLine(current_scaled, p2)
                
                painter.end()
                QLabel.setPixmap(self, temp_pixmap)
            else:
                QLabel.setPixmap(self, scaled)

    def mousePressEvent(self, event):
        if self.draw_mode and event.button() == Qt.LeftButton:
            pos = self._convert_pos_to_pixmap(event.position().toPoint())
            if pos is not None:
                self.start_pos = pos
                self.current_pos = pos
                self._update_scaled_pixmap()

    def mouseMoveEvent(self, event):
        if self.draw_mode and event.buttons() & Qt.LeftButton and self.start_pos:
            pos = self._convert_pos_to_pixmap(event.position().toPoint())
            if pos is not None:
                self.current_pos = pos
                self._update_scaled_pixmap()

    def mouseReleaseEvent(self, event):
        if self.draw_mode and event.button() == Qt.LeftButton and self.start_pos:
            pos = self._convert_pos_to_pixmap(event.position().toPoint())
            if pos is not None:
                self.current_pos = pos
                dx = self.current_pos.x() - self.start_pos.x()
                dy = self.current_pos.y() - self.start_pos.y()
                # Calculate angle in the correct direction (clockwise from horizontal)
                angle = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
                # Find the DeblurTab parent and update angle
                parent = self.parent()
                while parent and not isinstance(parent, DeblurTab):
                    parent = parent.parent()
                if parent:
                    parent.set_angle(angle)
            self.draw_mode = False
            self.start_pos = None
            self.current_pos = None
            self._update_scaled_pixmap()

class DeblurTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        layout = QHBoxLayout(self)
        
        # Create controls panel with scroll area
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setMaximumWidth(400)
        controls_panel = QWidget()
        controls_layout = QVBoxLayout(controls_panel)
        
        # File controls group
        file_group = QGroupBox("File Controls")
        file_layout = QVBoxLayout(file_group)
        self.upload_btn = QPushButton("Upload Image")
        self.upload_btn.clicked.connect(self.upload_image)
        self.save_btn = QPushButton("Save Result")
        self.save_btn.clicked.connect(self.save_image)
        self.save_btn.setEnabled(False)
        file_layout.addWidget(self.upload_btn)
        file_layout.addWidget(self.save_btn)
        controls_layout.addWidget(file_group)
        
        # Motion Blur Parameters group
        motion_group = QGroupBox("Motion Blur Parameters")
        motion_layout = QVBoxLayout(motion_group)
        
        # Add angle control with slider and draw button
        angle_widget = QWidget()
        angle_layout = QHBoxLayout(angle_widget)
        angle_label = QLabel("Angle (°):")
        self.draw_angle_btn = QPushButton("Draw")
        self.draw_angle_btn.setCheckable(True)
        self.draw_angle_btn.clicked.connect(self.toggle_angle_draw)
        self.angle_spin = QSpinBox()
        self.angle_spin.setRange(0, 360)
        self.angle_spin.setValue(45)
        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(0, 360)
        self.angle_slider.setValue(45)
        self.angle_spin.valueChanged.connect(self.angle_slider.setValue)
        self.angle_slider.valueChanged.connect(self.angle_spin.setValue)
        self.angle_slider.valueChanged.connect(self.update_kernel_preview)
        angle_layout.addWidget(angle_label)
        angle_layout.addWidget(self.draw_angle_btn)
        angle_layout.addWidget(self.angle_slider)
        angle_layout.addWidget(self.angle_spin)
        motion_layout.addWidget(angle_widget)
        
        # Add length control with slider
        length_widget = QWidget()
        length_layout = QHBoxLayout(length_widget)
        length_label = QLabel("Length:")
        self.length_spin = QSpinBox()
        self.length_spin.setRange(1, 200)
        self.length_spin.setValue(20)
        self.length_slider = QSlider(Qt.Horizontal)
        self.length_slider.setRange(1, 200)
        self.length_slider.setValue(20)
        self.length_spin.valueChanged.connect(self.length_slider.setValue)
        self.length_slider.valueChanged.connect(self.length_spin.setValue)
        self.length_slider.valueChanged.connect(self.update_kernel_preview)
        length_layout.addWidget(length_label)
        length_layout.addWidget(self.length_slider)
        length_layout.addWidget(self.length_spin)
        motion_layout.addWidget(length_widget)
        
        # Add kernel thickness
        thickness_widget = QWidget()
        thickness_layout = QHBoxLayout(thickness_widget)
        thickness_label = QLabel("Thickness:")
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setRange(0.1, 5.0)
        self.thickness_spin.setValue(1.0)
        self.thickness_spin.setSingleStep(0.1)
        self.thickness_spin.valueChanged.connect(self.update_kernel_preview)
        thickness_layout.addWidget(thickness_label)
        thickness_layout.addWidget(self.thickness_spin)
        motion_layout.addWidget(thickness_widget)
        
        # Add kernel preview
        self.kernel_label = QLabel()
        self.kernel_label.setMinimumSize(QSize(150, 150))
        self.kernel_label.setAlignment(Qt.AlignCenter)
        motion_layout.addWidget(self.kernel_label)
        controls_layout.addWidget(motion_group)
        
        # Wiener Parameters group
        wiener_group = QGroupBox("Wiener Deconvolution Parameters")
        wiener_layout = QVBoxLayout(wiener_group)
        
        # Add SNR control with slider
        snr_widget = QWidget()
        snr_layout = QHBoxLayout(snr_widget)
        snr_label = QLabel("SNR:")
        self.snr_spin = QDoubleSpinBox()
        self.snr_spin.setRange(0.1, 200.0)
        self.snr_spin.setValue(40.0)
        self.snr_spin.setSingleStep(0.1)
        self.snr_slider = QSlider(Qt.Horizontal)
        self.snr_slider.setRange(1, 2000)
        self.snr_slider.setValue(400)
        self.snr_spin.valueChanged.connect(lambda x: self.snr_slider.setValue(int(x * 10)))
        self.snr_slider.valueChanged.connect(lambda x: self.snr_spin.setValue(x / 10))
        snr_layout.addWidget(snr_label)
        snr_layout.addWidget(self.snr_slider)
        snr_layout.addWidget(self.snr_spin)
        wiener_layout.addWidget(snr_widget)
        
        # Add regularization parameter
        reg_widget = QWidget()
        reg_layout = QHBoxLayout(reg_widget)
        reg_label = QLabel("Regularization:")
        self.reg_spin = QDoubleSpinBox()
        self.reg_spin.setRange(0.0001, 1.0)
        self.reg_spin.setValue(0.01)
        self.reg_spin.setSingleStep(0.0001)
        self.reg_spin.setDecimals(4)
        reg_layout.addWidget(reg_label)
        reg_layout.addWidget(self.reg_spin)
        wiener_layout.addWidget(reg_widget)
        
        # Add advanced options
        self.edge_padding = QCheckBox("Edge Padding")
        self.edge_padding.setChecked(True)
        wiener_layout.addWidget(self.edge_padding)
        
        self.auto_snr = QCheckBox("Auto SNR")
        self.auto_snr.setChecked(False)
        wiener_layout.addWidget(self.auto_snr)
        
        controls_layout.addWidget(wiener_group)
        
        # Enhancement Parameters group
        enhance_group = QGroupBox("Enhancement Parameters")
        enhance_layout = QVBoxLayout(enhance_group)
        
        # Add denoise strength with slider
        denoise_widget = QWidget()
        denoise_layout = QHBoxLayout(denoise_widget)
        denoise_label = QLabel("Denoise:")
        self.denoise_spin = QDoubleSpinBox()
        self.denoise_spin.setRange(0, 1)
        self.denoise_spin.setValue(0.5)
        self.denoise_spin.setSingleStep(0.1)
        self.denoise_slider = QSlider(Qt.Horizontal)
        self.denoise_slider.setRange(0, 100)
        self.denoise_slider.setValue(50)
        self.denoise_spin.valueChanged.connect(lambda x: self.denoise_slider.setValue(int(x * 100)))
        self.denoise_slider.valueChanged.connect(lambda x: self.denoise_spin.setValue(x / 100))
        denoise_layout.addWidget(denoise_label)
        denoise_layout.addWidget(self.denoise_slider)
        denoise_layout.addWidget(self.denoise_spin)
        enhance_layout.addWidget(denoise_widget)
        
        # Add sharpness control with slider
        sharp_widget = QWidget()
        sharp_layout = QHBoxLayout(sharp_widget)
        sharp_label = QLabel("Sharpness:")
        self.sharp_spin = QDoubleSpinBox()
        self.sharp_spin.setRange(0, 5)
        self.sharp_spin.setValue(1.0)
        self.sharp_spin.setSingleStep(0.1)
        self.sharp_slider = QSlider(Qt.Horizontal)
        self.sharp_slider.setRange(0, 500)
        self.sharp_slider.setValue(100)
        self.sharp_spin.valueChanged.connect(lambda x: self.sharp_slider.setValue(int(x * 100)))
        self.sharp_slider.valueChanged.connect(lambda x: self.sharp_spin.setValue(x / 100))
        sharp_layout.addWidget(sharp_label)
        sharp_layout.addWidget(self.sharp_slider)
        sharp_layout.addWidget(self.sharp_spin)
        enhance_layout.addWidget(sharp_widget)
        
        # Add contrast enhancement
        contrast_widget = QWidget()
        contrast_layout = QHBoxLayout(contrast_widget)
        contrast_label = QLabel("Contrast:")
        self.contrast_spin = QDoubleSpinBox()
        self.contrast_spin.setRange(0.1, 3.0)
        self.contrast_spin.setValue(1.0)
        self.contrast_spin.setSingleStep(0.1)
        contrast_layout.addWidget(contrast_label)
        contrast_layout.addWidget(self.contrast_spin)
        enhance_layout.addWidget(contrast_widget)
        
        controls_layout.addWidget(enhance_group)
        
        # Add live preview checkbox
        self.live_preview = QCheckBox("Live Preview")
        self.live_preview.setChecked(True)
        controls_layout.addWidget(self.live_preview)
        
        # Add process button
        self.deblur_btn = QPushButton("Process Image")
        self.deblur_btn.clicked.connect(self.process_image)
        self.deblur_btn.setEnabled(False)
        controls_layout.addWidget(self.deblur_btn)
        
        # Connect all parameter changes to trigger processing
        for widget in [self.angle_slider, self.length_slider, self.snr_slider,
                      self.denoise_slider, self.sharp_slider, self.thickness_spin,
                      self.reg_spin, self.contrast_spin]:
            widget.valueChanged.connect(self.parameter_changed)
        
        controls_layout.addStretch()
        controls_scroll.setWidget(controls_panel)
        layout.addWidget(controls_scroll)
        
        # Create image display area
        display_widget = QWidget()
        display_layout = QHBoxLayout(display_widget)
        
        # Original image display
        self.original_label = ImageLabel()
        self.original_label.setText("Original Image")
        display_layout.addWidget(self.original_label)
        
        # Processed image display
        self.processed_label = ImageLabel()
        self.processed_label.setText("Processed Image")
        display_layout.addWidget(self.processed_label)
        
        layout.addWidget(display_widget)
        
        # Initialize processing variables
        self.original_image = None
        self.processed_image = None
        self.kernel_preview = None
        self.processing_timer = QTimer()
        self.processing_timer.timeout.connect(self.process_image)
        self.processing_timer.setSingleShot(True)
        
        # Update kernel preview
        self.update_kernel_preview()

    def parameter_changed(self):
        if self.live_preview.isChecked() and self.original_image is not None:
            self.processing_timer.start(500)  # Delay processing for 500ms
    
    def create_motion_kernel(self, length, angle, thickness=1.0):
        kernel = np.zeros((length, length))
        center = length // 2
        angle_rad = np.deg2rad(angle)
        x = np.cos(angle_rad)
        y = np.sin(angle_rad)
        
        # Create thicker line using multiple offset lines
        offsets = np.linspace(-thickness/2, thickness/2, max(3, int(thickness * 5)))
        for offset in offsets:
            x_offset = -offset * np.sin(angle_rad)
            y_offset = offset * np.cos(angle_rad)
            
            for i in range(-center, center + 1):
                x_pos = center + int(round(i * x + x_offset))
                y_pos = center + int(round(i * y + y_offset))
                if 0 <= x_pos < length and 0 <= y_pos < length:
                    kernel[y_pos, x_pos] = 1
        
        return kernel / kernel.sum()
    
    def estimate_snr(self, image):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Estimate noise using median filter difference
        denoised = cv2.medianBlur(gray, 3)
        noise = gray.astype(float) - denoised.astype(float)
        signal_power = np.mean(denoised ** 2)
        noise_power = np.mean(noise ** 2)
        
        return 10 * np.log10(signal_power / (noise_power + 1e-10))
    
    def wiener_deconvolution(self, image, kernel, snr, reg_param=0.01, pad_edges=True):
        if pad_edges:
            h, w = image.shape[:2]
            pad_h = h // 2
            pad_w = w // 2
            if len(image.shape) == 3:
                padded = np.pad(image, ((pad_h, pad_h), (pad_w, pad_w), (0, 0)), 'reflect')
            else:
                padded = np.pad(image, ((pad_h, pad_h), (pad_w, pad_w)), 'reflect')
        else:
            padded = image
        
        kernel_ft = np.fft.fft2(kernel, s=padded.shape[:2])
        kernel_ft_conj = np.conj(kernel_ft)
        
        if len(image.shape) == 3:
            result = np.zeros_like(padded, dtype=np.float32)
            for i in range(3):
                img_ft = np.fft.fft2(padded[:,:,i].astype(np.float32))
                denominator = np.abs(kernel_ft)**2 + reg_param + 1/snr
                result[:,:,i] = np.real(np.fft.ifft2(img_ft * kernel_ft_conj / denominator))
        else:
            img_ft = np.fft.fft2(padded.astype(np.float32))
            denominator = np.abs(kernel_ft)**2 + reg_param + 1/snr
            result = np.real(np.fft.ifft2(img_ft * kernel_ft_conj / denominator))
        
        if pad_edges:
            result = result[pad_h:-pad_h, pad_w:-pad_w]
            if len(image.shape) == 3:
                result = result[:,:,:3]  # Ensure we only have 3 channels
        
        return np.clip(result, 0, 255).astype(np.uint8)

    def enhance_image(self, image, denoise_strength, sharpness, contrast):
        # Denoise
        if denoise_strength > 0:
            image = cv2.fastNlMeansDenoisingColored(image, None, 
                                                   denoise_strength * 10, 
                                                   denoise_strength * 10,
                                                   7, 21)
        
        # Adjust contrast
        if contrast != 1.0:
            image = cv2.convertScaleAbs(image, alpha=contrast, beta=0)
        
        # Sharpen
        if sharpness > 1:
            kernel = np.array([[-1,-1,-1],
                             [-1, 9,-1],
                             [-1,-1,-1]]) * (sharpness - 1)
            image = cv2.filter2D(image, -1, kernel)
        
        return np.clip(image, 0, 255).astype(np.uint8)
    
    def process_image(self):
        if self.original_image is None:
            return
            
        # Get parameters
        kernel = self.create_motion_kernel(
            self.length_spin.value(),
            self.angle_spin.value(),
            self.thickness_spin.value()
        )
        
        # Get SNR value
        if self.auto_snr.isChecked():
            snr = self.estimate_snr(self.original_image)
            self.snr_spin.setValue(snr)
        else:
            snr = self.snr_spin.value()
        
        # Apply Wiener deconvolution
        self.processed_image = self.wiener_deconvolution(
            self.original_image,
            kernel,
            snr,
            self.reg_spin.value(),
            self.edge_padding.isChecked()
        )
        
        # Apply enhancements
        self.processed_image = self.enhance_image(
            self.processed_image,
            self.denoise_spin.value(),
            self.sharp_spin.value(),
            self.contrast_spin.value()
        )
        
        # Display result
        self.display_image(self.processed_image, self.processed_label)
        self.save_btn.setEnabled(True)
    
    def update_kernel_preview(self):
        length = self.length_spin.value()
        angle = self.angle_spin.value()
        thickness = self.thickness_spin.value()
        
        kernel = self.create_motion_kernel(length, angle, thickness)
        kernel_display = (kernel * 255).astype(np.uint8)
        kernel_display = cv2.resize(kernel_display, (150, 150), interpolation=cv2.INTER_NEAREST)
        
        h, w = kernel_display.shape
        bytes_per_line = w
        q_image = QImage(kernel_display.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        self.kernel_label.setPixmap(QPixmap.fromImage(q_image))
    
    def upload_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_name:
            self.original_image = cv2.imread(file_name)
            if self.original_image is not None:
                self.display_image(self.original_image, self.original_label)
                self.deblur_btn.setEnabled(True)
                self.save_btn.setEnabled(False)
                if self.live_preview.isChecked():
                    self.process_image()
    
    def save_image(self):
        if self.processed_image is None:
            return
            
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG Files (*.png);;JPEG Files (*.jpg)"
        )
        if file_name:
            cv2.imwrite(file_name, self.processed_image)
    
    def display_image(self, image, label):
        if image is None:
            return
        
        # Convert to RGB for display
        if len(image.shape) == 3:
            display_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            display_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        
        # Convert to QImage
        h, w = display_image.shape[:2]
        bytes_per_line = 3 * w
        q_image = QImage(display_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        label.setPixmap(QPixmap.fromImage(q_image))

    def toggle_angle_draw(self):
        if self.original_image is not None:
            self.original_label.draw_mode = self.draw_angle_btn.isChecked()
            if not self.draw_angle_btn.isChecked():
                self.original_label._update_scaled_pixmap()

    def set_angle(self, angle):
        self.angle_spin.setValue(int(round(angle)))
        self.draw_angle_btn.setChecked(False)
        if self.live_preview.isChecked():
            self.process_image()

class PerspectiveImageLabel(ImageLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = []
        self.max_points = 4
        self.draw_mode = False
        self.point_radius = 5
        self.current_point = None
        self.drag_threshold = 10
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if not self.draw_mode:
            return
            
        pos = event.position().toPoint()
        
        # Convert position to account for image scaling and position
        pos = self._convert_pos_to_pixmap(pos)
        if pos is None:
            return
            
        # Check if clicking near existing point
        for i, point in enumerate(self.points):
            if (pos - point).manhattanLength() < self.drag_threshold:
                self.current_point = i
                return
                
        # Add new point if we haven't reached max
        if len(self.points) < self.max_points:
            self.points.append(pos)
            self._update_scaled_pixmap()

    def mouseMoveEvent(self, event):
        if not self.draw_mode or self.current_point is None:
            return
            
        pos = event.position().toPoint()
        pos = self._convert_pos_to_pixmap(pos)
        if pos is not None:
            self.points[self.current_point] = pos
            self._update_scaled_pixmap()

    def mouseReleaseEvent(self, event):
        if not self.draw_mode:
            return
            
        self.current_point = None
        if len(self.points) == self.max_points:
            # Find the PerspectiveTab parent
            parent = self.parent()
            while parent and not isinstance(parent, PerspectiveTab):
                parent = parent.parent()
            if parent:
                parent.update_perspective()

    def _convert_pos_to_pixmap(self, pos):
        """Convert mouse position to pixmap coordinates"""
        if not self._pixmap:
            return None
            
        # Get the pixmap and label sizes
        pixmap_size = self._pixmap.size()
        label_size = self.size()
        
        # Calculate scaling
        scale = min(label_size.width() / pixmap_size.width(),
                   label_size.height() / pixmap_size.height())
        
        # Calculate image position within label (centered)
        scaled_width = pixmap_size.width() * scale
        scaled_height = pixmap_size.height() * scale
        x_offset = (label_size.width() - scaled_width) / 2
        y_offset = (label_size.height() - scaled_height) / 2
        
        # Convert position
        x = (pos.x() - x_offset) / scale
        y = (pos.y() - y_offset) / scale
        
        # Check if position is within image bounds
        if 0 <= x < pixmap_size.width() and 0 <= y < pixmap_size.height():
            return QPoint(int(x), int(y))
        return None

    def _update_scaled_pixmap(self):
        if self._original_pixmap:
            # Get the label size
            label_size = self.size()
            
            # Scale the original pixmap
            scaled = self._original_pixmap.scaled(
                label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._pixmap = scaled
            
            if self.draw_mode:
                temp_pixmap = scaled.copy()
                painter = QPainter(temp_pixmap)
                painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
                
                # Calculate scaling and offset for drawing
                pixmap_size = scaled.size()
                scale = min(label_size.width() / self._original_pixmap.width(),
                          label_size.height() / self._original_pixmap.height())
                x_offset = (label_size.width() - pixmap_size.width()) / 2
                y_offset = (label_size.height() - pixmap_size.height()) / 2
                
                # Draw lines between points
                scaled_points = []
                for point in self.points:
                    scaled_point = QPoint(
                        int(point.x() * scale + x_offset),
                        int(point.y() * scale + y_offset)
                    )
                    scaled_points.append(scaled_point)
                    painter.drawEllipse(scaled_point, self.point_radius, self.point_radius)
                
                # Draw lines
                for i in range(len(scaled_points)):
                    if i > 0:
                        painter.drawLine(scaled_points[i-1], scaled_points[i])
                
                # Close the polygon if we have all points
                if len(scaled_points) == self.max_points:
                    painter.drawLine(scaled_points[-1], scaled_points[0])
                
                painter.end()
                QLabel.setPixmap(self, temp_pixmap)
            else:
                QLabel.setPixmap(self, scaled)

    def clear_points(self):
        self.points = []
        self._update_scaled_pixmap()

class PerspectiveTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        layout = QHBoxLayout(self)
        
        # Create controls panel
        controls_panel = QWidget()
        controls_layout = QVBoxLayout(controls_panel)
        controls_panel.setMaximumWidth(400)
        
        # File controls group
        file_group = QGroupBox("File Controls")
        file_layout = QVBoxLayout(file_group)
        self.upload_btn = QPushButton("Upload Image")
        self.upload_btn.clicked.connect(self.upload_image)
        self.save_btn = QPushButton("Save Result")
        self.save_btn.clicked.connect(self.save_image)
        self.save_btn.setEnabled(False)
        file_layout.addWidget(self.upload_btn)
        file_layout.addWidget(self.save_btn)
        controls_layout.addWidget(file_group)
        
        # Perspective controls group
        perspective_group = QGroupBox("Perspective Controls")
        perspective_layout = QVBoxLayout(perspective_group)
        
        # Add instructions
        instructions = QLabel("1. Click 'Select Points'\n2. Click 4 corners clockwise\n3. Adjust points if needed\n4. Adjust output size")
        instructions.setWordWrap(True)
        perspective_layout.addWidget(instructions)
        
        # Add point selection button
        self.select_points_btn = QPushButton("Select Points")
        self.select_points_btn.setCheckable(True)
        self.select_points_btn.clicked.connect(self.toggle_point_selection)
        perspective_layout.addWidget(self.select_points_btn)
        
        # Add clear points button
        self.clear_points_btn = QPushButton("Clear Points")
        self.clear_points_btn.clicked.connect(self.clear_points)
        perspective_layout.addWidget(self.clear_points_btn)
        
        # Add output size controls
        size_widget = QWidget()
        size_layout = QGridLayout(size_widget)
        
        # Width control
        width_label = QLabel("Width:")
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 2000)
        self.width_spin.setValue(800)
        self.width_spin.setSingleStep(50)
        size_layout.addWidget(width_label, 0, 0)
        size_layout.addWidget(self.width_spin, 0, 1)
        
        # Height control
        height_label = QLabel("Height:")
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 2000)
        self.height_spin.setValue(600)
        self.height_spin.setSingleStep(50)
        size_layout.addWidget(height_label, 1, 0)
        size_layout.addWidget(self.height_spin, 1, 1)
        
        perspective_layout.addWidget(size_widget)
        
        # Add maintain aspect ratio checkbox
        self.maintain_aspect = QCheckBox("Maintain Aspect Ratio")
        self.maintain_aspect.setChecked(True)
        perspective_layout.addWidget(self.maintain_aspect)
        
        # Add process button
        self.process_btn = QPushButton("Apply Perspective Correction")
        self.process_btn.clicked.connect(self.update_perspective)
        self.process_btn.setEnabled(False)
        perspective_layout.addWidget(self.process_btn)
        
        controls_layout.addWidget(perspective_group)
        controls_layout.addStretch()
        layout.addWidget(controls_panel)
        
        # Create image display area
        display_widget = QWidget()
        display_layout = QHBoxLayout(display_widget)
        
        # Original image display
        self.original_label = PerspectiveImageLabel()
        self.original_label.setText("Original Image\nSelect 4 corners clockwise")
        display_layout.addWidget(self.original_label)
        
        # Processed image display
        self.processed_label = ImageLabel()
        self.processed_label.setText("Processed Image")
        display_layout.addWidget(self.processed_label)
        
        layout.addWidget(display_widget)
        
        # Initialize variables
        self.original_image = None
        self.processed_image = None

    def toggle_point_selection(self):
        if self.original_image is not None:
            self.original_label.draw_mode = self.select_points_btn.isChecked()
            if not self.select_points_btn.isChecked():
                self.original_label._update_scaled_pixmap()

    def clear_points(self):
        self.original_label.clear_points()
        self.process_btn.setEnabled(False)

    def upload_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_name:
            self.original_image = cv2.imread(file_name)
            if self.original_image is not None:
                self.display_image(self.original_image, self.original_label)
                self.clear_points()
                self.save_btn.setEnabled(False)

    def save_image(self):
        if self.processed_image is None:
            return
            
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG Files (*.png);;JPEG Files (*.jpg)"
        )
        if file_name:
            cv2.imwrite(file_name, self.processed_image)

    def display_image(self, image, label):
        if image is None:
            return
        
        # Convert to RGB for display
        if len(image.shape) == 3:
            display_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            display_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        
        # Convert to QImage
        h, w = display_image.shape[:2]
        bytes_per_line = 3 * w
        q_image = QImage(display_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        label.setPixmap(QPixmap.fromImage(q_image))

    def update_perspective(self):
        if len(self.original_label.points) != 4 or self.original_image is None:
            return
            
        # Get image scale factor
        scaled = self.original_label._pixmap.size()
        original = self.original_image.shape
        scale_x = original[1] / scaled.width()
        scale_y = original[0] / scaled.height()
        
        # Convert points to original image coordinates
        src_points = np.float32([
            [p.x() * scale_x, p.y() * scale_y] for p in self.original_label.points
        ])
        
        # Define destination points
        dst_width = self.width_spin.value()
        dst_height = self.height_spin.value()
        dst_points = np.float32([
            [0, 0],
            [dst_width - 1, 0],
            [dst_width - 1, dst_height - 1],
            [0, dst_height - 1]
        ])
        
        # Calculate perspective transform matrix
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # Apply perspective transformation
        self.processed_image = cv2.warpPerspective(
            self.original_image, matrix, (dst_width, dst_height))
        
        # Display result
        self.display_image(self.processed_image, self.processed_label)
        self.save_btn.setEnabled(True)
        self.process_btn.setEnabled(True)
        
        # Disable point selection mode
        self.select_points_btn.setChecked(False)
        self.original_label.draw_mode = False

class MediaAnalyzer(BaseHelper):
    name = "Media Analyzer"
    description = "Advanced image processing and analysis tool"
    
    def __init__(self, graph_manager, parent=None):
        super().__init__(graph_manager, parent)
        self.setMinimumSize(1400, 800)
        
    def setup_ui(self):
        # Create main widget and tab widget
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        
        tab_widget = QTabWidget()
        
        # Create and add tabs
        self.deblur_tab = DeblurTab(self)
        self.perspective_tab = PerspectiveTab(self)
        
        tab_widget.addTab(self.deblur_tab, "Deblurring")
        tab_widget.addTab(self.perspective_tab, "Perspective")
        
        self.main_layout.addWidget(tab_widget)
