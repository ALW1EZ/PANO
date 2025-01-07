from dataclasses import dataclass
from typing import Dict, ClassVar, Type
from .base import (
    Entity, StringValidator, entity_property
)

@dataclass
class Website(Entity):
    """Entity representing a website or web domain"""
    name: ClassVar[str] = "Website"
    description: ClassVar[str] = "A website, domain, or specific URL"
    color: ClassVar[str] = "#9C27B0"
    type_label: ClassVar[str] = "WEBSITE"
    
    def init_properties(self):
        """Initialize properties for this website"""
        # Setup properties with types and default validators
        self.setup_properties({
            "url": str,
            "domain": str,
            "title": str,
            "description": str,
            "ip_address": str,
            "status": str,  # active, inactive, redirecting
            "technologies": str,  # comma-separated list of technologies used
            "notes": str,
            "source": str
        })
        
        # Override specific validators that need constraints
        self.property_validators.update({
            "url": StringValidator(min_length=4),
            "domain": StringValidator(min_length=3)
        })
    
    def update_label(self):
        """Update the label based on domain or URL"""
        self.label = self.format_label(["title", "url"])