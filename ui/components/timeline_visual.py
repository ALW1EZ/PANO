from datetime import datetime, timedelta
from PySide6.QtWidgets import (QWidget, QApplication, QDialog)
from PySide6.QtCore import Qt, QRectF, QDateTime
from PySide6.QtGui import QPainter, QPen, QBrush, QFont

from ..styles.timeline_style import TimelineStyle
from ..dialogs.timeline_editor import TimelineEvent, EditEventDialog

class TimelineVisual(QWidget):
    def __init__(self):
        super().__init__()
        self.events = []
        self.offset_y = 0
        self.event_horizontal_offsets = {}  # Store horizontal offsets for overlapping events
        self.event_groups = []  # Store groups of overlapping events
        self.setMinimumWidth(TimelineStyle.PREFERRED_DOCK_WIDTH)
        
        # Increase box height for better text wrapping
        TimelineStyle.BOX_HEIGHT = 180  # Increased from default

    def _parse_date(self, date_str):
        """Convert string dates to datetime objects"""
        if isinstance(date_str, datetime):
            return date_str
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _detect_overlaps(self):
        """Detect overlapping events and group them"""
        self.event_horizontal_offsets.clear()
        self.event_groups = []
        
        if not self.events:
            return

        def events_overlap(event1, event2):
            start1 = self._parse_date(event1.start_time)
            end1 = self._parse_date(event1.end_time)
            start2 = self._parse_date(event2.start_time)
            end2 = self._parse_date(event2.end_time)
            
            if not all([start1, end1, start2, end2]):
                return False
                
            return (start1 <= end2) and (end1 >= start2)

        def is_contained_within(event1, event2):
            """Check if event1 is contained within event2's timespan"""
            start1 = self._parse_date(event1.start_time)
            end1 = self._parse_date(event1.end_time)
            start2 = self._parse_date(event2.start_time)
            end2 = self._parse_date(event2.end_time)
            
            if not all([start1, end1, start2, end2]):
                return False
                
            return start2 <= start1 and end1 <= end2

        def find_container_for_event(event, potential_containers):
            """Find the most immediate container for an event"""
            immediate_container = None
            smallest_timespan = timedelta.max
            
            for container in potential_containers:
                if is_contained_within(event, container):
                    container_start = self._parse_date(container.start_time)
                    container_end = self._parse_date(container.end_time)
                    timespan = container_end - container_start
                    if timespan < smallest_timespan:
                        smallest_timespan = timespan
                        immediate_container = container
            
            return immediate_container

        # First, sort events by start time to process them in chronological order
        sorted_events = sorted(self.events, key=lambda x: self._parse_date(x.start_time))
        
        # Create initial group
        if sorted_events:
            first_event = sorted_events[0]
            self.event_groups.append({
                'events': [first_event],
                'contained_by': {},  # Map of container events to their contained events
                'start_time': self._parse_date(first_event.start_time),
                'end_time': self._parse_date(first_event.end_time)
            })

        # Process remaining events
        for event in sorted_events[1:]:
            added_to_group = False
            
            for group in self.event_groups:
                if any(events_overlap(event, e) for e in group['events']):
                    # Find the immediate container for this event
                    container = find_container_for_event(event, group['events'])
                    
                    if container:
                        # This event should be nested under the container
                        if container not in group['contained_by']:
                            group['contained_by'][container] = []
                        group['contained_by'][container].append(event)
                        
                        # Check if this event contains any existing events
                        for existing_event in group['events']:
                            if existing_event != event and is_contained_within(existing_event, event):
                                # Move the existing event to be contained by this event instead
                                for container_events in group['contained_by'].values():
                                    if existing_event in container_events:
                                        container_events.remove(existing_event)
                                if event not in group['contained_by']:
                                    group['contained_by'][event] = []
                                group['contained_by'][event].append(existing_event)
                    
                    group['events'].append(event)
                    
                    # Update group boundaries
                    start_time = min(self._parse_date(e.start_time) for e in group['events'] if self._parse_date(e.start_time))
                    end_time = max(self._parse_date(e.end_time) for e in group['events'] if self._parse_date(e.end_time))
                    group['start_time'] = start_time
                    group['end_time'] = end_time
                    added_to_group = True
                    break
            
            if not added_to_group:
                # Create new group for this event
                self.event_groups.append({
                    'events': [event],
                    'contained_by': {},
                    'start_time': self._parse_date(event.start_time),
                    'end_time': self._parse_date(event.end_time)
                })

        # Sort groups by start time
        self.event_groups.sort(key=lambda x: x['start_time'])

    def _get_event_group(self, event):
        """Get the group containing the event"""
        for group in self.event_groups:
            if event in group['events']:
                return group
        return None

    def add_event(self, event):
        """Add a new event to the timeline"""
        self.events.append(event)
        self.events.sort(key=lambda x: x.start_time)
        self._detect_overlaps()
        self.update()

    def delete_event(self, event):
        """Delete an event from the timeline"""
        if event in self.events:
            self.events.remove(event)
            self._detect_overlaps()
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

        try:
            start_time = self._parse_date(event.start_time)
            end_time = self._parse_date(event.end_time)

            if not start_time or not end_time:
                # If dates couldn't be parsed, show raw strings
                painter.drawText(
                    QRectF(10, y_offset + (box_height - 20) // 2, 
                           TimelineStyle.LEFT_MARGIN - 20, 20),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    str(event.start_time)
                )
            else:
                # If start and end time are the same, show only one centered label
                if start_time == end_time:
                    painter.drawText(
                        QRectF(10, y_offset + (box_height - 20) // 2, 
                               TimelineStyle.LEFT_MARGIN - 20, 20),
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        end_time.strftime(time_format)
                    )
                else:
                    # Draw start time label
                    painter.drawText(
                        QRectF(10, y_offset, TimelineStyle.LEFT_MARGIN - 20, 20),
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        start_time.strftime(time_format)
                    )
                    
                    # Draw end time label
                    painter.drawText(
                        QRectF(10, y_offset + box_height - 20, 
                               TimelineStyle.LEFT_MARGIN - 20, 20),
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        end_time.strftime(time_format)
                    )
        except Exception as e:
            # Show raw strings if there's an error
            painter.drawText(
                QRectF(10, y_offset + (box_height - 20) // 2, 
                       TimelineStyle.LEFT_MARGIN - 20, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(event.start_time)
            )

    def _calculate_text_height(self, painter, text, width, font):
        """Calculate required height for text with wrapping"""
        try:
            painter.save()  # Save current painter state
            painter.setFont(font)
            metrics = painter.fontMetrics()
            rect = QRectF(0, 0, width, 1000)  # Temporary tall rect
            flags = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap
            
            # Create a temporary QStaticText for measurement
            bounds = metrics.boundingRect(rect.toRect(), flags, text)
            return bounds.height()
        finally:
            painter.restore()  # Restore painter state

    def _draw_event_box(self, painter, event, y_offset, last_event, indent_level=0):
        """Draw an event box and its contents with recursive nesting"""
        # Get event group for proper time calculations
        current_group = self._get_event_group(event)
        last_group = self._get_event_group(last_event) if last_event else None
        
        # Calculate if this event contains others
        contained_events = current_group['contained_by'].get(event, []) if current_group else []
        
        # Always use same x position and width for all boxes
        box_x = TimelineStyle.LEFT_MARGIN
        available_width = TimelineStyle.BOX_WIDTH
        
        # Calculate total height including space for contained events
        base_height = self._calculate_box_height(painter, event)
        total_height = base_height
        
        # Constants for spacing
        container_padding = 20  # Extra padding at bottom of container
        contained_spacing = 15  # Space between container and contained events
        
        if contained_events:
            # Calculate height needed for contained events
            current_y = base_height + contained_spacing
            for contained_event in contained_events:
                # Recursively calculate height for nested events
                contained_height = self._calculate_box_height(painter, contained_event)
                
                # Check if this contained event itself contains others
                nested_events = current_group['contained_by'].get(contained_event, [])
                if nested_events:
                    # Add container padding for this contained event
                    contained_height += container_padding
                    
                    # Add height for nested events
                    for nested_event in nested_events:
                        nested_height = self._calculate_box_height(painter, nested_event)
                        # If the nested event also contains others, add padding for it too
                        if current_group['contained_by'].get(nested_event, []):
                            nested_height += container_padding
                        contained_height += nested_height + contained_spacing
                
                current_y += contained_height + contained_spacing
            
            total_height = current_y
            # Add container padding for this event since it contains others
            total_height += container_padding

        # Draw vertical connector and time difference if there's a previous event
        if last_event and last_group and indent_level == 0:  # Only draw connectors for top-level events
            center_x = TimelineStyle.LEFT_MARGIN + TimelineStyle.BOX_WIDTH // 2
            start_y = y_offset - TimelineStyle.EVENT_SPACING
            end_y = y_offset
            
            # Draw vertical line
            painter.setPen(QPen(TimelineStyle.TIMELINE_COLOR, 2))
            painter.drawLine(center_x, start_y, center_x, end_y)
            
            # Calculate and draw time difference
            if current_group != last_group:
                last_end_time = self._parse_date(last_event.end_time)
                current_start_time = self._parse_date(event.start_time)
                
                if last_end_time and current_start_time:
                    time_diff = current_start_time - last_end_time
                    diff_text = self._format_relative_time(time_diff)
                    if "after" not in diff_text:
                        diff_text = f"after {diff_text}"
                    
                    # Draw time difference text
                    painter.setPen(QPen(TimelineStyle.TEXT_COLOR))
                    painter.setFont(QFont("Geist Mono", 11))
                    text_width = min(TimelineStyle.BOX_WIDTH - 20, 300)
                    text_rect = QRectF(center_x - text_width/2,
                                      start_y + (end_y - start_y)/2 - 20,
                                      text_width, 40)
                    painter.drawText(text_rect,
                                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                                   diff_text)
        
        # Draw main event box
        painter.setPen(QPen(event.color, 2))
        painter.setBrush(QBrush(TimelineStyle.EVENT_FILL_COLOR))
        box_rect = QRectF(box_x, y_offset, available_width, total_height)
        painter.drawRoundedRect(box_rect, 10, 10)
        
        # Draw main event content
        content_width = available_width - 2*TimelineStyle.CONTENT_MARGIN
        title_font = QFont("Geist Mono", 13)
        title_font.setBold(True)
        description_font = QFont("Geist Mono", 11)
        
        # Draw title and description
        self._draw_event_content(painter, event, box_x, y_offset, content_width, base_height)
        
        # Draw contained events recursively
        if contained_events:
            current_y = y_offset + base_height + contained_spacing
            for contained_event in contained_events:
                contained_height = self._draw_event_box(painter, contained_event, current_y, 
                                                      None, indent_level + 1)
                current_y += contained_height + contained_spacing
        
        return total_height

    def _draw_event_content(self, painter, event, box_x, y_offset, content_width, base_height):
        """Draw the content of an event (title, description, times)"""
        title_font = QFont("Geist Mono", 13)
        title_font.setBold(True)
        description_font = QFont("Geist Mono", 11)
        
        # Draw title
        title_height = self._calculate_text_height(painter, event.name, content_width, title_font)
        painter.setPen(QPen(TimelineStyle.TEXT_COLOR))
        painter.setFont(title_font)
        title_rect = QRectF(box_x + TimelineStyle.CONTENT_MARGIN, 
                           y_offset + TimelineStyle.CONTENT_MARGIN,
                           content_width,
                           title_height)
        painter.drawText(title_rect,
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                        event.name)
        
        # Draw description
        description_height = self._calculate_text_height(painter, event.description, content_width, description_font)
        painter.setFont(description_font)
        description_rect = QRectF(box_x + TimelineStyle.CONTENT_MARGIN, 
                                 y_offset + TimelineStyle.CONTENT_MARGIN * 2 + title_height,
                                 content_width,
                                 description_height)
        painter.drawText(description_rect,
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                        event.description)
        
        # Draw times
        self._draw_event_times(painter, event, box_x, y_offset, content_width, base_height)

    def _draw_event_times(self, painter, event, box_x, y_offset, content_width, base_height):
        """Draw the time labels for an event"""
        painter.setFont(QFont("Geist Mono", 11))
        time_width = 116
        
        try:
            start_time = self._parse_date(event.start_time)
            end_time = self._parse_date(event.end_time)
            
            if start_time and end_time:
                duration = end_time - start_time
                duration_text = self._format_relative_time(duration)
                
                if duration_text == "0m":
                    # For 0m duration, show single centered time
                    time_text = start_time.strftime("%H:%M")
                    painter.drawText(
                        QRectF(box_x + TimelineStyle.CONTENT_MARGIN,
                               y_offset + base_height - TimelineStyle.CONTENT_MARGIN - 20,
                               content_width, 20),
                        Qt.AlignmentFlag.AlignCenter,
                        time_text
                    )
                else:
                    # Show start-end time and duration for non-zero durations
                    start_time_text = start_time.strftime("%H:%M")
                    end_time_text = end_time.strftime("%H:%M")
                    painter.drawText(
                        QRectF(box_x + content_width - time_width,
                               y_offset + base_height - TimelineStyle.CONTENT_MARGIN - 20,
                               time_width, 20),
                        Qt.AlignmentFlag.AlignRight,
                        f"{start_time_text} - {end_time_text}"
                    )
                    painter.drawText(
                        QRectF(box_x + TimelineStyle.CONTENT_MARGIN,
                               y_offset + base_height - TimelineStyle.CONTENT_MARGIN - 20,
                               time_width, 20),
                        Qt.AlignmentFlag.AlignLeft,
                        duration_text
                    )
        except (ValueError, AttributeError) as e:
            painter.drawText(
                QRectF(box_x + TimelineStyle.CONTENT_MARGIN,
                       y_offset + base_height - TimelineStyle.CONTENT_MARGIN - 20,
                       content_width, 20),
                Qt.AlignmentFlag.AlignCenter,
                "Date not specified"
            )

    def _calculate_box_height(self, painter, event):
        """Calculate the total height of an event box"""
        # Calculate required heights
        title_font = QFont("Geist Mono", 13)
        title_font.setBold(True)
        description_font = QFont("Geist Mono", 11)
        
        content_width = TimelineStyle.BOX_WIDTH - 2*TimelineStyle.CONTENT_MARGIN
        
        # Set fonts to calculate heights
        painter.setFont(title_font)
        title_height = self._calculate_text_height(painter, event.name, content_width, title_font)
        
        painter.setFont(description_font)
        description_height = self._calculate_text_height(painter, event.description, content_width, description_font)
        
        # Calculate total box height
        return (TimelineStyle.CONTENT_MARGIN * 3 +  # Top margin + spacing between title/desc + bottom margin
                title_height + description_height + 30)  # Add 30px for time labels at bottom

    def paintEvent(self, event):
        try:
            painter = QPainter()
            painter.begin(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Fill background
            painter.fillRect(self.rect(), TimelineStyle.BACKGROUND_COLOR)
            
            if not self.events:
                return

            y_offset = TimelineStyle.TOP_MARGIN
            last_event = None
            
            # Only draw top-level events (those not contained by others)
            for current_event in self.events:
                is_contained = False
                for group in self.event_groups:
                    for container_events in group['contained_by'].values():
                        if current_event in container_events:
                            is_contained = True
                            break
                    if is_contained:
                        break
                
                if not is_contained:
                    painter.setPen(QPen(TimelineStyle.TEXT_COLOR))
                    box_height = self._draw_event_box(painter, current_event, y_offset, last_event)
                    self._draw_time_labels(painter, current_event, y_offset, box_height)
                    
                    y_offset += box_height + TimelineStyle.EVENT_SPACING
                    last_event = current_event
            
            # Update widget height to fit all events
            self.setMinimumHeight(y_offset + TimelineStyle.TOP_MARGIN)
            
        finally:
            painter.end()

    def _find_event_at_position(self, pos):
        """Find the event at the given position"""
        if not self.events:
            return None

        # Calculate y position
        adjusted_y = pos.y()
        
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
            title_lines = len(event.name) // 40 + 1  # Rough estimate of lines needed
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
            event.name = dialog.name_edit.text()
            event.description = dialog.description_edit.text()
            event.start_time = dialog.start_time_edit.dateTime().toPython()
            event.end_time = dialog.end_time_edit.dateTime().toPython()
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