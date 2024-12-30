from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from dataclasses import dataclass, field

@dataclass
class EdgeStyle:
    """Style configuration for edges"""
    width: float = 1.2
    color: QColor = field(default_factory=lambda: QColor(100, 100, 100))
    arrow_size: float = 10
    style: Qt.PenStyle = Qt.PenStyle.SolidLine
    label_color: QColor = field(default_factory=lambda: QColor(180, 180, 180))
    label_background: QColor = field(default_factory=lambda: QColor(35, 35, 38, 200)) 