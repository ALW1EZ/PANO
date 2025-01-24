from typing import Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QToolButton, QCheckBox, QLabel, QSizePolicy, QMenu
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from ui.styles.map_styles import MapStyles

class MapUIInitializer:
    def __init__(self, parent: QWidget):
        self.parent = parent
        self.layer_toggles: Dict[str, QCheckBox] = {}
        
    def init_ui(self) -> None:
        self.layout = QVBoxLayout(self.parent)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self._init_layer_toggles()
        self._init_search_bar()
        self._init_web_view()
        
        # Make the web_view stretch to fill available space
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _init_layer_toggles(self) -> None:
        """Initialize layer toggle checkboxes with proper parent ownership"""
        # Create a container widget to own the checkboxes
        self.toggle_container = QWidget(self.parent)
        toggle_layout = QVBoxLayout(self.toggle_container)
        
        # Buildings toggle (checked by default)
        self.layer_toggles['buildings'] = QCheckBox("3D Buildings", self.toggle_container)
        self.layer_toggles['buildings'].setChecked(True)
        toggle_layout.addWidget(self.layer_toggles['buildings'])
        
        # Area-based places
        toggle_layout.addWidget(QLabel("Areas:"))
        
        self.layer_toggles['education'] = QCheckBox("Educational", self.toggle_container)
        toggle_layout.addWidget(self.layer_toggles['education'])
        
        self.layer_toggles['health'] = QCheckBox("Healthcare", self.toggle_container)
        toggle_layout.addWidget(self.layer_toggles['health'])
        
        self.layer_toggles['leisure'] = QCheckBox("Leisure", self.toggle_container)
        toggle_layout.addWidget(self.layer_toggles['leisure'])
        
        self.layer_toggles['transport'] = QCheckBox("Transport", self.toggle_container)
        toggle_layout.addWidget(self.layer_toggles['transport'])
        
        # Point-based places
        toggle_layout.addWidget(QLabel("Places:"))
        
        self.layer_toggles['food'] = QCheckBox("Food & Drink", self.toggle_container)
        toggle_layout.addWidget(self.layer_toggles['food'])
        
        self.layer_toggles['shops'] = QCheckBox("Shops", self.toggle_container)
        toggle_layout.addWidget(self.layer_toggles['shops'])
        
        self.layer_toggles['entertainment'] = QCheckBox("Entertainment", self.toggle_container)
        toggle_layout.addWidget(self.layer_toggles['entertainment'])
        
        self.layer_toggles['tourism'] = QCheckBox("Tourism", self.toggle_container)
        toggle_layout.addWidget(self.layer_toggles['tourism'])
        
        self.layer_toggles['services'] = QCheckBox("Services", self.toggle_container)
        toggle_layout.addWidget(self.layer_toggles['services'])
        
        self.layer_toggles['other'] = QCheckBox("Other Places", self.toggle_container)
        toggle_layout.addWidget(self.layer_toggles['other'])
        
        # Set common style for all checkboxes and labels
        for widget in [self.toggle_container.findChild(QCheckBox) for _ in range(toggle_layout.count())]:
            if isinstance(widget, QCheckBox):
                widget.setStyleSheet(MapStyles.CHECKBOX)
        
        for widget in [self.toggle_container.findChild(QLabel) for _ in range(toggle_layout.count())]:
            if isinstance(widget, QLabel):
                widget.setStyleSheet("color: white; font-weight: bold; margin-top: 10px;")

    def _init_search_bar(self) -> None:
        self.search_layout = QHBoxLayout()
        self.search_layout.setSpacing(3)
        
        self._init_tools_button()
        self._init_search_box()
        
        self.layout.addLayout(self.search_layout)

    def _init_tools_button(self) -> None:
        # Create places button
        self.places_button = QToolButton(self.parent)
        self.places_button.setText("📍")
        self.places_button.setStyleSheet(MapStyles.TOOL_BUTTON)
        self.search_layout.addWidget(self.places_button)
        
        # Create tools button
        self.tools_button = QToolButton(self.parent)
        self.tools_button.setText("🛠")
        self.tools_button.setPopupMode(QToolButton.InstantPopup)
        self.tools_button.setStyleSheet(MapStyles.TOOL_BUTTON)
        
        self.tools_menu = QMenu(self.parent)
        self.tools_menu.setStyleSheet(MapStyles.MENU)
        
        self.route_connector_action = QAction("Connect Routes", self.parent)
        self.tools_menu.addAction(self.route_connector_action)
        
        self.tools_button.setMenu(self.tools_menu)
        self.search_layout.addWidget(self.tools_button)

    def _init_search_box(self) -> None:
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Enter location or coordinates...")
        self.search_box.setStyleSheet(MapStyles.SEARCH_CONTROLS)
        
        self.search_button = QPushButton("Search")
        self.search_button.setStyleSheet(MapStyles.SEARCH_CONTROLS)
        
        self.search_layout.addWidget(self.search_box)
        self.search_layout.addWidget(self.search_button)
        
    def _init_web_view(self) -> None:
        self.web_view = QWebEngineView()
        self.web_view.settings().setAttribute(
            self.web_view.settings().WebAttribute.JavascriptEnabled, True
        )
        self.web_view.settings().setAttribute(
            self.web_view.settings().WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Add JavaScript to capture right-click coordinates
        self.web_view.page().runJavaScript("""
            document.addEventListener('contextmenu', function(e) {
                const rect = e.target.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                window.lastClickCoords = {x, y};
            });
        """)
        
        self.layout.addWidget(self.web_view)

    @property
    def search_box_widget(self) -> QLineEdit:
        return self.search_box

    @property
    def search_button_widget(self) -> QPushButton:
        return self.search_button

    @property
    def web_view_widget(self) -> QWebEngineView:
        return self.web_view

    @property
    def places_button_widget(self) -> QToolButton:
        return self.places_button

    @property
    def route_connector_action_widget(self) -> QAction:
        return self.route_connector_action 