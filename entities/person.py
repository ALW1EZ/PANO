from dataclasses import dataclass
from typing import Dict, ClassVar, Type
from .base import (
    Entity, StringValidator, IntegerValidator, FloatValidator, entity_property
)

@dataclass
class Person(Entity):
    """Entity representing a person"""
    name: ClassVar[str] = "Person"
    description: ClassVar[str] = "A person representing an individual"
    color: ClassVar[str] = "#4CAF50"
    type_label: ClassVar[str] = "PERSON"
    
    def init_properties(self):
        """Initialize properties for this person"""
        # Setup properties with types and default validators
        self.setup_properties({
            "full_name": str,
            "age": int,
            "height": float,
            "nationality": str,
            "occupation": str,
        })
        
        # Override specific validators that need constraints
        self.property_validators.update({
            "full_name": StringValidator(min_length=2),
            "age": IntegerValidator(min_value=0, max_value=150),
            "height": FloatValidator(min_value=0, max_value=300),  # in cm
            "nationality": StringValidator(min_length=2)
        })
    
    def update_label(self):
        """Update the label based on person's name"""
        self.label = self.format_label(["full_name"])