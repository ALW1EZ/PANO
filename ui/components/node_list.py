from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QColor, QPalette
import asyncio
from qasync import asyncSlot

class NodeListItem(QWidget):
    def __init__(self, node, parent=None):
        super().__init__(parent)
        self._destroyed = False
        self.node = node
        self.setup_ui()
        
        # Connect to node's update signal
        if hasattr(self.node, 'node_updated'):
            self.node.node_updated.connect(self.update_display)
        
        # Load image if available
        if not self._destroyed and self.node.node.properties.get("image"):
            asyncio.create_task(self._load_initial_image())
            
    def closeEvent(self, event):
        self._destroyed = True
        if hasattr(self.node, 'node_updated'):
            self.node.node_updated.disconnect(self.update_display)
        super().closeEvent(event)
        
    async def _load_initial_image(self):
        """Load the initial image if available"""
        if self._destroyed:
            return
            
        try:
            await self.node._load_image(self.node.node.properties.get("image"))
            if not self._destroyed:
                self.update_image()
        except Exception:
            pass  # Handle image loading errors gracefully
        
    def setup_ui(self):
        # Set fixed height for consistency
        self.setFixedHeight(220)  # Increased height
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)  # Increased margins
        layout.setSpacing(24)  # Increased spacing
        
        # Image container with background
        image_container = QFrame()
        image_container.setFixedSize(160, 160)  # Increased size
        image_container.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 10px;
            }
        """)
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(5, 5, 5, 5)
        
        # Image
        self.image_label = QLabel()
        self.image_label.setFixedSize(150, 150)  # Increased size
        self.image_label.setStyleSheet("background-color: transparent;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_layout.addWidget(self.image_label)
        layout.addWidget(image_container)
        
        # Text content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(16)  # Increased spacing
        
        # Entity type label
        type_label = QLabel(self.node.node.type_label)
        type_label.setStyleSheet("color: #888888; font-size: 16px;")  # Increased font
        text_layout.addWidget(type_label)
        
        # Main label
        self.main_label = QLabel(self.node.node.get_main_display())
        self.main_label.setStyleSheet("color: #CCCCCC; font-weight: bold; font-size: 20px;")  # Increased font
        self.main_label.setWordWrap(True)
        text_layout.addWidget(self.main_label)
        
        # Properties
        self.props_label = QLabel()
        self.props_label.setStyleSheet("""
            color: #888888; 
            font-size: 15px; 
            line-height: 160%;
            padding: 8px;
            background-color: #262626;
            border-radius: 6px;
        """)  # Enhanced style
        self.props_label.setWordWrap(True)
        self.update_properties()
        text_layout.addWidget(self.props_label)
        
        layout.addLayout(text_layout, stretch=1)
        
    def update_properties(self):
        """Update the properties display"""
        if self._destroyed:
            return
            
        props = self.node.node.get_display_properties()
        if props:
            props_text = []
            for key, value in props.items():
                if key not in ['notes', 'source', 'image'] and value:
                    props_text.append(f"<b>{key}:</b> {value}")
            if props_text:
                self.props_label.setText('<br>'.join(props_text))
                self.props_label.setVisible(True)
            else:
                self.props_label.setVisible(False)
        else:
            self.props_label.setVisible(False)
            
    def update_image(self):
        """Update the image display"""
        if self._destroyed:
            return
            
        try:
            if self.node.image_item and self.node.image_item.pixmap():
                pixmap = self.node.image_item.pixmap().scaled(
                    150, 150,  # Increased size
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.clear()
        except RuntimeError:
            # Handle case where widget was deleted
            pass
            
    @asyncSlot()
    async def update_display(self):
        """Update the display when node changes"""
        if self._destroyed:
            return
            
        try:
            # Update main label
            self.main_label.setText(self.node.node.get_main_display())
            
            # Update properties
            self.update_properties()
            
            # Update image
            self.update_image()
            
            # If image path changed, load new image
            image_path = self.node.node.properties.get("image")
            if image_path and not self._destroyed:
                await self.node._load_image(image_path)
                if not self._destroyed:
                    self.update_image()
        except RuntimeError:
            # Handle case where widget was deleted
            pass

class NodeList(QListWidget):
    def __init__(self, graph_manager, parent=None):
        super().__init__(parent)
        self._destroyed = False
        self.graph_manager = graph_manager
        self._node_items = {}  # Track node_id -> QListWidgetItem mapping
        
        self.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: none;
            }
            QListWidget::item {
                background-color: #2d2d2d;
                padding: 8px;
                margin: 4px 8px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
        """)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setUniformItemSizes(True)  # Enable uniform sizes for better performance
        self.setSpacing(4)
        
        # Connect signals
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
    def closeEvent(self, event):
        self._destroyed = True
        self._node_items.clear()
        super().closeEvent(event)
        
    @asyncSlot()
    async def refresh_nodes(self):
        """Refresh the list of nodes asynchronously"""
        if self._destroyed:
            return
            
        try:
            # Track current nodes to remove stale ones
            current_nodes = set()
            
            # Update or add nodes
            for node_id, node in self.graph_manager.nodes.items():
                if self._destroyed:
                    return
                    
                current_nodes.add(node_id)
                
                # Update existing item if present
                if node_id in self._node_items:
                    item = self._node_items[node_id]
                    widget = self.itemWidget(item)
                    if widget:
                        await widget.update_display()
                else:
                    # Create new item
                    item = QListWidgetItem(self)
                    widget = NodeListItem(node)
                    item.setSizeHint(QSize(0, 240))  # Increased size to account for padding
                    self.setItemWidget(item, widget)
                    self._node_items[node_id] = item
                
                # Let the event loop process other events
                await asyncio.sleep(0)
            
            # Remove stale nodes
            stale_nodes = set(self._node_items.keys()) - current_nodes
            for node_id in stale_nodes:
                item = self._node_items.pop(node_id)
                self.takeItem(self.row(item))
                
        except RuntimeError:
            # Handle case where widget was deleted
            pass
            
    def _on_item_clicked(self, item):
        """Handle item click - zoom to node"""
        if self._destroyed:
            return
            
        try:
            widget = self.itemWidget(item)
            if widget and self.graph_manager:
                self.graph_manager.center_on_node(widget.node)
        except RuntimeError:
            pass
            
    def _on_item_double_clicked(self, item):
        """Handle item double click - edit properties"""
        if self._destroyed:
            return
            
        try:
            widget = self.itemWidget(item)
            if widget:
                widget.node._edit_properties()
        except RuntimeError:
            pass 