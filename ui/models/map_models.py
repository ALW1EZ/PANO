from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

@dataclass
class RouteData:
    start: Tuple[float, float]
    end: Tuple[float, float]
    path: List[List[float]]
    distance: float
    travel_times: Dict[str, float]

@dataclass
class Building:
    contour: List[List[float]]
    height: float
    name: Optional[str] = None
    type: Optional[str] = None
    amenity: Optional[str] = None
    address: Optional[str] = None
    opening_hours: Optional[str] = None
    cuisine: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None 