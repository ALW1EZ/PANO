from PyQt6.QtWidgets import (QDialog, QVBoxLayout,
                             QLineEdit, QLabel, QHBoxLayout, QDialogButtonBox,
                             QPushButton, QDateTimeEdit)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QIcon
from typing import Dict, Any
from entities import Entity
from datetime import datetime

class PropertyEditor(QDialog):
    def __init__(self, entity: Entity, parent=None):
        super().__init__(parent)
        self.entity = entity
        self.inputs = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle(f"Edit {self.entity.type_label} Properties")
        layout = QVBoxLayout(self)
        
        # Create input fields for each property
        for prop_name, validator in self.entity.property_validators.items():
            if prop_name.startswith('_'):  # Skip internal properties
                continue
                
            row = QHBoxLayout()
            
            # Label
            label = QLabel(f"{prop_name}:")
            row.addWidget(label)
            
            # Input field
            input_field = QLineEdit()
            current_value = self.entity.properties.get(prop_name, "")
            
            # Format datetime values
            if prop_name in ['start_date', 'end_date'] and isinstance(current_value, datetime):
                current_value = current_value.strftime("%Y-%m-%d %H:%M")
            else:
                current_value = str(current_value)
                
            input_field.setText(current_value)
            
            self.inputs[prop_name] = input_field
            row.addWidget(input_field)
            
            # Add date picker button for date fields
            if prop_name in ['start_date', 'end_date']:
                date_button = QPushButton("📅")  # Calendar emoji as icon
                date_button.setFixedWidth(30)
                date_button.clicked.connect(lambda checked, field=input_field, name=prop_name: 
                                         self._show_date_picker(field, name))
                row.addWidget(date_button)
            
            layout.addLayout(row)
        
        # Add buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
                color: #CCCCCC;
            }
            QLabel {
                color: #CCCCCC;
            }
            QLineEdit {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                padding: 5px;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #007ACC;
                color: #FFFFFF;
                border: none;
                padding: 5px 15px;
                border-radius: 2px;
            }
            QPushButton[text="📅"] {
                background-color: transparent;
                border: 1px solid #3F3F46;
                padding: 2px;
            }
            QPushButton[text="📅"]:hover {
                background-color: #3F3F46;
            }
        """)
        
    def get_values(self) -> Dict[str, Any]:
        """Get the current values from all inputs"""
        values = {}
        for prop_name, input_field in self.inputs.items():
            value = input_field.text().strip()
            
            # Convert date strings to datetime objects
            if prop_name in ['start_date', 'end_date'] and value:
                try:
                    # Parse the date string and set seconds to 00
                    dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
                    value = dt.replace(second=0)
                except ValueError:
                    value = None
                    
            values[prop_name] = value
        return values 

    def _show_date_picker(self, input_field: QLineEdit, prop_name: str):
        """Show date picker dialog and update the input field"""
        date_dialog = QDialog(self)
        date_dialog.setWindowTitle("Select Date and Time")
        layout = QVBoxLayout(date_dialog)
        
        date_picker = QDateTimeEdit(date_dialog)
        date_picker.setCalendarPopup(True)
        date_picker.setDisplayFormat("yyyy-MM-dd HH:mm")  # Removed seconds from display
        
        # Try to parse existing date if any
        current_text = input_field.text()
        try:
            if current_text:
                current_date = QDateTime.fromString(current_text, "yyyy-MM-dd HH:mm")
                if current_date.isValid():
                    date_picker.setDateTime(current_date)
                else:
                    date_picker.setDateTime(QDateTime.currentDateTime())
            else:
                date_picker.setDateTime(QDateTime.currentDateTime())
        except:
            date_picker.setDateTime(QDateTime.currentDateTime())
            
        # Set seconds to 00
        current_dt = date_picker.dateTime()
        current_dt.setTime(current_dt.time().addSecs(-current_dt.time().second()))
        date_picker.setDateTime(current_dt)
            
        layout.addWidget(date_picker)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(lambda: self._update_date_field(input_field, date_picker, date_dialog))
        buttons.rejected.connect(date_dialog.reject)
        layout.addWidget(buttons)
        
        # Apply dark theme to date picker dialog
        date_dialog.setStyleSheet("""
            QDialog, QDateTimeEdit {
                background-color: #2D2D30;
                color: #CCCCCC;
            }
            QDateTimeEdit {
                border: 1px solid #3F3F46;
                padding: 5px;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #007ACC;
                color: #FFFFFF;
                border: none;
                padding: 5px 15px;
                border-radius: 2px;
            }
            QCalendarWidget {
                background-color: #2D2D30;
                color: #CCCCCC;
            }
            QCalendarWidget QToolButton {
                color: #CCCCCC;
            }
            QCalendarWidget QMenu {
                background-color: #2D2D30;
                color: #CCCCCC;
            }
            QCalendarWidget QSpinBox {
                background-color: #2D2D30;
                color: #CCCCCC;
                selection-background-color: #007ACC;
            }
        """)
        
        date_dialog.exec()
        
    def _update_date_field(self, input_field: QLineEdit, date_picker: QDateTimeEdit, dialog: QDialog):
        """Update the input field with the selected date"""
        # Get date and ensure seconds are 00
        selected_dt = date_picker.dateTime()
        selected_dt.setTime(selected_dt.time().addSecs(-selected_dt.time().second()))
        
        # Format without seconds
        selected_date = selected_dt.toString("yyyy-MM-dd HH:mm")
        input_field.setText(selected_date)
        dialog.accept() 