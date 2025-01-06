from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QApplication, QDialog)
from PyQt6.QtCore import Qt, QRectF, QDateTime
from PyQt6.QtGui import QPainter, QPen, QBrush, QFont

from ..styles.timeline_style import TimelineStyle
from ..dialogs.timeline_editor import TimelineEvent, EditEventDialog

class TimelineVisual(QWidget):
    def __init__(self):
        super().__init__()
        self.events = []
        self.offset_y = 0
        self.setMinimumWidth(TimelineStyle.PREFERRED_DOCK_WIDTH)
        
        # Mouse tracking for panning
        self.is_panning = False
        self.last_mouse_pos = None
        self.setMouseTracking(True)
        
        # Increase box height for better text wrapping
        TimelineStyle.BOX_HEIGHT = 180  # Increased from default

    def add_event(self, event):
        """Add a new event to the timeline"""
        self.events.append(event)
        self.events.sort(key=lambda x: x.start_time)
        self.update()

    def delete_event(self, event):
        """Delete an event from the timeline"""
        if event in self.events:
            self.events.remove(event)
            self.is_panning = False
            self.last_mouse_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def _format_relative_time(self, time_delta):
        """Format timedelta into a human-readable relative time string"""
        total_seconds = int(time_delta.total_seconds())
        
        years = total_seconds // (365 * 24 * 3600)
        remaining = total_seconds % (365 * 24 * 3600)
        days = remaining // (24 * 3600)
        remaining = remaining % (24 * 3600)
        hours = remaining // 3600
        remaining = remaining % 3600
        minutes = remaining // 60
        
        parts = []
        if years > 0:
            parts.append(f"{years}y")
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "0m"

    def _draw_time_labels(self, painter, event, y_offset, box_height):
        """Draw the time labels for an event"""
        painter.setFont(QFont("Geist Mono", 11))
        time_format = "%d/%m/%y %H:%M"
        
        # If start and end time are the same, show only one centered label
        if event.start_time == event.end_time:
            painter.drawText(
                QRectF(10, y_offset + (box_height - 20) // 2, 
                       TimelineStyle.LEFT_MARGIN - 20, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                event.end_time.strftime(time_format)
            )
        else:
            # Draw start time label
            painter.drawText(
                QRectF(10, y_offset, TimelineStyle.LEFT_MARGIN - 20, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                event.start_time.strftime(time_format)
            )
            
            # Draw end time label
            painter.drawText(
                QRectF(10, y_offset + box_height - 20, 
                       TimelineStyle.LEFT_MARGIN - 20, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                event.end_time.strftime(time_format)
            )

    def _calculate_text_height(self, painter, text, width, font):
        """Calculate required height for text with wrapping"""
        painter.setFont(font)
        metrics = painter.fontMetrics()
        rect = QRectF(0, 0, width, 1000)  # Temporary tall rect
        flags = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap
        
        # Create a temporary QStaticText for measurement
        bounds = metrics.boundingRect(rect.toRect(), flags, text)
        return bounds.height()

    def _draw_event_box(self, painter, event, y_offset, last_event):
        """Draw an event box and its contents"""
        # Get the total height
        total_height = self._calculate_box_height(painter, event)
        
        # Calculate required heights for content
        title_font = QFont("Geist Mono", 13)
        title_font.setBold(True)
        description_font = QFont("Geist Mono", 11)
        content_width = TimelineStyle.BOX_WIDTH - 2*TimelineStyle.CONTENT_MARGIN
        
        painter.setFont(title_font)
        title_height = self._calculate_text_height(painter, event.title, content_width, title_font)
        
        painter.setFont(description_font)
        description_height = self._calculate_text_height(painter, event.description, content_width, description_font)
        
        # Draw vertical connector from previous event
        if last_event:
            center_x = TimelineStyle.LEFT_MARGIN + TimelineStyle.BOX_WIDTH // 2
            painter.setPen(QPen(TimelineStyle.TIMELINE_COLOR, 2))
            start_y = y_offset - TimelineStyle.EVENT_SPACING
            end_y = y_offset
            painter.drawLine(center_x, start_y, center_x, end_y)
            
            # Draw relative time difference centered on the line
            time_diff = event.start_time - last_event.end_time
            diff_text = self._format_relative_time(time_diff)
            if last_event.title and "after" not in diff_text:
                diff_text = f"after {diff_text}"
            
            painter.setPen(QPen(TimelineStyle.TEXT_COLOR))
            painter.setFont(QFont("Geist Mono", 11))
            
            # Calculate text width and create centered rect
            text_width = min(TimelineStyle.BOX_WIDTH - 20, 300)  # Limit width
            text_rect = QRectF(center_x - text_width/2,
                              start_y + (end_y - start_y)/2 - 20,
                              text_width, 40)
            
            # Draw text with wrapping
            painter.drawText(text_rect,
                            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                            diff_text)
        
        # Draw event box
        box_x = TimelineStyle.LEFT_MARGIN
        painter.setPen(QPen(event.color, 2))
        painter.setBrush(QBrush(TimelineStyle.EVENT_FILL_COLOR))
        box_rect = QRectF(box_x, y_offset, TimelineStyle.BOX_WIDTH, total_height)
        painter.drawRoundedRect(box_rect, 10, 10)
        
        # Draw title
        painter.setPen(QPen(TimelineStyle.TEXT_COLOR))
        painter.setFont(title_font)
        title_rect = QRectF(box_x + TimelineStyle.CONTENT_MARGIN, 
                           y_offset + TimelineStyle.CONTENT_MARGIN,
                           content_width,
                           title_height)
        painter.drawText(title_rect,
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                        event.title)
        
        # Draw description
        painter.setFont(description_font)
        description_rect = QRectF(box_x + TimelineStyle.CONTENT_MARGIN, 
                                 y_offset + TimelineStyle.CONTENT_MARGIN * 2 + title_height,
                                 content_width,
                                 description_height)
        painter.drawText(description_rect,
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                        event.description)
        
        # Draw times
        painter.setFont(QFont("Geist Mono", 11))
        time_width = 116
        
        # Calculate duration
        duration = event.end_time - event.start_time
        duration_text = self._format_relative_time(duration)
        
        if duration_text == "0m":
            # For 0m duration, show single centered time
            time_text = event.start_time.strftime("%H:%M")
            painter.drawText(
                QRectF(box_x + TimelineStyle.CONTENT_MARGIN,
                       y_offset + total_height - TimelineStyle.CONTENT_MARGIN - 20,
                       TimelineStyle.BOX_WIDTH - 2*TimelineStyle.CONTENT_MARGIN, 20),
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                time_text
            )
        else:
            # Show start-end time and duration for non-zero durations
            start_time_text = event.start_time.strftime("%H:%M")
            end_time_text = event.end_time.strftime("%H:%M")
            painter.drawText(
                QRectF(box_x + TimelineStyle.BOX_WIDTH - time_width - TimelineStyle.CONTENT_MARGIN,
                       y_offset + total_height - TimelineStyle.CONTENT_MARGIN - 20,
                       time_width, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{start_time_text} - {end_time_text}"
            )
            
            painter.drawText(
                QRectF(box_x + TimelineStyle.CONTENT_MARGIN,
                       y_offset + total_height - TimelineStyle.CONTENT_MARGIN - 20,
                       TimelineStyle.BOX_WIDTH - 2*TimelineStyle.CONTENT_MARGIN - time_width, 20),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                duration_text
            )
        
        return total_height

    def _calculate_box_height(self, painter, event):
        """Calculate the total height of an event box"""
        # Calculate required heights
        title_font = QFont("Geist Mono", 13)
        title_font.setBold(True)
        description_font = QFont("Geist Mono", 11)
        
        content_width = TimelineStyle.BOX_WIDTH - 2*TimelineStyle.CONTENT_MARGIN
        
        # Set fonts to calculate heights
        painter.setFont(title_font)
        title_height = self._calculate_text_height(painter, event.title, content_width, title_font)
        
        painter.setFont(description_font)
        description_height = self._calculate_text_height(painter, event.description, content_width, description_font)
        
        # Calculate total box height
        return (TimelineStyle.CONTENT_MARGIN * 3 +  # Top margin + spacing between title/desc + bottom margin
                title_height + description_height + 30)  # Add 30px for time labels at bottom

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), TimelineStyle.BACKGROUND_COLOR)
        
        if not self.events:
            return

        y_offset = TimelineStyle.TOP_MARGIN - self.offset_y
        last_event = None
        
        for current_event in self.events:
            painter.setPen(QPen(TimelineStyle.TEXT_COLOR))
            box_height = self._draw_event_box(painter, current_event, y_offset, last_event)
            self._draw_time_labels(painter, current_event, y_offset, box_height)
            
            y_offset += box_height + TimelineStyle.EVENT_SPACING
            last_event = current_event
            
        # Update widget height to fit all events
        self.setMinimumHeight(y_offset + TimelineStyle.TOP_MARGIN)

    def wheelEvent(self, event):
        scroll_amount = event.angleDelta().y() / 120 * 30  # Normalize scroll amount
        new_offset = self.offset_y - scroll_amount
        max_offset = max(0, self.minimumHeight() - self.height())
        self.offset_y = max(0, min(max_offset, new_offset))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False
            self.last_mouse_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_panning and self.last_mouse_pos is not None:
            delta = event.pos().y() - self.last_mouse_pos.y()
            new_offset = self.offset_y - delta
            max_offset = max(0, self.minimumHeight() - self.height())
            self.offset_y = max(0, min(max_offset, new_offset))
            self.last_mouse_pos = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def _find_event_at_position(self, pos):
        """Find the event at the given position"""
        if not self.events:
            return None

        # Calculate y position relative to scroll offset
        adjusted_y = pos.y() + self.offset_y
        
        # Check if click is within the box horizontally
        box_x = TimelineStyle.LEFT_MARGIN
        if pos.x() < box_x or pos.x() > box_x + TimelineStyle.BOX_WIDTH:
            return None
        
        # Calculate cumulative height to find the clicked event
        current_y = TimelineStyle.TOP_MARGIN
        
        # Use a fixed height estimation for each line of text
        line_height = 20  # Approximate height per line
        
        for event in self.events:
            # Estimate title height (1-2 lines)
            title_lines = len(event.title) // 40 + 1  # Rough estimate of lines needed
            title_height = title_lines * line_height
            
            # Estimate description height
            desc_lines = len(event.description) // 40 + 1  # Rough estimate of lines needed
            desc_height = desc_lines * line_height
            
            # Calculate total box height
            box_height = (TimelineStyle.CONTENT_MARGIN * 3 +  # Margins
                         title_height + desc_height + 30)     # Content + time labels
            
            # Check if click is within this box's vertical bounds
            if current_y <= adjusted_y <= current_y + box_height:
                return event
            
            current_y += box_height + TimelineStyle.EVENT_SPACING
        
        return None

    def show_edit_dialog(self, event):
        """Show dialog to edit an event"""
        dialog = EditEventDialog(self, event)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            # Store the event index before modification
            event_index = self.events.index(event)
            
            # Update the event
            event.title = dialog.title_edit.text()
            event.description = dialog.description_edit.text()
            event.start_time = dialog.start_time_edit.dateTime().toPyDateTime()
            event.end_time = dialog.end_time_edit.dateTime().toPyDateTime()
            event.color = dialog.selected_color
            
            # Remove and reinsert to trigger proper sorting
            self.events.pop(event_index)
            self.events.append(event)
            self.events.sort(key=lambda x: x.end_time)
            self.update()
        elif result == QDialog.DialogCode.Rejected:
            self.delete_event(event)

    def mouseDoubleClickEvent(self, event):
        clicked_event = self._find_event_at_position(event.pos())
        if clicked_event:
            self.show_edit_dialog(clicked_event)
        super().mouseDoubleClickEvent(event) 