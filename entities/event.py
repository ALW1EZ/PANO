from dataclasses import dataclass
from typing import ClassVar
from .base import Entity, entity_property
from datetime import datetime

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
            "start_date": datetime,
            "end_date": datetime,
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
    def start_date(self) -> datetime:
        return None
    
    @entity_property
    def end_date(self) -> datetime:
        return None

    def get_main_display(self) -> str:
        return self.name or "Event"
        
    def to_dict(self) -> dict:
        data = super().to_dict()
        # Convert datetime objects to ISO format strings
        if self.start_date:
            if isinstance(self.start_date, datetime):
                data['start_date'] = self.start_date.isoformat()
            elif isinstance(self.start_date, str):
                data['start_date'] = self.start_date
        if self.end_date:
            if isinstance(self.end_date, datetime):
                data['end_date'] = self.end_date.isoformat()
            elif isinstance(self.end_date, str):
                data['end_date'] = self.end_date
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        # Convert ISO format strings back to datetime objects
        if 'start_date' in data and data['start_date']:
            data['start_date'] = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data and data['end_date']:
            data['end_date'] = datetime.fromisoformat(data['end_date'])
        return super().from_dict(data)
