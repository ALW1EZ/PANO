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
        })

    def update_label(self):
        self.label = self.format_label(["name"])