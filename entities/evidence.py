from dataclasses import dataclass
from typing import ClassVar
from .base import Entity

@dataclass
class Evidence(Entity):
    """Entity representing evidence"""
    name: ClassVar[str] = "Evidence"
    description: ClassVar[str] = "Evidence"
    color: ClassVar[str] = "#02bfd4"
    type_label: ClassVar[str] = "EVIDENCE"

    def init_properties(self):
        """Initialize properties for this evidence"""
        self.setup_properties({
            "name": str,
            "description": str,
            "is_tampered": bool,
        })

    def update_label(self):
        """Update the label based on evidence name"""
        self.label = self.format_label(["name"])
