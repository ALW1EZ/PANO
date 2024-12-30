from dataclasses import dataclass
from typing import Dict, ClassVar, Type
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
            "notes": str,
            "source": str
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
        """Update the label based on address components"""
        self.label = self.format_label(["address", "city", "country"])
        
        # Only update image when both coordinates are valid
        image_url = self.generate_image_url()
        if image_url:
            self.properties["image"] = image_url
        elif "image" in self.properties:
            del self.properties["image"]  # Remove image if coordinates are invalid
    
    @entity_property
    def address(self) -> str:
        """Get the full address"""
        return ""
    
    @entity_property
    def city(self) -> str:
        """Get the city"""
        return ""
    
    @entity_property
    def state(self) -> str:
        """Get the state/province"""
        return ""
    
    @entity_property
    def country(self) -> str:
        """Get the country"""
        return ""
    
    @entity_property
    def postal_code(self) -> str:
        """Get the postal code"""
        return ""
    
    @entity_property
    def latitude(self) -> str:
        """Get the latitude"""
        return ""
    
    @entity_property
    def longitude(self) -> str:
        """Get the longitude"""
        return ""
    
    @entity_property
    def location_type(self) -> str:
        """Get the location type"""
        return ""
    
    def get_main_display(self) -> str:
        """Get the main text to display for this location"""
        return self.format_label(["address", "city", "country"]) 