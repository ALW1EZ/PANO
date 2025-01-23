from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QMenu, QToolButton, QDialog, QListWidget, QListWidgetItem, QLabel, QCheckBox, QSizePolicy
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Slot, Qt, QPoint
from PySide6.QtGui import QAction, QCloseEvent
import pydeck as pdk
import tempfile
import os
import logging
import json
import aiohttp
import asyncio
from qasync import QEventLoop, asyncSlot, asyncClose
from ui.managers.status_manager import StatusManager
from math import sin, cos, radians

# Constants
EARTH_RADIUS_METERS = 6371000
DEFAULT_BUILDING_HEIGHT = 10
DEFAULT_ZOOM = 2
DEFAULT_CENTER = [0, 0]
MARKER_PROXIMITY_THRESHOLD = 0.001

@dataclass
class RouteData:
    start: Tuple[float, float]
    end: Tuple[float, float]
    path: List[List[float]]
    distance: float
    travel_times: Dict[str, float]

@dataclass
class Building:
    contour: List[List[float]]
    height: float
    name: Optional[str] = None
    type: Optional[str] = None
    amenity: Optional[str] = None
    address: Optional[str] = None
    opening_hours: Optional[str] = None
    cuisine: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

class MapStyles:
    DIALOG = """
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
                min-width: 80px;
                height: 24px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
    """

class LocationService:
    @staticmethod
    async def geocode(query: str) -> Optional[Dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': query, 'format': 'json', 'limit': 1},
                headers={'User-Agent': 'PANO_APP'}
            ) as response:
                results = await response.json()
                return results[0] if results else None

class RouteService:
    @staticmethod
    async def get_route(start: Tuple[float, float], end: Tuple[float, float]) -> Optional[Dict[str, Any]]:
        try:
            url = f"http://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}"
            params = {
                "overview": "full",
                "geometries": "geojson",
                "steps": "false"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    if data["code"] == "Ok" and data["routes"]:
                        return {
                            "coordinates": data["routes"][0]["geometry"]["coordinates"],
                            "distance": data["routes"][0]["distance"]
                        }
            return None
        except Exception as e:
            logging.error(f"Error fetching route: {e}")
            return None

class BuildingService:
    @staticmethod
    async def fetch_buildings(lat: float, lon: float, radius: int = 500) -> List[Building]:
        overpass_url = "https://overpass-api.de/api/interpreter"
        query = f"""
        [out:json][timeout:25];
        (
          way["building"](around:{radius},{lat},{lon});
          // Also fetch amenities in the area
          node["amenity"](around:{radius},{lat},{lon});
          way["amenity"](around:{radius},{lat},{lon});
        );
        out body geom;
        """
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(overpass_url, data={"data": query}) as response:
                    data = await response.json()
                    buildings = []
                    for element in data.get('elements', []):
                        tags = element.get('tags', {})
                        
                        # Skip non-building nodes unless they are amenities
                        if element['type'] == 'node' and 'building' not in tags and 'amenity' not in tags:
                            continue
                            
                        # Get coordinates
                        if element['type'] == 'way' and 'geometry' in element:
                            coords = [[p['lon'], p['lat']] for p in element['geometry']]
                        elif element['type'] == 'node':
                            coords = [[element['lon'], element['lat']]]
                            # Create a smaller square around the point for visualization
                            lat_offset = 0.00002  # Roughly 2 meters
                            lon_offset = 0.00002 / cos(radians(element['lat']))
                            coords = [
                                [element['lon'] - lon_offset, element['lat'] - lat_offset],
                                [element['lon'] + lon_offset, element['lat'] - lat_offset],
                                [element['lon'] + lon_offset, element['lat'] + lat_offset],
                                [element['lon'] - lon_offset, element['lat'] + lat_offset],
                                [element['lon'] - lon_offset, element['lat'] - lat_offset]
                            ]
                        else:
                            continue

                        if len(coords) >= 3:  # Need at least 3 points for a polygon
                            # Get building height - only for actual buildings
                            height = DEFAULT_BUILDING_HEIGHT
                            if 'building' in tags:
                                height = tags.get('height', DEFAULT_BUILDING_HEIGHT)
                                try:
                                    height = float(height)
                                except ValueError:
                                    height = DEFAULT_BUILDING_HEIGHT
                            elif element['type'] == 'node' or tags.get('amenity') in {'school', 'university', 'library'}:
                                height = 1  # Make amenity points and educational areas flat
                            
                            # Get additional information
                            building = Building(
                                contour=coords,
                                height=height,
                                name=tags.get('name'),
                                type=tags.get('building') or tags.get('amenity'),
                                amenity=tags.get('amenity'),
                                address=BuildingService._format_address(tags),
                                opening_hours=tags.get('opening_hours'),
                                cuisine=tags.get('cuisine'),
                                phone=tags.get('phone'),
                                website=tags.get('website')
                            )
                            buildings.append(building)
                    return buildings
        except Exception as e:
            logging.error(f"Error fetching buildings: {e}")
            return []

    @staticmethod
    def _format_address(tags: Dict[str, str]) -> Optional[str]:
        """Format the address from OSM tags"""
        addr_parts = []
        if 'addr:street' in tags:
            house_number = tags.get('addr:housenumber', '')
            street = tags.get('addr:street', '')
            addr_parts.append(f"{street} {house_number}".strip())
        if 'addr:city' in tags:
            addr_parts.append(tags['addr:city'])
        if 'addr:postcode' in tags:
            addr_parts.append(tags['addr:postcode'])
        return ', '.join(addr_parts) if addr_parts else None

    @staticmethod
    def _format_tooltip(building: Building) -> str:
        """Format building information for tooltip display"""
        lines = []
        
        # Add name if available
        if building.name:
            lines.append(f"📍 {building.name}")
        
        # Add type/amenity
        if building.type:
            type_str = building.type.replace('_', ' ').title()
            lines.append(f"🏢 {type_str}")
        
        # Add address
        if building.address:
            lines.append(f"📮 {building.address}")
        
        # Add cuisine for restaurants
        if building.cuisine:
            cuisine_str = building.cuisine.replace(';', ', ').replace('_', ' ').title()
            lines.append(f"🍽️ {cuisine_str}")
        
        # Add opening hours
        if building.opening_hours:
            lines.append(f"🕒 {building.opening_hours}")
        
        # Add contact info
        if building.phone:
            lines.append(f"📞 {building.phone}")
        if building.website:
            lines.append(f"🌐 {building.website}")
        
        return '\n'.join(lines) if lines else "Building"

class MarkerSelectorDialog(QDialog):
    def __init__(self, markers: Dict[int, Tuple[float, float]], parent: Optional[QWidget] = None):
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
    def __init__(self, layer_toggles: Dict[str, QCheckBox], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Places")
        self.setModal(True)
        self.layer_toggles = layer_toggles
        self.dialog_toggles = {}  # Store dialog's own checkboxes
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
        
        # Create new checkboxes that mirror the state of original toggles
        for key, original_toggle in self.layer_toggles.items():
            checkbox = QCheckBox(original_toggle.text(), self)
            checkbox.setChecked(original_toggle.isChecked())
            checkbox.stateChanged.connect(lambda state, k=key: self._sync_toggle_state(k, state))
            self.dialog_toggles[key] = checkbox
            layout.addWidget(checkbox)
        
        layout.addStretch()
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def _sync_toggle_state(self, key: str, state: int) -> None:
        """Sync the state between dialog checkbox and original toggle"""
        self.layer_toggles[key].setChecked(state == Qt.CheckState.Checked.value)

class MapVisual(QWidget):
    # Transport speeds in meters per second
    TRANSPORT_SPEEDS = {
        'walking': 1.4,  # 5 km/h
        'car': 13.9,     # 50 km/h
        'bus': 8.3       # 30 km/h
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.markers: Dict[int, Tuple[float, float]] = {}
        self.marker_count: int = 0
        self.current_zoom: float = DEFAULT_ZOOM
        self.current_center: List[float] = DEFAULT_CENTER.copy()
        self.last_click_coords: Optional[Tuple[float, float]] = None
        self.routes: List[RouteData] = []
        self._temp_file: Optional[str] = None
        self.deck: Optional[pdk.Deck] = None
        
        self._init_ui()
        
        # Initialize map using QEventLoop
        loop = asyncio.get_event_loop()
        if loop and loop.is_running():
            asyncio.create_task(self.init_map())
        else:
            loop = QEventLoop()
            asyncio.set_event_loop(loop)
            with loop:
                loop.run_until_complete(self.init_map())

    def _init_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)  # Reduce spacing between elements
        
        self._init_layer_toggles()
        self._init_search_bar()
        self._init_web_view()
        
        # Make the web_view stretch to fill available space
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _init_layer_toggles(self) -> None:
        """Initialize layer toggle checkboxes with proper parent ownership"""
        self.layer_toggles = {}
        
        # Create a container widget to own the checkboxes
        self.toggle_container = QWidget(self)
        toggle_layout = QVBoxLayout(self.toggle_container)
        
        # 3D Buildings toggle (checked by default)
        self.layer_toggles['buildings'] = QCheckBox("3D Buildings", self.toggle_container)
        self.layer_toggles['buildings'].setChecked(True)
        self.layer_toggles['buildings'].stateChanged.connect(self._handle_layer_toggle)
        toggle_layout.addWidget(self.layer_toggles['buildings'])
        
        # Restaurants/Cafes toggle
        self.layer_toggles['food'] = QCheckBox("Restaurants/Cafes", self.toggle_container)
        self.layer_toggles['food'].stateChanged.connect(self._handle_layer_toggle)
        toggle_layout.addWidget(self.layer_toggles['food'])
        
        # Shops toggle
        self.layer_toggles['shops'] = QCheckBox("Shops", self.toggle_container)
        self.layer_toggles['shops'].stateChanged.connect(self._handle_layer_toggle)
        toggle_layout.addWidget(self.layer_toggles['shops'])
        
        # Educational toggle
        self.layer_toggles['education'] = QCheckBox("Educational", self.toggle_container)
        self.layer_toggles['education'].stateChanged.connect(self._handle_layer_toggle)
        toggle_layout.addWidget(self.layer_toggles['education'])
        
        # Other places toggle
        self.layer_toggles['other'] = QCheckBox("Other Places", self.toggle_container)
        self.layer_toggles['other'].stateChanged.connect(self._handle_layer_toggle)
        toggle_layout.addWidget(self.layer_toggles['other'])
        
        # Set common style for all checkboxes
        for toggle in self.layer_toggles.values():
            toggle.setStyleSheet("""
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
            """)

    def _init_search_bar(self) -> None:
        self.search_layout = QHBoxLayout()
        self.search_layout.setSpacing(3)
        
        self._init_tools_button()
        self._init_search_box()
        
        self.layout.addLayout(self.search_layout)

    def _init_tools_button(self) -> None:
        # Create places button
        self.places_button = QToolButton(self)
        self.places_button.setText("📍")
        self.places_button.setStyleSheet("""
            QToolButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
                min-width: 24px;
                height: 24px;
            }
            QToolButton:hover {
                background-color: #4d4d4d;
            }
        """)
        self.places_button.clicked.connect(self._show_places_dialog)
        self.search_layout.addWidget(self.places_button)
        
        # Create tools button
        self.tools_button = QToolButton(self)
        self.tools_button.setText("🛠")
        self.tools_button.setPopupMode(QToolButton.InstantPopup)
        self.tools_button.setStyleSheet("""
            QToolButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
                min-width: 24px;
                height: 24px;
            }
            QToolButton:hover {
                background-color: #4d4d4d;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        
        self.tools_menu = QMenu(self)
        self.tools_menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                color: #ffffff;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 25px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        """)
        
        self.route_connector_action = QAction("Connect Routes", self)
        self.route_connector_action.triggered.connect(self.show_route_connector)
        self.tools_menu.addAction(self.route_connector_action)
        
        self.tools_button.setMenu(self.tools_menu)
        self.search_layout.addWidget(self.tools_button)

    def _init_search_box(self) -> None:
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Enter location or coordinates...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
                height: 24px;
            }
            QLineEdit:focus {
                border: 1px solid #777777;
            }
        """)
        
        self.search_button = QPushButton("Search")
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
                min-width: 68px;
                height: 24px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        
        self.search_button.clicked.connect(self.handle_search)
        self.search_box.returnPressed.connect(self.handle_search)
        
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
        self.web_view.customContextMenuRequested.connect(self.show_context_menu)
        
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

    @staticmethod
    def calculate_travel_times(distance: float) -> Dict[str, float]:
        """Calculate travel times for different modes of transport"""
        return {mode: distance / speed for mode, speed in MapVisual.TRANSPORT_SPEEDS.items()}

    @staticmethod
    def format_time(seconds: float) -> str:
        """Format seconds into a human-readable time string"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

    def _create_circle_polygon(self, center_lat: float, center_lon: float, radius_meters: float = 500, num_points: int = 32) -> List[List[float]]:
        """Create a circle polygon around a point with radius in meters"""
        points = []
        for i in range(num_points + 1):
            angle = (i * 360 / num_points)
            dx = radius_meters * cos(radians(angle))
            dy = radius_meters * sin(radians(angle))
            
            # Convert meters to approximate degrees
            lat_offset = dy / 111111  # 1 degree = ~111111 meters for latitude
            lon_offset = dx / (111111 * cos(radians(center_lat)))  # Adjust for latitude
            
            lat = center_lat + lat_offset
            lon = center_lon + lon_offset
            points.append([lon, lat])  # Note: GeoJSON is [lon, lat]
            
        return points

    def _calculate_path_length(self, path_coords: List[List[float]]) -> float:
        """Calculate the total length of a path in meters"""
        total_length = 0
        for i in range(len(path_coords) - 1):
            # Convert to lat/lon for calculation
            start_lat = path_coords[i][1]
            start_lon = path_coords[i][0]
            end_lat = path_coords[i + 1][1]
            end_lon = path_coords[i + 1][0]
            
            # Convert degrees to radians
            lat1, lon1 = radians(start_lat), radians(start_lon)
            lat2, lon2 = radians(end_lat), radians(end_lon)
            
            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * EARTH_RADIUS_METERS * sin(radians(90) * (a ** 0.5))
            
            total_length += c
        return total_length

    async def init_map(self) -> None:
        # Set up the deck.gl map with dark theme
        self.deck = pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
            initial_view_state=pdk.ViewState(
                latitude=self.current_center[0],
                longitude=self.current_center[1],
                zoom=self.current_zoom,
                pitch=45,
                bearing=0
            ),
            layers=[]
        )

        if self.markers:
            await self._add_map_layers()
        await self.update_map_display()

    async def _add_map_layers(self) -> None:
        if not self.deck:
            return

        # Add 3D buildings around markers, avoiding duplicates for nearby markers
        processed_areas = set()
        # Create a copy of markers values for safe iteration
        for lat, lon in list(self.markers.values()):
            # Check if we already loaded buildings for a nearby location
            skip = False
            for processed_lat, processed_lon in processed_areas:
                if (abs(processed_lat - lat) < MARKER_PROXIMITY_THRESHOLD * 2 and 
                    abs(processed_lon - lon) < MARKER_PROXIMITY_THRESHOLD * 2):
                    skip = True
                    break
            
            if skip:
                continue
                
            buildings = await BuildingService.fetch_buildings(lat, lon)
            if buildings:
                building_data = []
                point_place_data = {
                    'food': [],      # For restaurants, cafes, bars
                    'shops': [],     # For shops and stores
                    'other': []      # For other amenities
                }
                area_place_data = {
                    'education': [], # For educational facilities
                    'other': []      # For other areas
                }
                
                for b in buildings:
                    try:
                        if b.amenity:  # This is a place/amenity
                            # Get center point for the place
                            center_lon = sum(p[0] for p in b.contour) / len(b.contour)
                            center_lat = sum(p[1] for p in b.contour) / len(b.contour)
                            
                            place_info = {
                                "position": [center_lon, center_lat],
                                "tooltip": BuildingService._format_tooltip(b)
                            }
                            
                            # Determine if this should be a point or area
                            is_area = (
                                b.amenity in {'school', 'university', 'library', 'hospital', 'parking'} or
                                len(b.contour) > 5  # If it has a complex shape, treat as area
                            )
                            
                            if is_area:
                                area_data = {
                                    "contour": b.contour,
                                    "height": 1,  # Keep areas flat
                                    "tooltip": BuildingService._format_tooltip(b)
                                }
                                if b.amenity in {'school', 'university', 'library'}:
                                    area_data["color"] = [100, 100, 255, 150]  # Transparent blue
                                    area_place_data['education'].append(area_data)
                                else:
                                    area_data["color"] = [255, 200, 0, 150]  # Transparent yellow
                                    area_place_data['other'].append(area_data)
                            else:
                                # Point-based places (restaurants, shops, etc.)
                                if b.amenity in {'restaurant', 'cafe', 'bar'}:
                                    place_info["color"] = [255, 100, 100]  # Red
                                    point_place_data['food'].append(place_info)
                                elif b.amenity in {'shop', 'store', 'supermarket'}:
                                    place_info["color"] = [100, 255, 100]  # Green
                                    point_place_data['shops'].append(place_info)
                                else:
                                    place_info["color"] = [255, 200, 0]  # Yellow
                                    point_place_data['other'].append(place_info)
                        else:  # This is a regular building
                            data = {
                                "contour": b.contour,
                                "height": b.height,
                                "tooltip": BuildingService._format_tooltip(b),
                                "color": [74, 80, 87, 200]  # Default gray for buildings
                            }
                            building_data.append(data)
                    except Exception as e:
                        logging.error(f"Error processing building data: {e}")
                        continue
                
                # Add buildings layer first (bottom layer)
                if building_data and self.layer_toggles['buildings'].isChecked():
                    building_layer = pdk.Layer(
                        "PolygonLayer",
                        building_data,  # Pass the list directly
                        get_polygon="contour",
                        get_elevation="height",
                        elevation_scale=1,
                        extruded=True,
                        wireframe=True,
                        get_fill_color="color",
                        get_line_color=[255, 255, 255],
                        line_width_min_pixels=1,
                        pickable=True,
                        opacity=0.8,
                        tooltip={"text": "{tooltip}"}
                    )
                    self.deck.layers.append(building_layer)
                
                # Add educational areas
                if area_place_data['education'] and self.layer_toggles['education'].isChecked():
                    edu_layer = pdk.Layer(
                        "PolygonLayer",
                        area_place_data['education'],
                        get_polygon="contour",
                        get_elevation="height",
                        elevation_scale=1,
                        extruded=True,
                        wireframe=False,
                        get_fill_color="color",
                        get_line_color=[255, 255, 255],
                        line_width_min_pixels=1,
                        pickable=True,
                        opacity=0.5,
                        tooltip={"text": "{tooltip}"}
                    )
                    self.deck.layers.append(edu_layer)
                
                # Add other areas
                if area_place_data['other'] and self.layer_toggles['other'].isChecked():
                    other_area_layer = pdk.Layer(
                        "PolygonLayer",
                        area_place_data['other'],
                        get_polygon="contour",
                        get_elevation="height",
                        elevation_scale=1,
                        extruded=True,
                        wireframe=False,
                        get_fill_color="color",
                        get_line_color=[255, 255, 255],
                        line_width_min_pixels=1,
                        pickable=True,
                        opacity=0.5,
                        tooltip={"text": "{tooltip}"}
                    )
                    self.deck.layers.append(other_area_layer)
                
                # Add food places
                if point_place_data['food'] and self.layer_toggles['food'].isChecked():
                    food_layer = pdk.Layer(
                        "ScatterplotLayer",
                        point_place_data['food'],
                        get_position="position",
                        get_fill_color="color",
                        get_line_color=[255, 255, 255],
                        line_width_min_pixels=2,
                        get_radius=15,
                        radius_min_pixels=5,
                        radius_max_pixels=15,
                        pickable=True,
                        opacity=0.8,
                        stroked=True,
                        tooltip={"text": "{tooltip}"},
                        get_elevation=1000,
                        elevation_scale=1,
                        parameters={"depthTest": False}
                    )
                    self.deck.layers.append(food_layer)
                
                # Add shop places
                if point_place_data['shops'] and self.layer_toggles['shops'].isChecked():
                    shop_layer = pdk.Layer(
                        "ScatterplotLayer",
                        point_place_data['shops'],
                        get_position="position",
                        get_fill_color="color",
                        get_line_color=[255, 255, 255],
                        line_width_min_pixels=2,
                        get_radius=15,
                        radius_min_pixels=5,
                        radius_max_pixels=15,
                        pickable=True,
                        opacity=0.8,
                        stroked=True,
                        tooltip={"text": "{tooltip}"},
                        get_elevation=1000,
                        elevation_scale=1,
                        parameters={"depthTest": False}
                    )
                    self.deck.layers.append(shop_layer)
                
                # Add other point places
                if point_place_data['other'] and self.layer_toggles['other'].isChecked():
                    other_point_layer = pdk.Layer(
                        "ScatterplotLayer",
                        point_place_data['other'],
                        get_position="position",
                        get_fill_color="color",
                        get_line_color=[255, 255, 255],
                        line_width_min_pixels=2,
                        get_radius=15,
                        radius_min_pixels=5,
                        radius_max_pixels=15,
                        pickable=True,
                        opacity=0.8,
                        stroked=True,
                        tooltip={"text": "{tooltip}"},
                        get_elevation=1000,
                        elevation_scale=1,
                        parameters={"depthTest": False}
                    )
                    self.deck.layers.append(other_point_layer)
                
                processed_areas.add((lat, lon))

        # Add routes if any exist
        if self.routes:
            route_data = []
            for route in self.routes:
                route_data.append({
                    "path": route.path,
                    "distance": f"{route.distance/1000:.2f} km",
                    "walking": f"🚶 {self.format_time(route.travel_times['walking'])}",
                    "driving": f"🚗 {self.format_time(route.travel_times['car'])}",
                    "bus": f"🚌 {self.format_time(route.travel_times['bus'])}"
                })
            
            route_layer = pdk.Layer(
                "PathLayer",
                route_data,
                get_path="path",
                get_width=5,
                get_color=[255, 140, 0],
                width_scale=1,
                width_min_pixels=2,
                pickable=True,
                opacity=0.8,
                tooltip={
                    "text": "Distance: {distance}\n{walking}\n{driving}\n{bus}"
                }
            )
            self.deck.layers.append(route_layer)

        # Add markers last (top layer)
        marker_data = [{"coordinates": [lon, lat]} for lat, lon in list(self.markers.values())]
        marker_layer = pdk.Layer(
            "ScatterplotLayer",
            marker_data,
            get_position="coordinates",
            get_fill_color=[18, 136, 232],
            get_line_color=[255, 255, 255],
            line_width_min_pixels=2,
            get_radius=20,
            radius_min_pixels=5,
            radius_max_pixels=15,
            pickable=True,
            opacity=1.0,
            stroked=True,
            get_elevation=3000,  # Highest elevation
            elevation_scale=1,
            parameters={
                "depthTest": False
            }
        )
        self.deck.layers.append(marker_layer)

    async def update_map_display(self) -> None:
        try:
            # Clean up previous temporary file
            if self._temp_file and os.path.exists(self._temp_file):
                try:
                    os.unlink(self._temp_file)
                except Exception as e:
                    logging.warning(f"Failed to delete previous temporary file: {e}")

            # Create new temporary file
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.html', delete=False) as temp_file:
                self._temp_file = temp_file.name
                
                if not self.deck:
                    logging.error("Deck.gl instance not initialized")
                    return
                    
                html_content = self.deck.to_html(as_string=True)
                
                if html_content is None:
                    logging.error("Failed to generate deck.gl HTML content")
                    return
                
                # Add required CSS for Mapbox GL
                css_link = '<link href="https://api.mapbox.com/mapbox-gl-js/v2.6.1/mapbox-gl.css" rel="stylesheet">'
                html_content = html_content.replace('</head>', f'{css_link}</head>')
                
                temp_file.write(html_content)
                temp_file.flush()
            
            if os.path.exists(self._temp_file):
                self.web_view.setUrl(QUrl.fromLocalFile(self._temp_file))
            else:
                logging.error("Generated temporary file not found")
                
        except Exception as e:
            logging.error(f"Error updating map display: {e}")
            if hasattr(e, '__traceback__'):
                import traceback
                logging.error(traceback.format_exc())
            
    @asyncClose
    async def closeEvent(self, event: QCloseEvent) -> None:
        """Handle cleanup when widget is closed"""
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.unlink(self._temp_file)
            except Exception as e:
                logging.warning(f"Failed to cleanup temporary file during close: {e}")
        event.accept()

    @asyncSlot()
    async def set_center(self, lat: float, lon: float, zoom: Optional[float] = None) -> None:
        """Set the map center and optionally zoom level"""
        self.current_center = [lat, lon]
        if zoom is not None:
            self.current_zoom = zoom
        await self.init_map()

    @asyncSlot()
    async def add_marker(self, lat: float, lon: float, popup: Optional[str] = None) -> None:
        """Add a marker to the map"""
        self.marker_count += 1
        marker_id = self.marker_count
        self.markers[marker_id] = (lat, lon)
        asyncio.create_task(self._refresh_map())

    @asyncSlot()
    async def add_marker_and_center(self, lat: float, lon: float, zoom: Optional[float] = None) -> None:
        """Add a marker and center the map in a single operation"""
        self.marker_count += 1
        marker_id = self.marker_count
        self.markers[marker_id] = (lat, lon)
        self.current_center = [lat, lon]
        if zoom is not None:
            self.current_zoom = zoom
        asyncio.create_task(self._refresh_map())

    @asyncSlot()
    async def _delete_nearby_marker(self, lat: float, lon: float, threshold: float = MARKER_PROXIMITY_THRESHOLD) -> None:
        """Delete any marker near the given coordinates"""
        for marker_id, marker_coords in list(self.markers.items()):
            if (abs(marker_coords[0] - lat) < threshold and 
                abs(marker_coords[1] - lon) < threshold):
                self.markers.pop(marker_id)
                await self.init_map()
                break

    def _handle_context_menu_creation(self, position: QPoint) -> Callable[[Optional[List[float]]], None]:
        @Slot(object)
        def callback(coords: Optional[List[float]]) -> None:
            if not coords:
                return
                
            menu = QMenu(self)
            
            copy_coords = QAction("Copy Coordinates", self)
            copy_coords.triggered.connect(lambda: self._copy_coordinates(coords))
            menu.addAction(copy_coords)
            
            add_marker = QAction("Add Marker", self)
            add_marker.triggered.connect(lambda: self._handle_add_marker(coords[0], coords[1]))
            menu.addAction(add_marker)
            
            if self._is_marker_nearby(coords[0], coords[1]):
                delete_marker = QAction("Delete Marker", self)
                delete_marker.triggered.connect(lambda: self._handle_delete_marker(coords[0], coords[1]))
                menu.addAction(delete_marker)
            
            menu.exec(self.web_view.mapToGlobal(position))
            
        return callback
        
    def _handle_add_marker(self, lat: float, lon: float) -> None:
        """Helper method to handle add marker action"""
        asyncio.get_event_loop().create_task(self.add_marker(lat, lon))

    def _handle_delete_marker(self, lat: float, lon: float) -> None:
        """Helper method to handle delete marker action"""
        asyncio.get_event_loop().create_task(self._delete_nearby_marker(lat, lon))
        
    def _copy_coordinates(self, coords: List[float]) -> None:
        from PySide6.QtWidgets import QApplication
        text = f"{coords[0]:.6f}, {coords[1]:.6f}"
        QApplication.clipboard().setText(text)
    
    def _is_marker_nearby(self, lat: float, lon: float, threshold: float = MARKER_PROXIMITY_THRESHOLD) -> bool:
        for marker_id, marker_coords in self.markers.items():
            if (abs(marker_coords[0] - lat) < threshold and 
                abs(marker_coords[1] - lon) < threshold):
                return True
        return False
    
    @asyncSlot()
    async def show_route_connector(self) -> None:
        """Show the route connector dialog"""
        if len(self.markers) < 2:
            status = StatusManager.get()
            status.set_text("Need at least 2 markers to connect routes")
            return
            
        dialog = MarkerSelectorDialog(self.markers, self)
        if dialog.exec() == QDialog.Accepted:
            selected_markers = dialog.get_selected_markers()
            if len(selected_markers) >= 2:
                status = StatusManager.get()
                operation_id = status.start_loading("Fetching Routes")
                
                try:
                    # Create routes between consecutive markers
                    for i in range(len(selected_markers) - 1):
                        start = selected_markers[i]
                        end = selected_markers[i + 1]
                        
                        status.set_text(f"Fetching route {i+1} of {len(selected_markers)-1}...")
                        route_data = await RouteService.get_route(start, end)
                        
                        if route_data:
                            path_coords = route_data["coordinates"]
                            distance = route_data["distance"]
                        else:
                            # Fallback to straight line if route fetch fails
                            path_coords = [start[1], start[0]], [end[1], end[0]]
                            distance = self._calculate_path_length(path_coords)
                        
                        # Calculate travel times
                        travel_times = self.calculate_travel_times(distance)
                        
                        self.routes.append(RouteData(
                            start=start,
                            end=end,
                            path=path_coords,
                            distance=distance,
                            travel_times=travel_times
                        ))
                    
                    # Use create_task to avoid task conflicts
                    asyncio.create_task(self._refresh_map())
                    status.set_text(f"Added {len(selected_markers) - 1} routes")
                except Exception as e:
                    logging.error(f"Error creating routes: {e}")
                    status.set_text(f"Error creating routes: {str(e)}")
                finally:
                    status.stop_loading(operation_id)

    async def _refresh_map(self) -> None:
        """Helper method to refresh the map safely"""
        try:
            await self.init_map()
        except Exception as e:
            logging.error(f"Error refreshing map: {e}")

    def _show_places_dialog(self) -> None:
        dialog = PlacesDialog(self.layer_toggles, self)
        dialog.finished.connect(lambda: asyncio.create_task(self._refresh_map()))
        dialog.exec()

    @asyncSlot()
    async def _handle_layer_toggle(self) -> None:
        """Handle layer visibility toggle"""
        asyncio.create_task(self._refresh_map())

    @asyncSlot()
    async def handle_search(self) -> None:
        query = self.search_box.text().strip()
        if not query:
            return
            
        status = StatusManager.get()
        operation_id = status.start_loading("Location Search")
        status.set_text("Searching location...")
            
        try:
            # Try to parse as "lat, lon"
            parts = query.split(',')
            if len(parts) == 2:
                try:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        status.set_text("Loading location data...")
                        await self.add_marker_and_center(lat, lon, zoom=13)
                    self.search_box.clear()
                    status.set_text(f"Found coordinates: {lat:.6f}, {lon:.6f}")
                    return
                except ValueError:
                    pass
            
            # If not coordinates, use geocoding service
            location = await LocationService.geocode(query)
            if location:
                lat = float(location['lat'])
                lon = float(location['lon'])
                status.set_text("Loading location data...")
                await self.add_marker_and_center(lat, lon, zoom=13)
                self.search_box.clear()
                status.set_text(f"Found location: {location.get('display_name', query)}")
            else:
                status.set_text(f"No results found for: {query}")
        except Exception as e:
            status.set_text(f"Error during search: {str(e)}")
        finally:
            status.stop_loading(operation_id) 

    def show_context_menu(self, position: QPoint) -> None:
        # Get coordinates from the click position
        js_code = """
        (function() {
            const map = document.querySelector('canvas').parentElement;
            if (!map || !map._deck) return null;
            
            const viewport = map._deck.getViewports()[0];
            if (!viewport) return null;
            
            const rect = map.getBoundingClientRect();
            const x = window.lastClickCoords ? window.lastClickCoords.x : 0;
            const y = window.lastClickCoords ? window.lastClickCoords.y : 0;
            
            const lngLat = viewport.unproject([x, y]);
            return [lngLat[1], lngLat[0]];  // [lat, lon]
        })();
        """
        
        self.web_view.page().runJavaScript(js_code, self._handle_context_menu_creation(position)) 