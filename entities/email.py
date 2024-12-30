from dataclasses import dataclass
from typing import Dict, ClassVar, Type
from .base import (
    Entity, EmailValidator, StringValidator, entity_property, PropertyValidationError
)

@dataclass
class Email(Entity):
    """Entity representing an email address"""
    name: ClassVar[str] = "Email"
    description: ClassVar[str] = "An email address"
    color: ClassVar[str] = "#2196F3"
    type_label: ClassVar[str] = "EMAIL"
    
    def init_properties(self):
        """Initialize properties for this email"""
        # Setup properties with types and default validators
        self.setup_properties({
            "address": str,
            "domain": str,
            "source": str,
            "notes": str
        })
        
        # Override specific validators that need constraints
        self.property_validators.update({
            "address": EmailValidator(),
            "domain": StringValidator(min_length=3, pattern=r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        })
    
    def __post_init__(self):
        super().__post_init__()
        # Auto-populate domain if address is provided
        if "address" in self.properties and "domain" not in self.properties:
            try:
                self.properties["domain"] = self.properties["address"].split("@")[1]
            except (IndexError, AttributeError) as e:
                raise PropertyValidationError(
                    "address", 
                    self.properties["address"],
                    "valid email address with domain"
                ) from e
    
    def update_label(self):
        """Update the label based on email address"""
        self.label = self.format_label(["address"])
    
    @entity_property
    def address(self) -> str:
        """Get the email address"""
        return ""
    
    @entity_property
    def domain(self) -> str:
        """Get the email domain"""
        return ""
    
    def get_main_display(self) -> str:
        """Get the main text to display for this email"""
        return self.address or "Email" 