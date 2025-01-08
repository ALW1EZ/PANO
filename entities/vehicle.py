from dataclasses import dataclass
from typing import Dict, ClassVar, Type
from .base import (
    Entity, StringValidator, entity_property
)

@dataclass
class Vehicle(Entity):
    """Entity representing a vehicle"""
    name: ClassVar[str] = "Vehicle"
    description: ClassVar[str] = "A vehicle with make, model, and metadata"
    color: ClassVar[str] = "#6c5952"
    type_label: ClassVar[str] = "VEHICLE"
    
    def init_properties(self):
        """Initialize properties for this vehicle"""
        # Setup properties with types and default validators
        self.setup_properties({
            "model": str,
            "color": str,
            "year": int,
            "vin": str,
        })

    def update_label(self):
        """Update the label based on make, model, and year"""
        self.label = self.format_label(["model", "year"])