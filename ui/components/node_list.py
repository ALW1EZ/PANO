from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QUrl, QTimer
from PySide6.QtGui import QPixmap, QIcon, QColor, QPalette, QDesktopServices
import asyncio
from qasync import asyncSlot
import os
from ui.views.image_viewer import ImageViewer

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
        
        # Force initial size calculation
        QTimer.singleShot(0, self._update_size)
            
    def _update_size(self):
        """Update widget size and propagate to list item"""
        if self._destroyed:
            return
            
        self.updateGeometry()
        if hasattr(self, 'list_item'):
            # Calculate content heights
            type_height = 30  # Fixed height for type label
            main_height = self.main_label.sizeHint().height()
            
            # For properties, calculate based on available width
            props_height = 0
            if self.props_label.isVisible():
                # Calculate available width for properties (total width - margins - padding)
                available_width = self.width() - 240 - 160 - 24 * 2 - 40 - 16  # notes width, image width, spacing, margins, padding
                # Force layout update to get accurate height
                self.props_label.updateGeometry()
                props_height = self.props_label.heightForWidth(available_width) or self.props_label.sizeHint().height()
            
            # For notes, use actual height only if visible
            notes_height = 0
            if self.notes_label.isVisible():
                # Force layout update to get accurate height
                self.notes_label.updateGeometry()
                notes_height = self.notes_label.heightForWidth(220) or self.notes_label.sizeHint().height()  # 240 - 20 padding
            
            # Calculate total height needed
            content_height = type_height + main_height + 40  # Base height with padding
            
            # Add container heights
            if props_height > 0:
                content_height += props_height + 32  # Add padding for properties container
            
            if notes_height > 0:
                content_height = max(content_height, notes_height + 60)  # Compare with notes height + padding
            
            # Ensure minimum height
            total_height = max(200, content_height + 40)  # Add extra padding for overall container
            
            # Update size hint
            self.list_item.setSizeHint(QSize(self.width(), total_height))
            
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
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(24)
        
        # Left side container for image
        left_container = QFrame()
        left_container.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 10px;
            }
        """)
        left_container.setFixedWidth(160)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(0)
        
        # Center container for image
        image_center = QFrame()
        image_center.setStyleSheet("background: transparent;")
        image_layout = QVBoxLayout(image_center)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)
        
        # Image
        self.image_label = QLabel()
        self.image_label.setFixedSize(150, 150)
        self.image_label.setStyleSheet("background-color: transparent;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        left_layout.addWidget(image_center, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(left_container)
        
        # Middle container for text content
        middle_container = QVBoxLayout()
        middle_container.setSpacing(16)
        
        # Entity type label
        type_label = QLabel(self.node.node.type_label)
        type_label.setStyleSheet("color: #888888; font-size: 16px;")
        type_label.setFixedHeight(30)
        middle_container.addWidget(type_label)
        
        # Main label
        self.main_label = QLabel(self.node.node.get_main_display())
        self.main_label.setStyleSheet("color: #CCCCCC; font-weight: bold; font-size: 20px;")
        self.main_label.setWordWrap(True)
        middle_container.addWidget(self.main_label)
        
        # Properties container
        props_container = QFrame()
        props_container.setStyleSheet("""
            QFrame {
                background-color: #262626;
                border-radius: 6px;
            }
        """)
        props_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        props_layout = QVBoxLayout(props_container)
        props_layout.setContentsMargins(8, 8, 8, 8)
        props_layout.setSpacing(0)
        
        # Properties label
        self.props_label = QLabel()
        self.props_label.setStyleSheet("""
            color: #888888; 
            font-size: 15px; 
            line-height: 160%;
        """)
        self.props_label.setWordWrap(True)
        self.props_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        props_layout.addWidget(self.props_label)
        
        middle_container.addWidget(props_container)
        self.update_properties()
        
        middle_container.addStretch()
        layout.addLayout(middle_container, stretch=1)
        
        # Right container for notes
        self.notes_container = QFrame()
        self.notes_container.setFixedWidth(240)
        self.notes_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.notes_container.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 10px;
            }
        """)
        notes_layout = QVBoxLayout(self.notes_container)
        notes_layout.setContentsMargins(10, 10, 10, 10)
        notes_layout.setSpacing(0)
        
        # Notes label
        self.notes_label = QLabel()
        self.notes_label.setStyleSheet("""
            color: #AAAAAA; 
            font-size: 13px;
            background-color: transparent;
        """)
        self.notes_label.setWordWrap(True)
        self.notes_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.notes_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        notes_layout.addWidget(self.notes_label)
        
        layout.addWidget(self.notes_container)
        
        # Initial notes update to hide container if no notes
        self.update_notes()
            
    def update_properties(self):
        """Update the properties display"""
        if self._destroyed:
            return
            
        props = self.node.node.get_display_properties()
        if props:
            props_text = []
            for key, value in props.items():
                if key not in ['notes', 'source', 'image'] and value:
                    # Replace newlines with HTML line breaks
                    value = value.replace('\n', '<br>')
                    props_text.append(f"<b>{key}:</b> {value}")
            if props_text:
                # Join with HTML line breaks
                self.props_label.setText('<br>'.join(props_text))
                self.props_label.setVisible(True)
            else:
                self.props_label.setText("")
                self.props_label.setVisible(False)
        else:
            self.props_label.setText("")
            self.props_label.setVisible(False)
        
        QTimer.singleShot(0, self._update_size)
            
    def update_notes(self):
        """Update the notes display"""
        if self._destroyed:
            return
            
        notes = self.node.node.properties.get('notes')
        if notes:
            # Replace newlines with HTML line breaks
            notes = notes.replace('\n', '<br>')
            self.notes_label.setText(f"<b>Notes:</b><br>{notes}")
            self.notes_label.setVisible(True)
            self.notes_container.setVisible(True)
        else:
            self.notes_label.setText("")
            self.notes_label.setVisible(False)
            self.notes_container.setVisible(False)
            
        QTimer.singleShot(0, self._update_size)
            
    def update_image(self):
        """Update the image display"""
        if self._destroyed:
            return
            
        try:
            if self.node.image_item and self.node.image_item.pixmap():
                pixmap = self.node.image_item.pixmap().scaled(
                    150, 150,
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
            
            # Update notes
            self.update_notes()
            
            # Update image
            self.update_image()
            
            # If image path changed, load new image
            image_path = self.node.node.properties.get("image")
            if image_path and not self._destroyed:
                await self.node._load_image(image_path)
                if not self._destroyed:
                    self.update_image()
            
            # Force layout update and size recalculation
            QTimer.singleShot(0, self._update_size)
                
        except RuntimeError:
            # Handle case where widget was deleted
            pass

class NodeList(QListWidget):
    def __init__(self, graph_manager, parent=None):
        super().__init__(parent)
        self._destroyed = False
        self.graph_manager = graph_manager
        self._node_items = {}  # Track node_id -> QListWidgetItem mapping
        self._image_viewers = {}  # Track node_id -> ImageViewer mapping
        
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
            QScrollBar {
                background-color: #2d2d2d;
                border: none;
            }
        """)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setSpacing(4)
        
        # Connect signals
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
    def closeEvent(self, event):
        self._destroyed = True
        # Close all open image viewers
        for viewer in self._image_viewers.values():
            viewer.close()
        self._image_viewers.clear()
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
                    widget.list_item = item  # Store reference to list item
                    item.setSizeHint(widget.sizeHint())
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
        """Handle item double click based on entity type"""
        if self._destroyed:
            return
            
        try:
            widget = self.itemWidget(item)
            if not widget:
                return
                
            # Get entity type and node id
            entity_type = widget.node.node.type_label
            node_id = widget.node.node.id
            
            # Handle different entity types
            if entity_type == 'WEBSITE':
                # Open URL in browser
                url = widget.node.node.properties.get('url')
                if url:
                    QDesktopServices.openUrl(QUrl(url))
            elif entity_type == 'USERNAME':
                # Open username in browser
                username_link = widget.node.node.properties.get('link')
                if username_link:
                    QDesktopServices.openUrl(QUrl(username_link))
            elif entity_type == 'IMAGE':
                # Check for image property
                image_path = widget.node.node.properties.get('image')
                if image_path:
                    # Check if viewer already exists for this node
                    if node_id in self._image_viewers and not self._image_viewers[node_id].isHidden():
                        # Bring existing viewer to front
                        self._image_viewers[node_id].raise_()
                        self._image_viewers[node_id].activateWindow()
                    else:
                        # Create and show new image viewer
                        viewer = ImageViewer(image_path, f"PANO - {widget.node.node.get_main_display()}")
                        viewer.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                        
                        # Connect close event to remove from tracking
                        def on_viewer_closed():
                            if node_id in self._image_viewers:
                                del self._image_viewers[node_id]
                        
                        viewer.destroyed.connect(on_viewer_closed)
                        self._image_viewers[node_id] = viewer
                        viewer.show()
            else:
                # Default behavior - edit properties
                widget.node._edit_properties()
        
        except RuntimeError:
            pass 