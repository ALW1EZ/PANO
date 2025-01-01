from dataclasses import dataclass
from typing import ClassVar, List, Dict, Any
from .base import Entity, entity_property

@dataclass
class Company(Entity):
    """Entity representing a company"""
    name: ClassVar[str] = "Company"
    description: ClassVar[str] = "A company"
    color: ClassVar[str] = "#037d9e"
    type_label: ClassVar[str] = "COMPANY"

    def init_properties(self):
        self.setup_properties({
            "name": str,
            "description": str,
            "notes": str,
            "source": str
        })

    def update_label(self):
        self.label = self.format_label(["name"])
    
    @entity_property
    def name(self) -> str:
        return ""

    @entity_property
    def description(self) -> str:
        return ""

    @entity_property
    def notes(self) -> str:
        return ""

    @entity_property
    def source(self) -> str:
        return ""

    def get_main_display(self) -> str:
        """Get the main text to display for this company"""
        return self.name or "Company" 