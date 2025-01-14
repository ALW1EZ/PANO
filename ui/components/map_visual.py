from PySide6.QtWidgets import QWidget, QVBoxLayout, QMenu
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Slot, QPoint, Qt
from PySide6.QtGui import QAction
import folium
from folium.plugins import Draw, MeasureControl, MousePosition
import tempfile
import os
import logging
import json
from folium.features import DivIcon
from math import pi, cos

class MapVisual(QWidget):
    # Average speeds in meters per second
    TRANSPORT_SPEEDS = {
        'walking': 1.4,  # 5 km/h
        'car': 13.9,     # 50 km/h
        'bus': 8.3       # 30 km/h
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Create web view for the map
        self.web_view = QWebEngineView()
        self.web_view.settings().setAttribute(
            self.web_view.settings().WebAttribute.JavascriptEnabled, True
        )
        self.web_view.settings().setAttribute(
            self.web_view.settings().WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        self.layout.addWidget(self.web_view)
        
        self._temp_file = None
        self.markers = {}
        self.marker_count = 0
        
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.web_view.customContextMenuRequested.connect(self.show_context_menu)
        
        self.init_map()

    def calculate_travel_times(self, distance):
        """Calculate travel times for different modes of transport"""
        return {mode: distance / speed for mode, speed in self.TRANSPORT_SPEEDS.items()}

    def format_time(self, seconds):
        """Format seconds into a human-readable time string"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def init_map(self):
        # Create a folium map centered at (0, 0) with CartoDB dark matter tiles
        self.folium_map = folium.Map(
            location=[0, 0],
            zoom_start=2,
            tiles=None,  # Start with no base layer
            control_scale=True,
            prefer_canvas=True
        )
        
        # Add base layers with radio buttons
        folium.TileLayer(
            tiles='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='© OpenStreetMap contributors',
            name='OpenStreetMap',
            control=True,
            overlay=False
        ).add_to(self.folium_map)

        folium.TileLayer(
            tiles='http://tile.memomaps.de/tilegen/{z}/{x}/{y}.png',
            attr='© MeMoMaps contributors',
            name='Transport Map',
            control=True,
            overlay=False
        ).add_to(self.folium_map)

        folium.TileLayer(
            tiles='CartoDB dark_matter',
            name='Dark Mode',
            control=True,
            overlay=False
        ).add_to(self.folium_map)

        # Add layer control with exclusive layers (radio buttons)
        folium.LayerControl(position='topright', collapsed=True).add_to(self.folium_map)
        
        # Add custom draw with travel time calculations
        draw = Draw(
            position='topleft',
            draw_options={
                'polyline': {
                    'metric': True,
                    'showLength': True,
                    'shapeOptions': {
                        'color': '#1288e8'
                    }
                },
                'rectangle': True,  # Re-enable rectangle
                'polygon': True,    # Re-enable polygon
                'circle': {
                    'metric': True,
                    'showRadius': True,
                    'shapeOptions': {
                        'color': '#1288e8'
                    }
                },
                'marker': True,
                'circlemarker': False,
                'polygon': {
                    'metric': True,
                    'showArea': True,
                    'shapeOptions': {
                        'color': '#1288e8',
                        'fillColor': '#1288e8',
                        'fillOpacity': 0.2
                    }
                },
                'rectangle': {
                    'metric': True,
                    'showArea': True,
                    'shapeOptions': {
                        'color': '#1288e8',
                        'fillColor': '#1288e8',
                        'fillOpacity': 0.2
                    }
                }
            },
            edit_options={
                'featureGroup': None,  # Required for edit to work
                'edit': True,
                'remove': True
            }
        )
        draw.add_to(self.folium_map)
        
        # Add measurement control
        measure = MeasureControl(
            position='topleft',
            primary_length_unit='meters',
            secondary_length_unit='kilometers',
            primary_area_unit='sqmeters',
            secondary_area_unit='hectares'
        )
        measure.add_to(self.folium_map)
        
        # Add mouse position display
        MousePosition().add_to(self.folium_map)
        
        # Add JavaScript for travel time calculations
        self.folium_map.get_root().script.add_child(folium.Element("""
            // Wait for the map to be ready
            document.addEventListener('DOMContentLoaded', function() {
                // Get the map container
                var mapContainer = document.querySelector('#map');
                if (!mapContainer) return;
                
                // Wait for Leaflet to be initialized
                var waitForMap = setInterval(function() {
                    // Find the Leaflet map instance
                    var maps = Object.values(window).filter(function(value) {
                        return value && value._leaflet_id && value instanceof L.Map;
                    });
                    
                    if (maps.length > 0) {
                        clearInterval(waitForMap);
                        var map = maps[0];
                        
                        // Initialize FeatureGroup for drawn items
                        var drawnItems = new L.FeatureGroup();
                        map.addLayer(drawnItems);
                        
                        // Configure draw control
                        var drawControl = document.querySelector('.leaflet-draw');
                        if (drawControl) {
                            drawControl.style.display = 'block';
                        }
                        
                        // Handle right-click events
                        map.on('contextmenu', function(e) {
                            window.lastRightClick = {
                                lat: e.latlng.lat,
                                lng: e.latlng.lng
                            };
                            // Prevent default context menu
                            e.originalEvent.preventDefault();
                        });
                        
                        // Format time helper function
                        function formatTime(seconds) {
                            var hours = Math.floor(seconds / 3600);
                            var minutes = Math.floor((seconds % 3600) / 60);
                            return hours > 0 ? hours + 'h ' + minutes + 'm' : minutes + 'm';
                        }
                        
                        // Handle draw events
                        map.on('draw:created', function(e) {
                            var layer = e.layer;
                            drawnItems.addLayer(layer);
                            
                            if (e.layerType === 'circle') {
                                var radius = layer.getRadius();
                                
                                // Calculate travel times
                                var walkTime = radius / 1.4;
                                var carTime = radius / 13.9;
                                var busTime = radius / 8.3;
                                
                                var popupContent = 
                                    '<div class="travel-times">' +
                                    '<strong>Radius:</strong> ' + (radius/1000).toFixed(2) + ' km<br>' +
                                    '<strong>Travel times:</strong><br>' +
                                    '🚶 Walking: ' + formatTime(walkTime) + '<br>' +
                                    '🚗 Car: ' + formatTime(carTime) + '<br>' +
                                    '🚌 Bus: ' + formatTime(busTime) +
                                    '</div>';
                                
                                layer.bindPopup(popupContent).openPopup();
                            }
                            else if (e.layerType === 'polyline') {
                                var distance = 0;
                                var latlngs = layer.getLatLngs();
                                
                                for (var i = 0; i < latlngs.length - 1; i++) {
                                    distance += latlngs[i].distanceTo(latlngs[i + 1]);
                                }
                                
                                // Calculate travel times
                                var walkTime = distance / 1.4;
                                var carTime = distance / 13.9;
                                var busTime = distance / 8.3;
                                
                                var popupContent = 
                                    '<div class="travel-times">' +
                                    '<strong>Distance:</strong> ' + (distance/1000).toFixed(2) + ' km<br>' +
                                    '<strong>Travel times:</strong><br>' +
                                    '🚶 Walking: ' + formatTime(walkTime) + '<br>' +
                                    '🚗 Car: ' + formatTime(carTime) + '<br>' +
                                    '🚌 Bus: ' + formatTime(busTime) +
                                    '</div>';
                                
                                layer.bindPopup(popupContent).openPopup();
                            }
                            else if (e.layerType === 'marker') {
                                var latlng = layer.getLatLng();
                                layer.bindPopup('Marker at: ' + latlng.lat.toFixed(6) + ', ' + latlng.lng.toFixed(6)).openPopup();
                            }
                        });
                        
                        // Handle edit events
                        map.on('draw:edited', function(e) {
                            var layers = e.layers;
                            layers.eachLayer(function(layer) {
                                if (layer instanceof L.Circle) {
                                    // Recalculate circle popup
                                    var radius = layer.getRadius();
                                    var walkTime = radius / 1.4;
                                    var carTime = radius / 13.9;
                                    var busTime = radius / 8.3;
                                    
                                    var popupContent = 
                                        '<div class="travel-times">' +
                                        '<strong>Radius:</strong> ' + (radius/1000).toFixed(2) + ' km<br>' +
                                        '<strong>Travel times:</strong><br>' +
                                        '🚶 Walking: ' + formatTime(walkTime) + '<br>' +
                                        '🚗 Car: ' + formatTime(carTime) + '<br>' +
                                        '🚌 Bus: ' + formatTime(busTime) +
                                        '</div>';
                                    
                                    layer.setPopupContent(popupContent);
                                }
                                else if (layer instanceof L.Polyline && !(layer instanceof L.Polygon)) {
                                    // Recalculate polyline popup
                                    var distance = 0;
                                    var latlngs = layer.getLatLngs();
                                    
                                    for (var i = 0; i < latlngs.length - 1; i++) {
                                        distance += latlngs[i].distanceTo(latlngs[i + 1]);
                                    }
                                    
                                    var walkTime = distance / 1.4;
                                    var carTime = distance / 13.9;
                                    var busTime = distance / 8.3;
                                    
                                    var popupContent = 
                                        '<div class="travel-times">' +
                                        '<strong>Distance:</strong> ' + (distance/1000).toFixed(2) + ' km<br>' +
                                        '<strong>Travel times:</strong><br>' +
                                        '🚶 Walking: ' + formatTime(walkTime) + '<br>' +
                                        '🚗 Car: ' + formatTime(carTime) + '<br>' +
                                        '🚌 Bus: ' + formatTime(busTime) +
                                        '</div>';
                                    
                                    layer.setPopupContent(popupContent);
                                }
                            });
                        });
                    }
                }, 100);
            });
        """))
        
        # Save map to temporary file and display it
        self.update_map_display()
        
    def show_context_menu(self, position: QPoint):
        js_code = """
        (function() {
            if (window.lastRightClick) {
                return [window.lastRightClick.lat, window.lastRightClick.lng];
            }
            return null;
        })();
        """
        self.web_view.page().runJavaScript(js_code, self._handle_context_menu_creation(position))
    
    def _handle_context_menu_creation(self, position: QPoint):
        @Slot()
        def callback(coords):
            if not coords:
                return
                
            menu = QMenu(self)
            
            # Copy coordinates action
            copy_coords = QAction("Copy Coordinates", self)
            copy_coords.triggered.connect(lambda: self._copy_coordinates(coords))
            menu.addAction(copy_coords)
            
            # Add marker action
            add_marker = QAction("Add Marker", self)
            add_marker.triggered.connect(lambda: self.add_marker(coords[0], coords[1]))
            menu.addAction(add_marker)
            
            # Delete marker action (only show if there's a marker near the click)
            if self._is_marker_nearby(coords[0], coords[1]):
                delete_marker = QAction("Delete Marker", self)
                delete_marker.triggered.connect(lambda: self._delete_nearby_marker(coords[0], coords[1]))
                menu.addAction(delete_marker)
            
            menu.exec(self.web_view.mapToGlobal(position))
            
        return callback
        
    def _copy_coordinates(self, coords):
        from PySide6.QtWidgets import QApplication
        text = f"{coords[0]:.6f}, {coords[1]:.6f}"
        QApplication.clipboard().setText(text)
    
    def _is_marker_nearby(self, lat, lon, threshold=0.001):
        for marker_id, marker_coords in self.markers.items():
            if (abs(marker_coords[0] - lat) < threshold and 
                abs(marker_coords[1] - lon) < threshold):
                return True
        return False
    
    def _delete_nearby_marker(self, lat, lon, threshold=0.001):
        """Delete any marker near the given coordinates"""
        for marker_id, marker_coords in list(self.markers.items()):
            if (abs(marker_coords[0] - lat) < threshold and 
                abs(marker_coords[1] - lon) < threshold):
                self.markers.pop(marker_id)
                # Recreate the map to remove the marker
                self.init_map()
                # Re-add all remaining markers
                for mid, (mlat, mlon) in self.markers.items():
                    folium.Marker(
                        [mlat, mlon],
                        popup=f"Marker {mid}"
                    ).add_to(self.folium_map)
                self.update_map_display()
                break
    
    def add_marker(self, lat, lon, popup=None):
        """Add a marker to the map"""
        # Remove any existing marker at this location first
        self._delete_nearby_marker(lat, lon)
        
        self.marker_count += 1
        marker_id = self.marker_count
        self.markers[marker_id] = (lat, lon)
        
        if popup is None:
            popup = f"Marker {marker_id}"
            
        folium.Marker(
            [lat, lon],
            popup=popup
        ).add_to(self.folium_map)
        self.update_map_display()
        
    def update_map_display(self):
        try:
            # Clean up previous temporary file if it exists
            if self._temp_file and os.path.exists(self._temp_file):
                try:
                    os.unlink(self._temp_file)
                except Exception as e:
                    logging.warning(f"Failed to delete previous temporary file: {e}")

            # Create new temporary file
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.html', delete=False) as temp_file:
                self._temp_file = temp_file.name
                # Save with all elements inline
                self.folium_map.save(temp_file.name, close_file=False)
                
                # Read the content
                temp_file.seek(0)
                content = temp_file.read()
                
                # Find where the map is initialized
                map_init_index = content.find('var map = L.map(')
                if map_init_index != -1:
                    # Add right-click handling right after map initialization
                    right_click_js = """
                    map.on('contextmenu', function(e) {
                        window.lastRightClick = {
                            lat: e.latlng.lat,
                            lng: e.latlng.lng
                        };
                    });
                    """
                    # Find the semicolon after map initialization
                    semicolon_index = content.find(';', map_init_index)
                    if semicolon_index != -1:
                        content = content[:semicolon_index + 1] + right_click_js + content[semicolon_index + 1:]
                
                # Add map container div
                content = content.replace(
                    '<body>',
                    '<body><div id="map" style="height:100%;width:100%;">'
                )
                content = content.replace('</body>', '</div></body>')
                
                # Write back the modified content
                temp_file.seek(0)
                temp_file.truncate()
                temp_file.write(content)
                temp_file.flush()
            
            # Ensure file exists before loading
            if os.path.exists(self._temp_file):
                self.web_view.setUrl(QUrl.fromLocalFile(self._temp_file))
            else:
                logging.error("Generated temporary file not found")
                
        except Exception as e:
            logging.error(f"Error updating map display: {e}")
            
    def __del__(self):
        # Cleanup temporary file when object is destroyed
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.unlink(self._temp_file)
            except Exception as e:
                logging.warning(f"Failed to cleanup temporary file during destruction: {e}")
                
    def set_center(self, lat, lon, zoom=None):
        """Set the map center and optionally zoom level"""
        self.folium_map.location = [lat, lon]
        if zoom is not None:
            self.folium_map.zoom_start = zoom
        self.update_map_display() 