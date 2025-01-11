from datetime import datetime
import aiofiles
import asyncio
import json
import logging
import sys
from PySide6.QtCore import Qt, QPointF, QMimeData, QSize, QTimer
from PySide6.QtGui import QAction, QDrag, QIcon, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QToolBar,
    QLineEdit, QMessageBox, QFileDialog, QListWidget, QLabel,
    QSplitter, QListWidgetItem, QDockWidget, QVBoxLayout, QWidget, QStatusBar, QPushButton, QDialog
)
from qasync import QEventLoop, asyncSlot

from entities import ENTITY_TYPES, load_entities
from transforms import ENTITY_TRANSFORMS, load_transforms
from ui.components.map_visual import MapVisual
from ui.components.timeline_visual import TimelineVisual, TimelineEvent
from ui.managers.layout_manager import LayoutManager
from ui.managers.map_manager import MapManager
from ui.managers.timeline_manager import TimelineManager
from ui.managers.status_manager import StatusManager
from ui.views.graph_view import GraphView, NodeVisual, EdgeVisual
from ui.components.ai_dock import AIDock

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
        self.version = "5.3.1"
        self.setWindowTitle(f"PANO - Platform for Analysis and Network Operations | v{self.version}")
        self.selected_entity = None
        self.current_file = None
        
        # Ensure entities and transforms are loaded
        load_entities()
        load_transforms()
        
        # Setup initial UI components
        self._setup_actions()
        self._init_ui_components()
        
        # Create managers first
        self._setup_managers()
        
        # Now setup the complete UI with managers
        self._setup_ui()
        
        self.resize(1200, 800)
        logger.info("PANO initialized successfully")
        
    def _init_ui_components(self):
        """Initialize basic UI components needed by managers"""
        # Create central widget with splitter
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create vertical splitter
        self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create map widget first
        self.map_widget = MapVisual()
        
        # Create the graph view after map widget
        self.graph_view = GraphView()
        
        # Add widgets to splitter in order
        self.vertical_splitter.addWidget(self.graph_view)
        self.vertical_splitter.addWidget(self.map_widget)
        
        # Set initial sizes (100% graph, 0% map at start)
        self.vertical_splitter.setSizes([1000, 0])
        
        central_layout.addWidget(self.vertical_splitter)
        self.setCentralWidget(central_widget)
        
    def _setup_managers(self):
        """Setup all managers"""
        # Create managers in correct order
        self.layout_manager = LayoutManager(self.graph_view)
        self.timeline_manager = TimelineManager(self)
        self.map_manager = MapManager(self.map_widget)
        
        # Connect map manager to graph manager
        self.graph_view.graph_manager.set_map_manager(self.map_manager)
        
    def _setup_ui(self):
        """Setup the complete UI with managers"""
        # Set application style
        self.setStyleSheet(self._get_stylesheet())
        
        # Create left dock widget with entities and transforms
        self.setup_left_dock()
        
        # Create toolbar
        self.setup_toolbar()

        # Create status bar
        self.setup_status_bar()

    def setup_status_bar(self):
        """Setup the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Initialize global status manager
        StatusManager.initialize(self.status_bar)
        
        # Connect about label double click
        StatusManager.get().about_label.mouseDoubleClickEvent = lambda e: self.show_about_dialog()

    def show_about_dialog(self):
        """Show floating about dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("About")
        dialog.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"PANO v{self.version}"))
        layout.addWidget(QLabel("Platform for Analysis and Network Operations"))
        layout.addWidget(QLabel(""))

        all_about_text = """
        Olay zaman analizi ve açık kaynak istihbaratı için yazdığım PANO'yu
        Yazarken yakınımda olmayan herkese teşekkürler.
        Onlar her zaman benim yanımda oldular.

        Kendisini her zaman idol gördüğüm, ne zaman çaresiz kalsam
        O ne yapardı diye düşündüğüm, anılarını dinleyerek büyüdüğüm,
        "Halk kendinin polisidir." sözüyle beni derinden etkilemiş,
        Çok özlediğim başkomiser
        - Babam

        Her şeye rağmen, beni koşulsuz şartsız seven ve destekleyen
        - Annem

        İki arkadaşımdan biri olan
        - U

        İki arkadaşımdan bir diğeri olan
        - Rhotav

        Kendisinin benden haberi olmasa da, bana şarkıları ile destek olan
        - Sagopa Kajmer

        Ve işimin kolaylaşmasını sağlayan bütün kütüphane yazarlarına teşekkürler.

                                                                        - ALW1EZ
        """
        layout.addWidget(QLabel(all_about_text))

        # add a close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.show()

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
        
        # Lower part - AI Dock
        ai_dock_widget = QWidget()
        ai_dock_layout = QVBoxLayout(ai_dock_widget)
        ai_label = QLabel("PANAI")
        ai_label.setStyleSheet("color: white; font-weight: bold; padding: 5px;")
        ai_dock_layout.addWidget(ai_label)
        self.ai_dock = AIDock(self.graph_view.graph_manager, self.timeline_manager)
        ai_dock_layout.addWidget(self.ai_dock)
        
        # Add widgets to splitter
        splitter.addWidget(entities_widget)
        splitter.addWidget(ai_dock_widget)
        
        # Add splitter to left dock
        left_layout.addWidget(splitter)
        left_dock.setWidget(left_widget)
        
        # Add left dock to main window
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, left_dock)
        
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

        self.view_timeline_action = QAction("Timeline", self)
        self.view_timeline_action.setShortcut("Ctrl+T")
        self.view_timeline_action.setStatusTip("Show/Hide timeline")
        self.view_timeline_action.triggered.connect(self.view_timeline)
    
    def setup_toolbar(self):
        """Setup the toolbar with search and basic actions"""
        self.toolbar = QToolBar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
        # Add basic actions
        self.toolbar.addAction(self.new_action)
        self.toolbar.addAction(self.save_action)
        self.toolbar.addAction(self.load_action)
        self.toolbar.addAction(self.view_timeline_action)

        # Add separator
        self.toolbar.addSeparator()

        # Add search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Start smart search")
        self.search_bar.setMinimumWidth(200)
        self.toolbar.addWidget(self.search_bar)
        
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
            QStatusBar {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QStatusBar QLabel {
                color: #ffffff;
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
            status = StatusManager.get()
            status.set_text("Saving investigation...")
            
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
                'edges': edges_data
            }

            # Save to file
            async with aiofiles.open(self.current_file, 'w') as f:
                await f.write(json.dumps(investigation_data, indent=2, cls=DateTimeEncoder))

            status.set_text(f"Investigation saved to {self.current_file}")

        except Exception as e:
            logger.error(f"Failed to save investigation: {str(e)}", exc_info=True)
            status.set_text("Failed to save investigation")
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
            status = StatusManager.get()
            status.set_text("Loading investigation...")
            
            async with aiofiles.open(file_name, 'r') as f:
                content = await f.read()
                investigation_data = json.loads(content)

            # Clear existing graph
            self.graph_view.graph_manager.clear()
            timeline_visual = self.timeline_manager.timeline_dock.findChild(TimelineVisual)
            if timeline_visual:
                timeline_visual.events.clear()
                timeline_visual.update()

            # Load nodes
            nodes = {}
            for node_data in investigation_data['nodes']:
                entity_type = ENTITY_TYPES[node_data['entity_type']]
                properties = node_data['properties']
                properties['_id'] = node_data['id']  # Set ID in properties before creating entity
                entity = entity_type.from_dict(properties)
                entity.update_label()  # Ensure label is properly set
                pos = QPointF(node_data['pos']['x'], node_data['pos']['y'])
                node = self.graph_view.graph_manager.add_node(entity, pos)
                node.update_label()  # Update the visual representation
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

            self.current_file = file_name
            status.set_text(f"Investigation loaded from {file_name}")

        except Exception as e:
            logger.error(f"Failed to load investigation: {str(e)}", exc_info=True)
            status.set_text("Failed to load investigation")
            QMessageBox.critical(self, "Load Error", f"Failed to load investigation: {str(e)}")

    def view_timeline(self):
        """View the timeline"""
        # Show/Hide the timeline dock
        self.timeline_manager.timeline_dock.setVisible(not self.timeline_manager.timeline_dock.isVisible())
        self.timeline_manager.timeline_dock.raise_()

    def new_investigation(self):
        """Create a new investigation"""
        if QMessageBox.question(self, "Clear Investigation", "Are you sure you want to clear the current investigation?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.graph_view.graph_manager.clear()
            timeline_visual = self.timeline_manager.timeline_dock.findChild(TimelineVisual)
            if timeline_visual:
                timeline_visual.events.clear()
                timeline_visual.update()
            self.current_file = None
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