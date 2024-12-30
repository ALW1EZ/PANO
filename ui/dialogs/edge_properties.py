from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QDialogButtonBox, QComboBox
)
from PyQt6.QtCore import Qt

class EdgePropertiesDialog(QDialog):
    def __init__(self, edge, parent=None):
        super().__init__(parent)
        self.edge = edge
        self.setWindowTitle("Edge Properties")
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Relationship input
        relationship_layout = QHBoxLayout()
        relationship_label = QLabel("Relationship:")
        self.relationship_input = QLineEdit(self.edge.relationship)
        relationship_layout.addWidget(relationship_label)
        relationship_layout.addWidget(self.relationship_input)
        layout.addLayout(relationship_layout)
        
        # Line style selector
        style_layout = QHBoxLayout()
        style_label = QLabel("Line Style:")
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Solid", "Dashed", "Dotted"])
        
        # Set current style
        current_style = self.edge.style.style
        if current_style == Qt.PenStyle.DashLine:
            self.style_combo.setCurrentText("Dashed")
        elif current_style == Qt.PenStyle.DotLine:
            self.style_combo.setCurrentText("Dotted")
        else:
            self.style_combo.setCurrentText("Solid")
            
        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo)
        layout.addLayout(style_layout)
        
        # Source and target labels (read-only)
        source_layout = QHBoxLayout()
        source_label = QLabel("Source:")
        source_value = QLabel(self.edge.source.node.get_main_display())
        source_value.setStyleSheet("color: #888888;")
        source_layout.addWidget(source_label)
        source_layout.addWidget(source_value)
        layout.addLayout(source_layout)
        
        target_layout = QHBoxLayout()
        target_label = QLabel("Target:")
        target_value = QLabel(self.edge.target.node.get_main_display())
        target_value.setStyleSheet("color: #888888;")
        target_layout.addWidget(target_label)
        target_layout.addWidget(target_value)
        layout.addLayout(target_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
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
            QComboBox {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                padding: 5px;
                border-radius: 2px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 3px solid none;
                border-right: 3px solid none;
                border-top: 5px solid #CCCCCC;
                width: 0;
                height: 0;
                margin-right: 5px;
            }
            QPushButton {
                background-color: #007ACC;
                color: #FFFFFF;
                border: none;
                padding: 5px 15px;
                border-radius: 2px;
            }
        """)
        
    def get_values(self):
        """Get the updated values"""
        return {
            'relationship': self.relationship_input.text(),
            'line_style': self._get_line_style()
        }
        
    def _get_line_style(self) -> Qt.PenStyle:
        """Convert combo box selection to Qt.PenStyle"""
        style_text = self.style_combo.currentText()
        if style_text == "Dashed":
            return Qt.PenStyle.DashLine
        elif style_text == "Dotted":
            return Qt.PenStyle.DotLine
        return Qt.PenStyle.SolidLine 
