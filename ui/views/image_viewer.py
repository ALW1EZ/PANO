from PySide6.QtWidgets import (
    QMainWindow, QGraphicsView, QGraphicsScene, QToolBar,
    QFileDialog, QColorDialog, QSpinBox, QLabel, QVBoxLayout,
    QWidget, QHBoxLayout, QPushButton, QProgressDialog,
    QComboBox, QSlider, QStatusBar
)
from PySide6.QtCore import Qt, QRectF, QPointF, QUrl
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, QIcon,
    QTransform, QPainterPath, QAction, QBrush, QPolygonF
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
import os
import tempfile
import aiofiles
import aiohttp
import asyncio
from qasync import asyncSlot
import math

class DrawingScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drawing = False
        self.last_point = None
        self.current_path = None
        self.pen = QPen(QColor("#ff0000"), 2, Qt.PenStyle.SolidLine)
        self.brush = QBrush(Qt.BrushStyle.NoBrush)
        self.tool = "pen"
        self.undo_stack = []
        self.redo_stack = []
        self.current_item = None
        self.background_item = None
        
    def push_to_undo_stack(self, items=None):
        if items is None:
            # Get all items except background
            items = [item for item in self.items() if item != self.background_item]
        self.undo_stack.append(items)
        self.redo_stack.clear()
        
    def undo(self):
        if not self.undo_stack:
            return
        current_state = [item for item in self.items() if item != self.background_item]
        self.redo_stack.append(current_state)
        previous_state = self.undo_stack.pop()
        
        # Remove all items except background
        for item in self.items():
            if item != self.background_item:
                self.removeItem(item)
                
        # Add back previous state
        for item in previous_state:
            self.addItem(item)
            
    def redo(self):
        if not self.redo_stack:
            return
        current_state = [item for item in self.items() if item != self.background_item]
        self.undo_stack.append(current_state)
        next_state = self.redo_stack.pop()
        
        # Remove all items except background
        for item in self.items():
            if item != self.background_item:
                self.removeItem(item)
                
        # Add back next state
        for item in next_state:
            self.addItem(item)
            
    def create_arrow(self, start, end):
        """Create an arrow polygon"""
        # Create the arrow head
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = self.pen.width() * 4
        
        arrow_p1 = QPointF(
            end.x() - arrow_size * math.cos(angle - math.pi/6),
            end.y() - arrow_size * math.sin(angle - math.pi/6)
        )
        arrow_p2 = QPointF(
            end.x() - arrow_size * math.cos(angle + math.pi/6),
            end.y() - arrow_size * math.sin(angle + math.pi/6)
        )
        
        # Create arrow polygon
        arrow_head = QPolygonF([end, arrow_p1, arrow_p2])
        
        # Create the line
        path = QPainterPath()
        path.moveTo(start)
        path.lineTo(end)
        path.addPolygon(arrow_head)
        
        return self.addPath(path, self.pen, self.brush)
        
    def mousePressEvent(self, event):
        if self.parent().drawing_enabled:
            self.drawing = True
            self.last_point = event.scenePos()
            if self.tool == "pen":
                self.current_path = QPainterPath()
                self.current_path.moveTo(self.last_point)
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        if self.drawing and self.parent().drawing_enabled:
            new_point = event.scenePos()
            if self.tool == "pen":
                line = self.addLine(
                    self.last_point.x(),
                    self.last_point.y(),
                    new_point.x(),
                    new_point.y(),
                    self.pen
                )
                self.current_path.lineTo(new_point)
                self.last_point = new_point  # Update last_point for pen
            else:
                # Update preview for all other tools
                self.clear_last_shape()
                if self.tool == "rectangle":
                    # Calculate rect based on start point and current point
                    width = new_point.x() - self.last_point.x()
                    height = new_point.y() - self.last_point.y()
                    rect = QRectF(
                        self.last_point.x(),
                        self.last_point.y(),
                        width,
                        height
                    )
                    self.current_item = self.addRect(rect, self.pen, self.brush)
                elif self.tool == "circle":
                    # Calculate circle based on start point and current point
                    width = new_point.x() - self.last_point.x()
                    height = new_point.y() - self.last_point.y()
                    rect = QRectF(
                        self.last_point.x(),
                        self.last_point.y(),
                        width,
                        height
                    )
                    self.current_item = self.addEllipse(rect, self.pen, self.brush)
                elif self.tool == "line":
                    self.current_item = self.addLine(
                        self.last_point.x(),
                        self.last_point.y(),
                        new_point.x(),
                        new_point.y(),
                        self.pen
                    )
                elif self.tool == "arrow":
                    self.current_item = self.create_arrow(self.last_point, new_point)
            super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if self.drawing and self.parent().drawing_enabled:
            new_point = event.scenePos()
            if self.tool == "pen":
                self.push_to_undo_stack()
            else:
                # Finalize shape
                if self.tool == "rectangle":
                    width = new_point.x() - self.last_point.x()
                    height = new_point.y() - self.last_point.y()
                    rect = QRectF(
                        self.last_point.x(),
                        self.last_point.y(),
                        width,
                        height
                    )
                    self.addRect(rect, self.pen, self.brush)
                elif self.tool == "circle":
                    width = new_point.x() - self.last_point.x()
                    height = new_point.y() - self.last_point.y()
                    rect = QRectF(
                        self.last_point.x(),
                        self.last_point.y(),
                        width,
                        height
                    )
                    self.addEllipse(rect, self.pen, self.brush)
                elif self.tool == "line":
                    self.addLine(
                        self.last_point.x(),
                        self.last_point.y(),
                        new_point.x(),
                        new_point.y(),
                        self.pen
                    )
                elif self.tool == "arrow":
                    self.create_arrow(self.last_point, new_point)
                self.push_to_undo_stack()
                
            self.drawing = False
            self.current_path = None
            self.current_item = None
            
        super().mouseReleaseEvent(event)
        
    def clear_last_shape(self):
        if self.current_item:
            self.removeItem(self.current_item)
            self.current_item = None

class ImageViewer(QMainWindow):
    def __init__(self, image_path=None, title="PANO - Image Viewer"):
        super().__init__()
        self.setWindowTitle(title)
        self.image_path = image_path
        self.drawing_enabled = False
        self.temp_file = None
        self.setup_ui()
        
        if image_path:
            asyncio.create_task(self.load_image(image_path))
            
    def setup_ui(self):
        # Set window style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QToolBar {
                background-color: #2d2d2d;
                border: none;
                spacing: 3px;
                padding: 6px;
                min-height: 42px;
            }
            QToolBar QToolButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
                min-height: 24px;
            }
            QToolBar QToolButton:hover {
                background-color: #4d4d4d;
            }
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
                min-width: 120px;
                min-height: 24px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 6px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 6px;
            }
            QSpinBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
                min-height: 24px;
            }
            QLabel {
                color: #ffffff;
                padding: 0px 4px;
            }
            QStatusBar {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 4px;
                background: #3d3d3d;
                margin: 0px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: none;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create toolbar
        self.toolbar = QToolBar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
        # Add undo/redo actions
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        self.toolbar.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Shift+Z")
        redo_action.triggered.connect(self.redo)
        self.toolbar.addAction(redo_action)
        
        self.toolbar.addSeparator()
        
        # Add zoom controls
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        self.toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        self.toolbar.addAction(zoom_out_action)
        
        fit_action = QAction("Fit to View", self)
        fit_action.setShortcut("Ctrl+0")
        fit_action.triggered.connect(self.fit_to_view)
        self.toolbar.addAction(fit_action)
        
        self.toolbar.addSeparator()
        
        # Add drawing tools
        draw_action = QAction("Toggle Drawing", self)
        draw_action.setCheckable(True)
        draw_action.triggered.connect(self.toggle_drawing)
        self.toolbar.addAction(draw_action)
        
        # Add tool selector
        self.tool_selector = QComboBox()
        self.tool_selector.addItems(["Pen", "Rectangle", "Circle", "Line", "Arrow"])
        self.tool_selector.currentTextChanged.connect(self.change_tool)
        self.toolbar.addWidget(self.tool_selector)
        
        # Add color picker
        color_action = QAction("Pen Color", self)
        color_action.triggered.connect(self.choose_color)
        self.toolbar.addAction(color_action)
        
        # Add fill color picker
        fill_color_action = QAction("Fill Color", self)
        fill_color_action.triggered.connect(self.choose_fill_color)
        self.toolbar.addAction(fill_color_action)
        
        # Add pen width control
        width_label = QLabel("Pen Width:")
        self.toolbar.addWidget(width_label)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 50)
        self.width_spin.setValue(2)
        self.width_spin.valueChanged.connect(self.change_pen_width)
        self.toolbar.addWidget(self.width_spin)
        
        self.toolbar.addSeparator()
        
        # Add opacity control
        opacity_label = QLabel("Opacity:")
        self.toolbar.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(100)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        self.toolbar.addWidget(self.opacity_slider)
        
        self.toolbar.addSeparator()
        
        # Add save actions
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_image)
        self.toolbar.addAction(save_action)
        
        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_image_as)
        self.toolbar.addAction(save_as_action)
        
        # Create graphics view and scene
        self.scene = DrawingScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setStyleSheet("""
            QGraphicsView {
                border: none;
                background-color: #1e1e1e;
            }
        """)
        
        layout.addWidget(self.view)
        
        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Set minimum size
        self.setMinimumSize(1000, 800)
        
    def change_tool(self, tool_name):
        """Change the current drawing tool"""
        self.scene.tool = tool_name.lower()
        
    def choose_fill_color(self):
        """Choose fill color for shapes"""
        color = QColorDialog.getColor(self.scene.brush.color(), self)
        if color.isValid():
            self.scene.brush = QBrush(color)
            
    def change_opacity(self, value):
        """Change opacity of the pen and brush"""
        opacity = value / 100.0
        color = self.scene.pen.color()
        color.setAlphaF(opacity)
        self.scene.pen.setColor(color)
        
        fill_color = self.scene.brush.color()
        fill_color.setAlphaF(opacity)
        self.scene.brush = QBrush(fill_color, self.scene.brush.style())
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)
        
    async def load_image(self, image_path):
        """Load image from local path or URL"""
        if not image_path:
            return
            
        try:
            # Check if it's a URL
            if image_path.startswith(('http://', 'https://')):
                # Show progress dialog
                progress = QProgressDialog("Downloading image...", "Cancel", 0, 0, self)
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.show()
                
                try:
                    # Download image
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_path) as response:
                            if response.status == 200:
                                # Create temp file
                                suffix = os.path.splitext(image_path)[1] or '.jpg'
                                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                                    self.temp_file = tmp.name
                                    # Save to temp file
                                    async with aiofiles.open(self.temp_file, 'wb') as f:
                                        await f.write(await response.read())
                                    # Load the temp file
                                    self._display_image(self.temp_file)
                finally:
                    progress.close()
            else:
                # Local file
                if os.path.exists(image_path):
                    self._display_image(image_path)
                    
        except Exception as e:
            print(f"Error loading image: {e}")
            
    def _display_image(self, image_path):
        """Display the image in the viewer"""
        image = QImage(image_path)
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            self.scene.clear()
            # Set the background image
            self.scene.background_item = self.scene.addPixmap(pixmap)
            self.scene.setSceneRect(QRectF(pixmap.rect()))
            self.fit_to_view()
            
    def zoom_in(self):
        self.view.scale(1.2, 1.2)
        
    def zoom_out(self):
        self.view.scale(1/1.2, 1/1.2)
        
    def fit_to_view(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
    def toggle_drawing(self, enabled):
        self.drawing_enabled = enabled
        self.view.setDragMode(
            QGraphicsView.DragMode.NoDrag if enabled 
            else QGraphicsView.DragMode.ScrollHandDrag
        )
        
    def choose_color(self):
        color = QColorDialog.getColor(self.scene.pen.color(), self)
        if color.isValid():
            self.scene.pen.setColor(color)
            
    def change_pen_width(self, width):
        self.scene.pen.setWidth(width)
        
    def save_image(self):
        if not self.image_path:
            self.save_image_as()
            return
            
        self.save_to_file(self.image_path)
        
    def save_image_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image As",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if file_path:
            self.save_to_file(file_path)
            self.image_path = file_path
            
    def save_to_file(self, file_path):
        # Create a new image with the scene contents
        image = QImage(
            self.scene.sceneRect().size().toSize(),
            QImage.Format.Format_ARGB32
        )
        image.fill(Qt.GlobalColor.transparent)
        
        # Setup painter
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Render the scene
        self.scene.render(painter)
        painter.end()
        
        # Save the image
        image.save(file_path)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.scene.items():
            self.fit_to_view()
            
    def closeEvent(self, event):
        # Clean up temp file if it exists
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.unlink(self.temp_file)
            except:
                pass
        super().closeEvent(event) 
        
    def undo(self):
        self.scene.undo()
        
    def redo(self):
        self.scene.redo() 