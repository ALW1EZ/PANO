from typing import Dict, Optional
from entities.location import Location
from ..components.map_visual import MapVisual

class MapManager:
    def __init__(self, map_visual: MapVisual):
        self.map_visual = map_visual
        self.location_markers: Dict[str, tuple] = {}  # Maps entity_id to (lat, lon)
        
    def update_location(self, location: Location) -> None:
        """Update or add a location marker on the map"""
        try:
            lat = location.properties.get("latitude", "")
            lon = location.properties.get("longitude", "")
            
            if lat and lon:
                lat_float = float(lat)
                lon_float = float(lon)
                
                # Store marker position
                self.location_markers[location.id] = (lat_float, lon_float)
                
                # Create popup content
                popup = f"{location.get_main_display()}"
                
                # Add or update marker
                self.map_visual.add_marker(lat_float, lon_float, popup)
                
                # Center map on the most recently added/updated location
                self.map_visual.set_center(lat_float, lon_float, zoom=12)
                
        except (ValueError, TypeError) as e:
            print(f"Error updating location marker: {e}")
            
    def remove_location(self, location_id: str) -> None:
        """Remove a location marker from the map"""
        if location_id in self.location_markers:
            lat, lon = self.location_markers[location_id]
            # Remove marker from the map
            self.map_visual._delete_nearby_marker(lat, lon)
            # Remove from our tracking dict
            del self.location_markers[location_id] 