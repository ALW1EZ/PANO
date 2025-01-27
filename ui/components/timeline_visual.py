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

        # Sort events by duration first (longer events first), then by start time
        def event_sort_key(event):
            start = self._parse_date(event.start_time)
            end = self._parse_date(event.end_time)
            if not start or not end:
                return (timedelta.min, datetime.max)
            duration = end - start
            return (duration, -start.timestamp())  # Negative timestamp to sort earlier dates first
            
        sorted_events = sorted(self.events, key=event_sort_key, reverse=True)  # Reverse to get longer durations first
        
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
                    else:
                        # Check if this event contains any existing events
                        for existing_event in group['events']:
                            if is_contained_within(existing_event, event):
                                # Move the existing event to be contained by this event
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
        # Sort events by duration first (longer events first), then by start time
        def event_sort_key(e):
            start = self._parse_date(e.start_time)
            end = self._parse_date(e.end_time)
            if not start or not end:
                return (timedelta.min, datetime.max)
            duration = end - start
            return (duration, -start.timestamp())  # Negative timestamp to sort earlier dates first
            
        self.events.sort(key=event_sort_key, reverse=True)  # Reverse to get longer durations first
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
        
        # If we're very close to a full day (within 1 minute), round up to a day
        if abs(total_seconds - (24 * 3600)) < 60:
            return "1d"
            
        years = total_seconds // (365 * 24 * 3600)
        remaining = total_seconds % (365 * 24 * 3600)
        months = remaining // (30 * 24 * 3600)  # Approximate months as 30 days
        remaining = remaining % (30 * 24 * 3600)
        days = remaining // (24 * 3600)
        remaining = remaining % (24 * 3600)
        hours = remaining // 3600
        remaining = remaining % 3600
        minutes = remaining // 60
        
        parts = []
        if years > 0:
            parts.append(f"{years}y")
        if months > 0:
            parts.append(f"{months}m")
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}mi")
        
        return " ".join(parts) if parts else "0mi"

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

    def _calculate_box_height(self, painter, event):
        """Calculate the total height of an event box including all nested events"""
        # Calculate required heights for the main event
        title_font = QFont("Geist Mono", 13)
        title_font.setBold(True)
        description_font = QFont("Geist Mono", 11)
        
        content_width = TimelineStyle.BOX_WIDTH - 2*TimelineStyle.CONTENT_MARGIN
        
        # Set fonts to calculate heights
        painter.setFont(title_font)
        title_height = self._calculate_text_height(painter, event.name, content_width, title_font)
        
        painter.setFont(description_font)
        description_height = self._calculate_text_height(painter, event.description, content_width, description_font)
        
        # Base height for the event itself
        base_height = (TimelineStyle.CONTENT_MARGIN * 3 +  # Top margin + spacing between title/desc + bottom margin
                      title_height + description_height + 30)  # Add 30px for time labels at bottom
        
        # Get nested events
        current_group = self._get_event_group(event)
        if not current_group:
            return base_height
            
        contained_events = current_group['contained_by'].get(event, [])
        if not contained_events:
            return base_height
            
        # Constants for spacing
        container_padding = 20  # Extra padding at bottom of container
        contained_spacing = 15  # Space between container and contained events
        
        # Calculate total height including nested events
        total_height = base_height + contained_spacing  # Start with base height plus initial spacing
        
        # Add height for each contained event
        for contained_event in contained_events:
            contained_height = self._calculate_box_height(painter, contained_event)  # Recursive calculation
            total_height += contained_height + contained_spacing
            
        return total_height + container_padding  # Add final container padding

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
        
        # Calculate base height for the main event content
        title_font = QFont("Geist Mono", 13)
        title_font.setBold(True)
        description_font = QFont("Geist Mono", 11)
        content_width = available_width - 2*TimelineStyle.CONTENT_MARGIN
        
        painter.setFont(title_font)
        title_height = self._calculate_text_height(painter, event.name, content_width, title_font)
        painter.setFont(description_font)
        description_height = self._calculate_text_height(painter, event.description, content_width, description_font)
        base_height = (TimelineStyle.CONTENT_MARGIN * 3 + title_height + description_height + 30)
        
        # Calculate total height including all nested events
        total_height = self._calculate_box_height(painter, event)
        
        # Draw vertical connector and time difference if there's a previous event
        if last_event and last_group and indent_level == 0:
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
                    if current_start_time > last_end_time:
                        time_diff = current_start_time - last_end_time
                        # Only show time difference if it's at least 1 minute
                        if time_diff.total_seconds() >= 60:
                            diff_text = f"after {self._format_relative_time(time_diff)}"
                            
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
                    else:
                        time_diff = last_end_time - current_start_time
                        # Only show time difference if it's at least 1 minute
                        if time_diff.total_seconds() >= 60:
                            diff_text = f"before {self._format_relative_time(time_diff)}"
                            
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
        self._draw_event_content(painter, event, box_x, y_offset, content_width, base_height)
        
        # Draw time labels
        painter.setPen(QPen(TimelineStyle.TEXT_COLOR))
        painter.setFont(QFont("Geist Mono", 11))
        start_time = self._parse_date(event.start_time)
        end_time = self._parse_date(event.end_time)
        
        if start_time and end_time:
            if start_time == end_time:
                # For instant events, show single centered time
                time_text = start_time.strftime("%d/%m/%y %H:%M")
                painter.drawText(
                    QRectF(10, y_offset + (total_height - 20) // 2, TimelineStyle.LEFT_MARGIN - 20, 20),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    time_text
                )
            else:
                # For events with duration, show start and end times
                time_text = start_time.strftime("%d/%m/%y %H:%M")
                painter.drawText(
                    QRectF(10, y_offset, TimelineStyle.LEFT_MARGIN - 20, 20),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    time_text
                )
                
                # Draw duration at the bottom left
                duration = end_time - start_time
                duration_text = self._format_relative_time(duration)
                painter.drawText(
                    QRectF(box_x + TimelineStyle.CONTENT_MARGIN,
                           y_offset + total_height - TimelineStyle.CONTENT_MARGIN - 20,
                           content_width // 2, 20),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    duration_text
                )
                
                # Draw end time at the bottom right
                time_text = end_time.strftime("%d/%m/%y %H:%M")
                painter.drawText(
                    QRectF(10, y_offset + total_height - 20, TimelineStyle.LEFT_MARGIN - 20, 20),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    time_text
                )
        
        # Draw contained events recursively
        if contained_events:
            current_y = y_offset + base_height + TimelineStyle.CONTENT_MARGIN
            for contained_event in contained_events:
                contained_height = self._draw_event_box(painter, contained_event, current_y, 
                                                      None, indent_level + 1)
                current_y += contained_height + TimelineStyle.CONTENT_MARGIN
        
        return total_height

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

        # Check if click is within the box horizontally
        box_x = TimelineStyle.LEFT_MARGIN
        if pos.x() < box_x or pos.x() > box_x + TimelineStyle.BOX_WIDTH:
            return None

        def get_event_height(event):
            """Calculate height for a single event box"""
            title_lines = len(event.name) // 40 + 1
            desc_lines = len(event.description) // 40 + 1
            return (TimelineStyle.CONTENT_MARGIN * 3 +  # Margins
                    title_lines * 20 +                  # Title height
                    desc_lines * 20 +                  # Description height
                    30)                                # Time labels

        def find_event_at_y(events_to_check, start_y):
            """Find event at given y position"""
            current_y = start_y
            
            for event in events_to_check:
                box_height = get_event_height(event)
                
                # Check if click is in this event's box
                if current_y <= pos.y() <= current_y + box_height:
                    return event
                
                # Get nested events
                current_group = self._get_event_group(event)
                if current_group and event in current_group['contained_by']:
                    nested_events = current_group['contained_by'][event]
                    if nested_events:
                        # Check nested events
                        nested_y = current_y + box_height + TimelineStyle.CONTENT_MARGIN
                        nested_result = find_event_at_y(nested_events, nested_y)
                        if nested_result:
                            return nested_result
                        
                        # Update current_y to account for nested events
                        for nested_event in nested_events:
                            nested_height = get_event_height(nested_event)
                            nested_y += nested_height + TimelineStyle.CONTENT_MARGIN
                
                current_y += box_height + TimelineStyle.CONTENT_MARGIN
            
            return None

        # Get top-level events (not contained by others)
        top_level_events = []
        for event in self.events:
            is_contained = False
            for group in self.event_groups:
                for container_events in group['contained_by'].values():
                    if event in container_events:
                        is_contained = True
                        break
                if is_contained:
                    break
            if not is_contained:
                top_level_events.append(event)

        # Start searching from top-level events
        return find_event_at_y(top_level_events, TimelineStyle.TOP_MARGIN)

    def show_edit_dialog(self, event):
        """Show dialog to edit an event"""
        dialog = EditEventDialog(self, event)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            # Update the event in place without removing and re-adding
            event.name = dialog.name_edit.text()
            event.description = dialog.description_edit.text()
            event.start_time = dialog.start_time_edit.dateTime().toPython()
            event.end_time = dialog.end_time_edit.dateTime().toPython()
            event.color = dialog.selected_color
            
            # Just recalculate overlaps without resorting
            self._detect_overlaps()
            self.update()
        elif result == QDialog.DialogCode.Rejected:
            self.delete_event(event)

    def mouseDoubleClickEvent(self, event):
        clicked_event = self._find_event_at_position(event.pos())
        if clicked_event:
            self.show_edit_dialog(clicked_event)
        super().mouseDoubleClickEvent(event) 