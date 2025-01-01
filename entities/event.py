from dataclasses import dataclass
from typing import ClassVar
from .base import Entity, entity_property
from datetime import date

@dataclass
class Event(Entity):
    name: ClassVar[str] = "Event"
    description: ClassVar[str] = "An event"
    color: ClassVar[str] = "#F22416"
    type_label: ClassVar[str] = "EVENT"

    def init_properties(self):
        self.setup_properties({
            "name": str,
            "description": str,
            "start_date": date,
            "ends_date": date,
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
    
    @entity_property
    def start_date(self) -> str:
        return ""
    
    @entity_property
    def end_date(self) -> str:
        return ""

    def get_main_display(self) -> str:
        return self.name or "Event"
