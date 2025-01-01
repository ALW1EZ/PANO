from dataclasses import dataclass
from typing import Dict, ClassVar, Type
from .base import (
    Entity, StringValidator, entity_property
)

@dataclass
class Phone(Entity):
    """Entity representing a phone number"""
    name: ClassVar[str] = "Phone"
    description: ClassVar[str] = "A phone number with country code and metadata"
    color: ClassVar[str] = "#b82549"
    type_label: ClassVar[str] = "PHONE"
    
    def init_properties(self):
        """Initialize properties for this phone"""
        # Setup properties with types and default validators
        self.setup_properties({
            "number": str,
            "country_code": str,
            "phone_type": str,  # mobile, landline, fax, etc.
            "carrier": str,
            "notes": str,
            "source": str
        })
        
        # Override specific validators that need constraints
        self.property_validators.update({
            "number": StringValidator(min_length=5),
            "country_code": StringValidator(min_length=1)
        })
    
    def update_label(self):
        """Update the label based on phone number"""
        if "country_code" in self.properties:
            self.properties["_display_number"] = f"+{self.properties['country_code']}{self.properties['number']}"
        else:
            self.properties["_display_number"] = self.properties.get("number", "")
        self.label = self.format_label(["_display_number"])
    
    @entity_property
    def number(self) -> str:
        """Get the phone number"""
        return ""
    
    @entity_property
    def country_code(self) -> str:
        """Get the country code"""
        return ""
    
    @entity_property
    def phone_type(self) -> str:
        """Get the phone type"""
        return ""
    
    @entity_property
    def carrier(self) -> str:
        """Get the phone carrier"""
        return ""
    
    def get_main_display(self) -> str:
        """Get the main text to display for this phone number"""
        if "country_code" in self.properties and "number" in self.properties:
            return f"+{self.country_code}{self.number}"
        return self.number or "Phone" 