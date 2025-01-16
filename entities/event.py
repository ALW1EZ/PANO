from dataclasses import dataclass
from typing import ClassVar, Dict
from .base import Entity, entity_property, StringValidator
from datetime import datetime

class DateTimeValidator(StringValidator):
    """Validator for datetime strings in YYYY-MM-DD HH:mm format"""
    def validate(self, value: any) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
            
        if not isinstance(value, str):
            value = str(value)
            
        try:
            # Try to parse the date to validate format
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
            # Return formatted string without seconds
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            # Try to parse with seconds and convert to HH:mm format
            try:
                dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                raise ValueError(f"Invalid datetime format. Expected YYYY-MM-DD HH:mm, got {value}")

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
            "start_date": str,  # Format: YYYY-MM-DD HH:mm
            "end_date": str,    # Format: YYYY-MM-DD HH:mm
            "add_to_timeline": bool,  # New property to control timeline visibility
        })
        
        # Add validators for date fields
        self.property_validators.update({
            "start_date": DateTimeValidator(),
            "end_date": DateTimeValidator()
        })
        
        # Set default value for add_to_timeline
        if "add_to_timeline" not in self.properties:
            self.properties["add_to_timeline"] = False
    
    def update_label(self):
        """Update the node label"""
        if "name" in self.properties and self.properties["name"]:
            self.label = self.properties["name"]
        else:
            self.label = "Event"

    @property
    def name(self) -> str:
        """Get the event name property"""
        return self.properties.get("name", "")
    
    @property
    def description(self) -> str:
        return self.properties.get("description", "")
    
    @property
    def start_date(self) -> datetime | None:
        """Get the start date as a datetime object"""
        date_val = self.properties.get("start_date")
        if not date_val:
            return None
            
        if isinstance(date_val, datetime):
            return date_val.replace(second=0, microsecond=0)
            
        try:
            dt = datetime.strptime(date_val, "%Y-%m-%d %H:%M")
            return dt
        except (ValueError, TypeError):
            return None
    
    @property
    def end_date(self) -> datetime | None:
        """Get the end date as a datetime object"""
        date_val = self.properties.get("end_date")
        if not date_val:
            return None
            
        if isinstance(date_val, datetime):
            return date_val.replace(second=0, microsecond=0)
            
        try:
            dt = datetime.strptime(date_val, "%Y-%m-%d %H:%M")
            return dt
        except (ValueError, TypeError):
            return None
        
    def to_dict(self) -> dict:
        """Convert to dictionary, ensuring dates are in string format"""
        data = super().to_dict()
        # Ensure dates are in string format without seconds
        if "start_date" in data["properties"] and isinstance(data["properties"]["start_date"], datetime):
            data["properties"]["start_date"] = data["properties"]["start_date"].strftime("%Y-%m-%d %H:%M")
        if "end_date" in data["properties"] and isinstance(data["properties"]["end_date"], datetime):
            data["properties"]["end_date"] = data["properties"]["end_date"].strftime("%Y-%m-%d %H:%M")
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        """Create from dictionary, converting date strings to proper format"""
        # Convert any date strings to proper format
        if "properties" in data:
            for date_field in ["start_date", "end_date"]:
                if date_field in data["properties"] and data["properties"][date_field]:
                    if isinstance(data["properties"][date_field], str):
                        try:
                            # Parse and reformat to ensure consistent format without seconds
                            dt = datetime.strptime(data["properties"][date_field], "%Y-%m-%d %H:%M")
                            data["properties"][date_field] = dt.strftime("%Y-%m-%d %H:%M")
                        except ValueError:
                            try:
                                # Try parsing with seconds and convert to HH:mm format
                                dt = datetime.strptime(data["properties"][date_field], "%Y-%m-%d %H:%M:%S")
                                data["properties"][date_field] = dt.strftime("%Y-%m-%d %H:%M")
                            except ValueError:
                                data["properties"][date_field] = None
        return super().from_dict(data)

    def get_display_properties(self) -> Dict[str, str]:
        """Get a dictionary of properties to display in the UI with formatted dates"""
        props = super().get_display_properties()
        
        # Format dates without seconds
        if "start_date" in props:
            try:
                dt = datetime.strptime(props["start_date"], "%Y-%m-%d %H:%M:%S")
                props["start_date"] = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pass
                
        if "end_date" in props:
            try:
                dt = datetime.strptime(props["end_date"], "%Y-%m-%d %H:%M:%S")
                props["end_date"] = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pass
                
        return props
