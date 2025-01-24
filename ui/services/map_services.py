from typing import Dict, List, Tuple, Optional, Any
import aiohttp
import logging
from math import sin, cos, radians
from ui.models.map_models import Building

EARTH_RADIUS_METERS = 6371000
DEFAULT_BUILDING_HEIGHT = 10

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

    @staticmethod
    def calculate_path_length(path_coords: List[List[float]]) -> float:
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

    @staticmethod
    def create_circle_polygon(center_lat: float, center_lon: float, radius_meters: float = 500, num_points: int = 32) -> List[List[float]]:
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

class BuildingService:
    # Categories for different types of places
    AREA_PLACES = {
        'education': {'school', 'university', 'library', 'college', 'kindergarten'},
        'leisure': {'park', 'playground', 'sports_centre', 'stadium', 'swimming_pool'},
        'transport': {'parking', 'bus_station', 'train_station', 'subway_station'},
        'other': {'place_of_worship', 'police', 'post_office', 'townhall', 'marketplace'}
    }
    
    POINT_PLACES = {
        'food': {'restaurant', 'cafe', 'bar', 'pub', 'fast_food', 'food_court', 'ice_cream'},
        'shops': {'shop', 'store', 'supermarket', 'mall', 'convenience', 'bakery', 'butcher'},
        'entertainment': {'cinema', 'theatre', 'nightclub', 'casino', 'arts_centre'},
        'tourism': {'hotel', 'hostel', 'guest_house', 'museum', 'gallery', 'tourist_info'},
        'services': {'bank', 'atm', 'bureau_de_change', 'laundry', 'hairdresser'},
        'health': {'hospital', 'clinic', 'doctors', 'pharmacy', 'dentist', 'veterinary', 'physiotherapist', 'optician', 'healthcare'}
    }

    @staticmethod
    async def fetch_buildings(lat: float, lon: float, radius: int = 500) -> List[Building]:
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Create amenity filter for all categories
        amenity_values = set()
        for categories in [BuildingService.AREA_PLACES.values(), BuildingService.POINT_PLACES.values()]:
            for category in categories:
                amenity_values.update(category)
        
        # Ensure we have valid amenities before creating the filter
        if not amenity_values:
            amenity_filter = "."  # Match any amenity if no specific ones are defined
        else:
            amenity_filter = '|'.join(sorted(amenity_values))  # Sort for consistency
        
        query = f"""
        [out:json][timeout:25];
        (
          // Get buildings
          way["building"](around:{radius},{lat},{lon});
          
          // Get amenities
          node["amenity"~"{amenity_filter}"](around:{radius},{lat},{lon});
          way["amenity"~"{amenity_filter}"](around:{radius},{lat},{lon});
          
          // Get shops
          node["shop"](around:{radius},{lat},{lon});
          way["shop"](around:{radius},{lat},{lon});
          
          // Get tourism
          node["tourism"](around:{radius},{lat},{lon});
          way["tourism"](around:{radius},{lat},{lon});
          
          // Get leisure
          node["leisure"](around:{radius},{lat},{lon});
          way["leisure"](around:{radius},{lat},{lon});
        );
        out body geom;
        """
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(overpass_url, data={"data": query}) as response:
                    if response.status != 200:
                        logging.error(f"Overpass API returned status {response.status}")
                        return []
                        
                    data = await response.json()
                    if not isinstance(data, dict) or 'elements' not in data:
                        logging.error("Invalid response format from Overpass API")
                        return []
                        
                    buildings = []
                    for element in data.get('elements', []):
                        try:
                            tags = element.get('tags', {})
                            
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
                                    except (ValueError, TypeError):
                                        height = DEFAULT_BUILDING_HEIGHT
                                elif element['type'] == 'node' or any(
                                    tags.get(key) and tags.get(key) in category 
                                    for categories in BuildingService.AREA_PLACES.values() 
                                    for key in ['amenity', 'leisure', 'tourism'] 
                                    for category in categories
                                ):
                                    height = 1  # Make amenity points and areas flat
                                
                                # Determine amenity type
                                amenity = None
                                for key in ['amenity', 'shop', 'tourism', 'leisure']:
                                    value = tags.get(key)
                                    if value:  # Only set amenity if we have a non-None value
                                        amenity = value
                                        break
                                
                                # Get additional information
                                building = Building(
                                    contour=coords,
                                    height=height,
                                    name=tags.get('name'),
                                    type=tags.get('building') or amenity,
                                    amenity=amenity,
                                    address=BuildingService._format_address(tags),
                                    opening_hours=tags.get('opening_hours'),
                                    cuisine=tags.get('cuisine'),
                                    phone=tags.get('phone'),
                                    website=tags.get('website')
                                )
                                buildings.append(building)
                        except Exception as e:
                            logging.error(f"Error processing building element: {e}")
                            continue
                            
                    return buildings
        except Exception as e:
            logging.error(f"Error fetching buildings: {e}")
            return []

    @staticmethod
    def get_place_category(amenity: Optional[str]) -> Tuple[str, str]:
        """Determine the category of a place based on its amenity tag"""
        if not amenity:
            return 'building', 'regular'
            
        # Check area places
        for category, types in BuildingService.AREA_PLACES.items():
            if amenity in types:
                return 'area', category
                
        # Check point places
        for category, types in BuildingService.POINT_PLACES.items():
            if amenity in types:
                return 'point', category
                
        return 'point', 'other'  # Default to point, other category

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