from dataclasses import dataclass
from typing import Dict, ClassVar, Type, Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from .base import (
    Entity, StringValidator, entity_property
)

@dataclass
class Location(Entity):
    """Entity representing a physical location or address"""
    name: ClassVar[str] = "Location"
    description: ClassVar[str] = "A physical location, address, or place of interest"
    color: ClassVar[str] = "#FF5722"
    type_label: ClassVar[str] = "LOCATION"
    
    def init_properties(self):
        """Initialize properties for this location"""
        # Setup properties with types and default validators
        self.setup_properties({
            "address": str,
            "city": str,
            "state": str,
            "country": str,
            "postal_code": str,
            "latitude": str,  # Changed to string
            "longitude": str,  # Changed to string
            "location_type": str,  # residential, commercial, industrial
        })
        
        # Override specific validators that need constraints
        self.property_validators.update({
            "latitude": StringValidator(),
            "longitude": StringValidator()
        })
    
    def generate_image_url(self) -> str:
        """Generate the image URL based on latitude and longitude"""
        lat = self.properties.get("latitude", "")
        lng = self.properties.get("longitude", "")
        
        # Only generate URL if both coordinates are valid numbers
        try:
            if lat and lng:
                float(lat)  # Validate latitude is a number
                float(lng)  # Validate longitude is a number
                return f"https://maps.geoapify.com/v1/staticmap?style=dark-matter-brown&width=600&height=400&center=lonlat:{lng},{lat}&zoom=16&scaleFactor=2&marker=lonlat:{lng},{lat};type:awesome;color:%23e01401&apiKey=b8568cb9afc64fad861a69edbddb2658"
        except ValueError:
            pass
        return ""
    
    def update_label(self):
        """Update the label based on address components and handle geocoding"""
        try:
            geolocator = Nominatim(user_agent="PANO_APP")
            location = None
            
            # Get coordinates either from properties or from forward geocoding
            lat = self.properties.get("latitude", "")
            lng = self.properties.get("longitude", "")
            
            # If no coordinates, try to get them from address
            if not (lat and lng):
                address_parts = []
                for field in ["address", "city", "state", "country"]:
                    if self.properties.get(field):
                        address_parts.append(self.properties[field])
                
                if address_parts:
                    location = geolocator.geocode(", ".join(address_parts), exactly_one=True)
                    if location:
                        lat = str(location.latitude)
                        lng = str(location.longitude)
            
            # Now that we have coordinates (either from properties or forward geocoding),
            # use reverse geocoding to get complete address details
            if lat and lng:
                try:
                    coords = (float(lat), float(lng))
                    location = geolocator.reverse(coords, exactly_one=True)
                    if location:
                        # Update coordinates
                        self.properties["latitude"] = str(location.latitude)
                        self.properties["longitude"] = str(location.longitude)
                        
                        # Update address components from raw data
                        address = location.raw.get('address', {})
                        
                        # Map OpenStreetMap fields to our properties
                        if 'road' in address and 'house_number' in address:
                            self.properties["address"] = f"{address['house_number']} {address['road']}"
                        elif 'road' in address:
                            self.properties["address"] = address['road']
                            
                        self.properties["city"] = address.get('city', address.get('town', address.get('village', '')))
                        self.properties["state"] = address.get('state', '')
                        self.properties["country"] = address.get('country', '')
                        self.properties["postal_code"] = address.get('postcode', '')
                except ValueError:
                    pass
        
        except (GeocoderTimedOut, GeocoderUnavailable):
            pass
        
        # Set the label using available properties
        self.label = self.format_label(["address", "city", "country"])
        
        # Update image
        image_url = self.generate_image_url()
        if image_url:
            self.properties["image"] = image_url
        elif "image" in self.properties:
            del self.properties["image"]  # Remove image if coordinates are invalid