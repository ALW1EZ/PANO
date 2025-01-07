from PySide6.QtGui import QColor
from dataclasses import dataclass, field
from entities import Entity, ENTITY_TYPES

@dataclass
class NodeStyle:
    """Style configuration for nodes"""
    min_width: float = 210
    min_height: float = 70
    radius: float = 8
    normal_color: QColor = field(default_factory=lambda: QColor(45, 45, 48))
    selected_color: QColor = field(default_factory=lambda: QColor(55, 55, 58))
    highlighted_color: QColor = field(default_factory=lambda: QColor(65, 65, 68))
    label_color: QColor = field(default_factory=lambda: QColor(230, 230, 230))
    property_color: QColor = field(default_factory=lambda: QColor(150, 150, 150))
    border_width: float = 1.5
    padding: float = 12
    text_padding: float = 8
    image_padding: float = 8
    shadow_color: QColor = field(default_factory=lambda: QColor(0, 0, 0, 50))
    shadow_blur: float = 10
    shadow_offset: float = 4

    @classmethod
    def get_type_color(cls, entity_type: str) -> QColor:
        """Get the color for an entity type"""
        # Get the entity class for this type
        entity_class = ENTITY_TYPES.get(entity_type)
        if entity_class:
            # Use the entity's color property
            return QColor(entity_class.color)
        
        # Use default color for unknown types
        return QColor(Entity.color) 