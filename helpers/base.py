from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget, QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QPointF, QRect
from PySide6.QtGui import QFontMetrics, QFont
import random

class HelperItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        # Get the default size
        size = super().sizeHint(option, index)
        # Make each item taller to accommodate two lines
        size.setHeight(70)
        return size
        
    def paint(self, painter, option, index):
        if not index.isValid():
            return
            
        # Get item data
        helper_class = index.data(Qt.ItemDataRole.UserRole)
        if not helper_class:
            return
            
        # Get name and description
        name = helper_class.name
        description = helper_class.description
        
        # Draw selection background if selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            
        # Set text color
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())
            
        # Calculate text rectangles
        name_rect = QRect(option.rect)
        name_rect.setHeight(35)
        desc_rect = QRect(option.rect)
        desc_rect.setTop(option.rect.top() + 35)
        desc_rect.setHeight(35)
        
        # Add padding
        padding = 10
        name_rect.setLeft(name_rect.left() + padding)
        desc_rect.setLeft(desc_rect.left() + padding)
        
        # Draw name with larger font
        name_font = QFont(painter.font())
        name_font.setPointSize(13)
        name_font.setBold(True)
        painter.setFont(name_font)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        
        # Draw description with smaller font
        desc_font = QFont(painter.font())
        desc_font.setPointSize(11)
        desc_font.setItalic(True)
        painter.setFont(desc_font)
        painter.drawText(desc_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, description)

class BaseHelper(QDialog):
    name = "Base Helper"
    description = "Base class for all helpers"
    
    def __init__(self, graph_manager, parent=None):
        super().__init__(parent)
        self.graph_manager = graph_manager
        self.setWindowTitle(self.name)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Set default theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
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
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
            }
            QListView {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QPlainTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
                selection-background-color: #3d3d3d;
            }
            QPlainTextEdit:focus {
                border: 1px solid #777777;
            }
            QTreeWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QTreeWidget::item {
                color: #ffffff;
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #3d3d3d;
            }
            QTreeWidget::item:hover {
                background-color: #353535;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                color: #ffffff;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 2px;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #777777;
            }
        """)
        
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.setup_ui()
        
    def setup_ui(self):
        """Override this method to setup the helper's UI"""
        pass
        
    def add_to_graph(self, entities):
        """Add entities to the graph with automatic positioning
        Args:
            entities: List of entity objects to add to graph
        """
        # Get the view center
        view_center = self.graph_manager.view.mapToScene(
            self.graph_manager.view.viewport().rect().center()
        )
        
        # Add each entity with a slight random offset from center
        for i, entity in enumerate(entities):
            # Create random offset from center (-100 to 100 pixels)
            offset_x = random.uniform(-100, 100)
            offset_y = random.uniform(-100, 100)
            
            # Calculate position
            pos = QPointF(view_center.x() + offset_x, view_center.y() + offset_y)
            
            # Add node to graph
            self.graph_manager.add_node(entity, pos) 