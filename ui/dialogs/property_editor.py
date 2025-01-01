from PyQt6.QtWidgets import (QDialog, QVBoxLayout,
                             QLineEdit, QLabel, QHBoxLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt
from typing import Dict, Any
from entities import Entity

class PropertyEditor(QDialog):
    def __init__(self, entity: Entity, parent=None):
        super().__init__(parent)
        self.entity = entity
        self.inputs = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle(f"Edit Properties")
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
            input_field.setText(str(current_value))
            
            self.inputs[prop_name] = input_field
            row.addWidget(input_field)
            
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
        """)
        
    def get_values(self) -> Dict[str, Any]:
        """Get the current values from all inputs"""
        values = {}
        for prop_name, input_field in self.inputs.items():
            value = input_field.text().strip()
            # Always include the value, even if empty
            values[prop_name] = value
        return values 