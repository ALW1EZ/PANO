from dataclasses import dataclass
from typing import ClassVar, Dict
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
    
    # override properties for the timeline
    @property
    def name(self) -> str:
        return self.properties.get("name", "") or "Event"
    
    @property
    def description(self) -> str:
        return self.properties.get("description", "")
        
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

    def get_display_properties(self) -> Dict[str, str]:
        """Get a dictionary of properties to display in the UI with formatted dates"""
        props = super().get_display_properties()
        
        # Format dates if they exist
        if self.start_date:
            if isinstance(self.start_date, datetime):
                props['start_date'] = self.start_date.strftime("%Y-%m-%d %H:%M")
            elif isinstance(self.start_date, str):
                try:
                    dt = datetime.fromisoformat(self.start_date)
                    props['start_date'] = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    props['start_date'] = self.start_date  # Keep original if parsing fails
                    
        if self.end_date:
            if isinstance(self.end_date, datetime):
                props['end_date'] = self.end_date.strftime("%Y-%m-%d %H:%M")
            elif isinstance(self.end_date, str):
                try:
                    dt = datetime.fromisoformat(self.end_date)
                    props['end_date'] = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    props['end_date'] = self.end_date  # Keep original if parsing fails
            
        return props
