from datetime import datetime
import sys
import os
import json
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QToolBar,
    QLineEdit, QMessageBox, QFileDialog, QListWidget, QLabel,
    QSplitter, QListWidgetItem, QDockWidget, QVBoxLayout, QWidget
)
from PyQt6.QtCore import Qt, QPointF, QMimeData, QSize
from PyQt6.QtGui import QAction, QDrag, QIcon, QColor
import networkx as nx
from ui.views.graph_view import GraphView, NodeVisual
from entities import ENTITY_TYPES, load_entities
from transforms import TRANSFORMS, ENTITY_TRANSFORMS, load_transforms
import asyncio
import logging
from typing import Optional, Dict, Any
from qasync import QEventLoop, asyncSlot
from ui.managers.layout_manager import LayoutManager
from ui.managers.timeline_manager import TimelineManager
import aiofiles

from ui.views.graph_view import GraphView, NodeVisual, EdgeVisual
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QVBoxLayout, QWidget, QToolBar,
    QLineEdit, QMessageBox, QListWidget, QLabel, 
    QSplitter, QListWidgetItem, QFileDialog
)
from PyQt6.QtCore import Qt, QPointF, QMimeData, QSize
from PyQt6.QtGui import QAction, QDrag, QIcon
import networkx as nx
from ui.views.graph_view import GraphView, NodeVisual
from entities import ENTITY_TYPES, load_entities
from transforms import TRANSFORMS, ENTITY_TRANSFORMS, load_transforms
import json
import os
import math
import logging
from typing import Optional, Dict, Any
from qasync import QEventLoop, asyncSlot
from ui.managers.layout_manager import LayoutManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DraggableEntityList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setIconSize(QSize(24, 24))
        self.populate_entities()
        
    def populate_entities(self):
        """Populate the entity list with available entity types"""
        self.clear()
        for entity_name, entity_class in ENTITY_TYPES.items():
            item = QListWidgetItem(entity_name)
            item.setData(Qt.ItemDataRole.UserRole, entity_name)
            
            # # Set icon if available
            # if hasattr(entity_class, 'icon'):
            #     icon_path = os.path.join(os.path.dirname(__file__), entity_class.icon)
            #     if os.path.exists(icon_path):
            #         item.setIcon(QIcon(icon_path))
            
            # Set description as tooltip if available
            # if hasattr(entity_class, 'description'):
            #     item.setToolTip(entity_class.description)
            
            self.addItem(item)
            
    def startDrag(self, actions):
        item = self.currentItem()
        if item is None:
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        entity_name = item.data(Qt.ItemDataRole.UserRole)
        mime_data.setData("application/x-entity", entity_name.encode())
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        # If it's already a string in ISO format, return it as is
        if isinstance(obj, str) and 'T' in obj and obj.count('-') == 2:
            return obj
        return super().default(obj)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PANO - Platform for Analysis and Network Operations")
        self.selected_entity = None
        self.current_file = None
        
        # Ensure entities and transforms are loaded
        load_entities()
        load_transforms()
        
        self._setup_actions()
        self._setup_ui()
        self.resize(1200, 800)
        
        # Create managers
        self.layout_manager = LayoutManager(self.graph_view)
        self.timeline_manager = TimelineManager(self)
        
        logger.info("PANO initialized successfully")
        
    def _setup_ui(self):
        """Setup the main UI components"""
        # Set application style
        self.setStyleSheet(self._get_stylesheet())
        
        # Create the graph view
        self.graph_view = GraphView()
        self.setCentralWidget(self.graph_view)
        
        # Create left dock widget with entities and transforms
        self.setup_left_dock()
        
        # Create toolbar
        self.setup_toolbar()
        
    def setup_left_dock(self):
        """Setup the left dock with entities and transforms"""
        left_dock = QDockWidget("Tools", self)
        left_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Create splitter for entities and transforms
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Upper part - Entities
        entities_widget = QWidget()
        entities_layout = QVBoxLayout(entities_widget)
        entities_label = QLabel("Entities")
        entities_label.setStyleSheet("color: white; font-weight: bold; padding: 5px;")
        self.entities_list = DraggableEntityList()
        entities_layout.addWidget(entities_label)
        entities_layout.addWidget(self.entities_list)
        
        # Lower part - Transforms
        transforms_widget = QWidget()
        transforms_layout = QVBoxLayout(transforms_widget)
        transforms_label = QLabel("Transforms")
        transforms_label.setStyleSheet("color: white; font-weight: bold; padding: 5px;")
        self.transforms_list = QListWidget()
        transforms_layout.addWidget(transforms_label)
        transforms_layout.addWidget(self.transforms_list)
        
        # Add widgets to splitter
        splitter.addWidget(entities_widget)
        splitter.addWidget(transforms_widget)
        
        # Add splitter to left dock
        left_layout.addWidget(splitter)
        left_dock.setWidget(left_widget)
        
        # Add left dock to main window
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, left_dock)
        
        # Connect transform list double click
        self.transforms_list.itemDoubleClicked.connect(self._handle_transform_selected)
        
    def _handle_transform_selected(self, item):
        """Handle transform selection from the transforms list"""
        if not self.selected_entity:
            self.statusBar().showMessage("No entity selected", 3000)
            return
            
        transform = item.data(Qt.ItemDataRole.UserRole)
        if not transform:
            return
            
        try:
            # Get the node visual
            node_visual = self.graph_view.graph_manager.nodes.get(self.selected_entity.id)
            if node_visual:
                # Create and run coroutine
                loop = asyncio.get_event_loop()
                loop.create_task(node_visual._execute_transform(transform))
            else:
                self.statusBar().showMessage("Node visual not found", 3000)
        except Exception as e:
            logger.error(f"Transform execution failed: {str(e)}", exc_info=True)
            self.statusBar().showMessage(f"Transform error: {str(e)}", 3000)
            QMessageBox.critical(self, "Transform Error", str(e))
            
    def update_transforms_list(self, entity):
        """Update the transforms list based on the selected entity"""
        self.transforms_list.clear()
        self.selected_entity = entity
        
        if entity is None:
            return
            
        # Get available transforms for the entity type
        entity_type = entity.__class__.__name__
        available_transforms = ENTITY_TRANSFORMS.get(entity_type, [])
        
        for transform in available_transforms:
            item = QListWidgetItem(transform.name)
            item.setToolTip(transform.description)
            item.setData(Qt.ItemDataRole.UserRole, transform)
            self.transforms_list.addItem(item)
    
    def _setup_actions(self):
        """Setup application actions"""
        self.new_action = QAction("New", self)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.setStatusTip("Create new investigation")
        self.new_action.triggered.connect(self.new_investigation)
        
        self.save_action = QAction("Save", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.setStatusTip("Save current investigation")
        self.save_action.triggered.connect(self.save_investigation)
        
        self.load_action = QAction("Load", self)
        self.load_action.setShortcut("Ctrl+O")
        self.load_action.setStatusTip("Load investigation")
        self.load_action.triggered.connect(self.load_investigation)
        
        # Create status bar
        self.statusBar()
    
    def setup_toolbar(self):
        """Setup the toolbar with search and basic actions"""
        self.toolbar = QToolBar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
        # Add search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Start smart search")
        self.search_bar.setMinimumWidth(200)
        self.toolbar.addWidget(self.search_bar)
        
        # Add basic actions
        self.toolbar.addAction(self.new_action)
        self.toolbar.addAction(self.save_action)
        self.toolbar.addAction(self.load_action)
        
        # Add separator
        self.toolbar.addSeparator()
        
        # Add layout actions
        self.circular_layout_action = QAction("Circular", self)
        self.circular_layout_action.setStatusTip("Arrange nodes in a circle")
        self.circular_layout_action.triggered.connect(self.apply_circular_layout)
        self.toolbar.addAction(self.circular_layout_action)
        
        self.hierarchical_layout_action = QAction("Hierarchical", self)
        self.hierarchical_layout_action.setStatusTip("Arrange nodes in a hierarchical tree")
        self.hierarchical_layout_action.triggered.connect(self.apply_hierarchical_layout)
        self.toolbar.addAction(self.hierarchical_layout_action)
        
        self.grid_layout_action = QAction("Grid", self)
        self.grid_layout_action.setStatusTip("Arrange nodes in a grid")
        self.grid_layout_action.triggered.connect(self.apply_grid_layout)
        self.toolbar.addAction(self.grid_layout_action)
        
        self.radial_layout_action = QAction("Radial", self)
        self.radial_layout_action.setStatusTip("Arrange nodes in a radial tree layout")
        self.radial_layout_action.triggered.connect(self.apply_radial_layout)
        self.toolbar.addAction(self.radial_layout_action)
        
        self.force_directed_action = QAction("Force-Directed", self)
        self.force_directed_action.setStatusTip("Apply force-directed layout algorithm")
        self.force_directed_action.triggered.connect(self.apply_force_directed_layout)
        self.toolbar.addAction(self.force_directed_action)
    
    def _get_stylesheet(self) -> str:
        """Get the application stylesheet"""
        return """
            * {
                font-family: 'Geist Mono', monospace;
                font-size: 13px;
            }
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QToolBar {
                background-color: #2d2d2d;
                border: none;
                spacing: 3px;
                padding: 3px;
            }
            QToolBar QToolButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QToolBar QToolButton:hover {
                background-color: #4d4d4d;
            }
            QLineEdit {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QDockWidget {
                color: #ffffff;
                titlebar-close-icon: url(close.png);
            }
            QDockWidget::title {
                background-color: #2d2d2d;
                padding: 8px;
            }
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
            QSplitter::handle {
                background-color: #2d2d2d;
            }
            QMessageBox {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """
    
    @asyncSlot()
    async def save_investigation(self):
        """Save the current investigation to a file"""
        if not self.current_file:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save Investigation",
                "",
                "PANO Files (*.pano);;All Files (*)"
            )
            if not file_name:
                return
            if not file_name.endswith('.pano'):
                file_name += '.pano'
            self.current_file = file_name

        try:
            # Get graph data
            nodes_data = []
            edges_data = []
            
            # Save nodes with all properties
            for node_id, node in self.graph_view.graph_manager.nodes.items():
                node_data = {
                    'id': node_id,
                    'entity_type': node.node.__class__.__name__,
                    'properties': node.node.to_dict(),
                    'pos': {
                        'x': node.pos().x(),
                        'y': node.pos().y()
                    }
                }
                nodes_data.append(node_data)
            
            # Save edges with all properties including style and relationship
            for edge_id, edge in self.graph_view.graph_manager.edges.items():
                edge_data = {
                    'id': edge_id,
                    'source': edge.source.node.id,
                    'target': edge.target.node.id,
                    'relationship': getattr(edge, 'relationship', ''),
                    'style': {
                        'pen_style': edge.style.style.value if hasattr(edge.style, 'style') else Qt.PenStyle.SolidLine.value,
                        'color': edge.style.color.name() if hasattr(edge.style, 'color') else '#000000',
                        'width': getattr(edge.style, 'width', 1)
                    }
                }
                
                # Add optional properties if they exist
                if hasattr(edge, 'label'):
                    edge_data['label'] = edge.label
                if hasattr(edge, 'properties'):
                    edge_data['properties'] = edge.properties
                
                edges_data.append(edge_data)

            # Create investigation data
            investigation_data = {
                'nodes': nodes_data,
                'edges': edges_data,
                'timeline_events': self.timeline_manager.serialize_events()
            }

            # Save to file
            async with aiofiles.open(self.current_file, 'w') as f:
                await f.write(json.dumps(investigation_data, indent=2, cls=DateTimeEncoder))

            self.statusBar().showMessage(f"Investigation saved to {self.current_file}", 3000)
            logger.info(f"Investigation saved to {self.current_file}")

        except Exception as e:
            logger.error(f"Failed to save investigation: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Save Error", f"Failed to save investigation: {str(e)}")
    
    @asyncSlot()
    async def load_investigation(self):
        """Load an investigation from a file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load Investigation",
            "",
            "PANO Files (*.pano);;All Files (*)"
        )
        if not file_name:
            return

        try:
            async with aiofiles.open(file_name, 'r') as f:
                content = await f.read()
                investigation_data = json.loads(content)

            # Clear existing graph
            self.graph_view.graph_manager.clear()
            self.timeline_manager.clear_events()

            # Load nodes
            nodes = {}
            for node_data in investigation_data['nodes']:
                entity_type = ENTITY_TYPES[node_data['entity_type']]
                properties = node_data['properties']
                properties['_id'] = node_data['id']  # Set ID in properties before creating entity
                entity = entity_type.from_dict(properties)
                pos = QPointF(node_data['pos']['x'], node_data['pos']['y'])
                node = self.graph_view.graph_manager.add_node(entity, pos)
                nodes[node_data['id']] = node

            # Load edges with all properties
            for edge_data in investigation_data['edges']:
                source_id = edge_data['source']
                target_id = edge_data['target']
                
                # Create edge with relationship
                edge = self.graph_view.graph_manager.add_edge(
                    source_id, 
                    target_id,
                    edge_data.get('relationship', '')
                )
                
                if edge and 'style' in edge_data:
                    # Restore edge style
                    style_data = edge_data['style']
                    edge.style.style = Qt.PenStyle(style_data['pen_style'])
                    edge.style.color = QColor(style_data['color'])
                    edge.style.width = style_data['width']
                    edge.update()  # Ensure the edge is redrawn with new style
                
                if edge and 'label' in edge_data:
                    edge.label = edge_data['label']
                    edge.update()
                
                if edge and 'properties' in edge_data:
                    edge.properties = edge_data['properties']

            # Load timeline events
            if 'timeline_events' in investigation_data:
                self.timeline_manager.deserialize_events(investigation_data['timeline_events'])

            self.current_file = file_name
            self.statusBar().showMessage(f"Investigation loaded from {file_name}", 3000)
            logger.info(f"Investigation loaded from {file_name}")

        except Exception as e:
            logger.error(f"Failed to load investigation: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Load Error", f"Failed to load investigation: {str(e)}")
    
    def new_investigation(self):
        """Create a new investigation"""
        if QMessageBox.question(self, "Clear Investigation", "Are you sure you want to clear the current investigation?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.graph_view.graph_manager.clear()
            self.timeline_manager.clear_events()
            self.current_file = None
            self.statusBar().showMessage("New investigation created", 3000)
            logger.info("New investigation created")

    def apply_circular_layout(self):
        """Arrange nodes in a circular layout"""
        if hasattr(self, 'layout_manager'):
            self.layout_manager.apply_circular_layout()

    def apply_hierarchical_layout(self):
        """Arrange nodes in a hierarchical tree layout"""
        if hasattr(self, 'layout_manager'):
            self.layout_manager.apply_hierarchical_layout()

    def apply_grid_layout(self):
        """Arrange nodes in a grid layout"""
        if hasattr(self, 'layout_manager'):
            self.layout_manager.apply_grid_layout()
            
    def apply_radial_layout(self):
        """Arrange nodes in a radial tree layout"""
        if hasattr(self, 'layout_manager'):
            self.layout_manager.apply_radial_tree_layout()
            
    def apply_force_directed_layout(self):
        """Apply force-directed layout"""
        if hasattr(self, 'layout_manager'):
            self.layout_manager.apply_force_directed_layout()

def main():
    """Main entry point for the application"""
    try:
        app = QApplication(sys.argv)
        
        # Create async event loop
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Run event loop
        with loop:
            sys.exit(loop.run_forever())
            
    except Exception as e:
        logger.critical(f"Application failed to start: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 