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
from PyQt6.QtGui import QAction, QDrag, QIcon
import networkx as nx
from ui.views.graph_view import GraphView, NodeVisual
from entities import ENTITY_TYPES, load_entities
from transforms import TRANSFORMS, ENTITY_TRANSFORMS, load_transforms
import asyncio
import logging
from typing import Optional, Dict, Any
from qasync import QEventLoop, asyncSlot
from ui.managers.layout_manager import LayoutManager

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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PANO - Investigation Platform")
        self.selected_entity = None
        self.current_file = None
        
        # Ensure entities and transforms are loaded
        load_entities()
        load_transforms()
        
        self._setup_actions()
        self._setup_ui()
        self.resize(1200, 800)
        
        # Create layout manager
        self.layout_manager = LayoutManager(self.graph_view)
        
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
        try:
            if not self.current_file:
                file_name, _ = QFileDialog.getSaveFileName(
                    self,
                    "Save Investigation",
                    "",
                    "PANO Files (*.pano);;All Files (*)"
                )
                if not file_name:
                    return
                self.current_file = file_name
            
            # Get graph data
            graph_data = self.graph_view.graph_manager.to_dict()
            
            # Save to file
            with open(self.current_file, 'w') as f:
                json.dump(graph_data, f, indent=2)
                
            self.statusBar().showMessage(f"Investigation saved to {self.current_file}", 3000)
            logger.info(f"Investigation saved to {self.current_file}")
            
        except Exception as e:
            logger.error(f"Failed to save investigation: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Save Error", f"Failed to save investigation: {str(e)}")
    
    @asyncSlot()
    async def load_investigation(self):
        """Load an investigation from a file"""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Load Investigation",
                "",
                "PANO Files (*.pano);;All Files (*)"
            )
            if not file_name:
                return
                
            # Load from file
            with open(file_name, 'r') as f:
                graph_data = json.load(f)
            
            # Clear current graph and load new data
            self.graph_view.graph_manager.clear()
            await self.graph_view.graph_manager.from_dict(graph_data)
            
            self.current_file = file_name
            self.statusBar().showMessage(f"Investigation loaded from {file_name}", 3000)
            logger.info(f"Investigation loaded from {file_name}")
            
        except Exception as e:
            logger.error(f"Failed to load investigation: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Load Error", f"Failed to load investigation: {str(e)}")
    
    def new_investigation(self):
        """Create a new investigation"""
        try:
            self.graph_view.graph_manager.clear()
            self.current_file = None
            self.statusBar().showMessage("New investigation created", 3000)
            logger.info("New investigation created")
            
        except Exception as e:
            logger.error(f"Failed to create new investigation: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to create new investigation: {str(e)}")

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