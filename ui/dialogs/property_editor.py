from PySide6.QtWidgets import (QDialog, QVBoxLayout,
                             QLineEdit, QLabel, QHBoxLayout, QDialogButtonBox,
                             QPushButton, QDateTimeEdit, QCheckBox, QTextEdit,
                             QComboBox)
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QIcon
from typing import Dict, Any, Optional
from entities import Entity
from datetime import datetime

class PropertyEditor(QDialog):
    def __init__(self, entity: Entity, parent=None):
        super().__init__(parent)
        self.entity = entity
        self.inputs = {}
        self.date_checkboxes = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle(f"Edit {self.entity.type_label.lower()} Properties")
        layout = QVBoxLayout(self)
        
        # Get property metadata for UI rendering
        property_metadata = self.entity.get_property_metadata()
        
        # Create input fields for each property
        for prop_name, validator in self.entity.property_validators.items():
            if prop_name.startswith('_'):  # Skip internal properties
                continue
                
            row = QHBoxLayout()
            
            # Label
            label = QLabel(f"{prop_name}:")
            row.addWidget(label)
            
            # Get property metadata
            metadata = property_metadata.get(prop_name, {"type": "text", "choices": []})
            
            # Input field based on property type
            if metadata["type"] == "dropdown":
                input_field = QComboBox()
                if self.entity.property_validators[prop_name].allow_empty:
                    input_field.addItem("")  # Add empty option
                input_field.addItems(metadata["choices"])
                
                # Set current value if exists
                current_value = str(self.entity.properties.get(prop_name, ""))
                index = input_field.findText(current_value)
                if index >= 0:
                    input_field.setCurrentIndex(index)
                    
                # Style the combo box
                input_field.setStyleSheet("""
                    QComboBox {
                        background-color: #1E1E1E;
                        color: #CCCCCC;
                        border: 1px solid #3F3F46;
                        padding: 5px;
                        border-radius: 2px;
                        min-width: 200px;
                    }
                    QComboBox::drop-down {
                        border: none;
                        width: 20px;
                    }
                    QComboBox::down-arrow {
                        image: none;
                        width: 12px;
                        height: 12px;
                    }
                    QComboBox QAbstractItemView {
                        background-color: #1E1E1E;
                        color: #CCCCCC;
                        selection-background-color: #007ACC;
                    }
                """)
                row.addWidget(input_field)
            elif isinstance(self.entity.property_types.get(prop_name), type) and self.entity.property_types[prop_name] == bool:
                input_field = QCheckBox()
                input_field.setChecked(bool(self.entity.properties.get(prop_name, False)))
                input_field.setStyleSheet("""
                    QCheckBox {
                        color: #CCCCCC;
                    }
                    QCheckBox::indicator {
                        width: 13px;
                        height: 13px;
                    }
                    QCheckBox::indicator:unchecked {
                        background-color: #1E1E1E;
                        border: 1px solid #3F3F46;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #007ACC;
                        border: 1px solid #007ACC;
                    }
                """)
                row.addWidget(input_field)
            elif prop_name in ['start_date', 'end_date']:
                # Create date input
                input_field = QDateTimeEdit()
                input_field.setCalendarPopup(True)
                input_field.setDisplayFormat("yyyy-MM-dd HH:mm")
                input_field.setEnabled(True)
                
                current_value = self.entity.properties.get(prop_name)
                if current_value:
                    try:
                        # Try parsing the date string directly
                        if isinstance(current_value, str):
                            dt = datetime.strptime(current_value, "%Y-%m-%d %H:%M")
                        else:
                            dt = current_value
                        input_field.setDateTime(QDateTime.fromString(dt.strftime("%Y-%m-%d %H:%M"), "yyyy-MM-dd HH:mm"))
                    except (ValueError, TypeError):
                        # If parsing fails, use current time
                        current_dt = datetime.now().replace(second=0, microsecond=0)
                        input_field.setDateTime(QDateTime.fromString(current_dt.strftime("%Y-%m-%d %H:%M"), "yyyy-MM-dd HH:mm"))
                else:
                    # No existing value, use current time
                    current_dt = datetime.now().replace(second=0, microsecond=0)
                    input_field.setDateTime(QDateTime.fromString(current_dt.strftime("%Y-%m-%d %H:%M"), "yyyy-MM-dd HH:mm"))
                
                row.addWidget(input_field)
            elif prop_name == 'notes':
                input_field = QTextEdit()
                input_field.setFixedHeight(50)
                input_field.setStyleSheet("""
                    QTextEdit {
                        background-color: #1E1E1E;
                        color: #CCCCCC;
                        border: 1px solid #3F3F46;
                        padding: 5px;
                        border-radius: 2px;
                    }
                """)
                # Set initial text value
                current_value = str(self.entity.properties.get(prop_name, ""))
                input_field.setPlainText(current_value)
                row.addWidget(input_field)
            else:
                input_field = QLineEdit()
                current_value = str(self.entity.properties.get(prop_name, ""))
                input_field.setText(current_value)
                row.addWidget(input_field)
            
            self.inputs[prop_name] = input_field
            
            # Add custom styling for QDateTimeEdit
            if prop_name in ['start_date', 'end_date']:
                input_field.setStyleSheet("""
                    QDateTimeEdit {
                        background-color: #1E1E1E;
                        color: #CCCCCC;
                        border: 1px solid #3F3F46;
                        padding: 5px;
                        border-radius: 2px;
                    }
                    QDateTimeEdit::drop-down {
                        border: none;
                        width: 20px;
                    }
                    QDateTimeEdit::down-arrow {
                        image: none;
                        width: 12px;
                        height: 12px;
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
                font-family: "Geist Mono";
                font-size: 12px;
            }
            QLabel {
                color: #CCCCCC;
                font-family: "Geist Mono";
                font-size: 12px;
            }
            QLineEdit {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                padding: 5px;
                border-radius: 2px;
                font-family: "Geist Mono";
                font-size: 12px;
            }
            QPushButton {
                background-color: #007ACC;
                color: #FFFFFF;
                border: none;
                padding: 5px 15px;
                border-radius: 2px;
                font-family: "Geist Mono";
                font-size: 12px;
            }
            QPushButton[text="S"] {
                border: 1px solid #3F3F46;
                padding: 2px;
            }
            QPushButton[text="S"]:hover {
                background-color: #3F3F46;
            }
        """)
        
    def get_properties(self) -> Dict[str, Any]:
        """Get the current values from all inputs"""
        values = {}
        for prop_name, input_field in self.inputs.items():
            if prop_name in ['start_date', 'end_date']:
                if isinstance(input_field, QDateTimeEdit):
                    dt = input_field.dateTime().toPython()
                    # Strip both seconds and microseconds
                    value = dt.replace(second=0, microsecond=0)
                else:
                    value = None
            elif prop_name == 'notes':
                value = input_field.toPlainText()
            elif isinstance(input_field, QComboBox):
                value = input_field.currentText()
            elif isinstance(input_field, QCheckBox):
                value = input_field.isChecked()
            else:
                value = input_field.text().strip()
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