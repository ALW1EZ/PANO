from dataclasses import dataclass, field
from typing import Dict, Any, ClassVar, Optional, Type, TypeVar, Generic, Callable, get_type_hints
import uuid
from abc import ABC, abstractmethod
import re
import functools

class EntityValidationError(Exception):
    """Exception raised when entity validation fails"""
    pass

class PropertyValidationError(EntityValidationError):
    """Exception raised when property validation fails"""
    def __init__(self, property_name: str, value: Any, expected_type: Any):
        self.property_name = property_name
        self.value = value
        self.expected_type = expected_type
        super().__init__(
            f"Invalid value for property '{property_name}': "
            f"expected {self._get_type_name(expected_type)}, got {type(value).__name__}"
        )
    
    def _get_type_name(self, type_obj: Any) -> str:
        """Get a readable name for a type object"""
        if isinstance(type_obj, str):
            return type_obj
        elif isinstance(type_obj, type):
            return type_obj.__name__
        else:
            return str(type_obj)

T = TypeVar('T')

class PropertyValidator(Generic[T]):
    """Base class for property validators"""
    def __init__(self, property_type: Type[T]):
        self.property_type = property_type
        
    def validate(self, value: Any) -> T:
        """Validate and convert a value to the expected type"""
        if not isinstance(value, self.property_type):
            try:
                value = self.property_type(value)
            except (ValueError, TypeError) as e:
                raise PropertyValidationError(
                    "unknown", value, self.property_type
                ) from e
        return value

class StringValidator(PropertyValidator[str]):
    """Validator for string properties"""
    def __init__(self, min_length: int = 0, max_length: int = None, 
                 pattern: str = None):
        super().__init__(str)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
        
    def validate(self, value: Any) -> str:
        value = super().validate(value)
        if len(value) < self.min_length:
            raise PropertyValidationError(
                "unknown", value,
                f"String length must be at least {self.min_length}"
            )
        if self.max_length and len(value) > self.max_length:
            raise PropertyValidationError(
                "unknown", value,
                f"String length must be at most {self.max_length}"
            )
        if self.pattern and not self.pattern.match(value):
            raise PropertyValidationError(
                "unknown", value,
                f"String must match pattern {self.pattern.pattern}"
            )
        return value

class EmailValidator(StringValidator):
    """Validator for email addresses"""
    def __init__(self):
        super().__init__(pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

class IntegerValidator(PropertyValidator[int]):
    """Validator for integer properties"""
    def __init__(self, min_value: int = None, max_value: int = None):
        super().__init__(int)
        self.min_value = min_value
        self.max_value = max_value
        
    def validate(self, value: Any) -> int:
        value = super().validate(value)
        if self.min_value is not None and value < self.min_value:
            raise PropertyValidationError(
                "unknown", value,
                f"Value must be at least {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise PropertyValidationError(
                "unknown", value,
                f"Value must be at most {self.max_value}"
            )
        return value

class FloatValidator(PropertyValidator[float]):
    """Validator for float properties"""
    def __init__(self, min_value: float = None, max_value: float = None, precision: int = None):
        super().__init__(float)
        self.min_value = min_value
        self.max_value = max_value
        self.precision = precision
        
    def validate(self, value: Any) -> float:
        # Handle string input with more precision
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError as e:
                raise PropertyValidationError(
                    "unknown", value, float
                ) from e
        else:
            value = super().validate(value)
            
        if self.min_value is not None and value < self.min_value:
            raise PropertyValidationError(
                "unknown", value,
                f"Value must be at least {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise PropertyValidationError(
                "unknown", value,
                f"Value must be at most {self.max_value}"
            )
        # Don't round during validation to preserve precision
        return value

    def _format_display_value(self, key: str, value: Any) -> str:
        """Format a property value for display"""
        if isinstance(value, float):
            return f"{value:,.2f}"
        elif isinstance(value, int):
            return f"{value:,}"
        return str(value)

class ListValidator(PropertyValidator[str]):
    """Validator for list/dropdown properties"""
    def __init__(self, choices: list[str], allow_empty: bool = True):
        super().__init__(str)
        self.choices = choices
        self.allow_empty = allow_empty
        
    def validate(self, value: Any) -> str:
        if not value and self.allow_empty:
            return ""
            
        value = super().validate(value)
        if value not in self.choices:
            raise PropertyValidationError(
                "unknown", value,
                f"Value must be one of: {', '.join(self.choices)}"
            )
        return value
    
    def get_choices(self) -> list[str]:
        """Get the list of valid choices"""
        return self.choices

@dataclass
class EntityData:
    """Data container for entity attributes"""
    id: str
    type: str
    label: str
    properties: Dict[str, Any]
    color: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity data to a dictionary"""
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "properties": self.properties,
            "color": self.color
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityData':
        """Create entity data from a dictionary"""
        return cls(
            id=data["id"],
            type=data["type"],
            label=data["label"],
            properties=data["properties"],
            color=data.get("color")
        )

def entity_property(func: Callable) -> property:
    """Decorator to create entity property getters.
    Usage: 
    @entity_property
    def my_property(self) -> str:
        return self.properties.get("my_property", "")
    """
    prop_name = func.__name__
    
    @property
    @functools.wraps(func)
    def wrapper(self):
        return self.properties.get(prop_name, func(self))
    
    return wrapper

@dataclass
class Entity(ABC):
    """Base class for all entities"""
    label: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Class variables that should be overridden by subclasses
    name: ClassVar[str] = "Base Entity"
    description: ClassVar[str] = "Base entity class"
    color: ClassVar[str] = "#607D8B"  # Default color for unknown entity types
    type_label: ClassVar[str] = "BASE"  # Default type label for display
    
    @property
    def type(self) -> str:
        """Get the entity type name"""
        return self.__class__.name
    
    def get_display_type(self) -> str:
        """Get the type label to display in the UI.
        Can be overridden by subclasses to customize type display."""
        return self.type.upper()
    
    def __post_init__(self):
        """Initialize the entity after dataclass initialization"""
        # Initialize instance-specific property types and validators
        self.property_types: Dict[str, Type] = {}  # Start with empty dict
        self.property_validators: Dict[str, PropertyValidator] = {}
        
        # Let subclasses initialize their properties
        self.init_properties()
        
        # Add standard properties last to ensure they appear at the bottom
        self.property_types.update({
            "notes": str,
            "source": str,
            "image": str
        })
        self.property_validators.update({
            "notes": StringValidator(),
            "source": StringValidator(),
            "image": StringValidator()
        })
        
        # Auto-generate property getters for all properties
        self._generate_property_getters()
        
        # Validate and update data
        self.validate_properties()
        self.update_data()
    
    def _generate_property_getters(self):
        """Auto-generate property getters for all properties defined in property_types"""
        for prop_name, prop_type in self.property_types.items():
            if not hasattr(self.__class__, prop_name):
                # Create a default property getter if one doesn't exist
                default_value = "" if prop_type == str else 0 if prop_type == int else 0.0 if prop_type == float else None
                
                def getter(self, _name=prop_name, _default=default_value) -> Any:
                    """Auto-generated property getter"""
                    return _default
                
                # Set the name and doc before applying the decorator
                getter.__name__ = prop_name
                getter.__doc__ = f"Get the {prop_name} property"
                
                # Apply the decorator and set the property
                decorated_getter = entity_property(getter)
                setattr(self.__class__, prop_name, decorated_getter)
    
    def init_properties(self):
        """Initialize properties for this entity.
        Should be overridden by subclasses to setup their properties."""
        pass
    
    @classmethod
    def create_validator(cls, prop_name: str, prop_type: Type) -> PropertyValidator:
        """Create a default validator for a property based on its type"""
        if prop_type == str:
            return StringValidator()
        elif prop_type == int:
            return IntegerValidator()
        elif prop_type == float:
            return FloatValidator()
        return PropertyValidator(prop_type)
    
    def setup_properties(self, properties: Dict[str, Type]):
        """Helper to setup property types and validators at once"""
        self.property_types.update(properties)
        self.property_validators.update({
            name: self.create_validator(name, type_)
            for name, type_ in properties.items()
            if name not in self.property_validators
        })
    
    def format_label(self, primary_props: list[str], separator: str = ", ") -> str:
        """Helper to format label from properties
        Args:
            primary_props: List of property names to use for label in priority order
            separator: String to use between property values
        """
        components = []
        for prop in primary_props:
            if prop in self.properties and self.properties[prop]:
                components.append(str(self.properties[prop]))
        
        if components:
            return separator.join(components)
        return self.name

    def get_display_properties(self) -> Dict[str, str]:
        """Get a dictionary of properties to display in the UI
        By default shows all non-empty properties except those starting with _"""
        # First get all non-image properties
        props = {
            k: self._format_display_value(k, v) 
            for k, v in self.properties.items()
            if v and k != "image" and not k.startswith("_")
        }   
        return props
    
    def _format_display_value(self, key: str, value: Any) -> str:
        """Format a property value for display"""
        if isinstance(value, float):
            # Use more precision for coordinates
            if key in ('latitude', 'longitude'):
                return f"{value:.8f}".rstrip('0').rstrip('.')
            return f"{value:,.2f}"
        elif isinstance(value, int):
            return f"{value:,}"
        return str(value)
    
    def validate_properties(self):
        """Validate all properties against their types and validators"""
        for name, value in self.properties.items():
            if name not in self.property_types:
                raise PropertyValidationError(
                    name, value,
                    f"Unknown property '{name}' for {self.__class__.__name__}"
                )
            
            # Get validator for this property
            validator = self.property_validators.get(
                name,
                PropertyValidator(self.property_types[name])
            )
            
            try:
                # Validate and convert the value
                self.properties[name] = validator.validate(value)
            except PropertyValidationError as e:
                e.property_name = name
                raise
    
    def update_data(self):
        """Update the entity's data and label based on current properties"""
        # Let subclasses update their label first
        self.update_label()
        
        # Then update the data object
        self.data = EntityData(
            id=getattr(self, 'data', None) and self.data.id or str(uuid.uuid4()),
            type=self.__class__.__name__,
            label=self.label,
            properties=self.properties,
            color=self.color
        )
    
    @abstractmethod
    def update_label(self):
        """Update the entity's label based on its properties.
        Must be implemented by subclasses to provide custom label formatting."""
        pass
    
    @property
    def id(self) -> str:
        """Get the entity's unique identifier"""
        return self.data.id
        
    def get_main_display(self) -> str:
        """Get the main text to display for this entity
        Override this in subclasses to customize the main display text"""
        return self.label
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the entity to a dictionary representation"""
        return self.data.to_dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """Create an entity from a dictionary representation"""
        from . import ENTITY_TYPES  # Import here to avoid circular import
        
        # Get the correct entity class based on type
        entity_type = data["type"]
        entity_class = ENTITY_TYPES.get(entity_type)
        if not entity_class:
            raise ValueError(f"Unknown entity type: {entity_type}")
            
        # Create instance of the correct class
        entity = entity_class(label=data["label"])
        entity.properties = data["properties"]
        entity.data = EntityData.from_dict(data)
        return entity
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id) 
    
    def get_property_type(self, prop_name: str) -> str:
        """Get the UI type for a property (e.g. 'text', 'number', 'dropdown', etc.)"""
        if prop_name not in self.property_validators:
            return "text"
            
        validator = self.property_validators[prop_name]
        if isinstance(validator, ListValidator):
            return "dropdown"
        elif isinstance(validator, IntegerValidator):
            return "number"
        elif isinstance(validator, FloatValidator):
            return "number"
        return "text"
    
    def get_property_choices(self, prop_name: str) -> list[str]:
        """Get choices for a dropdown property"""
        if prop_name not in self.property_validators:
            return []
            
        validator = self.property_validators[prop_name]
        if isinstance(validator, ListValidator):
            return validator.get_choices()
        return []
    
    def get_property_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata about all properties for UI rendering"""
        metadata = {}
        for prop_name in self.property_types:
            prop_type = self.get_property_type(prop_name)
            metadata[prop_name] = {
                "type": prop_type,
                "choices": self.get_property_choices(prop_name) if prop_type == "dropdown" else []
            }
        return metadata 