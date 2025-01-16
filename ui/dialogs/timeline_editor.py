from datetime import datetime
from PySide6.QtWidgets import (QDialog, QLineEdit, QDateTimeEdit, QPushButton,
                           QFormLayout, QColorDialog)
from PySide6.QtCore import QDateTime
from PySide6.QtGui import QColor

from ..styles.timeline_style import TimelineStyle

class TimelineEvent:
    def __init__(self, name, description, start_time, end_time, color=None):
        self.name = name
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.color = color or TimelineStyle.DEFAULT_EVENT_COLOR
        self.column = 0  # For handling overlapping events

class AddEventDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Forensic Event")
        self.selected_color = TimelineStyle.EVENT_FILL_COLOR
        self.setup_ui()
        self.setStyleSheet(TimelineStyle.DIALOG_STYLE)

    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.name_edit = QLineEdit()
        self.description_edit = QLineEdit()
        
        # Enhanced DateTime selectors
        current_time = QDateTime.currentDateTime()
        current_time.setTime(current_time.time().addSecs(-current_time.time().second()))
        
        self.start_time_edit = QDateTimeEdit(current_time)
        self.end_time_edit = QDateTimeEdit(current_time)
        
        # Configure DateTime editors
        for dt_edit in [self.start_time_edit, self.end_time_edit]:
            dt_edit.setCalendarPopup(True)
            dt_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
            dt_edit.setTime(dt_edit.time().addSecs(-dt_edit.time().second()))
            dt_edit.setStyleSheet(TimelineStyle.DATETIME_STYLE)
        
        # Color selection button
        self.color_button = QPushButton("Select Color")
        self.color_button.clicked.connect(self.choose_color)
        self.color_button.setStyleSheet(f"background-color: {self.selected_color.name()}")
        
        layout.addRow("Name:", self.name_edit)
        layout.addRow("Description:", self.description_edit)
        layout.addRow("Start Time:", self.start_time_edit)
        layout.addRow("End Time:", self.end_time_edit)
        layout.addRow("Event Color:", self.color_button)
        
        self.submit_button = QPushButton("Add Event")
        self.submit_button.clicked.connect(self.accept)
        layout.addRow(self.submit_button)

    def choose_color(self):
        color = QColorDialog.getColor(self.selected_color, self, "Choose Event Color")
        if color.isValid():
            self.selected_color = color
            self.color_button.setStyleSheet(f"background-color: {color.name()}")

    def accept(self):
        # Ensure seconds are set to 00 before accepting
        for dt_edit in [self.start_time_edit, self.end_time_edit]:
            dt = dt_edit.dateTime()
            dt.setTime(dt.time().addSecs(-dt.time().second()))
            dt_edit.setDateTime(dt)
        super().accept()

class EditEventDialog(AddEventDialog):
    def __init__(self, parent=None, event=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Event")
        self.submit_button.setText("Save Changes")
        
        # Add delete button
        self.delete_button = QPushButton("Delete Event")
        self.delete_button.setStyleSheet("""
            background-color: #d42828;
        """)
        self.delete_button.clicked.connect(self.reject)
        self.layout().addRow(self.delete_button)
        
        if event:
            self.name_edit.setText(event.name)
            self.description_edit.setText(event.description)
            self.start_time_edit.setDateTime(QDateTime(event.start_time))
            self.end_time_edit.setDateTime(QDateTime(event.end_time))
            self.selected_color = event.color
            self.color_button.setStyleSheet(f"background-color: {event.color.name()}") 