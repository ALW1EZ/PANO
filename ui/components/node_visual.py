from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsTextItem, QGraphicsObject,
    QGraphicsPixmapItem, QMenu, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QDialogButtonBox, QGraphicsLineItem
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QPropertyAnimation, QEasingCurve, QAbstractAnimation, QLineF
from PyQt6.QtGui import (
    QPainter, QPixmap, QColor, QPen, QBrush, QPainterPath, QLinearGradient,
    QPolygonF
)
from dataclasses import dataclass
from enum import Enum, auto
import urllib.request
import tempfile
import logging
import asyncio
import math
import os
from qasync import asyncSlot

from entities import Entity
from entities.event import Event
from transforms import ENTITY_TRANSFORMS
from ..styles.node_style import NodeStyle
from ..dialogs.property_editor import PropertyEditor
from ..managers.timeline_manager import TimelineEvent
logger = logging.getLogger(__name__)

class NodeVisualState(Enum):
    """Enum for node visual states"""
    NORMAL = auto()
    SELECTED = auto()
    HIGHLIGHTED = auto()

@dataclass
class NodeDimensions:
    """Tracks dimensions for a node"""
    def __init__(self, min_width: float = 200, min_height: float = 64):
        self.min_width = min_width
        self.min_height = min_height
        self._width = min_width
        self._height = min_height
        
    @property
    def width(self) -> float:
        return self._width
        
    @width.setter
    def width(self, value: float):
        self._width = max(value, self.min_width)
        
    @property
    def height(self) -> float:
        return self._height
        
    @height.setter
    def height(self, value: float):
        self._height = max(value, self.min_height)

class NodeVisual(QGraphicsObject):
    def __init__(self, node: Entity, style: NodeStyle = NodeStyle(), parent=None):
        super().__init__(parent)
        self.node = node
        self.style = style
        self.dimensions = NodeDimensions(style.min_width, style.min_height)
        self._state = NodeVisualState.NORMAL
        self._current_scale = 1.0
        self.original_pixmap = None
        self.current_image_size = None
        
        self._setup_visual()
        self._setup_interaction()
        
    def _setup_visual(self):
        self._init_items()
        self._update_layout()
        self._temp_line = None
        
    def _setup_interaction(self):
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setData(0, self.node.id)

    def _init_items(self):
        """Initialize all visual items"""
        # Type label (small, above)
        self.type_label = QGraphicsTextItem(self)
        self.type_label.setDefaultTextColor(self.style.property_color)
        font = self.type_label.font()
        font.setPointSize(7)
        self.type_label.setFont(font)
        self.type_label.setPlainText(self.node.type_label)
        
        # Main label (larger, centered)
        self.label = QGraphicsTextItem(self)
        self.label.setDefaultTextColor(self.style.label_color)
        font = self.label.font()
        font.setPointSize(9)
        self.label.setFont(font)
        
        # Properties text
        self.properties_item = QGraphicsTextItem(self)
        self.properties_item.setDefaultTextColor(self.style.property_color)
        font = self.properties_item.font()
        font.setPointSize(7)
        self.properties_item.setFont(font)
        
        # Image
        self.image_item = QGraphicsPixmapItem(self)
        self.image_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        
        # Load image if available
        image_path = self.node.properties.get("image")
        if image_path:
            if image_path.startswith(("http://", "https://")):
                self._load_remote_image(image_path)
            else:
                self._load_local_image(image_path)

    def _update_layout(self):
        """Update all text and layout"""
        content_sizes = self._calculate_content_sizes()
        self._update_dimensions(content_sizes)
        self._position_elements(content_sizes)
        self.update()

    def _calculate_content_sizes(self):
        """Calculate sizes of all content elements"""
        # Update labels
        self.type_label.setPlainText(self.node.type_label)
        self.label.setPlainText(self.node.get_main_display())
        
        # Update properties
        prop_text = []
        for key, value in self.node.get_display_properties().items():
            if len(str(value)) > 30:
                value = str(value)[:27] + "..."
            prop_text.append(f"{key}: {value}")
        self.properties_item.setPlainText("\n".join(prop_text))
        
        # Calculate text dimensions
        text_width = max(
            self.label.boundingRect().width(),
            self.properties_item.boundingRect().width(),
            self.type_label.boundingRect().width()
        )
        
        text_height = (self.type_label.boundingRect().height() +
                      self.label.boundingRect().height() +
                      self.properties_item.boundingRect().height() +
                      self.style.text_padding * 2)
        
        # Check if we have a valid image
        has_image = self.original_pixmap and not self.original_pixmap.isNull()
        
        image_width = 0
        image_height = 0
        if has_image:
            # Calculate image dimensions based on text height
            base_height = text_height + self.style.padding * 2
            image_height = base_height
            aspect_ratio = self.original_pixmap.width() / self.original_pixmap.height()
            image_width = image_height * aspect_ratio
            
        return {
            'text_width': text_width,
            'text_height': text_height,
            'has_image': has_image,
            'image_width': image_width,
            'image_height': image_height,
            'base_height': text_height + self.style.padding * 2
        }

    def _update_dimensions(self, content_sizes):
        """Update node dimensions based on content sizes"""
        text_width = content_sizes['text_width']
        has_image = content_sizes['has_image']
        image_width = content_sizes['image_width']
        image_height = content_sizes['image_height']
        base_height = content_sizes['base_height']
        
        # Calculate minimum content width
        if has_image:
            min_content_width = (text_width + 
                               image_width + 
                               self.style.padding * 2 + 
                               self.style.image_padding * 2)
        else:
            min_content_width = text_width + self.style.padding * 2
            
        # Update dimensions
        self.dimensions.width = max(min_content_width, self.dimensions.min_width)
        self.dimensions.height = max(base_height, image_height + self.style.padding * 2, self.dimensions.min_height)

    def _position_elements(self, content_sizes):
        """Position all elements based on current dimensions"""
        text_width = content_sizes['text_width']
        has_image = content_sizes['has_image']
        image_width = content_sizes['image_width']
        image_height = content_sizes['image_height']
        
        # Calculate text area starting position
        if has_image:
            text_area_start = -self.dimensions.width/2 + image_width + self.style.padding + self.style.image_padding * 2
        else:
            text_area_start = -text_width/2
            
        # Calculate vertical positions
        total_text_height = (self.type_label.boundingRect().height() +
                           self.style.text_padding +
                           self.label.boundingRect().height() +
                           self.style.text_padding +
                           self.properties_item.boundingRect().height())
                           
        current_y = -total_text_height/2
        
        # Position elements
        self.type_label.setPos(text_area_start, current_y)
        current_y += self.type_label.boundingRect().height() + self.style.text_padding
        
        self.label.setPos(text_area_start, current_y)
        current_y += self.label.boundingRect().height() + self.style.text_padding
        
        self.properties_item.setPos(text_area_start, current_y)
        
        # Position image if present
        if has_image:
            self.image_item.setPos(
                -self.dimensions.width/2 + self.style.image_padding,
                -image_height/2  # Center vertically
            )
            self._update_image_scale(target_height=image_height)

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle of the node"""
        return QRectF(-self.dimensions.width/2, -self.dimensions.height/2,
                     self.dimensions.width, self.dimensions.height)

    def paint(self, painter: QPainter, option, widget):
        """Paint the node with shadow and gradient"""
        # Draw shadow
        shadow_path = QPainterPath()
        shadow_rect = self.boundingRect().adjusted(0, 0, 0, 0)
        shadow_path.addRoundedRect(shadow_rect, self.style.radius, self.style.radius)
        
        painter.save()
        painter.setBrush(self.style.shadow_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.translate(self.style.shadow_offset, self.style.shadow_offset)
        painter.drawPath(shadow_path)
        painter.restore()
        
        # Create gradient for background
        gradient = QLinearGradient(
            self.boundingRect().topLeft(),
            self.boundingRect().bottomRight()
        )
        base_color = self._get_current_color()
        gradient.setColorAt(0, base_color.lighter(105))
        gradient.setColorAt(1, base_color)
        
        # Draw main rectangle with gradient
        painter.setBrush(QBrush(gradient))
        border_pen = QPen(NodeStyle.get_type_color(self.node.__class__.__name__))
        border_pen.setWidthF(self.style.border_width)
        painter.setPen(border_pen)
        painter.drawRoundedRect(self.boundingRect(), self.style.radius, self.style.radius)

    def _get_current_color(self) -> QColor:
        """Get the current background color based on node state"""
        if self._state == NodeVisualState.SELECTED:
            return self.style.selected_color
        elif self._state == NodeVisualState.HIGHLIGHTED:
            return self.style.highlighted_color
        return self.style.normal_color

    def set_state(self, state: NodeVisualState):
        """Set the node's visual state"""
        self._state = state
        self.update()

    def mouseDoubleClickEvent(self, event):
        """Handle double-click to edit properties"""
        self._edit_properties()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D30;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3F3F46;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3F3F46;
                margin: 4px 0px;
            }
        """)
        
        # Add menu items
        delete_text = "Delete Selected" if self.scene().selectedItems() else "Delete"
        delete_action = menu.addAction(delete_text)
        delete_action.triggered.connect(self._delete_selected_nodes)
        
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(self._edit_properties)

        # Add transforms submenu
        transforms_menu = menu.addMenu("Transforms")
        entity_type = self.node.__class__.__name__
        available_transforms = ENTITY_TRANSFORMS.get(entity_type, [])
        
        for transform in available_transforms:
            action = transforms_menu.addAction(transform.name)
            action.setToolTip(transform.description)
            action.triggered.connect(
                lambda checked, t=transform: self._handle_transform_action(t)
            )
        
        menu.exec(event.screenPos())

    def _handle_transform_action(self, transform):
        """Handle transform action from context menu"""
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._execute_transform(transform))
        except Exception as e:
            QMessageBox.critical(None, "Transform Error", str(e))

    async def _execute_transform(self, transform):
        """Execute a transform on this node"""
        if not transform:
            raise ValueError("No transform provided")
            
        try:
            new_entities = await transform.run(self.node, self.scene().views()[0].graph_manager)
            if not new_entities:
                return
                
            # Position new nodes in a circle
            source_pos = self.pos()
            radius = 200
            angle_step = 2 * math.pi / len(new_entities)
            
            view = self.scene().views()[0]
            if not hasattr(view, 'graph_manager'):
                raise RuntimeError("Could not find graph manager")
                
            # Add new nodes and relationships
            for i, entity in enumerate(new_entities):
                angle = i * angle_step
                new_pos = QPointF(
                    source_pos.x() + radius * math.cos(angle),
                    source_pos.y() + radius * math.sin(angle)
                )
                
                node_visual = view.graph_manager.add_node(entity, new_pos)
                view.graph_manager.add_edge(self.node.id, entity.id, "")
                
        except Exception as e:
            QMessageBox.critical(None, "Transform Error", str(e))
            raise

    def _edit_properties(self):
        """Open property editor dialog"""
        dialog = PropertyEditor(self.node)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the updated properties
            updated_properties = dialog.get_properties()
            
            # Update the node's properties
            for key, value in updated_properties.items():
                self.node.properties[key] = value
            
            # Update the node's label
            self.node.update_label()
            
            # Update visual representation
            self._update_layout()
            
            # Notify graph manager of the update
            scene = self.scene()
            if scene and hasattr(scene.views()[0], 'graph_manager'):
                graph_manager = scene.views()[0].graph_manager
                graph_manager.update_node(self.node.id, self.node)
                
            # Load image if available
            image_path = self.node.properties.get("image")
            if image_path:
                if image_path.startswith(("http://", "https://")):
                    self._load_remote_image(image_path)
                else:
                    self._load_local_image(image_path)

    def _delete_node(self):
        """Delete this node"""
        view = self.scene().views()[0]
        if hasattr(view, 'graph_manager'):
            view.graph_manager.remove_node(self.node.id)

    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._temp_line = QGraphicsLineItem()
            self._temp_line.setPen(QPen(self.style.normal_color, 2, Qt.PenStyle.DashLine))
            if self.scene():
                self.scene().addItem(self._temp_line)
                event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        if self._temp_line and self.scene():
            start_pos = self.scenePos()
            end_pos = self.mapToScene(event.pos())
            self._temp_line.setLine(QLineF(start_pos, end_pos))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if self._temp_line and self.scene():
            end_pos = self.mapToScene(event.pos())
            items = self.scene().items(end_pos)
            target_node = None
            
            for item in items:
                if isinstance(item, NodeVisual) and item != self:
                    target_node = item
                    break
            
            self.scene().removeItem(self._temp_line)
            self._temp_line = None
            
            if target_node:
                self._show_relationship_dialog(target_node)
            
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _show_relationship_dialog(self, target_node):
        """Show dialog to create relationship"""
        dialog = QDialog(self.scene().views()[0])
        dialog.setWindowTitle("Create Relationship")
        
        layout = QVBoxLayout(dialog)
        
        # Label input
        label_layout = QHBoxLayout()
        label_label = QLabel("Relationship:")
        label_input = QLineEdit()
        label_layout.addWidget(label_label)
        label_layout.addWidget(label_input)
        layout.addLayout(label_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Apply dark theme
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
                color: #CCCCCC;
            }
            QLabel {
                color: #CCCCCC;
            }
            QLineEdit {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                padding: 5px;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #007ACC;
                color: #FFFFFF;
                border: none;
                padding: 5px 15px;
                border-radius: 2px;
            }
        """)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            view = self.scene().views()[0]
            if hasattr(view, 'graph_manager'):
                try:
                    view.graph_manager.add_edge(
                        self.node.id,
                        target_node.node.id,
                        label_input.text()
                    )
                except Exception as e:
                    QMessageBox.warning(
                        view, "Error Creating Relationship", str(e)
                    )

    def _load_remote_image(self, url: str):
        """Load image from URL"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".svg") as tmp_file:
                urllib.request.urlretrieve(url, tmp_file.name)
                self._load_local_image(tmp_file.name)
                os.unlink(tmp_file.name)
        except Exception as e:
            logger.error(f"Failed to load remote image: {e}")

    def _load_local_image(self, path: str):
        """Load image from local file"""
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.original_pixmap = pixmap
                self._update_layout()

    def _update_image_scale(self, target_height=None):
        """Update image scale based on current view transform"""
        if not self.original_pixmap or self.original_pixmap.isNull():
            return

        view_scale = 1.0
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            view_scale = view.transform().m11()

        if target_height is None:
            content_sizes = self._calculate_content_sizes()
            target_height = content_sizes['image_height']

        # Calculate scaled dimensions while preserving aspect ratio
        aspect_ratio = self.original_pixmap.width() / self.original_pixmap.height()
        target_width = target_height * aspect_ratio

        # Scale based on view scale
        scale_factor = max(1.0, 1.0 / view_scale)
        scaled_width = int(target_width * scale_factor)
        scaled_height = int(target_height * scale_factor)

        # Scale the image
        scaled_pixmap = self.original_pixmap.scaled(
            scaled_width, scaled_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Create rounded corners
        rounded_pixmap = QPixmap(scaled_pixmap.size())
        rounded_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(
            0, 0,
            scaled_pixmap.width(), scaled_height,
            self.style.radius * scale_factor, self.style.radius * scale_factor
        )
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled_pixmap)
        painter.end()

        self.image_item.setPixmap(rounded_pixmap)
        self.image_item.setScale(1.0 / scale_factor)

    def update_label(self):
        """Update the node's visual appearance"""
        image_path = self.node.properties.get("image")
        if image_path:
            if image_path.startswith(("http://", "https://")):
                self._load_remote_image(image_path)
            else:
                self._load_local_image(image_path)
        
        self._update_layout()
        
        if hasattr(self, 'image_item') and self.image_item.pixmap():
            self._update_image_scale() 

    def _delete_selected_nodes(self):
        """Delete all selected nodes"""
        if not self.scene():
            return
            
        # Get all selected nodes
        selected_nodes = [item for item in self.scene().selectedItems() 
                         if isinstance(item, NodeVisual)]
        
        # If no nodes are selected, delete just this node
        if not selected_nodes:
            self._delete_node()
            return
            
        view = self.scene().views()[0]
        if hasattr(view, 'graph_manager'):
            # Delete all selected nodes
            for node in selected_nodes:
                view.graph_manager.remove_node(node.node.id) 