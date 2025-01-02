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
        self.zoom_level = 1.0
        self.offset_y = 0
        self.setMinimumWidth(800)
        self.pixels_per_hour = TimelineStyle.BASE_PIXELS_PER_HOUR
        
        # Mouse tracking for panning
        self.is_panning = False
        self.last_mouse_pos = None
        self.setMouseTracking(True)

    def add_event(self, event):
        self.events.append(event)
        self.events.sort(key=lambda x: x.start_time)
        self._assign_columns()
        self.update()

    def _assign_columns(self):
        if not self.events:
            return
            
        sorted_events = sorted(self.events, key=lambda x: x.start_time)
        columns = [[sorted_events[0]]]
        sorted_events[0].column = 0
        
        for event in sorted_events[1:]:
            placed = False
            for col_idx, column in enumerate(columns):
                if not any(self._events_overlap(event, existing) for existing in column):
                    column.append(event)
                    event.column = col_idx
                    placed = True
                    break
            
            if not placed:
                event.column = len(columns)
                columns.append([event])

    def _events_overlap(self, event1, event2):
        return (event1.start_time < event2.end_time and 
                event2.start_time < event1.end_time)

    def _time_to_y(self, time):
        if not self.events:
            return TimelineStyle.TOP_MARGIN
        
        min_time = min(event.start_time for event in self.events)
        time_diff = (time - min_time).total_seconds() / 3600
        return TimelineStyle.TOP_MARGIN + (time_diff * self.pixels_per_hour * self.zoom_level) - self.offset_y

    def _get_time_increment_and_format(self):
        hour_pixels = self.pixels_per_hour * self.zoom_level
        
        if hour_pixels >= 3600:
            return timedelta(seconds=1), "%H:%M:%S"
        elif hour_pixels >= 1800:
            return timedelta(seconds=2), "%H:%M:%S"
        elif hour_pixels >= 900:
            return timedelta(seconds=4), "%H:%M:%S"
        elif hour_pixels >= 600:
            return timedelta(seconds=6), "%H:%M:%S"
        elif hour_pixels >= 300:
            return timedelta(seconds=12), "%H:%M:%S"
        elif hour_pixels >= 200:
            return timedelta(seconds=18), "%H:%M:%S"
        elif hour_pixels >= 100:
            return timedelta(seconds=36), "%H:%M:%S"
        elif hour_pixels >= 50:
            return timedelta(minutes=1), "%H:%M"
        elif hour_pixels >= 25:
            return timedelta(minutes=2), "%H:%M"
        elif hour_pixels >= 10:
            return timedelta(minutes=5), "%H:%M"
        elif hour_pixels >= 5:
            return timedelta(hours=1), "%H:00"
        elif hour_pixels >= 2:
            return timedelta(days=1), "%Y-%m-%d"
        elif hour_pixels >= 0.5:
            return timedelta(days=7), "%Y-%m-%d"
        elif hour_pixels >= 0.2:
            return timedelta(days=30), "%Y-%m"
        else:
            return timedelta(days=365), "%Y"

    def _format_duration(self, start_time, end_time):
        duration = end_time - start_time
        total_seconds = int(duration.total_seconds())
        
        days = total_seconds // (24 * 3600)
        remaining = total_seconds % (24 * 3600)
        hours = remaining // 3600
        remaining = remaining % 3600
        minutes = remaining // 60
        seconds = remaining % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), TimelineStyle.BACKGROUND_COLOR)
        
        if not self.events:
            return

        # Get time range
        min_time = min(event.start_time for event in self.events)
        max_time = max(event.end_time for event in self.events)
        
        # Draw timeline and dates
        timeline_x = TimelineStyle.LEFT_MARGIN
        painter.setPen(QPen(TimelineStyle.TIMELINE_COLOR, 2))
        painter.drawLine(timeline_x, 0, timeline_x, self.height())
        
        # Get appropriate time increment and format based on zoom level
        time_increment, time_format = self._get_time_increment_and_format()
        
        # Draw time markers
        current_time = min_time
        date_font = QFont()
        date_font.setPointSize(10)
        painter.setFont(date_font)
        
        last_label_y = -float('inf')
        
        while current_time <= max_time:
            y_pos = self._time_to_y(current_time)
            
            if y_pos - last_label_y >= TimelineStyle.MIN_LABEL_SPACING:
                painter.setPen(QPen(TimelineStyle.TIMELINE_COLOR, 1))
                painter.drawLine(timeline_x - 5, int(y_pos), timeline_x + 5, int(y_pos))
                
                painter.setPen(QPen(TimelineStyle.TEXT_COLOR))
                time_text = current_time.strftime(time_format)
                painter.drawText(5, int(y_pos + 5), time_text)
                
                last_label_y = y_pos
            
            current_time += time_increment

        # Draw events
        time_font = QFont()
        time_font.setPointSize(9)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        desc_font = QFont()
        desc_font.setPointSize(9)
        
        for event in self.events:
            start_y = self._time_to_y(event.start_time)
            end_y = self._time_to_y(event.end_time)
            
            content_margin = TimelineStyle.CONTENT_MARGIN
            title_height = TimelineStyle.TITLE_HEIGHT
            desc_min_height = TimelineStyle.DESC_MIN_HEIGHT
            duration_height = TimelineStyle.DURATION_HEIGHT
            
            min_content_height = (2 * content_margin +
                                title_height +
                                desc_min_height +
                                duration_height)
            
            height = max(end_y - start_y, min_content_height)
            
            # Calculate box position with new spacing
            box_x = (timeline_x + TimelineStyle.CONNECTOR_LENGTH + 
                    (event.column * (TimelineStyle.BOX_WIDTH + TimelineStyle.COLUMN_SPACING)))
            
            # Draw connection line
            painter.setPen(QPen(TimelineStyle.TIMELINE_COLOR, 2))
            painter.drawLine(timeline_x, int(start_y + height/2),
                           box_x, int(start_y + height/2))
            
            # Draw event box
            painter.setPen(QPen(event.color, 2))
            painter.setBrush(QBrush(TimelineStyle.EVENT_FILL_COLOR))
            painter.drawRoundedRect(QRectF(box_x, start_y, TimelineStyle.BOX_WIDTH, height), 10, 10)
            
            time_width = 60
            
            painter.setPen(QPen(TimelineStyle.TEXT_COLOR))
            
            # Draw title
            painter.setFont(title_font)
            title_rect = QRectF(box_x + content_margin, start_y + content_margin, 
                              TimelineStyle.BOX_WIDTH - 2*content_margin - time_width, title_height)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           event.title)
            
            # Draw time labels
            painter.setFont(time_font)
            
            start_time_text = event.start_time.strftime("%H:%M")
            start_time_rect = QRectF(box_x + TimelineStyle.BOX_WIDTH - time_width - content_margin,
                                   start_y + content_margin,
                                   time_width, title_height)
            painter.drawText(start_time_rect, 
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                           start_time_text)
            
            end_time_text = event.end_time.strftime("%H:%M")
            end_time_rect = QRectF(box_x + TimelineStyle.BOX_WIDTH - time_width - content_margin,
                                 start_y + height - content_margin - duration_height,
                                 time_width, duration_height)
            painter.drawText(end_time_rect,
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                           end_time_text)
            
            # Draw description
            painter.setFont(desc_font)
            desc_rect = QRectF(box_x + content_margin, 
                             start_y + content_margin + title_height,
                             TimelineStyle.BOX_WIDTH - 2*content_margin, 
                             height - 3*content_margin - title_height - duration_height)
            painter.drawText(desc_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                           event.description)
            
            # Draw duration
            painter.setFont(time_font)
            duration_text = self._format_duration(event.start_time, event.end_time)
            duration_rect = QRectF(box_x + content_margin, 
                                 start_y + height - content_margin - duration_height,
                                 TimelineStyle.BOX_WIDTH - 2*content_margin - time_width, duration_height)
            painter.drawText(duration_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           duration_text)

    def wheelEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            zoom_factor = (TimelineStyle.ZOOM_IN_FACTOR 
                         if event.angleDelta().y() > 0 
                         else TimelineStyle.ZOOM_OUT_FACTOR)
            
            mouse_y = event.position().y() + self.offset_y
            
            if self.events:
                min_time = min(event.start_time for event in self.events)
                old_time_offset = ((mouse_y - TimelineStyle.TOP_MARGIN) / 
                                 (self.pixels_per_hour * self.zoom_level))
                
                new_zoom = self.zoom_level * zoom_factor
                
                if (self.pixels_per_hour * new_zoom >= TimelineStyle.MIN_PIXELS_PER_HOUR and 
                    self.pixels_per_hour * new_zoom <= TimelineStyle.MAX_PIXELS_PER_HOUR):
                    self.zoom_level = new_zoom
                    
                    new_y = (TimelineStyle.TOP_MARGIN + 
                            old_time_offset * self.pixels_per_hour * self.zoom_level)
                    self.offset_y += (new_y - mouse_y)
                    
                    self.update()
        else:
            if event.angleDelta().y() > 0:
                self.offset_y = max(0, self.offset_y - 30)
            else:
                self.offset_y += 30
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.is_panning = False
            self.last_mouse_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_panning and self.last_mouse_pos is not None:
            delta = event.pos().y() - self.last_mouse_pos.y()
            self.offset_y = max(0, self.offset_y - delta)
            self.last_mouse_pos = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def _find_event_at_position(self, pos):
        if not self.events:
            return None

        timeline_x = TimelineStyle.LEFT_MARGIN
        
        for event in self.events:
            start_y = self._time_to_y(event.start_time)
            end_y = self._time_to_y(event.end_time)
            height = max(end_y - start_y, 50)
            box_x = (timeline_x + TimelineStyle.CONNECTOR_LENGTH + 
                    (event.column * (TimelineStyle.BOX_WIDTH + TimelineStyle.COLUMN_SPACING)))
            
            if (pos.x() >= box_x and pos.x() <= box_x + TimelineStyle.BOX_WIDTH and
                pos.y() >= start_y and pos.y() <= start_y + height):
                return event
        return None

    def show_edit_dialog(self, event):
        dialog = EditEventDialog(self, event)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            event.title = dialog.title_edit.text()
            event.description = dialog.description_edit.text()
            event.start_time = dialog.start_time_edit.dateTime().toPyDateTime()
            event.end_time = dialog.end_time_edit.dateTime().toPyDateTime()
            event.color = dialog.selected_color
            
            self.events.sort(key=lambda x: x.start_time)
            self._assign_columns()
            self.update()
        elif result == QDialog.DialogCode.Rejected:
            self.delete_event(event)

    def delete_event(self, event):
        """Delete an event from the timeline without affecting the graph"""
        if event in self.events:
            self.events.remove(event)
            self._assign_columns()
            self.is_panning = False
            self.last_mouse_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def mouseDoubleClickEvent(self, event):
        clicked_event = self._find_event_at_position(event.pos())
        if clicked_event:
            self.show_edit_dialog(clicked_event)
        super().mouseDoubleClickEvent(event) 