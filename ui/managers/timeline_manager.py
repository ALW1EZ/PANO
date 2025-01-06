from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QPushButton, QScrollArea
from PySide6.QtCore import Qt, QSize

from ..components.timeline_visual import TimelineVisual
from ..dialogs.timeline_editor import TimelineEvent, AddEventDialog
from ..styles.timeline_style import TimelineStyle

class TimelineManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.timeline_widget = None
        self.setup_timeline_dock()

    def setup_timeline_dock(self):
        """Setup the timeline dock widget"""
        # Create dock widget
        self.timeline_dock = QDockWidget("Timeline", self.main_window)
        self.timeline_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                     QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        
        # Create container widget
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Create scroll area and timeline widget
        scroll_area = QScrollArea()
        self.timeline_widget = TimelineVisual()
        scroll_area.setWidget(self.timeline_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Add Event button
        add_button = QPushButton("Add Event")
        add_button.clicked.connect(self.show_add_event_dialog)
        layout.addWidget(add_button)
        
        # Set widget and add dock
        self.timeline_dock.setWidget(container)
        
        # Set minimum and preferred size
        self.timeline_dock.setMinimumWidth(TimelineStyle.MINIMUM_DOCK_WIDTH)
        self.timeline_dock.resize(TimelineStyle.PREFERRED_DOCK_WIDTH, self.timeline_dock.height())
        
        # Add dock to main window
        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.timeline_dock)
        
        # Apply styles
        container.setStyleSheet(TimelineStyle.MAIN_STYLE)

    def show_add_event_dialog(self):
        """Show dialog to add a new timeline event"""
        dialog = AddEventDialog(self.main_window)
        if dialog.exec():
            event = TimelineEvent(
                dialog.title_edit.text(),
                dialog.description_edit.text(),
                dialog.start_time_edit.dateTime().toPython(),
                dialog.end_time_edit.dateTime().toPython(),
                dialog.selected_color
            )
            self.timeline_widget.add_event(event)

    def get_events(self):
        """Get all timeline events"""
        return self.timeline_widget.events if self.timeline_widget else []

    def clear_events(self):
        """Clear all timeline events"""
        if self.timeline_widget:
            self.timeline_widget.events.clear()
            self.timeline_widget.update()

    def add_event(self, event):
        """Add a single event to the timeline"""
        if self.timeline_widget:
            self.timeline_widget.add_event(event)

    def serialize_events(self):
        """Serialize timeline events for saving"""
        events = []
        for event in self.get_events():
            event_data = {
                'title': event.title,
                'description': event.description,
                'start_time': event.start_time.isoformat(),
                'end_time': event.end_time.isoformat(),
                'color': event.color.name()
            }
            # Save source entity ID if it exists
            if hasattr(event, 'source_entity_id'):
                event_data['source_entity_id'] = event.source_entity_id
            events.append(event_data)
        return events

    def deserialize_events(self, events_data):
        """Deserialize and load timeline events"""
        from datetime import datetime
        from PySide6.QtGui import QColor
        
        self.clear_events()
        for event_data in events_data:
            event = TimelineEvent(
                event_data['title'],
                event_data['description'],
                datetime.fromisoformat(event_data['start_time']),
                datetime.fromisoformat(event_data['end_time']),
                QColor(event_data['color'])
            )
            # Restore source entity ID if it exists
            if 'source_entity_id' in event_data:
                event.source_entity_id = event_data['source_entity_id']
            self.add_event(event) 