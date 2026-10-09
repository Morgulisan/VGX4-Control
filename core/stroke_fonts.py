"""Selectable single-stroke fonts (Hershey data, see stroke_font_data.py).

The built-in handwriting font stays in stroke_generator.FONT_DICT and is the default.
"""
from typing import Dict, List, Optional, Tuple

from core.stroke_font_data import FONT_DATA

DEFAULT_FONT = 'handwriting'
DEFAULT_LABEL = 'Handschrift · Standard'
WORD_SPACE_FACTOR = .85  # Hershey space glyphs are wide; this matches the default word gap better


class StrokeFont:
    def __init__(self, key: str, label: str, glyphs: Dict[str, Tuple[float, List[List[Tuple[float, float]]]]]):
        self.key = key
        self.label = label
        self.glyphs = glyphs
        self.word_spacing = glyphs[' '][0] * WORD_SPACE_FACTOR
        self.char_spacing = 0.0  # the glyph advances already contain side bearings

    def advance(self, char: str) -> float:
        return self.glyphs[char][0]

    def paths(self, char: str) -> List[Dict]:
        return [{'points': s, 'smooth': False} for s in self.glyphs[char][1]]


STROKE_FONTS: Dict[str, StrokeFont] = {key: StrokeFont(key, label, glyphs) for key, (label, glyphs) in FONT_DATA.items()}
FONT_CHOICES: List[Tuple[str, str]] = [(DEFAULT_FONT, DEFAULT_LABEL)] + [(f.key, f.label) for f in STROKE_FONTS.values()]


def get_stroke_font(key: str) -> Optional[StrokeFont]:
    """None selects the built-in handwriting font."""
    if key == DEFAULT_FONT:
        return None
    return STROKE_FONTS[key]
