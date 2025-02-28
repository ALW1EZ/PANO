from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsTextItem, QGraphicsObject,
    QGraphicsPixmapItem, QMenu, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QDialogButtonBox, QGraphicsLineItem
)
from PySide6.QtCore import Qt, QPointF, QRectF, QPropertyAnimation, QEasingCurve, QAbstractAnimation, QLineF
from PySide6.QtGui import (
    QPainter, QPixmap, QColor, QPen, QBrush, QPainterPath, QLinearGradient,
    QPolygonF, QFont
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
from PySide6.QtCore import Signal

import requests
from bs4 import BeautifulSoup
import random
import aiohttp

from entities import Entity
from entities.event import Event
from transforms import ENTITY_TRANSFORMS
from ..styles.node_style import NodeStyle
from ..dialogs.property_editor import PropertyEditor
from ..managers.timeline_manager import TimelineEvent
from ui.managers.status_manager import StatusManager

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
    """Visual representation of a node in the graph"""
    node_updated = Signal()  # Signal emitted when node is updated
    
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
        font = QFont("Geist Mono", 9)
        self.type_label.setFont(font)
        self.type_label.setPlainText(self.node.type_label)
        
        # Main label (larger, centered)
        self.label = QGraphicsTextItem(self)
        self.label.setDefaultTextColor(self.style.label_color)
        font = QFont("Geist Mono", 12)
        self.label.setFont(font)
        
        # Enable word wrapping for text entities
        if self.node.type == "Text":
            self.label.setTextWidth(self.style.min_width - self.style.padding * 2)
        
        # Properties text
        self.properties_item = QGraphicsTextItem(self)
        self.properties_item.setDefaultTextColor(self.style.property_color)
        font = QFont("Geist Mono", 9)
        self.properties_item.setFont(font)
        
        # Image
        self.image_item = QGraphicsPixmapItem(self)
        self.image_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        
        # Load image if available
        image_path = self.node.properties.get("image")
        if image_path:
            asyncio.create_task(self._load_image(image_path))

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
        # Remove character limit for text entities
        if self.node.type == "Text":
            self.label.setPlainText(self.node.get_main_display())
        else:
            if len(self.node.get_main_display()) > 30:
                self.label.setPlainText(self.node.get_main_display()[:30] + "...")
            else:
                self.label.setPlainText(self.node.get_main_display())
        
        # Update properties
        prop_text = []
        for key, value in self.node.get_display_properties().items():
            if len(value) > 30:
                value = value[:30] + "..."
            if key == 'notes':
                value = f"\n{value}"
            prop_text.append(f"{key.upper()}: {value}")
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
        
        # Update text width for text entities
        if self.node.type == "Text":
            available_width = self.dimensions.width - self.style.padding * 2
            if has_image:
                available_width -= (image_width + self.style.image_padding * 2)
            self.label.setTextWidth(available_width)

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
        
        # Get border color - use display_color if available, otherwise use type color
        if hasattr(self.node, 'display_color'):
            border_color = QColor(self.node.display_color)
        else:
            border_color = NodeStyle.get_type_color(self.node.__class__.__name__)
            
        border_pen = QPen(border_color)
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
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 8px 24px;
                margin: 2px 4px;
                border-radius: 4px;
                color: #CCCCCC;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3d3d3d;
                margin: 4px 8px;
            }
            QMenu::item:disabled {
                color: #666666;
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
        transforms_menu.setStyleSheet(menu.styleSheet())  # Apply same style to submenu
        
        entity_type = self.node.__class__.__name__
        available_transforms = ENTITY_TRANSFORMS.get(entity_type, [])
        
        for transform in available_transforms:
            action = transforms_menu.addAction(transform.name)
            action.setToolTip(transform.description)
            action.triggered.connect(
                lambda checked, t=transform: self._handle_transform_action(t)
            )

        # Add separator before groups section
        menu.addSeparator()

        # Groups submenu
        groups_menu = menu.addMenu("Groups")
        groups_menu.setStyleSheet(menu.styleSheet())

        # Create group action
        create_group_action = groups_menu.addAction("Create Group")
        create_group_action.triggered.connect(self._create_group)

        # Add to group submenu
        add_to_group_menu = groups_menu.addMenu("Add to Group")
        add_to_group_menu.setStyleSheet(menu.styleSheet())
        self._populate_add_to_group_menu(add_to_group_menu)

        # Remove from group submenu
        remove_from_group_menu = groups_menu.addMenu("Remove from Group")
        remove_from_group_menu.setStyleSheet(menu.styleSheet())
        self._populate_remove_from_group_menu(remove_from_group_menu)

        # Remove from all groups action
        remove_all_groups_action = groups_menu.addAction("Remove from All Groups")
        remove_all_groups_action.triggered.connect(self._remove_from_all_groups)

        # Clear all groups action (now deletes ALL groups)
        clear_groups_action = groups_menu.addAction("Clear All Groups")
        clear_groups_action.triggered.connect(lambda: self.scene().views()[0].graph_manager.group_manager.clear_all_groups())
        
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

    @asyncSlot()
    async def update_label(self):
        """Update the node's visual appearance"""
        image_path = self.node.properties.get("image")
        if image_path:
            await self._load_image(image_path)
        self._update_layout()
        
        if hasattr(self, 'image_item') and self.image_item.pixmap():
            self._update_image_scale()
            
        # Emit update signal
        self.node_updated.emit()

    def _edit_properties(self):
        """Open property editor dialog"""
        dialog = PropertyEditor(self.node)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the updated properties
            updated_properties = dialog.get_properties()
            
            # Check if image property was removed or cleared
            old_image = self.node.properties.get("image")
            new_image = updated_properties.get("image")
            if old_image and (not new_image or new_image.strip() == ""):
                # Clear the image if URL was removed
                self.original_pixmap = None
                self.image_item.setPixmap(QPixmap())
            
            # Update the node's properties
            for key, value in updated_properties.items():
                self.node.properties[key] = value
            
            # Update the entity's label
            self.node.update_label()
            
            # Create task for updating the node
            asyncio.create_task(self._update_node_after_edit())
            
            # Notify graph manager of the update
            scene = self.scene()
            if scene and hasattr(scene.views()[0], 'graph_manager'):
                graph_manager = scene.views()[0].graph_manager
                graph_manager.update_node(self.node.id, self.node)

    async def _update_node_after_edit(self):
        """Update node after properties edit"""
        # Load image if available
        image_path = self.node.properties.get("image")
        if image_path:
            await self._load_image(image_path)
        
        # Update layout after image is loaded
        self._update_layout()
        
        # Emit update signal
        self.node_updated.emit()

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

    @asyncSlot()
    async def _load_remote_image(self, url: str):
        """Load image from URL asynchronously"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                async with aiohttp.ClientSession() as session:
                    status = StatusManager.get()
                    status.set_text(f"Loading remote image from {url}...")
                    async with session.get(url, headers=headers) as response:
                        response.raise_for_status()
                        with open(tmp_file.name, 'wb') as f:
                            while True:
                                chunk = await response.content.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                self._load_local_image(tmp_file.name)
                os.unlink(tmp_file.name)
        except Exception as e:
            status.set_text(f"Failed to load remote image: {e}")
    
    async def _search_image(self, path: str):
        url = f"https://www.bing.com/images/search?q={path}"
        async with aiohttp.ClientSession() as session:
            status = StatusManager.get()
            status.set_text(f"Searching for image {path}...")
            async with session.get(url) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                images = soup.find_all('img')
                image_urls = [img['src'] for img in images if 'src' in img.attrs]
                image_urls = [url for url in image_urls if url.startswith("http")]
                if image_urls:
                    return random.choice(image_urls).split("?")[0]
                else:
                    return None
        
    def _load_local_image(self, path: str):
        """Load image from local file"""
        if path.startswith("file://"):
            path = path[7:]
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.original_pixmap = pixmap
                self._update_layout()
    
    async def _load_image(self, image_path: str):
        if image_path:
            if image_path.startswith(("http://", "https://")):
                await self._load_remote_image(image_path)
            elif "/" not in image_path:
                image_url = await self._search_image(image_path)
                if image_url:
                    await self._load_remote_image(image_url)
                    self.node.properties["image"] = image_url
            else:
                self._load_local_image(image_path)
        else:
            self.original_pixmap = None
            self.image_item.setPixmap(QPixmap())
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
    
    def _show_delete_confirmation(self, title: str, message: str) -> bool:
        """Show a delete confirmation dialog"""
        msg_box = QMessageBox()
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2D2D30;
                color: #ffffff;
            }
            QMessageBox QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
            }
        """)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        return msg_box.exec() == QMessageBox.StandardButton.Yes

    def _delete_selected_nodes(self):
        """Delete all selected nodes"""
        if not self.scene():
            return
            
        # Get all selected nodes
        selected_nodes = [item for item in self.scene().selectedItems() 
                         if isinstance(item, NodeVisual)]
        
        # If no nodes are selected, delete just this node
        if not selected_nodes:
            if self._show_delete_confirmation("Delete Node", "Are you sure you want to delete this node?"):
                self._delete_node()
            return
            
        view = self.scene().views()[0]
        if hasattr(view, 'graph_manager'):
            # Delete all selected nodes
            if self._show_delete_confirmation("Delete Nodes", "Are you sure you want to delete these nodes?"):
                for node in selected_nodes:
                    view.graph_manager.remove_node(node.node.id)

    def _create_group(self):
        """Create a new group from selected nodes"""
        selected_nodes = [item for item in self.scene().selectedItems() 
                         if isinstance(item, NodeVisual)]
        if not selected_nodes:
            QMessageBox.warning(None, "Create Group", "Please select nodes to create a group")
            return

        dialog = QDialog(self.scene().views()[0])
        dialog.setWindowTitle("Create Group")
        layout = QVBoxLayout(dialog)

        # Group name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Group Name:")
        name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_input)
        layout.addLayout(name_layout)

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
            group_name = name_input.text().strip()
            if group_name:
                view = self.scene().views()[0]
                if hasattr(view, 'graph_manager'):
                    node_ids = [node.node.id for node in selected_nodes]
                    view.graph_manager.group_manager.create_group(group_name, node_ids)

    def _populate_add_to_group_menu(self, menu):
        """Populate the Add to Group submenu with existing groups"""
        view = self.scene().views()[0]
        if hasattr(view, 'graph_manager'):
            groups = view.graph_manager.group_manager.groups.values()
            if not groups:
                action = menu.addAction("No groups available")
                action.setEnabled(False)
            else:
                for group in groups:
                    action = menu.addAction(group.name)
                    action.triggered.connect(
                        lambda checked, g=group: self._add_to_group(g.id)
                    )

    def _populate_remove_from_group_menu(self, menu):
        """Populate the Remove from Group submenu with groups the node belongs to"""
        view = self.scene().views()[0]
        if hasattr(view, 'graph_manager'):
            node_groups = view.graph_manager.group_manager.get_node_groups(self.node.id)
            if not node_groups:
                action = menu.addAction("Not in any groups")
                action.setEnabled(False)
            else:
                for group in node_groups:
                    action = menu.addAction(group.name)
                    action.triggered.connect(
                        lambda checked, g=group: self._remove_from_group(g.id)
                    )

    def _add_to_group(self, group_id):
        """Add selected nodes to the specified group"""
        selected_nodes = [item for item in self.scene().selectedItems() 
                         if isinstance(item, NodeVisual)]
        if not selected_nodes:
            selected_nodes = [self]

        view = self.scene().views()[0]
        if hasattr(view, 'graph_manager'):
            for node in selected_nodes:
                view.graph_manager.group_manager.add_node_to_group(group_id, node.node.id)

    def _remove_from_group(self, group_id):
        """Remove selected nodes from the specified group"""
        selected_nodes = [item for item in self.scene().selectedItems() 
                         if isinstance(item, NodeVisual)]
        if not selected_nodes:
            selected_nodes = [self]

        view = self.scene().views()[0]
        if hasattr(view, 'graph_manager'):
            for node in selected_nodes:
                view.graph_manager.group_manager.remove_node_from_group(group_id, node.node.id)

    def _remove_from_all_groups(self):
        """Remove selected nodes from all their groups"""
        selected_nodes = [item for item in self.scene().selectedItems() 
                         if isinstance(item, NodeVisual)]
        if not selected_nodes:
            selected_nodes = [self]

        view = self.scene().views()[0]
        if hasattr(view, 'graph_manager'):
            for node in selected_nodes:
                node_groups = view.graph_manager.group_manager.get_node_groups(node.node.id)
                for group in node_groups:
                    view.graph_manager.group_manager.remove_node_from_group(group.id, node.node.id)