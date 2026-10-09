from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class Stroke:
    """
    A single stroke representing a line to be drawn.
    points: A list of (x, y) coordinates.
    pen_down: True if the pen is touching the paper, False for a travel move.
    """
    points: List[Tuple[float, float]] = field(default_factory=list)
    pen_down: bool = True
