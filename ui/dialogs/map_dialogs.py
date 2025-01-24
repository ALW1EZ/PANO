from typing import Dict, List, Tuple, Optional
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QCheckBox
from PySide6.QtCore import Qt
from ui.styles.map_styles import MapStyles

class MarkerSelectorDialog(QDialog):
    def __init__(self, markers: Dict[int, Tuple[float, float]], parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("Connect Routes")
        self.setModal(True)
        self.setStyleSheet(MapStyles.DIALOG)
        self._init_ui(markers)
        self.resize(400, 300)
    
    def _init_ui(self, markers: Dict[int, Tuple[float, float]]) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select two or more markers to connect:"))
        
        self.marker_list = QListWidget()
        self.marker_list.setSelectionMode(QListWidget.ExtendedSelection)
        for marker_id, (lat, lon) in markers.items():
            item = QListWidgetItem(f"Marker {marker_id} ({lat:.4f}, {lon:.4f})")
            item.setData(Qt.UserRole, (lat, lon))
            self.marker_list.addItem(item)
        layout.addWidget(self.marker_list)
        
        button_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
    def get_selected_markers(self) -> List[Tuple[float, float]]:
        return [item.data(Qt.UserRole) for item in self.marker_list.selectedItems()]

class PlacesDialog(QDialog):
    def __init__(self, layer_toggles: Dict[str, QCheckBox], parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("Places")
        self.setModal(True)
        self.layer_toggles = layer_toggles
        self.dialog_toggles = {}  # Store dialog's own checkboxes
        self.initial_states = {}  # Store initial states
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
                padding: 5px;
            }
            QCheckBox {
                color: white;
                background: transparent;
                padding: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #3d3d3d;
                border: 1px solid #777777;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                color: #ffffff;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        self._init_ui()
        self.resize(250, 300)
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title = QLabel("Show Places:")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        
        # Create new checkboxes and store initial states
        for key, original_toggle in self.layer_toggles.items():
            checkbox = QCheckBox(original_toggle.text(), self)
            checkbox.setChecked(original_toggle.isChecked())
            self.initial_states[key] = original_toggle.isChecked()
            self.dialog_toggles[key] = checkbox
            layout.addWidget(checkbox)
        
        layout.addStretch()
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply_changes)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    def _apply_changes(self) -> None:
        """Apply the changes and close the dialog"""
        for key, dialog_toggle in self.dialog_toggles.items():
            self.layer_toggles[key].setChecked(dialog_toggle.isChecked())
        self.accept()
    
    def reject(self) -> None:
        """Restore original states when canceling"""
        for key, original_state in self.initial_states.items():
            self.layer_toggles[key].setChecked(original_state)
        super().reject() 