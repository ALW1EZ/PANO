from dataclasses import dataclass
from typing import ClassVar
from .base import Entity, entity_property

@dataclass
class Text(Entity):
    name: ClassVar[str] = "Text"
    description: ClassVar[str] = "A text"
    color: ClassVar[str] = "#D0BD1D"
    type_label: ClassVar[str] = "TEXT"

    def init_properties(self):
        self.setup_properties({
            "text": str,
            "notes": str,
            "source": str
        })

    def update_label(self):
        self.label = self.format_label(["text"])
    
    @entity_property
    def text(self) -> str:
        return ""
    
    def get_main_display(self) -> str:
        return self.text or "Text"