from typing import Dict, List, Tuple, Optional, Any
import pydeck as pdk
from ui.models.map_models import RouteData, Building
from ui.services.map_services import BuildingService
import logging

class MapLayerManager:
    def __init__(self, layer_toggles: Dict[str, Any]):
        self.layer_toggles = layer_toggles
        self.processed_areas = set()

    def create_building_layer(self, buildings: List[Building]) -> Optional[pdk.Layer]:
        if not buildings or not self.layer_toggles['buildings'].isChecked():
            return None

        building_data = []
        for b in buildings:
            try:
                if not b.amenity:  # Only include non-amenity buildings
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

        if not building_data:
            return None

        return pdk.Layer(
            "PolygonLayer",
            building_data,
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

    def create_place_layers(self, buildings: List[Building]) -> List[pdk.Layer]:
        layers = []
        point_place_data = {
            'food': [],          # Restaurants, cafes, bars
            'shops': [],         # Shops and stores
            'entertainment': [], # Entertainment venues
            'tourism': [],       # Tourism-related places
            'services': [],      # Various services
            'health': [],        # Healthcare facilities
            'other': []         # Other amenities
        }
        area_place_data = {
            'education': [],     # Educational facilities
            'leisure': [],       # Leisure areas
            'transport': [],     # Transport hubs
            'other': []         # Other areas
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
                    
                    # Get place category
                    place_type, category = BuildingService.get_place_category(b.amenity)
                    
                    if place_type == 'area' or len(b.contour) > 5:  # Complex shapes are always areas
                        area_data = {
                            "contour": b.contour,
                            "height": 1,  # Keep areas flat
                            "tooltip": BuildingService._format_tooltip(b)
                        }
                        
                        # Set color based on category
                        if category == 'education':
                            area_data["color"] = [100, 100, 255, 150]  # Blue
                        elif category == 'leisure':
                            area_data["color"] = [100, 255, 100, 150]  # Green
                        elif category == 'transport':
                            area_data["color"] = [255, 165, 0, 150]    # Orange
                        else:
                            area_data["color"] = [255, 200, 0, 150]    # Yellow
                        
                        if category in area_place_data:
                            area_place_data[category].append(area_data)
                        else:
                            area_place_data['other'].append(area_data)
                    else:
                        # Set color based on category
                        if category == 'food':
                            place_info["color"] = [255, 100, 100]  # Red
                        elif category == 'shops':
                            place_info["color"] = [100, 255, 100]  # Green
                        elif category == 'entertainment':
                            place_info["color"] = [255, 100, 255]  # Pink
                        elif category == 'tourism':
                            place_info["color"] = [100, 200, 255]  # Light blue
                        elif category == 'services':
                            place_info["color"] = [255, 165, 0]    # Orange
                        elif category == 'health':
                            place_info["color"] = [255, 50, 50]    # Bright red for healthcare
                        else:
                            place_info["color"] = [255, 200, 0]    # Yellow
                        
                        if category in point_place_data:
                            point_place_data[category].append(place_info)
                        else:
                            point_place_data['other'].append(place_info)
            except Exception as e:
                logging.error(f"Error processing place data: {e}")
                continue

        # Create layers based on toggle states
        for category, data in area_place_data.items():
            if data and self.layer_toggles.get(category, {}).isChecked():
                layers.append(self._create_area_layer(data))
        
        for category, data in point_place_data.items():
            if data and self.layer_toggles.get(category, {}).isChecked():
                layers.append(self._create_point_layer(data))

        return layers

    def create_route_layer(self, routes: List[RouteData]) -> Optional[pdk.Layer]:
        if not routes:
            return None

        route_data = []
        for route in routes:
            route_data.append({
                "path": route.path,
                "distance": f"{route.distance/1000:.2f} km",
                "walking": f"🚶 {self._format_time(route.travel_times['walking'])}",
                "driving": f"🚗 {self._format_time(route.travel_times['car'])}",
                "bus": f"🚌 {self._format_time(route.travel_times['bus'])}"
            })
        
        return pdk.Layer(
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

    def create_marker_layer(self, markers: Dict[int, Tuple[float, float]]) -> pdk.Layer:
        marker_data = [{"coordinates": [lon, lat]} for lat, lon in markers.values()]
        return pdk.Layer(
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
            get_elevation=3000,
            elevation_scale=1,
            parameters={"depthTest": False}
        )

    @staticmethod
    def _create_area_layer(data: List[Dict[str, Any]]) -> pdk.Layer:
        return pdk.Layer(
            "PolygonLayer",
            data,
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

    @staticmethod
    def _create_point_layer(data: List[Dict[str, Any]]) -> pdk.Layer:
        return pdk.Layer(
            "ScatterplotLayer",
            data,
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

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds into a human-readable time string"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m" 