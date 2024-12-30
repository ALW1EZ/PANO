from dataclasses import dataclass
from typing import ClassVar
from .base import Entity, entity_property

@dataclass
class Username(Entity):
    name: ClassVar[str] = "Username"
    description: ClassVar[str] = "A username"
    color: ClassVar[str] = "#21B57D"
    type_label: ClassVar[str] = "USERNAME"

    def init_properties(self):
        self.setup_properties({
            "username": str,
            "notes": str,
            "source": str
        })

    def update_label(self):
        self.label = self.format_label(["username"])
    
    @entity_property
    def username(self) -> str:
        return ""
