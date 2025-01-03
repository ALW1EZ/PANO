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
            "year": int,
            "vin": str,
            "notes": str,
            "source": str
        })

    def update_label(self):
        """Update the label based on make, model, and year"""
        self.label = f"{self.model} {self.year}"

    @entity_property
    def model(self) -> str:
        """Get the model of the vehicle"""
        return ""

    @entity_property
    def year(self) -> int:
        """Get the year of the vehicle"""
        return 0

    @entity_property
    def vin(self) -> str:
        """Get the VIN of the vehicle"""
        return ""

    @entity_property
    def notes(self) -> str:
        """Get the notes for the vehicle"""
        return ""

    @entity_property
    def source(self) -> str:
        """Get the source of the vehicle"""
        return ""

    def get_main_display(self) -> str:
        """Get the main text to display for this vehicle"""
        if "model" in self.properties and "year" in self.properties:
            return f"{self.model} {self.year}"
        return self.model or "Vehicle"