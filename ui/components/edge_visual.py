from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QMenu
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF
from PySide6.QtGui import QPainter, QPen, QPolygonF, QBrush
import math

from .node_visual import NodeVisual
from ..styles.edge_style import EdgeStyle
from ..dialogs.edge_properties import EdgePropertiesDialog

class EdgeVisual(QGraphicsItem):
    def __init__(self, source: NodeVisual, target: NodeVisual, 
                 relationship: str = "", parent=None):
        super().__init__(parent)
        self.source = source
        self.target = target
        self.relationship = relationship
        self.style = EdgeStyle()
        
        # Create text item for relationship label
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setDefaultTextColor(self.style.label_color)
        self.text_item.setPlainText(self.relationship)
        
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)  # Draw edges below nodes
        
        # Update position when nodes move
        if isinstance(source, NodeVisual):
            source.xChanged.connect(self.updatePosition)
            source.yChanged.connect(self.updatePosition)
        if isinstance(target, NodeVisual):
            target.xChanged.connect(self.updatePosition)
            target.yChanged.connect(self.updatePosition)
            
        self.updatePosition()
        
    def _calculate_intersection_points(self) -> tuple[QPointF, QPointF]:
        """Calculate where the edge intersects with the source and target nodes"""
        source_center = self.source.scenePos()
        target_center = self.target.scenePos()
        
        source_rect = self.source.boundingRect()
        target_rect = self.target.boundingRect()
        
        def find_intersection(rect: QRectF, from_point: QPointF, to_point: QPointF) -> QPointF:
            """Find intersection of line with rectangle using parametric equations"""
            # Transform to local coordinates
            rect_center = rect.center()
            rect_width = rect.width()
            rect_height = rect.height()
            
            # Calculate direction vector
            dx = to_point.x() - from_point.x()
            dy = to_point.y() - from_point.y()
            
            # Handle degenerate case
            if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                return from_point
            
            # Normalize direction vector
            length = math.sqrt(dx * dx + dy * dy)
            dx /= length
            dy /= length
            
            # Calculate intersection parameters for all edges
            # For each edge, solve: from + t * dir = edge_point
            t_values = []
            
            # Right edge: x = center.x + width/2
            if abs(dx) > 1e-6:
                t = (rect_center.x() + rect_width/2 - from_point.x()) / dx
                y = from_point.y() + t * dy
                if abs(y - rect_center.y()) <= rect_height/2:
                    t_values.append(t)
            
            # Left edge: x = center.x - width/2
            if abs(dx) > 1e-6:
                t = (rect_center.x() - rect_width/2 - from_point.x()) / dx
                y = from_point.y() + t * dy
                if abs(y - rect_center.y()) <= rect_height/2:
                    t_values.append(t)
            
            # Top edge: y = center.y - height/2
            if abs(dy) > 1e-6:
                t = (rect_center.y() - rect_height/2 - from_point.y()) / dy
                x = from_point.x() + t * dx
                if abs(x - rect_center.x()) <= rect_width/2:
                    t_values.append(t)
            
            # Bottom edge: y = center.y + height/2
            if abs(dy) > 1e-6:
                t = (rect_center.y() + rect_height/2 - from_point.y()) / dy
                x = from_point.x() + t * dx
                if abs(x - rect_center.x()) <= rect_width/2:
                    t_values.append(t)
            
            # Find the closest valid intersection
            if not t_values:
                return from_point
                
            # Get the smallest positive t value
            t = min((t for t in t_values if t >= 0), default=0)
            
            # Calculate intersection point
            return QPointF(
                from_point.x() + t * dx,
                from_point.y() + t * dy
            )
            
        # Get intersection points in scene coordinates
        source_point = find_intersection(
            source_rect.translated(source_center),
            source_center,
            target_center
        )
        target_point = find_intersection(
            target_rect.translated(target_center),
            target_center,
            source_center
        )
        
        # Convert points to item coordinates
        return (self.mapFromScene(source_point),
                self.mapFromScene(target_point))

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle of the edge"""
        if not self.source or not self.target:
            return QRectF()
            
        # Get intersection points
        source_point, target_point = self._calculate_intersection_points()
        
        # Create rect that encompasses both points
        rect = QRectF(source_point, target_point).normalized()
        
        # Add padding for arrow and text
        padding = max(self.style.arrow_size * 2, self.text_item.boundingRect().height())
        rect.adjust(-padding, -padding, padding, padding)
        
        return rect

    def paint(self, painter: QPainter, option, widget):
        """Paint the edge"""
        if not self.source or not self.target:
            return
            
        # Set up painter
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get intersection points
        source_point, target_point = self._calculate_intersection_points()
        
        # Calculate line
        line = QLineF(source_point, target_point)
        if line.length() == 0:
            return
            
        # Draw line
        pen = QPen(
            self.style.color if not self.isUnderMouse() else self.style.color.lighter(),
            self.style.width,
            self.style.style
        )
        painter.setPen(pen)
        painter.drawLine(line)
        
        # Draw arrow
        angle = math.atan2(line.dy(), line.dx())
        arrow_p1 = target_point - QPointF(
            math.cos(angle - math.pi/6) * self.style.arrow_size,
            math.sin(angle - math.pi/6) * self.style.arrow_size
        )
        arrow_p2 = target_point - QPointF(
            math.cos(angle + math.pi/6) * self.style.arrow_size,
            math.sin(angle + math.pi/6) * self.style.arrow_size
        )
        
        # Create arrow polygon
        arrow = QPolygonF([target_point, arrow_p1, arrow_p2])
        
        # Draw arrow
        painter.setBrush(QBrush(
            self.style.color if not self.isUnderMouse() 
            else self.style.color.lighter()
        ))
        painter.drawPolygon(arrow)

    def updatePosition(self):
        """Update the edge's position and text label"""
        if not self.source or not self.target:
            return
            
        self.prepareGeometryChange()
        
        # Get intersection points
        source_point, target_point = self._calculate_intersection_points()
        
        # Update text position
        if self.relationship:
            # Calculate center point
            center = (source_point + target_point) / 2
            
            # Get text dimensions
            text_rect = self.text_item.boundingRect()
            
            # Position text at center
            self.text_item.setPos(
                center.x() - text_rect.width() / 2,
                center.y() - text_rect.height() / 2
            )
            
            # Draw text background
            self.text_item.setDefaultTextColor(self.style.label_color)
        
        # Update edge position
        self.setPos(0, 0)  # Reset position to ensure proper coordinate system

    def mouseDoubleClickEvent(self, event):
        """Handle double click to edit relationship"""
        dialog = EdgePropertiesDialog(self, self.scene().views()[0])
        if dialog.exec() == EdgePropertiesDialog.DialogCode.Accepted:
            values = dialog.get_values()
            self.relationship = values['relationship']
            self.style.style = values['line_style']
            self.text_item.setPlainText(self.relationship)
            self.updatePosition()
            self.update()
        super().mouseDoubleClickEvent(event) 

    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D30;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3F3F46;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3F3F46;
                margin: 4px 0px;
            }
        """)
        
        # Add menu items
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(self._edit_properties)
        
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self._delete_edge)
        
        menu.exec(event.screenPos())
        
    def _edit_properties(self):
        """Edit edge properties"""
        dialog = EdgePropertiesDialog(self, self.scene().views()[0])
        if dialog.exec() == EdgePropertiesDialog.DialogCode.Accepted:
            values = dialog.get_values()
            self.relationship = values['relationship']
            self.style.style = values['line_style']
            self.text_item.setPlainText(self.relationship)
            self.updatePosition()
            self.update()
            
    def _delete_edge(self):
        """Delete this edge"""
        if self.scene():
            view = self.scene().views()[0]
            if hasattr(view, 'graph_manager'):
                edge_id = f"{self.source.node.id}->{self.target.node.id}"
                view.graph_manager.edges.pop(edge_id, None)
                self.scene().removeItem(self) 