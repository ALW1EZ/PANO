from PySide6.QtWidgets import (
    QLineEdit, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QWidget, QSlider, QComboBox,
    QListWidget, QListWidgetItem, QDialog, QDialogButtonBox,
    QCheckBox, QGroupBox, QGridLayout, QCompleter
)
from PySide6.QtCore import Qt, QTimer, QStringListModel
from PySide6.QtGui import QIcon
from entities.location import Location
from .base import BaseHelper
import requests
import json
from datetime import datetime
from math import radians, cos, sqrt
import asyncio
from qasync import asyncSlot
import aiohttp

class FilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Custom Filter")
        layout = QVBoxLayout(self)
        
        # Filter key input with autocomplete
        key_layout = QHBoxLayout()
        key_label = QLabel("Filter Key:")
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("e.g., amenity, shop, building")
        
        # Setup autocomplete
        self.completer_model = QStringListModel()
        self.completer = QCompleter()
        self.completer.setModel(self.completer_model)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.key_input.setCompleter(self.completer)
        
        # Setup timer for autocomplete
        self.autocomplete_timer = QTimer()
        self.autocomplete_timer.setInterval(500)  # 500ms delay
        self.autocomplete_timer.timeout.connect(self.fetch_suggestions)
        self.key_input.textChanged.connect(self.start_autocomplete_timer)
        
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        layout.addLayout(key_layout)
        
        # Filter value input (optional)
        value_layout = QHBoxLayout()
        value_label = QLabel("Filter Value (optional):")
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("e.g., restaurant, school")
        value_layout.addWidget(value_label)
        value_layout.addWidget(self.value_input)
        layout.addLayout(value_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def start_autocomplete_timer(self):
        """Start or restart autocomplete timer"""
        self.autocomplete_timer.stop()
        self.autocomplete_timer.start()
        
    def fetch_suggestions(self):
        """Fetch tag suggestions from OSM Taginfo"""
        text = self.key_input.text().strip()
        if not text:
            return
            
        try:
            response = requests.get(
                f"https://taginfo.openstreetmap.org/search/suggest?format=simple&term={text}",
                headers={"User-Agent": "PANO_APP"}
            )
            suggestions = response.json()
            self.completer_model.setStringList(suggestions)
        except:
            pass  # Silently fail for autocomplete
        finally:
            self.autocomplete_timer.stop()

class LocationSearchHelper(BaseHelper):
    name = "Base Location Searcher"
    description = "Search for nearby places using a base location"
    
    # Tag filters
    TAG_FILTERS = {
        "Contact Info": [
            {"label": "Phone", "tags": ["contact:phone", "phone"]},
            {"label": "Email", "tags": ["contact:email", "email"]},
            {"label": "Website", "tags": ["contact:website", "website"]}
        ],
        "Social Media": [
            {"label": "Facebook", "tags": ["contact:facebook"]},
            {"label": "Instagram", "tags": ["contact:instagram"]},
            {"label": "Twitter", "tags": ["contact:twitter"]},
            {"label": "YouTube", "tags": ["contact:youtube"]},
            {"label": "LinkedIn", "tags": ["contact:linkedin"]}
        ],
        "Details": [
            {"label": "Opening Hours", "tags": ["opening_hours"]},
            {"label": "Description", "tags": ["description"]},
            {"label": "Operator", "tags": ["operator"]},
            {"label": "Brand", "tags": ["brand"]},
            {"label": "Cuisine", "tags": ["cuisine"]},
            {"label": "Payment Methods", "tags": ["payment:*"]}
        ]
    }
    
    # Preset filters
    PRESET_FILTERS = {
        "All Places": [
            {"key": "amenity"},
            {"key": "shop"},
            {"key": "leisure"},
            {"key": "tourism"},
            {"key": "historic"},
            {"key": "office"},
            {"key": "building"}
        ],
        "Food & Drink": [
            {"key": "amenity", "value": "restaurant"},
            {"key": "amenity", "value": "cafe"},
            {"key": "amenity", "value": "bar"},
            {"key": "amenity", "value": "fast_food"}
        ],
        "Shopping": [
            {"key": "shop"}
        ],
        "Tourism": [
            {"key": "tourism"},
            {"key": "historic"}
        ],
        "Services": [
            {"key": "office"},
            {"key": "amenity", "value": "bank"},
            {"key": "amenity", "value": "post_office"}
        ]
    }
    
    def setup_ui(self):
        """Setup the location search UI"""
        # Create main horizontal layout
        main_horizontal = QHBoxLayout()
        
        # Left side - Search and filters
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Search input
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter a location to find nearby places...")
        search_layout.addWidget(self.search_input)
        
        # Radius slider layout
        radius_layout = QHBoxLayout()
        radius_label = QLabel("Search Radius (km):")
        self.radius_value = QLabel("1")
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setMinimum(1)
        self.radius_slider.setMaximum(50)
        self.radius_slider.setValue(1)
        self.radius_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.radius_slider.setTickInterval(5)
        self.radius_slider.valueChanged.connect(self.update_radius_label)
        
        radius_layout.addWidget(radius_label)
        radius_layout.addWidget(self.radius_slider)
        radius_layout.addWidget(self.radius_value)
        
        # Filter management
        filter_layout = QHBoxLayout()
        
        # Preset filter combo
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Custom"] + list(self.PRESET_FILTERS.keys()))
        self.preset_combo.currentTextChanged.connect(self.preset_changed)
        filter_layout.addWidget(QLabel("Preset:"))
        filter_layout.addWidget(self.preset_combo)
        
        # Active filters list with stretching
        filters_widget = QWidget()
        filters_layout = QVBoxLayout(filters_widget)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        
        filters_label = QLabel("Active Filters:")
        filters_layout.addWidget(filters_label)
        
        self.filters_list = QListWidget()
        filters_layout.addWidget(self.filters_list, 1)  # Add stretch factor
        
        # Filter management buttons
        filter_buttons = QHBoxLayout()
        add_filter_btn = QPushButton("Add Filter")
        remove_filter_btn = QPushButton("Remove Selected")
        add_filter_btn.clicked.connect(self.add_custom_filter)
        remove_filter_btn.clicked.connect(self.remove_selected_filter)
        filter_buttons.addWidget(add_filter_btn)
        filter_buttons.addWidget(remove_filter_btn)
        filters_layout.addLayout(filter_buttons)
        
        # Tag filters
        tag_filters_group = QGroupBox("Required Tags (OR)")
        tag_filters_layout = QVBoxLayout()
        self.tag_checkboxes = {}
        
        for category, filters in self.TAG_FILTERS.items():
            category_group = QGroupBox(category)
            category_layout = QGridLayout()
            row = 0
            col = 0
            
            for filter_info in filters:
                checkbox = QCheckBox(filter_info["label"])
                checkbox.stateChanged.connect(self.start_search_timer)
                self.tag_checkboxes[filter_info["label"]] = (checkbox, filter_info["tags"])
                category_layout.addWidget(checkbox, row, col)
                col += 1
                if col > 1:  # 2 columns
                    col = 0
                    row += 1
                    
            category_group.setLayout(category_layout)
            tag_filters_layout.addWidget(category_group)
            
        tag_filters_group.setLayout(tag_filters_layout)
        
        # Add all to left layout
        left_layout.addLayout(search_layout)
        left_layout.addLayout(radius_layout)
        left_layout.addLayout(filter_layout)
        left_layout.addWidget(filters_widget, 1)  # Add stretch factor
        left_layout.addWidget(tag_filters_group)
        
        # Right side - Results
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Property", "Value"])
        self.results_tree.setColumnWidth(0, 150)
        self.results_tree.itemDoubleClicked.connect(self.add_to_graph_clicked)
        
        # Add to main horizontal layout
        main_horizontal.addWidget(left_widget)
        main_horizontal.addWidget(self.results_tree)
        
        # Set layout
        self.main_layout.addLayout(main_horizontal)
        
        # Setup search timer and state
        self.search_timer = QTimer()
        self.search_timer.setInterval(1000)  # 1 second delay
        self.search_timer.timeout.connect(self.start_search)
        self.is_searching = False
        
        # Add loading indicator
        self.loading_label = QLabel("Searching...")
        self.loading_label.setVisible(False)
        self.main_layout.addWidget(self.loading_label)
        
        # Connect signals
        self.search_input.textChanged.connect(self.start_search_timer)
        self.radius_slider.valueChanged.connect(self.start_search_timer)
        
        # Set dialog size
        self.resize(1000, 800)
        
        # Initialize with "All Places" preset
        self.preset_combo.setCurrentText("All Places")
        
    def preset_changed(self, preset_name):
        """Handle preset filter change"""
        self.filters_list.clear()
        if preset_name == "Custom":
            return
            
        for filter_dict in self.PRESET_FILTERS[preset_name]:
            text = filter_dict["key"]
            if "value" in filter_dict:
                text += f"={filter_dict['value']}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, filter_dict)
            self.filters_list.addItem(item)
        
        self.start_search_timer()
        
    def add_custom_filter(self):
        """Add a custom filter"""
        dialog = FilterDialog(self)
        if dialog.exec():
            key = dialog.key_input.text().strip()
            value = dialog.value_input.text().strip()
            
            if key:
                filter_dict = {"key": key}
                if value:
                    filter_dict["value"] = value
                    
                text = key
                if value:
                    text += f"={value}"
                    
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, filter_dict)
                self.filters_list.addItem(item)
                
                # Switch to Custom preset
                self.preset_combo.setCurrentText("Custom")
                self.start_search_timer()
        
    def remove_selected_filter(self):
        """Remove selected filter"""
        for item in self.filters_list.selectedItems():
            self.filters_list.takeItem(self.filters_list.row(item))
        self.start_search_timer()
        
    def get_active_filters(self):
        """Get list of active filters"""
        filters = []
        for i in range(self.filters_list.count()):
            item = self.filters_list.item(i)
            filters.append(item.data(Qt.ItemDataRole.UserRole))
        return filters
        
    def get_required_tags(self):
        """Get list of required tags from checkboxes using OR logic"""
        tag_conditions = []
        for label, (checkbox, tags) in self.tag_checkboxes.items():
            if checkbox.isChecked():
                tag_conditions.extend(tags)
        return tag_conditions
        
    def build_overpass_query(self, lat, lon, radius, filters):
        """Build Overpass query from filters and required tags"""
        query = '[out:json][timeout:25];\n('
        
        required_tags = self.get_required_tags()
        
        for filter_dict in filters:
            key = filter_dict["key"]
            
            # For each type filter, create separate queries for each tag combination
            if "value" in filter_dict:
                # Type filter with specific value
                if required_tags:
                    for tag in required_tags:
                        if tag.endswith("*"):
                            # Handle wildcard tags (e.g., payment:*)
                            base = f'  node["name"](around:{radius*1000},{lat},{lon})["{key}"="{filter_dict["value"]}"][~"^{tag[:-1]}.*$"~".*"];'
                        else:
                            base = f'  node["name"](around:{radius*1000},{lat},{lon})["{key}"="{filter_dict["value"]}"]["{tag}"];'
                        query += base + "\n"
                else:
                    # Just the type filter
                    query += f'  node["name"](around:{radius*1000},{lat},{lon})["{key}"="{filter_dict["value"]}"];\n'
            else:
                # Type filter without specific value
                if required_tags:
                    for tag in required_tags:
                        if tag.endswith("*"):
                            # Handle wildcard tags (e.g., payment:*)
                            base = f'  node["name"](around:{radius*1000},{lat},{lon})["{key}"][~"^{tag[:-1]}.*$"~".*"];'
                        else:
                            base = f'  node["name"](around:{radius*1000},{lat},{lon})["{key}"]["{tag}"];'
                        query += base + "\n"
                else:
                    # Just the type filter
                    query += f'  node["name"](around:{radius*1000},{lat},{lon})["{key}"];\n'
                
        query += ');\nout body;'
        return query
        
    def update_radius_label(self, value):
        """Update the radius label when slider changes"""
        self.radius_value.setText(f"{value}")
        
    def start_search_timer(self):
        """Start or restart search timer"""
        self.search_timer.stop()
        self.search_timer.start()
        
    @asyncSlot()
    async def start_search(self):
        """Start the search process"""
        if self.is_searching:
            return
            
        self.is_searching = True
        self.loading_label.setVisible(True)
        self.search_input.setEnabled(False)
        self.radius_slider.setEnabled(False)
        self.preset_combo.setEnabled(False)
        self.filters_list.setEnabled(False)
        
        try:
            await self.perform_search()
        finally:
            self.is_searching = False
            self.loading_label.setVisible(False)
            self.search_input.setEnabled(True)
            self.radius_slider.setEnabled(True)
            self.preset_combo.setEnabled(True)
            self.filters_list.setEnabled(True)
            self.search_timer.stop()
        
    async def perform_search(self):
        """Perform location search using Nominatim API"""
        query = self.search_input.text().strip()
        if not query:
            return
            
        try:
            async with aiohttp.ClientSession() as session:
                # First, get the coordinates of the input location
                async with session.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1
                    },
                    headers={"User-Agent": "PANO_APP"}
                ) as response:
                    response.raise_for_status()
                    results = await response.json()
                
                if not results:
                    self.results_tree.clear()
                    error_item = QTreeWidgetItem(self.results_tree)
                    error_item.setText(0, "Error")
                    error_item.setText(1, "Location not found")
                    return
                    
                # Get coordinates of the search location
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                radius = self.radius_slider.value()  # in km
                
                # Get active filters
                filters = self.get_active_filters()
                if not filters:
                    self.results_tree.clear()
                    error_item = QTreeWidgetItem(self.results_tree)
                    error_item.setText(0, "Error")
                    error_item.setText(1, "No filters selected")
                    return
                
                # Build and execute query
                area_query = self.build_overpass_query(lat, lon, radius, filters)
                async with session.get(
                    "https://overpass-api.de/api/interpreter",
                    params={"data": area_query},
                    headers={"User-Agent": "PANO_APP"}
                ) as response:
                    response.raise_for_status()
                    nearby = await response.json()
                
                # Process results
                self.process_results(nearby, lat, lon)
                
        except Exception as e:
            self.results_tree.clear()
            error_item = QTreeWidgetItem(self.results_tree)
            error_item.setText(0, "Error")
            error_item.setText(1, str(e))
            
    def process_results(self, nearby, center_lat, center_lon):
        """Process and display search results"""
        self.results_tree.clear()
        
        filtered_results = []
        for element in nearby.get("elements", []):
            if "lat" not in element or "lon" not in element or "tags" not in element:
                continue
                
            # Skip if no name
            if "name" not in element["tags"]:
                continue
                
            place_lat = float(element["lat"])
            place_lon = float(element["lon"])
            
            # Calculate distance in km
            dist_lat = abs(center_lat - place_lat) * 111.0
            dist_lon = abs(center_lon - place_lon) * 111.0 * abs(cos(radians(center_lat)))
            distance = sqrt(dist_lat**2 + dist_lon**2)
            
            # Add tags and distance to element
            element["distance"] = distance
            filtered_results.append(element)
        
        # Sort by distance
        filtered_results.sort(key=lambda x: x["distance"])
        
        # Add results to tree
        for result in filtered_results[:50]:
            self.add_result_to_tree(result)
            
        # Show result count
        if not filtered_results:
            error_item = QTreeWidgetItem(self.results_tree)
            error_item.setText(0, "Info")
            error_item.setText(1, "No places found in this area")
            
    def add_result_to_tree(self, result):
        """Add a single result to the tree"""
        # Create top-level item
        item = QTreeWidgetItem(self.results_tree)
        item.setText(0, "Name")
        name = result["tags"]["name"]
        item.setText(1, name)
        
        # Store full result data in item
        item.setData(0, Qt.ItemDataRole.UserRole, result)
        
        # Get the primary type
        place_type = None
        for type_key in ["amenity", "shop", "leisure", "tourism", "historic", "office", "building"]:
            if type_key in result["tags"]:
                place_type = f"{type_key}:{result['tags'][type_key]}"
                break
        
        # Add child items with details
        self.add_detail(item, "Type", place_type or "Unknown")
        self.add_detail(item, "Distance", f"{result['distance']:.2f} km")
        self.add_detail(item, "Centre Point", f"{result.get('lat', 0)}, {result.get('lon', 0)}")
        
        # Add all tags
        if "tags" in result:
            tags_item = QTreeWidgetItem(item)
            tags_item.setText(0, "Tags")
            for key, value in result["tags"].items():
                if key not in ["name"]:  # Skip already shown tags
                    self.add_detail(tags_item, key, value)
        
    def add_detail(self, parent, key, value):
        """Add a detail item to the tree"""
        item = QTreeWidgetItem(parent)
        item.setText(0, key)
        item.setText(1, str(value))
        
    def add_to_graph_clicked(self, item, column):
        """Handle double-click on result item"""
        # Get the top-level item
        while item.parent():
            item = item.parent()
            
        # Get the full result data
        result = item.data(0, Qt.ItemDataRole.UserRole)
        if not result:
            return
            
        # Create location entity
        tags = []
        if "tags" in result:
            for key, value in result["tags"].items():
                if key not in ["name", "brand"]:  # Skip name as it's used as title
                    tags.append(f"{key}: {value}")
                    
        name = result.get("tags", {}).get("name", 
               result.get("tags", {}).get("brand", "Unknown Location"))
                
        location = Location(properties={
            "latitude": float(result["lat"]),
            "longitude": float(result["lon"]),
            "notes": "\n".join(tags) if tags else ""
        })
        
        # Add to graph
        self.add_to_graph([location]) 