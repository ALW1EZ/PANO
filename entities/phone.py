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
            self.properties["_display_number"] = f"+{self.properties['country_code']} {self.properties['number']}"
        else:
            self.properties["_display_number"] = self.properties.get("number", "")
        self.label = self.format_label(["_display_number"])