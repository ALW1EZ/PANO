from typing import Dict, List, Tuple, Optional, Any, Callable
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QMenu, QToolButton, QDialog, QListWidget, QListWidgetItem, QLabel, QCheckBox, QSizePolicy
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Slot, Qt, QPoint
from PySide6.QtGui import QAction, QCloseEvent
import pydeck as pdk
import tempfile
import os
import logging
import json
import asyncio
from qasync import QEventLoop, asyncSlot, asyncClose
from ui.managers.status_manager import StatusManager
from math import sin, cos, radians

# Import modularized components
from ui.models.map_models import RouteData, Building
from ui.services.map_services import LocationService, RouteService, BuildingService, EARTH_RADIUS_METERS
from ui.styles.map_styles import MapStyles
from ui.dialogs.map_dialogs import MarkerSelectorDialog, PlacesDialog
from ui.components.map_ui_initializer import MapUIInitializer
from ui.components.map_layer_manager import MapLayerManager

# Constants
DEFAULT_ZOOM = 2
DEFAULT_CENTER = [0, 0]
MARKER_PROXIMITY_THRESHOLD = 0.001

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
        
        # Initialize UI components
        self.ui = MapUIInitializer(self)
        self.ui.init_ui()
        self.layer_manager = MapLayerManager(self.ui.layer_toggles)
        
        # Connect signals
        self._connect_signals()
        
        # Initialize map using QEventLoop
        loop = asyncio.get_event_loop()
        if loop and loop.is_running():
            asyncio.create_task(self.init_map())
        else:
            loop = QEventLoop()
            asyncio.set_event_loop(loop)
            with loop:
                loop.run_until_complete(self.init_map())

    def _connect_signals(self) -> None:
        self.ui.search_button_widget.clicked.connect(self.handle_search)
        self.ui.search_box_widget.returnPressed.connect(self.handle_search)
        self.ui.web_view_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.places_button_widget.clicked.connect(self._show_places_dialog)
        self.ui.route_connector_action_widget.triggered.connect(self.show_route_connector)
        for toggle in self.ui.layer_toggles.values():
            toggle.stateChanged.connect(self._handle_layer_toggle)

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
                # Add building layer
                building_layer = self.layer_manager.create_building_layer(buildings)
                if building_layer:
                    self.deck.layers.append(building_layer)
                
                # Add place layers
                place_layers = self.layer_manager.create_place_layers(buildings)
                self.deck.layers.extend(place_layers)
                
                processed_areas.add((lat, lon))

        # Add routes if any exist
        if self.routes:
            route_layer = self.layer_manager.create_route_layer(self.routes)
            if route_layer:
                self.deck.layers.append(route_layer)

        # Add markers last (top layer)
        marker_layer = self.layer_manager.create_marker_layer(self.markers)
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
                self.ui.web_view_widget.setUrl(QUrl.fromLocalFile(self._temp_file))
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
            menu.setStyleSheet(MapStyles.MENU)
            
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
            
            menu.exec(self.ui.web_view_widget.mapToGlobal(position))
            
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
                            path_coords = [[start[1], start[0]], [end[1], end[0]]]
                            distance = RouteService.calculate_path_length(path_coords)
                        
                        # Calculate travel times
                        travel_times = {mode: distance / speed for mode, speed in self.TRANSPORT_SPEEDS.items()}
                        
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
        dialog = PlacesDialog(self.ui.layer_toggles, self)
        dialog.finished.connect(lambda: asyncio.create_task(self._refresh_map()))
        dialog.exec()

    @asyncSlot()
    async def _handle_layer_toggle(self) -> None:
        """Handle layer visibility toggle"""
        asyncio.create_task(self._refresh_map())

    @asyncSlot()
    async def handle_search(self) -> None:
        query = self.ui.search_box_widget.text().strip()
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
                    self.ui.search_box_widget.clear()
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
                self.ui.search_box_widget.clear()
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
        
        self.ui.web_view_widget.page().runJavaScript(js_code, self._handle_context_menu_creation(position)) 