from dataclasses import dataclass
from typing import Dict, ClassVar, Type
from .base import (
    Entity, StringValidator, ListValidator
)

@dataclass
class Phone(Entity):
    """Entity representing a phone number"""
    name: ClassVar[str] = "Phone"
    description: ClassVar[str] = "A phone number"
    color: ClassVar[str] = "#b82549"
    type_label: ClassVar[str] = "PHONE"
    
    # Define phone types as a class variable for easy access
    PHONE_TYPES: ClassVar[list[str]] = [
        "Mobile",
        "Home",
        "Work",
        "Fax",
        "Other"
    ]
    
    def init_properties(self):
        """Initialize properties for this phone"""
        # Setup properties with types and default validators
        self.setup_properties({
            "number": str,
            "phone_type": str,
            "country_code": str
        })
        
        # Override specific validators that need constraints
        self.property_validators.update({
            "number": StringValidator(min_length=3),
            "phone_type": ListValidator(choices=self.PHONE_TYPES, allow_empty=True),
            "country_code": StringValidator(pattern=r"^\+?[1-9]\d{0,2}$")
        })
    
    def update_label(self):
        """Update the label based on phone number"""
        self.label = self.format_label(["number"])
