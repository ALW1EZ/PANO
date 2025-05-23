from datetime import datetime
import importlib
import aiofiles
import asyncio
import json
import logging
import sys
import os

from PySide6.QtCore import Qt, QPointF, QMimeData, QSize, QTimer
from PySide6.QtGui import QAction, QDrag, QIcon, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QToolBar,
    QLineEdit, QMessageBox, QFileDialog, QListWidget, QLabel,
    QSplitter, QListWidgetItem, QDockWidget, QVBoxLayout, QWidget, QStatusBar, QPushButton, QDialog,
    QComboBox, QSizePolicy, QListView, QMenu, QInputDialog, QColorDialog
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
from ui.components.node_list import NodeList
from helpers import HELPERS
from helpers.base import HelperItemDelegate

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
        self.version = "8.2.8"
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
        
        # Create node list first
        self.node_list = NodeList(None)  # We'll set the graph manager later
        
        # Create the graph view after node list
        self.graph_view = GraphView()
        
        # Create map widget last
        self.map_widget = MapVisual()
        
        # Add widgets to splitter in order
        self.vertical_splitter.addWidget(self.node_list)
        self.vertical_splitter.addWidget(self.graph_view)
        self.vertical_splitter.addWidget(self.map_widget)
        
        # Set initial sizes (0% node list, 1000% graph, 0% map at start)
        self.vertical_splitter.setSizes([0, 1000, 0])
        
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
        
        # Set graph manager for node list
        self.node_list.graph_manager = self.graph_view.graph_manager
        
        # Connect graph manager signals to node list
        self.graph_view.graph_manager.nodes_changed.connect(self.node_list.refresh_nodes)

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

        # View actions
        self.view_timeline_action = QAction("Timeline", self)
        self.view_timeline_action.setShortcut("Ctrl+T")
        self.view_timeline_action.setStatusTip("Show/Hide timeline")
        self.view_timeline_action.triggered.connect(self.view_timeline)
        self.addAction(self.view_timeline_action)  # Add to window for shortcut to work

        self.view_tools_action = QAction("Tools", self)
        self.view_tools_action.setShortcut("Ctrl+L")
        self.view_tools_action.setStatusTip("Show/Hide tools")
        self.view_tools_action.triggered.connect(self.view_tools)
        self.addAction(self.view_tools_action)  # Add to window for shortcut to work

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
        self.status_bar.setFixedHeight(25)
        
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

        Varlığıyla övündüğüm, iyi ki var dediğim dostum
        - Utku (@rhotav) Çorbacı

        Kendisinin benden haberi olmasa da,
        Şiirleri ile en çok bana destek olan
        - Sagopa Kajmer

        İşimin kolaylaşmasını sağlayan bütün kütüphane yazarlarına ve
        Yapay zekaya teşekkürler.

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
        self.tools_dock = QDockWidget("Tools", self)
        self.tools_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                  QDockWidget.DockWidgetFeature.DockWidgetFloatable)
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
        self.tools_dock.setWidget(left_widget)
        
        # Add left dock to main window
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tools_dock)
        
    def setup_toolbar(self):
        """Setup the toolbar with search and basic actions"""
        self.toolbar = QToolBar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
        # Add basic actions
        self.toolbar.addAction(self.new_action)
        self.toolbar.addAction(self.save_action)
        self.toolbar.addAction(self.load_action)
        
        # Add separator
        self.toolbar.addSeparator()
        
        # Add Windows button with menu
        windows_button = QPushButton("Windows")
        windows_menu = QMenu(self)
        windows_menu.addAction(self.view_timeline_action)
        windows_menu.addAction(self.view_tools_action)
        windows_button.clicked.connect(lambda: windows_menu.exec(windows_button.mapToGlobal(windows_button.rect().bottomLeft())))
        self.toolbar.addWidget(windows_button)
        
        # Add separator
        self.toolbar.addSeparator()
        
        # Add helper dropdown
        self.helper_combo = QComboBox()
        self.helper_combo.setMinimumWidth(200)  # Make wider
        self.helper_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.helper_combo.setEditable(True)
        self.helper_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.helper_combo.lineEdit().setPlaceholderText("Search for a helper")
        self.helper_combo.setMaxVisibleItems(10)  # Show more items at once
        
        # Set custom delegate
        delegate = HelperItemDelegate()
        self.helper_combo.setItemDelegate(delegate)
        
        # Set view mode and size
        self.helper_combo.view().setMinimumWidth(500)  # Make dropdown wider
        self.helper_combo.view().setSpacing(2)  # Add spacing between items
        
        # Initial population of helpers
        self.populate_helpers()
        
        # Setup timer for checking new helpers
        self.helper_check_timer = QTimer(self)
        self.helper_check_timer.timeout.connect(self.check_for_new_helpers)
        self.helper_check_timer.start(2000)  # Check every 2 seconds
        
        # Connect activation signal
        self.helper_combo.activated.connect(self.launch_helper)
        self.toolbar.addWidget(self.helper_combo)
        
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

    def populate_helpers(self):
        """Populate the helper combo box with available helpers"""
        # Store current text if any
        current_text = self.helper_combo.lineEdit().text()
        
        # Clear and repopulate
        self.helper_combo.clear()
        for name, helper_class in HELPERS.items():
            self.helper_combo.addItem(name, helper_class)
            
        # Restore text and clear selection
        self.helper_combo.setCurrentIndex(-1)
        self.helper_combo.lineEdit().setText(current_text)
        
    def check_for_new_helpers(self):
        """Check for new helper modules and update if needed"""
        # Reload helpers
        importlib.reload(importlib.import_module('helpers'))
        from helpers import HELPERS as new_helpers
        
        # Compare with current helpers
        current_helpers = {self.helper_combo.itemText(i): self.helper_combo.itemData(i) 
                         for i in range(self.helper_combo.count())}
        
        # Update if different
        if set(new_helpers.keys()) != set(current_helpers.keys()):
            self.populate_helpers()
            logger.info("New helpers detected and loaded")

    def launch_helper(self, index):
        """Launch the selected helper dialog"""
        helper_class = self.helper_combo.itemData(index)
        if helper_class:
            helper = helper_class(self.graph_view.graph_manager, self)
            helper.show()
            # Reset combo box
            self.helper_combo.setCurrentIndex(-1)
            self.helper_combo.lineEdit().clear()

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
            QToolBar QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                min-width: 68px;
                height: 20px;
            }
            QToolBar QPushButton:hover {
                background-color: #4d4d4d;
            }
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                color: #ffffff;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 25px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
            QMenu::item:checked {
                background-color: #404040;
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
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
                padding-right: 5px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 14px;
                height: 14px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                color: #ffffff;
                selection-background-color: #3d3d3d;
                selection-color: #ffffff;
                padding: 5px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 70px;
                padding: 8px;
                margin: 2px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #353535;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #404040;
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

            # Get timeline data - only save manually added events
            timeline_data = []
            timeline_visual = self.timeline_manager.timeline_dock.findChild(TimelineVisual)
            if timeline_visual:
                for event in timeline_visual.events:
                    # Only save events that don't have a source_entity_id (manually added events)
                    if not hasattr(event, 'source_entity_id'):
                        event_data = {
                            'name': event.name,
                            'description': event.description,
                            'start_time': event.start_time.isoformat() if isinstance(event.start_time, datetime) else event.start_time,
                            'end_time': event.end_time.isoformat() if isinstance(event.end_time, datetime) else event.end_time,
                            'color': event.color.name() if hasattr(event.color, 'name') else event.color
                        }
                        timeline_data.append(event_data)

            # Get groups data
            groups_data = self.graph_view.graph_manager.group_manager.to_dict()

            # Create investigation data
            investigation_data = {
                'nodes': nodes_data,
                'edges': edges_data,
                'timeline_events': timeline_data,
                'groups': groups_data
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
                # Only clear manually added events, keep auto-generated ones
                timeline_visual.events = [e for e in timeline_visual.events if hasattr(e, 'source_entity_id')]
                timeline_visual.update()

            # Load nodes first (this will generate entity events automatically)
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

            # Load edges
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

            # Load manually added timeline events
            if 'timeline_events' in investigation_data and timeline_visual:
                for event_data in investigation_data['timeline_events']:
                    # Parse dates from ISO format if they're strings
                    start_time = event_data['start_time']
                    end_time = event_data['end_time']
                    
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time)
                    if isinstance(end_time, str):
                        end_time = datetime.fromisoformat(end_time)
                        
                    event = TimelineEvent(
                        name=event_data['name'],
                        description=event_data['description'],
                        start_time=start_time,
                        end_time=end_time,
                        color=QColor(event_data['color'])
                    )
                    timeline_visual.add_event(event)

            # Load groups
            if 'groups' in investigation_data:
                self.graph_view.graph_manager.group_manager.from_dict(investigation_data['groups'])

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

    def view_tools(self):
        """Show/Hide the tools dock"""
        self.tools_dock.setVisible(not self.tools_dock.isVisible())
        self.tools_dock.raise_()

    def create_group(self):
        """Create a new group from selected nodes"""
        # Get selected nodes
        selected_nodes = [item for item in self.graph_view.scene.selectedItems() 
                         if isinstance(item, NodeVisual)]
        
        if not selected_nodes:
            QMessageBox.warning(self, "Create Group", "Please select nodes to group")
            return
            
        # Create dialog for group name
        name, ok = QInputDialog.getText(
            self, 
            "Create Group",
            "Enter group name:",
            QLineEdit.EchoMode.Normal,
            f"Group {len(self.graph_view.graph_manager.group_manager.groups) + 1}"
        )
        
        if ok and name:
            # Create color picker dialog
            color = QColorDialog.getColor(
                QColor("#3d3d3d"),
                self,
                "Choose Group Color"
            )
            
            if color.isValid():
                # Create group with selected nodes
                node_ids = [node.node.id for node in selected_nodes]
                self.graph_view.graph_manager.group_manager.create_group(
                    name,
                    node_ids,
                    color
                )
                
    def clear_groups(self):
        """Clear all groups"""
        if QMessageBox.question(
            self,
            "Clear Groups",
            "Are you sure you want to remove all groups?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.graph_view.graph_manager.group_manager.groups.clear()
            self.graph_view.graph_manager.group_manager.groups_changed.emit()

def configure_rendering():
    """Configure rendering mode based on user input."""
    # Check for an environment variable or command-line argument to disable GPU rendering
    if os.environ.get("DISABLE_GPU_RENDERING", "false").lower() == "true" or "--disable-gpu" in sys.argv:
        os.environ["QT_OPENGL"] = "software"
        logger.info("Software rendering mode enabled.")
    else:
        logger.info("Default rendering mode enabled.")

# Call the function before initializing the application
configure_rendering()

def main():
    """Main entry point for the application"""
    try:
        app = QApplication(sys.argv)
        
        # Create and configure event loop
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Run event loop
        with loop:
            loop.run_forever()
            
    except Exception as e:
        logger.critical(f"Application failed to start: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
