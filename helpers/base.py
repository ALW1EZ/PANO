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
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            QLineEdit {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #777777;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666666;
            }
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
                min-height: 25px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QComboBox:on {
                border: 1px solid #777777;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                color: #ffffff;
                selection-background-color: #3d3d3d;
            }
            QListView {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QListView::item {
                padding: 5px;
            }
            QListView::item:selected {
                background-color: #3d3d3d;
            }
            QListView::item:hover {
                background-color: #353535;
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
            QTreeWidget::branch {
                background-color: transparent;
            }
            QTreeWidget::branch:has-siblings:!adjoins-item {
                border-image: url(vline.png) 0;
            }
            QTreeWidget::branch:has-siblings:adjoins-item {
                border-image: url(branch-more.png) 0;
            }
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {
                border-image: url(branch-end.png) 0;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: #2d2d2d;
            }
            QGroupBox::title {
                color: #ffffff;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                background-color: transparent;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 5px;
                background-color: transparent;
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
            QSpinBox, QDoubleSpinBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
                min-height: 25px;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 16px;
                border-left: 1px solid #555555;
                border-bottom: 1px solid #555555;
                background-color: #2d2d2d;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 16px;
                border-left: 1px solid #555555;
                background-color: #2d2d2d;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #777777;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 8px;
                background: #2d2d2d;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3d3d3d;
                border: 1px solid #555555;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #4d4d4d;
            }
            QScrollArea {
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 12px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #3d3d3d;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #2d2d2d;
                height: 12px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #3d3d3d;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px 12px;
                border: 1px solid #555555;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #3d3d3d;
            }
            QTabBar::tab:hover {
                background-color: #353535;
            }
            QVBoxLayout, QHBoxLayout, QGridLayout {
                background-color: transparent;
                spacing: 5px;
                margin: 5px;
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