from dataclasses import dataclass
from typing import ClassVar, List, Dict, Any
from .base import Entity, entity_property

@dataclass
class Image(Entity):
    name: ClassVar[str] = "Image"
    description: ClassVar[str] = "An image"
    color: ClassVar[str] = "#E9B96E"
    type_label: ClassVar[str] = "IMAGE"

    def init_properties(self):
        self.setup_properties({
            "title": str,
            "url": str,
            "description": str,
        })

    def update_label(self):
        self.label = self.format_label(["title"])