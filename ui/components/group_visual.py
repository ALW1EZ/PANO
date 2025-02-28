from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QBrush
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget, QMessageBox
import math

class GroupVisual(QGraphicsItem):
    """Visual representation of a node group"""
    
    def __init__(self, group, graph_manager, parent=None):
        super().__init__(parent)
        self.group = group
        self.graph_manager = graph_manager
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)  # Draw behind nodes
        self.padding = 40  # Padding around grouped nodes
        self.header_height = 30  # Height of group header
        self.is_hovered = False
        self.delete_button_hovered = False
        self.stored_positions = {}  # Store original positions of nodes
        
    def boundingRect(self) -> QRectF:
        """Get the bounding rectangle of the group"""
        if not self.group.nodes:
            return QRectF()
            
        # Get positions of all nodes in group
        positions = []
        for node_id in self.group.nodes:
            if node_id in self.graph_manager.nodes:
                node = self.graph_manager.nodes[node_id]
                rect = node.boundingRect()
                pos = node.pos()
                positions.append(QRectF(
                    pos.x() + rect.x(),
                    pos.y() + rect.y(),
                    rect.width(),
                    rect.height()
                ))
                
        if not positions:
            return QRectF()
            
        # Calculate bounding rectangle that encompasses all nodes
        left = min(rect.left() for rect in positions)
        top = min(rect.top() for rect in positions)
        right = max(rect.right() for rect in positions)
        bottom = max(rect.bottom() for rect in positions)
        
        # Add padding and header
        return QRectF(
            left - self.padding,
            top - self.padding - self.header_height,
            right - left + 2 * self.padding,
            bottom - top + 2 * self.padding + self.header_height
        )
        
    def shape(self) -> QPainterPath:
        """Get the shape for collision detection"""
        path = QPainterPath()
        rect = self.boundingRect()
        if not rect.isEmpty():
            path.addRoundedRect(rect, 15, 15)
        return path
        
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        """Paint the group visual"""
        rect = self.boundingRect()
        if rect.isEmpty():
            return
            
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw group background
        background_color = self.group.color.darker(110) if self.is_hovered else self.group.color
        background_color.setAlpha(40)  # Make semi-transparent
        painter.setBrush(QBrush(background_color))
        
        # Draw border
        border_color = self.group.color.lighter(120) if self.is_hovered else self.group.color
        border_color.setAlpha(100)
        painter.setPen(QPen(border_color, 2, Qt.PenStyle.SolidLine))
        
        # Draw rounded rectangle
        painter.drawRoundedRect(rect, 15, 15)
        
        # Draw header
        header_rect = QRectF(
            rect.left(),
            rect.top(),
            rect.width(),
            self.header_height
        )
        
        # Draw header text
        painter.setPen(QPen(QColor(230, 230, 230, 180)))
        painter.setFont(widget.font() if widget else painter.font())
        text = f"{self.group.name} ({len(self.group.nodes)} nodes)"
        
        # Calculate text width to position buttons
        text_width = painter.fontMetrics().horizontalAdvance(text)
        text_x = header_rect.left() + (header_rect.width() - text_width) / 2
        painter.drawText(QPointF(text_x, header_rect.top() + self.header_height * 0.7), text)
        
        # Draw expand/collapse indicator
        if self.group.nodes:
            indicator_size = 16
            indicator_rect = QRectF(
                rect.right() - indicator_size - 10,
                rect.top() + (self.header_height - indicator_size) / 2,
                indicator_size,
                indicator_size
            )
            
            painter.setPen(QPen(QColor(230, 230, 230, 180), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Draw circle
            painter.drawEllipse(indicator_rect)
            
            # Draw plus/minus
            line_padding = 4
            center = indicator_rect.center()
            
            # Horizontal line
            painter.drawLine(
                QPointF(center.x() - indicator_size/2 + line_padding, center.y()),
                QPointF(center.x() + indicator_size/2 - line_padding, center.y())
            )
            
            # Vertical line (only if collapsed)
            if not self.group.expanded:
                painter.drawLine(
                    QPointF(center.x(), center.y() - indicator_size/2 + line_padding),
                    QPointF(center.x(), center.y() + indicator_size/2 - line_padding)
                )
            
            # Draw delete button (X) when expanded
            if self.group.expanded:
                delete_size = 16
                self.delete_rect = QRectF(
                    rect.right() - indicator_size - delete_size - 20,
                    rect.top() + (self.header_height - delete_size) / 2,
                    delete_size,
                    delete_size
                )
                
                # Draw delete button background when hovered
                if self.delete_button_hovered:
                    painter.setBrush(QBrush(QColor(255, 50, 50, 100)))
                    painter.setPen(QPen(QColor(255, 50, 50, 180), 2))
                else:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.setPen(QPen(QColor(230, 230, 230, 180), 2))
                
                painter.drawEllipse(self.delete_rect)
                
                # Draw X
                x_padding = 4
                x_center = self.delete_rect.center()
                painter.drawLine(
                    QPointF(x_center.x() - delete_size/2 + x_padding, x_center.y() - delete_size/2 + x_padding),
                    QPointF(x_center.x() + delete_size/2 - x_padding, x_center.y() + delete_size/2 - x_padding)
                )
                painter.drawLine(
                    QPointF(x_center.x() - delete_size/2 + x_padding, x_center.y() + delete_size/2 - x_padding),
                    QPointF(x_center.x() + delete_size/2 - x_padding, x_center.y() - delete_size/2 + x_padding)
                )
                
    def hoverEnterEvent(self, event) -> None:
        """Handle hover enter event"""
        self.is_hovered = True
        self.update_delete_button_hover(event.pos())
        self.update()
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event) -> None:
        """Handle hover leave event"""
        self.is_hovered = False
        self.delete_button_hovered = False
        self.update()
        super().hoverLeaveEvent(event)
        
    def hoverMoveEvent(self, event) -> None:
        """Handle hover move event"""
        self.update_delete_button_hover(event.pos())
        super().hoverMoveEvent(event)
        
    def update_delete_button_hover(self, pos) -> None:
        """Update delete button hover state"""
        if hasattr(self, 'delete_rect') and self.group.expanded:
            was_hovered = self.delete_button_hovered
            self.delete_button_hovered = self.delete_rect.contains(pos)
            if was_hovered != self.delete_button_hovered:
                self.update()
        
    def mousePressEvent(self, event) -> None:
        """Handle mouse press event"""
        rect = self.boundingRect()
        if not rect.isEmpty():
            # Check if click is on delete button
            if hasattr(self, 'delete_rect') and self.group.expanded and self.delete_rect.contains(event.pos()):
                # Confirm deletion with sheet
                if QMessageBox.question(
                    None,
                    "Delete Group",
                    f"Are you sure you want to delete the group '{self.group.name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                ) == QMessageBox.StandardButton.Yes:
                    self.graph_manager.group_manager.delete_group(self.group.id)
                event.accept()
                return
                
            # Check if click is in header area
            header_rect = QRectF(
                rect.left(),
                rect.top(),
                rect.width(),
                self.header_height
            )
            
            if header_rect.contains(event.pos()):
                # Calculate current group center before toggling
                if self.group.nodes:
                    total_x = 0
                    total_y = 0
                    for node_id in self.group.nodes:
                        if node_id in self.graph_manager.nodes:
                            node = self.graph_manager.nodes[node_id]
                            pos = node.pos()
                            total_x += pos.x()
                            total_y += pos.y()
                    avg_x = total_x / len(self.group.nodes)
                    avg_y = total_y / len(self.group.nodes)
                    self.group.center = QPointF(avg_x, avg_y)

                # Toggle group expansion
                self.group.expanded = not self.group.expanded
                
                if not self.group.expanded:
                    # Collapse: Store current positions and move nodes to group center
                    self.stored_positions.clear()
                    
                    # Get all nodes and their sizes
                    node_sizes = []
                    for node_id in self.group.nodes:
                        if node_id in self.graph_manager.nodes:
                            node = self.graph_manager.nodes[node_id]
                            rect = node.boundingRect()
                            size = rect.width() * rect.height()  # Calculate area
                            node_sizes.append((node_id, size))
                    
                    # Sort nodes by size in descending order (largest first)
                    node_sizes.sort(key=lambda x: x[1], reverse=True)
                    
                    # Set z-values and positions based on size
                    base_z = -1  # Start below the group visual
                    for i, (node_id, _) in enumerate(node_sizes):
                        node = self.graph_manager.nodes[node_id]
                        self.stored_positions[node_id] = node.pos()  # Store current position
                        node.setPos(self.group.center)
                        # Set z-value: larger nodes go to the back (more negative z)
                        node.setZValue(base_z - i)
                else:
                    # Expand: Restore original positions and reset z-values
                    for node_id in self.group.nodes:
                        if node_id in self.graph_manager.nodes and node_id in self.stored_positions:
                            node = self.graph_manager.nodes[node_id]
                            node.setPos(self.stored_positions[node_id])
                            node.setZValue(0)  # Reset to default z-value
                    
                event.accept()
                self.update()
                return
                
        super().mousePressEvent(event)
        
    def _arrange_nodes_in_circle(self) -> None:
        """Arrange nodes in a circle around the group center"""
        if not self.group.nodes:
            return
            
        center = self.group.center
        radius = 200  # Radius of the circle
        angle_step = 2 * math.pi / len(self.group.nodes)
        
        for i, node_id in enumerate(self.group.nodes):
            if node_id in self.graph_manager.nodes:
                node = self.graph_manager.nodes[node_id]
                angle = i * angle_step
                new_pos = QPointF(
                    center.x() + radius * math.cos(angle),
                    center.y() + radius * math.sin(angle)
                )
                node.setPos(new_pos) 