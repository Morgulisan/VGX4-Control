from typing import List, Tuple, Dict, Optional
import math
import random
from core.models import Stroke

FONT_DICT: Dict[str, List[Dict]] = {
    # Buchstabe A-Z
    'A': [
        {'points': [(0.0, 0.0), (0.5, 2.0), (1.0, 0.0)], 'smooth': False},
        {'points': [(0.25, 0.8), (0.75, 0.8)], 'smooth': False}
    ],
    'B': [
        {'points': [(0.0, 0.0), (0.0, 2.0)], 'smooth': False},
        {'points': [(0.0, 2.0), (0.75, 2.0), (1.0, 1.5), (0.75, 1.0), (0.0, 1.0)], 'smooth': True},
        {'points': [(0.0, 1.0), (0.75, 1.0), (1.0, 0.5), (0.75, 0.0), (0.0, 0.0)], 'smooth': True}
    ],
    'C': [
        {'points': [(1.0, 1.75), (0.75, 2.0), (0.25, 2.0), (0.0, 1.5), (0.0, 0.5), (0.25, 0.0), (0.75, 0.0), (1.0, 0.25)], 'smooth': True}
    ],
    'D': [
        {'points': [(0.0, 0.0), (0.0, 2.0)], 'smooth': False},
        {'points': [(0.0, 2.0), (0.75, 2.0), (1.0, 1.0), (0.75, 0.0), (0.0, 0.0)], 'smooth': True}
    ],
    'E': [
        {'points': [(1.0, 2.0), (0.0, 2.0), (0.0, 0.0), (1.0, 0.0)], 'smooth': False},
        {'points': [(0.0, 1.0), (0.75, 1.0)], 'smooth': False}
    ],
    'F': [
        {'points': [(1.0, 2.0), (0.0, 2.0), (0.0, 0.0)], 'smooth': False},
        {'points': [(0.0, 1.0), (0.75, 1.0)], 'smooth': False}
    ],
    'G': [
        {'points': [(1.0, 1.75), (0.75, 2.0), (0.25, 2.0), (0.0, 1.5), (0.0, 0.5), (0.25, 0.0), (0.75, 0.0), (1.0, 0.25), (1.0, 1.0), (0.5, 1.0)], 'smooth': True}
    ],
    'H': [
        {'points': [(0.0, 0.0), (0.0, 2.0)], 'smooth': False},
        {'points': [(1.0, 0.0), (1.0, 2.0)], 'smooth': False},
        {'points': [(0.0, 1.0), (1.0, 1.0)], 'smooth': False}
    ],
    'I': [
        {'points': [(0.5, 0.0), (0.5, 2.0)], 'smooth': False},
        {'points': [(0.25, 2.0), (0.75, 2.0)], 'smooth': False},
        {'points': [(0.25, 0.0), (0.75, 0.0)], 'smooth': False}
    ],
    'J': [
        {'points': [(0.25, 2.0), (0.75, 2.0)], 'smooth': False},
        {'points': [(0.5, 2.0), (0.5, 0.5), (0.25, 0.0), (0.0, 0.5)], 'smooth': True}
    ],
    'K': [
        {'points': [(0.0, 0.0), (0.0, 2.0)], 'smooth': False},
        {'points': [(1.0, 2.0), (0.0, 1.0), (1.0, 0.0)], 'smooth': False}
    ],
    'L': [
        {'points': [(0.0, 2.0), (0.0, 0.0), (1.0, 0.0)], 'smooth': False}
    ],
    'M': [
        {'points': [(0.0, 0.0), (0.0, 2.0), (0.5, 1.0), (1.0, 2.0), (1.0, 0.0)], 'smooth': False}
    ],
    'N': [
        {'points': [(0.0, 0.0), (0.0, 2.0), (1.0, 0.0), (1.0, 2.0)], 'smooth': False}
    ],
    'O': [
        {'points': [(0.5, 2.0), (0.0, 1.5), (0.0, 0.5), (0.5, 0.0), (1.0, 0.5), (1.0, 1.5), (0.5, 2.0)], 'smooth': True}
    ],
    'P': [
        {'points': [(0.0, 0.0), (0.0, 2.0)], 'smooth': False},
        {'points': [(0.0, 2.0), (0.75, 2.0), (1.0, 1.5), (0.75, 1.0), (0.0, 1.0)], 'smooth': True}
    ],
    'Q': [
        {'points': [(0.5, 2.0), (0.0, 1.5), (0.0, 0.5), (0.5, 0.0), (1.0, 0.5), (1.0, 1.5), (0.5, 2.0)], 'smooth': True},
        {'points': [(0.5, 0.5), (1.0, 0.0)], 'smooth': False}
    ],
    'R': [
        {'points': [(0.0, 0.0), (0.0, 2.0)], 'smooth': False},
        {'points': [(0.0, 2.0), (0.75, 2.0), (1.0, 1.5), (0.75, 1.0), (0.0, 1.0)], 'smooth': True},
        {'points': [(0.5, 1.0), (1.0, 0.0)], 'smooth': False}
    ],
    'S': [
        {'points': [(1.0, 1.75), (0.75, 2.0), (0.25, 2.0), (0.0, 1.5), (0.5, 1.0), (1.0, 0.5), (0.75, 0.0), (0.25, 0.0), (0.0, 0.25)], 'smooth': True}
    ],
    'T': [
        {'points': [(0.0, 2.0), (1.0, 2.0)], 'smooth': False},
        {'points': [(0.5, 2.0), (0.5, 0.0)], 'smooth': False}
    ],
    'U': [
        {'points': [(0.0, 2.0), (0.0, 0.5), (0.25, 0.0), (0.75, 0.0), (1.0, 0.5), (1.0, 2.0)], 'smooth': True}
    ],
    'V': [
        {'points': [(0.0, 2.0), (0.5, 0.0), (1.0, 2.0)], 'smooth': False}
    ],
    'W': [
        {'points': [(0.0, 2.0), (0.25, 0.0), (0.5, 1.0), (0.75, 0.0), (1.0, 2.0)], 'smooth': False}
    ],
    'X': [
        {'points': [(0.0, 2.0), (1.0, 0.0)], 'smooth': False},
        {'points': [(1.0, 2.0), (0.0, 0.0)], 'smooth': False}
    ],
    'Y': [
        {'points': [(0.0, 2.0), (0.5, 1.0), (1.0, 2.0)], 'smooth': False},
        {'points': [(0.5, 1.0), (0.5, 0.0)], 'smooth': False}
    ],
    'Z': [
        {'points': [(0.0, 2.0), (1.0, 2.0), (0.0, 0.0), (1.0, 0.0)], 'smooth': False}
    ],
    # Deutsche Umlaute & Sonderzeichen
    'Ä': [
        {'points': [(0.0, 0.0), (0.5, 1.7), (1.0, 0.0)], 'smooth': False},
        {'points': [(0.25, 0.7), (0.75, 0.7)], 'smooth': False},
        {'points': [(0.3, 2.0), (0.35, 2.0)], 'smooth': False},
        {'points': [(0.7, 2.0), (0.75, 2.0)], 'smooth': False}
    ],
    'Ö': [
        {'points': [(0.5, 1.7), (0.0, 1.25), (0.0, 0.45), (0.5, 0.0), (1.0, 0.45), (1.0, 1.25), (0.5, 1.7)], 'smooth': True},
        {'points': [(0.3, 2.0), (0.35, 2.0)], 'smooth': False},
        {'points': [(0.7, 2.0), (0.75, 2.0)], 'smooth': False}
    ],
    'Ü': [
        {'points': [(0.0, 1.7), (0.0, 0.45), (0.25, 0.0), (0.75, 0.0), (1.0, 0.45), (1.0, 1.7)], 'smooth': True},
        {'points': [(0.3, 2.0), (0.35, 2.0)], 'smooth': False},
        {'points': [(0.7, 2.0), (0.75, 2.0)], 'smooth': False}
    ],
    'ß': [
        {'points': [(0.0, 0.0), (0.0, 2.0)], 'smooth': False},
        {'points': [(0.0, 2.0), (0.7, 2.0), (0.9, 1.5), (0.6, 1.0), (0.0, 1.0)], 'smooth': True},
        {'points': [(0.0, 1.0), (0.7, 1.0), (1.0, 0.5), (0.6, 0.0), (0.0, 0.0)], 'smooth': True}
    ],
    # Kleinbuchstaben a-z (echte handschriftliche Formen mit x-Höhe 1.0, Oberlängen bis 2.0, Unterlängen bis -0.5)
    'a': [
        {'points': [(0.8, 1.0), (0.3, 1.0), (0.0, 0.5), (0.3, 0.0), (0.8, 0.0)], 'smooth': True},
        {'points': [(0.8, 1.0), (0.8, 0.0)], 'smooth': False}
    ],
    'b': [
        {'points': [(0.0, 2.0), (0.0, 0.0)], 'smooth': False},
        {'points': [(0.0, 0.9), (0.6, 1.0), (0.9, 0.5), (0.6, 0.0), (0.0, 0.0)], 'smooth': True}
    ],
    'c': [
        {'points': [(0.8, 0.9), (0.5, 1.0), (0.1, 0.7), (0.0, 0.3), (0.3, 0.0), (0.8, 0.1)], 'smooth': True}
    ],
    'd': [
        {'points': [(0.8, 0.9), (0.4, 1.0), (0.0, 0.5), (0.4, 0.0), (0.8, 0.0)], 'smooth': True},
        {'points': [(0.8, 2.0), (0.8, 0.0)], 'smooth': False}
    ],
    'e': [
        {'points': [(0.0, 0.5), (0.8, 0.5), (0.8, 0.9), (0.4, 1.0), (0.0, 0.6), (0.2, 0.0), (0.8, 0.0)], 'smooth': True}
    ],
    'f': [
        {'points': [(0.7, 2.0), (0.4, 2.0), (0.3, 1.6), (0.3, 0.0)], 'smooth': True},
        {'points': [(0.1, 1.1), (0.6, 1.1)], 'smooth': False}
    ],
    'g': [
        {'points': [(0.8, 0.9), (0.4, 1.0), (0.0, 0.5), (0.4, 0.0), (0.8, 0.0)], 'smooth': True},
        {'points': [(0.8, 1.0), (0.8, -0.4), (0.4, -0.6), (0.1, -0.4)], 'smooth': True}
    ],
    'h': [
        {'points': [(0.0, 2.0), (0.0, 0.0)], 'smooth': False},
        {'points': [(0.0, 0.6), (0.4, 1.0), (0.8, 0.9), (0.8, 0.0)], 'smooth': True}
    ],
    'i': [
        {'points': [(0.4, 1.0), (0.4, 0.0)], 'smooth': False},
        {'points': [(0.4, 1.35), (0.42, 1.35)], 'smooth': False}
    ],
    'j': [
        {'points': [(0.5, 1.0), (0.5, -0.4), (0.2, -0.6), (0.0, -0.4)], 'smooth': True},
        {'points': [(0.5, 1.35), (0.52, 1.35)], 'smooth': False}
    ],
    'k': [
        {'points': [(0.0, 2.0), (0.0, 0.0)], 'smooth': False},
        {'points': [(0.7, 1.0), (0.0, 0.4), (0.7, 0.0)], 'smooth': False}
    ],
    'l': [
        {'points': [(0.3, 2.0), (0.3, 0.1), (0.5, 0.0), (0.7, 0.0)], 'smooth': True}
    ],
    'm': [
        {'points': [(0.0, 1.0), (0.0, 0.0)], 'smooth': False},
        {'points': [(0.0, 0.7), (0.25, 1.0), (0.5, 0.8), (0.5, 0.0)], 'smooth': True},
        {'points': [(0.5, 0.7), (0.75, 1.0), (1.0, 0.8), (1.0, 0.0)], 'smooth': True}
    ],
    'n': [
        {'points': [(0.0, 1.0), (0.0, 0.0)], 'smooth': False},
        {'points': [(0.0, 0.6), (0.3, 1.0), (0.7, 0.8), (0.7, 0.0)], 'smooth': True}
    ],
    'o': [
        {'points': [(0.4, 1.0), (0.0, 0.7), (0.0, 0.3), (0.4, 0.0), (0.8, 0.3), (0.8, 0.7), (0.4, 1.0)], 'smooth': True}
    ],
    'p': [
        {'points': [(0.0, 1.0), (0.0, -0.6)], 'smooth': False},
        {'points': [(0.0, 0.9), (0.5, 1.0), (0.8, 0.5), (0.5, 0.0), (0.0, 0.0)], 'smooth': True}
    ],
    'q': [
        {'points': [(0.8, 0.9), (0.4, 1.0), (0.0, 0.5), (0.4, 0.0), (0.8, 0.0)], 'smooth': True},
        {'points': [(0.8, 1.0), (0.8, -0.6), (1.0, -0.4)], 'smooth': False}
    ],
    'r': [
        {'points': [(0.0, 1.0), (0.0, 0.0)], 'smooth': False},
        {'points': [(0.0, 0.6), (0.3, 1.0), (0.6, 0.9)], 'smooth': True}
    ],
    's': [
        {'points': [(0.7, 0.9), (0.4, 1.0), (0.1, 0.7), (0.6, 0.4), (0.5, 0.0), (0.1, 0.1)], 'smooth': True}
    ],
    't': [
        {'points': [(0.3, 1.7), (0.3, 0.1), (0.5, 0.0), (0.7, 0.1)], 'smooth': True},
        {'points': [(0.1, 1.2), (0.6, 1.2)], 'smooth': False}
    ],
    'u': [
        {'points': [(0.1, 1.0), (0.1, 0.2), (0.4, 0.0), (0.7, 0.2), (0.7, 1.0)], 'smooth': True},
        {'points': [(0.7, 1.0), (0.7, 0.0)], 'smooth': False}
    ],
    'v': [
        {'points': [(0.1, 1.0), (0.4, 0.0), (0.7, 1.0)], 'smooth': False}
    ],
    'w': [
        {'points': [(0.0, 1.0), (0.25, 0.0), (0.5, 0.7), (0.75, 0.0), (1.0, 1.0)], 'smooth': False}
    ],
    'x': [
        {'points': [(0.1, 1.0), (0.8, 0.0)], 'smooth': False},
        {'points': [(0.8, 1.0), (0.1, 0.0)], 'smooth': False}
    ],
    'y': [
        {'points': [(0.1, 1.0), (0.4, 0.2)], 'smooth': False},
        {'points': [(0.7, 1.0), (0.4, 0.2), (0.1, -0.6)], 'smooth': False}
    ],
    'z': [
        {'points': [(0.1, 1.0), (0.8, 1.0), (0.1, 0.0), (0.8, 0.0)], 'smooth': False}
    ],
    'ä': [
        {'points': [(0.8, 1.0), (0.3, 1.0), (0.0, 0.5), (0.3, 0.0), (0.8, 0.0)], 'smooth': True},
        {'points': [(0.8, 1.0), (0.8, 0.0)], 'smooth': False},
        {'points': [(0.3, 1.3), (0.35, 1.3)], 'smooth': False},
        {'points': [(0.6, 1.3), (0.65, 1.3)], 'smooth': False}
    ],
    'ö': [
        {'points': [(0.4, 1.0), (0.0, 0.7), (0.0, 0.3), (0.4, 0.0), (0.8, 0.3), (0.8, 0.7), (0.4, 1.0)], 'smooth': True},
        {'points': [(0.3, 1.3), (0.35, 1.3)], 'smooth': False},
        {'points': [(0.6, 1.3), (0.65, 1.3)], 'smooth': False}
    ],
    'ü': [
        {'points': [(0.1, 1.0), (0.1, 0.2), (0.4, 0.0), (0.7, 0.2), (0.7, 1.0)], 'smooth': True},
        {'points': [(0.7, 1.0), (0.7, 0.0)], 'smooth': False},
        {'points': [(0.3, 1.3), (0.35, 1.3)], 'smooth': False},
        {'points': [(0.6, 1.3), (0.65, 1.3)], 'smooth': False}
    ],
    # Zahlen 0-9
    '0': [
        {'points': [(0.5, 2.0), (0.0, 1.5), (0.0, 0.5), (0.5, 0.0), (1.0, 0.5), (1.0, 1.5), (0.5, 2.0)], 'smooth': True},
        {'points': [(0.8, 1.8), (0.2, 0.2)], 'smooth': False}
    ],
    '1': [
        {'points': [(0.1, 1.5), (0.5, 2.0), (0.5, 0.0)], 'smooth': False},
        {'points': [(0.1, 0.0), (0.9, 0.0)], 'smooth': False}
    ],
    '2': [
        {'points': [(0.0, 1.6), (0.2, 2.0), (0.8, 2.0), (1.0, 1.5), (0.0, 0.0), (1.0, 0.0)], 'smooth': True}
    ],
    '3': [
        {'points': [(0.0, 1.8), (0.8, 2.0), (0.5, 1.0), (0.9, 0.5), (0.5, 0.0), (0.0, 0.2)], 'smooth': True}
    ],
    '4': [
        {'points': [(0.8, 0.0), (0.8, 2.0), (0.0, 0.6), (1.0, 0.6)], 'smooth': False}
    ],
    '5': [
        {'points': [(0.9, 2.0), (0.1, 2.0), (0.1, 1.1), (0.6, 1.2), (0.9, 0.8), (0.7, 0.0), (0.1, 0.1)], 'smooth': True}
    ],
    '6': [
        {'points': [(0.8, 1.8), (0.3, 1.4), (0.0, 0.6), (0.5, 0.0), (0.9, 0.4), (0.6, 1.0), (0.0, 0.6)], 'smooth': True}
    ],
    '7': [
        {'points': [(0.0, 2.0), (1.0, 2.0), (0.3, 0.0)], 'smooth': False},
        {'points': [(0.15, 1.0), (0.75, 1.0)], 'smooth': False}
    ],
    '8': [
        {'points': [(0.5, 2.0), (0.1, 1.6), (0.9, 1.0), (0.5, 0.0), (0.1, 0.6), (0.9, 1.4), (0.5, 2.0)], 'smooth': True}
    ],
    '9': [
        {'points': [(0.9, 1.2), (0.4, 1.0), (0.1, 1.5), (0.5, 2.0), (0.9, 1.4), (0.6, 0.4), (0.2, 0.0)], 'smooth': True}
    ],
    # Satzzeichen
    '.': [
        {'points': [(0.4, 0.0), (0.5, 0.1), (0.6, 0.0), (0.5, -0.05), (0.4, 0.0)], 'smooth': True}
    ],
    ',': [
        {'points': [(0.5, 0.2), (0.5, 0.0), (0.3, -0.3)], 'smooth': True}
    ],
    '!': [
        {'points': [(0.5, 2.0), (0.5, 0.6)], 'smooth': False},
        {'points': [(0.45, 0.1), (0.55, 0.1), (0.55, 0.0), (0.45, 0.0), (0.45, 0.1)], 'smooth': True}
    ],
    '?': [
        {'points': [(0.1, 1.6), (0.3, 2.0), (0.7, 2.0), (0.9, 1.5), (0.5, 1.0), (0.5, 0.6)], 'smooth': True},
        {'points': [(0.45, 0.1), (0.55, 0.1), (0.55, 0.0), (0.45, 0.0), (0.45, 0.1)], 'smooth': True}
    ],
    '-': [
        {'points': [(0.1, 1.0), (0.9, 1.0)], 'smooth': False}
    ],
    ':': [
        {'points': [(0.45, 1.4), (0.55, 1.4), (0.55, 1.3), (0.45, 1.3), (0.45, 1.4)], 'smooth': True},
        {'points': [(0.45, 0.2), (0.55, 0.2), (0.55, 0.1), (0.45, 0.1), (0.45, 0.2)], 'smooth': True}
    ],
    '/': [
        {'points': [(0.0, 0.0), (1.0, 2.0)], 'smooth': False}
    ],
    '&': [
        {'points': [(0.85, 0.0), (0.3, 1.1), (0.3, 1.6), (0.6, 1.9), (0.75, 1.6), (0.7, 1.2), (0.1, 0.4), (0.2, 0.0), (0.65, 0.0), (0.9, 0.4)], 'smooth': True}
    ],
    ';': [
        {'points': [(0.45, 1.4), (0.55, 1.4), (0.55, 1.3), (0.45, 1.3), (0.45, 1.4)], 'smooth': True},
        {'points': [(0.5, 0.3), (0.5, 0.1), (0.3, -0.2)], 'smooth': True}
    ],
    '+': [
        {'points': [(0.1, 1.0), (0.9, 1.0)], 'smooth': False},
        {'points': [(0.5, 1.4), (0.5, 0.6)], 'smooth': False}
    ],
    '*': [
        {'points': [(0.1, 1.0), (0.9, 1.0)], 'smooth': False},
        {'points': [(0.25, 1.4), (0.75, 0.6)], 'smooth': False},
        {'points': [(0.25, 0.6), (0.75, 1.4)], 'smooth': False}
    ],
    '=': [
        {'points': [(0.1, 1.2), (0.9, 1.2)], 'smooth': False},
        {'points': [(0.1, 0.8), (0.9, 0.8)], 'smooth': False}
    ],
    '(': [
        {'points': [(0.7, 2.0), (0.3, 1.0), (0.7, 0.0)], 'smooth': True}
    ],
    ')': [
        {'points': [(0.3, 2.0), (0.7, 1.0), (0.3, 0.0)], 'smooth': True}
    ],
    "'": [
        {'points': [(0.5, 2.0), (0.4, 1.5)], 'smooth': False}
    ],
    '"': [
        {'points': [(0.35, 2.0), (0.3, 1.5)], 'smooth': False},
        {'points': [(0.65, 2.0), (0.6, 1.5)], 'smooth': False}
    ],
    '_': [
        {'points': [(0.0, -0.2), (1.0, -0.2)], 'smooth': False}
    ],
    '#': [
        {'points': [(0.35, 2.0), (0.25, 0.0)], 'smooth': False},
        {'points': [(0.75, 2.0), (0.65, 0.0)], 'smooth': False},
        {'points': [(0.1, 1.4), (0.9, 1.4)], 'smooth': False},
        {'points': [(0.1, 0.6), (0.9, 0.6)], 'smooth': False}
    ],
    '%': [
        {'points': [(0.1, 0.0), (0.9, 2.0)], 'smooth': False},
        {'points': [(0.25, 1.7), (0.35, 1.7), (0.35, 1.5), (0.25, 1.5), (0.25, 1.7)], 'smooth': True},
        {'points': [(0.65, 0.5), (0.75, 0.5), (0.75, 0.3), (0.65, 0.3), (0.65, 0.5)], 'smooth': True}
    ],
    '@': [
        {'points': [(0.85, 0.5), (0.7, 0.9), (0.4, 0.9), (0.2, 0.5), (0.4, 0.1), (0.7, 0.1), (0.8, 0.5), (0.8, 0.8), (0.5, 1.2), (0.1, 0.7), (0.1, 0.3), (0.5, -0.2), (0.9, 0.2)], 'smooth': True}
    ],
    '$': [
        {'points': [(0.7, 1.7), (0.4, 1.9), (0.1, 1.5), (0.6, 1.1), (0.5, 0.3), (0.1, 0.5)], 'smooth': True},
        {'points': [(0.4, 2.0), (0.4, 0.0)], 'smooth': False}
    ],
    '<': [
        {'points': [(0.8, 1.6), (0.2, 1.0), (0.8, 0.4)], 'smooth': False}
    ],
    '>': [
        {'points': [(0.2, 1.6), (0.8, 1.0), (0.2, 0.4)], 'smooth': False}
    ],
    '[': [
        {'points': [(0.6, 2.0), (0.3, 2.0), (0.3, 0.0), (0.6, 0.0)], 'smooth': False}
    ],
    ']': [
        {'points': [(0.4, 2.0), (0.7, 2.0), (0.7, 0.0), (0.4, 0.0)], 'smooth': False}
    ],
    '^': [
        {'points': [(0.2, 1.4), (0.5, 1.9), (0.8, 1.4)], 'smooth': False}
    ],
    '`': [
        {'points': [(0.4, 2.0), (0.5, 1.6)], 'smooth': False}
    ],
    '{': [
        {'points': [(0.7, 2.0), (0.4, 1.8), (0.4, 1.2), (0.2, 1.0), (0.4, 0.8), (0.4, 0.2), (0.7, 0.0)], 'smooth': True}
    ],
    '|': [
        {'points': [(0.5, 2.0), (0.5, 0.0)], 'smooth': False}
    ],
    '}': [
        {'points': [(0.3, 2.0), (0.6, 1.8), (0.6, 1.2), (0.8, 1.0), (0.6, 0.8), (0.6, 0.2), (0.3, 0.0)], 'smooth': True}
    ],
    '~': [
        {'points': [(0.1, 1.0), (0.3, 1.2), (0.6, 0.8), (0.9, 1.0)], 'smooth': True}
    ],
    '\\': [
        {'points': [(0.0, 2.0), (1.0, 0.0)], 'smooth': False}
    ],
    ' ': []
}

# Proportionale Breiten für natürliche Handschrift (Basisbreite 1.0)
GLYPH_METRICS: Dict[str, float] = {
    # Schmale Zeichen
    'i': 0.5, 'j': 0.5, 'l': 0.5, 't': 0.6, 'r': 0.65, 'f': 0.65,
    'I': 0.7, 'J': 0.7, '1': 0.7,
    '.': 0.4, ',': 0.4, '!': 0.4, ':': 0.4,
    # Breite Zeichen
    'm': 1.2, 'w': 1.15, 'M': 1.2, 'W': 1.25,
    # Standardbreite für alle nicht gelisteten Zeichen: 0.85
}

# Handschriftliche Glyphen-Varianten für häufige Zeichen
# Struktur: GLYPH_VARIANTS[char] = [ [path_defs_variant_1], [path_defs_variant_2], ... ]
GLYPH_VARIANTS: Dict[str, List[List[Dict]]] = {
    'e': [
        # Variante 1: Standard gerundet
        [{'points': [(0.0, 0.5), (0.8, 0.5), (0.8, 0.9), (0.4, 1.0), (0.0, 0.6), (0.2, 0.0), (0.8, 0.0)], 'smooth': True}],
        # Variante 2: Leicht offener Loop
        [{'points': [(0.0, 0.45), (0.75, 0.55), (0.75, 0.95), (0.35, 1.0), (0.0, 0.55), (0.3, 0.0), (0.85, 0.05)], 'smooth': True}],
        # Variante 3: Schnell geschriebenes e mit sanfterem Schwung
        [{'points': [(0.05, 0.4), (0.8, 0.5), (0.7, 0.9), (0.4, 0.95), (0.05, 0.6), (0.15, 0.0), (0.75, 0.0)], 'smooth': True}],
    ],
    'a': [
        # Variante 1: Oval + gerader Schaft
        [{'points': [(0.8, 1.0), (0.3, 1.0), (0.0, 0.5), (0.3, 0.0), (0.8, 0.0)], 'smooth': True},
         {'points': [(0.8, 1.0), (0.8, 0.0)], 'smooth': False}],
        # Variante 2: Fließender Bauch mit kleinem Abgang
        [{'points': [(0.75, 0.95), (0.25, 0.95), (0.0, 0.45), (0.35, 0.0), (0.75, 0.1)], 'smooth': True},
         {'points': [(0.75, 1.0), (0.75, 0.0), (0.85, 0.05)], 'smooth': True}],
        # Variante 3: Kompaktes rundes a
        [{'points': [(0.8, 0.9), (0.35, 1.0), (0.05, 0.5), (0.35, 0.0), (0.8, 0.0)], 'smooth': True},
         {'points': [(0.8, 0.95), (0.8, 0.0)], 'smooth': False}],
    ],
    'n': [
        # Variante 1: Standard
        [{'points': [(0.0, 1.0), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.0, 0.6), (0.3, 1.0), (0.7, 0.8), (0.7, 0.0)], 'smooth': True}],
        # Variante 2: Weicherer oberer Bogen
        [{'points': [(0.0, 1.0), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.0, 0.5), (0.35, 1.0), (0.75, 0.9), (0.75, 0.0)], 'smooth': True}],
        # Variante 3: Leicht nach rechts geneigt
        [{'points': [(0.05, 1.0), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.0, 0.65), (0.4, 0.98), (0.7, 0.75), (0.7, 0.0)], 'smooth': True}],
    ],
    't': [
        # Variante 1: Standard mit Querstrich
        [{'points': [(0.3, 1.7), (0.3, 0.1), (0.5, 0.0), (0.7, 0.1)], 'smooth': True},
         {'points': [(0.1, 1.2), (0.6, 1.2)], 'smooth': False}],
        # Variante 2: Höherer Querbalken
        [{'points': [(0.3, 1.75), (0.3, 0.1), (0.55, 0.0)], 'smooth': True},
         {'points': [(0.1, 1.3), (0.65, 1.25)], 'smooth': False}],
    ],
    'l': [
        # Variante 1: Weicher Haken unten
        [{'points': [(0.3, 2.0), (0.3, 0.1), (0.5, 0.0), (0.7, 0.0)], 'smooth': True}],
        # Variante 2: Gerader Abstrich mit kurzem Auslauf
        [{'points': [(0.3, 2.0), (0.3, 0.05), (0.55, 0.0)], 'smooth': True}],
    ],
    'i': [
        # Variante 1: Gerader Strich + Punkt
        [{'points': [(0.4, 1.0), (0.4, 0.0)], 'smooth': False},
         {'points': [(0.4, 1.35), (0.42, 1.35)], 'smooth': False}],
        # Variante 2: Leicht geschwungener Strich
        [{'points': [(0.38, 1.0), (0.4, 0.4), (0.45, 0.0)], 'smooth': True},
         {'points': [(0.42, 1.38), (0.44, 1.38)], 'smooth': False}],
    ],
    'o': [
        # Variante 1: Standard gerundet
        [{'points': [(0.4, 1.0), (0.0, 0.7), (0.0, 0.3), (0.4, 0.0), (0.8, 0.3), (0.8, 0.7), (0.4, 1.0)], 'smooth': True}],
        # Variante 2: Leicht ovaler, dynamischer Schwung
        [{'points': [(0.45, 0.98), (0.05, 0.75), (0.0, 0.25), (0.4, 0.0), (0.85, 0.35), (0.8, 0.8), (0.45, 0.98)], 'smooth': True}],
    ],
    'h': [
        # Variante 1: Standard
        [{'points': [(0.0, 2.0), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.0, 0.6), (0.4, 1.0), (0.8, 0.9), (0.8, 0.0)], 'smooth': True}],
        # Variante 2: Weicherer Bogen mit leichtem Abgang
        [{'points': [(0.0, 2.0), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.0, 0.55), (0.35, 1.0), (0.75, 0.85), (0.75, 0.05), (0.85, 0.0)], 'smooth': True}],
    ],
    'm': [
        # Variante 1: Dreibeinig Standard
        [{'points': [(0.0, 1.0), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.0, 0.7), (0.25, 1.0), (0.5, 0.8), (0.5, 0.0)], 'smooth': True},
         {'points': [(0.5, 0.7), (0.75, 1.0), (1.0, 0.8), (1.0, 0.0)], 'smooth': True}],
        # Variante 2: Fließende Doppelwelle
        [{'points': [(0.0, 0.95), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.0, 0.6), (0.28, 1.0), (0.52, 0.75), (0.52, 0.0)], 'smooth': True},
         {'points': [(0.52, 0.6), (0.78, 0.98), (1.05, 0.75), (1.05, 0.05)], 'smooth': True}],
    ],
    'u': [
        # Variante 1: U-Bogen + Abstrich
        [{'points': [(0.1, 1.0), (0.1, 0.2), (0.4, 0.0), (0.7, 0.2), (0.7, 1.0)], 'smooth': True},
         {'points': [(0.7, 1.0), (0.7, 0.0)], 'smooth': False}],
        # Variante 2: Leicht runderer Boden mit kleinem Schwung
        [{'points': [(0.1, 0.95), (0.12, 0.15), (0.42, 0.0), (0.72, 0.25), (0.72, 0.95)], 'smooth': True},
         {'points': [(0.72, 0.95), (0.72, 0.0), (0.82, 0.05)], 'smooth': True}],
    ],
    'g': [
        # Variante 1: Bauch + Unterlängenschlaufe
        [{'points': [(0.8, 0.9), (0.4, 1.0), (0.0, 0.5), (0.4, 0.0), (0.8, 0.0)], 'smooth': True},
         {'points': [(0.8, 1.0), (0.8, -0.4), (0.4, -0.6), (0.1, -0.4)], 'smooth': True}],
        # Variante 2: Weiterer Schwung unten
        [{'points': [(0.75, 0.95), (0.35, 1.0), (0.05, 0.55), (0.4, 0.0), (0.75, 0.05)], 'smooth': True},
         {'points': [(0.75, 1.0), (0.75, -0.45), (0.3, -0.65), (0.05, -0.35)], 'smooth': True}],
    ],
    'y': [
        # Variante 1: Gerader Abstrich
        [{'points': [(0.1, 1.0), (0.4, 0.2)], 'smooth': False},
         {'points': [(0.7, 1.0), (0.4, 0.2), (0.1, -0.6)], 'smooth': False}],
        # Variante 2: Leicht geschwungene Unterlänge
        [{'points': [(0.12, 0.95), (0.38, 0.25)], 'smooth': False},
         {'points': [(0.68, 0.95), (0.38, 0.25), (0.15, -0.55), (0.0, -0.5)], 'smooth': True}],
    ],
    'r': [
        # Variante 1: Standard
        [{'points': [(0.0, 1.0), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.0, 0.6), (0.3, 1.0), (0.6, 0.9)], 'smooth': True}],
        # Variante 2: Ausgeprägterer Schwungarm
        [{'points': [(0.0, 0.95), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.0, 0.5), (0.25, 0.98), (0.65, 0.92)], 'smooth': True}],
    ],
    's': [
        # Variante 1: Standard S
        [{'points': [(0.7, 0.9), (0.4, 1.0), (0.1, 0.7), (0.6, 0.4), (0.5, 0.0), (0.1, 0.1)], 'smooth': True}],
        # Variante 2: Schlankere Rundung
        [{'points': [(0.65, 0.95), (0.35, 1.0), (0.08, 0.65), (0.55, 0.45), (0.45, 0.0), (0.15, 0.05)], 'smooth': True}],
    ],
    'd': [
        # Variante 1: Standard
        [{'points': [(0.8, 0.9), (0.4, 1.0), (0.0, 0.5), (0.4, 0.0), (0.8, 0.0)], 'smooth': True},
         {'points': [(0.8, 2.0), (0.8, 0.0)], 'smooth': False}],
        # Variante 2: Leicht geschwungener Oberstrich
        [{'points': [(0.75, 0.95), (0.35, 1.0), (0.05, 0.5), (0.4, 0.0), (0.75, 0.05)], 'smooth': True},
         {'points': [(0.75, 2.0), (0.75, 0.05), (0.85, 0.0)], 'smooth': True}],
    ],
    'c': [
        # Variante 1: Standard
        [{'points': [(0.8, 0.9), (0.5, 1.0), (0.1, 0.7), (0.0, 0.3), (0.3, 0.0), (0.8, 0.1)], 'smooth': True}],
        # Variante 2: Weiter geöffneter Schwung
        [{'points': [(0.82, 0.85), (0.45, 1.0), (0.08, 0.65), (0.02, 0.25), (0.35, 0.0), (0.82, 0.15)], 'smooth': True}],
    ],
    'b': [
        # Variante 1: Gerader Schaft + runder Bauch
        [{'points': [(0.0, 2.0), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.0, 0.85), (0.55, 1.0), (0.85, 0.5), (0.55, 0.0), (0.0, 0.0)], 'smooth': True}],
        # Variante 2: Fließender Abgang und ovalerer Bauch
        [{'points': [(0.0, 2.0), (0.0, 0.05)], 'smooth': False},
         {'points': [(0.0, 0.75), (0.5, 0.95), (0.8, 0.45), (0.45, 0.0), (0.0, 0.0), (0.1, 0.05)], 'smooth': True}],
    ],
    'f': [
        # Variante 1: Bogen oben + horizontaler Querstrich
        [{'points': [(0.65, 2.0), (0.4, 2.0), (0.3, 1.6), (0.3, 0.0)], 'smooth': True},
         {'points': [(0.1, 1.1), (0.6, 1.1)], 'smooth': False}],
        # Variante 2: Tieferer Einstieg und leicht geschwungener Querbalken
        [{'points': [(0.7, 1.95), (0.45, 2.0), (0.28, 1.55), (0.28, 0.0)], 'smooth': True},
         {'points': [(0.08, 1.15), (0.62, 1.08)], 'smooth': False}],
    ],
    'j': [
        # Variante 1: Standardhaken nach links
        [{'points': [(0.5, 1.0), (0.5, -0.4), (0.2, -0.6), (0.0, -0.4)], 'smooth': True},
         {'points': [(0.5, 1.35), (0.52, 1.35)], 'smooth': False}],
        # Variante 2: Weiterer Schwungbogen in der Unterlänge
        [{'points': [(0.48, 1.0), (0.48, -0.35), (0.25, -0.65), (-0.05, -0.45)], 'smooth': True},
         {'points': [(0.5, 1.38), (0.52, 1.38)], 'smooth': False}],
    ],
    'k': [
        # Variante 1: Gerader Schaft + zwei getrennte Diagonalen
        [{'points': [(0.0, 2.0), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.65, 1.0), (0.0, 0.45), (0.7, 0.0)], 'smooth': False}],
        # Variante 2: Sanfterer Knick und auslaufender Fuß
        [{'points': [(0.0, 2.0), (0.0, 0.0)], 'smooth': False},
         {'points': [(0.6, 0.95), (0.0, 0.4)], 'smooth': False},
         {'points': [(0.0, 0.4), (0.68, 0.0), (0.78, 0.05)], 'smooth': True}],
    ],
    'p': [
        # Variante 1: Gerader Abstrich + runder Kopf
        [{'points': [(0.0, 1.0), (0.0, -0.6)], 'smooth': False},
         {'points': [(0.0, 0.9), (0.5, 1.0), (0.8, 0.5), (0.5, 0.0), (0.0, 0.0)], 'smooth': True}],
        # Variante 2: Leicht geschwungene Unterlänge und kompakterer Bogen
        [{'points': [(0.0, 1.0), (0.0, -0.55), (-0.05, -0.6)], 'smooth': True},
         {'points': [(0.0, 0.85), (0.45, 0.98), (0.78, 0.52), (0.48, 0.02), (0.0, 0.05)], 'smooth': True}],
    ],
    'q': [
        # Variante 1: Bauch + gerader Abstrich mit Häkchen
        [{'points': [(0.8, 0.9), (0.4, 1.0), (0.0, 0.5), (0.4, 0.0), (0.8, 0.0)], 'smooth': True},
         {'points': [(0.8, 1.0), (0.8, -0.6), (1.0, -0.4)], 'smooth': False}],
        # Variante 2: Schlanker Bauch mit weichem Auslauf nach rechts
        [{'points': [(0.78, 0.92), (0.35, 1.0), (0.02, 0.48), (0.38, 0.0), (0.78, 0.05)], 'smooth': True},
         {'points': [(0.78, 1.0), (0.78, -0.58), (0.95, -0.48)], 'smooth': True}],
    ],
    'v': [
        # Variante 1: Symmetrisches V
        [{'points': [(0.1, 1.0), (0.4, 0.0), (0.7, 1.0)], 'smooth': False}],
        # Variante 2: Leicht asymmetrisch mit gerundeter Spitze unten
        [{'points': [(0.08, 0.95), (0.38, 0.0), (0.44, 0.02), (0.72, 1.0)], 'smooth': True}],
    ],
    'w': [
        # Variante 1: Scharfes Doppel-V
        [{'points': [(0.0, 1.0), (0.25, 0.0), (0.5, 0.7), (0.75, 0.0), (1.0, 1.0)], 'smooth': False}],
        # Variante 2: Leicht geschwungene Täler
        [{'points': [(0.02, 0.98), (0.23, 0.02), (0.48, 0.68), (0.73, 0.02), (0.98, 0.95)], 'smooth': True}],
    ],
    'x': [
        # Variante 1: Zwei sich kreuzende Diagonalen
        [{'points': [(0.1, 1.0), (0.8, 0.0)], 'smooth': False},
         {'points': [(0.8, 1.0), (0.1, 0.0)], 'smooth': False}],
        # Variante 2: Asymmetrischer Strichansatz
        [{'points': [(0.12, 0.98), (0.78, 0.0)], 'smooth': False},
         {'points': [(0.75, 1.0), (0.1, 0.05), (0.05, 0.0)], 'smooth': True}],
    ],
    'z': [
        # Variante 1: Standard Z
        [{'points': [(0.1, 1.0), (0.8, 1.0), (0.1, 0.0), (0.8, 0.0)], 'smooth': False}],
        # Variante 2: Leicht geschwungener Deckstrich und Basis
        [{'points': [(0.08, 0.98), (0.78, 1.0), (0.12, 0.0), (0.82, 0.0)], 'smooth': True}],
    ],
}

def chaikin_smooth(points: List[Tuple[float, float]], iterations: int = 2) -> List[Tuple[float, float]]:
    if len(points) <= 2:
        return points

    for _ in range(iterations):
        new_points = [points[0]]
        for i in range(len(points) - 1):
            p0 = points[i]
            p1 = points[i + 1]
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            new_points.append(q)
            new_points.append(r)
        new_points.append(points[-1])
        points = new_points
    return points

class HandwritingStyle:
    def __init__(self, seed: Optional[int] = None, slant_deg: float = 0.0,
                 height_var: float = 0.04, width_var: float = 0.04, rot_var_deg: float = 1.0):
        self.seed = seed
        self.rng = random.Random(seed) if seed is not None else random.Random()
        # Dokumentenweiter Grund-Slant (z. B. 0 - 8 Grad)
        self.base_slant_deg = slant_deg if slant_deg != 0.0 else (self.rng.uniform(-1.0, 4.0) if seed is not None else 0.0)
        self.height_var = height_var
        self.width_var = width_var
        self.rot_var_deg = rot_var_deg

    def perturb_glyph(self, points: List[Tuple[float, float]], char_idx: int) -> List[Tuple[float, float]]:
        """
        Wendet subtile typografische Variationen auf eine Glyphe an:
        - Leichter konsistenter Slant
        - Subtile zufällige Skalierung (Höhe/Breite ± few %)
        - Minimalste Rotation
        """
        # Lokaler deterministischer RNG pro Buchstabe (echter Seedpfad für 0)
        base_s = self.seed if self.seed is not None else 12345
        c_rng = random.Random(base_s + char_idx * 7919)
        s_height = 1.0 + c_rng.uniform(-self.height_var, self.height_var)
        s_width = 1.0 + c_rng.uniform(-self.width_var, self.width_var)
        slant = math.radians(self.base_slant_deg + c_rng.uniform(-0.5, 0.5))
        rot = math.radians(c_rng.uniform(-self.rot_var_deg, self.rot_var_deg))
        cos_r, sin_r = math.cos(rot), math.sin(rot)

        new_pts = []
        for x, y in points:
            # 1. Slant (Scherung nach rechts mit der Höhe y)
            x_slanted = x + y * math.tan(slant)
            # 2. Skalierung
            x_scaled = x_slanted * s_width
            y_scaled = y * s_height
            # 3. Subtile Rotation um Mitte (0.5, 1.0)
            cx, cy = 0.5, 1.0
            dx, dy = x_scaled - cx, y_scaled - cy
            x_rot = cx + dx * cos_r - dy * sin_r
            y_rot = cy + dx * sin_r + dy * cos_r
            new_pts.append((x_rot, y_rot))
        return new_pts

class StrokeGenerator:
    def __init__(self, char_spacing: float = 0.5, word_spacing: float = 1.0,
                 line_height: float = 3.0, smooth_iterations: int = 2,
                 seed: Optional[int] = None, enable_variants: bool = True):
        self.char_spacing = char_spacing
        self.word_spacing = word_spacing
        self.line_height = line_height
        self.smooth_iterations = smooth_iterations
        self.default_char_width = 0.85
        self.seed = seed
        self.enable_variants = enable_variants
        self.style = HandwritingStyle(seed=seed)
        self._warned_unsupported: set = set()

    def _offset_path(self, path: List[Tuple[float, float]], offset_x: float, offset_y: float) -> List[Tuple[float, float]]:
        return [(x + offset_x, y + offset_y) for x, y in path]

    def _get_char_width(self, char: str) -> float:
        return GLYPH_METRICS.get(char, self.default_char_width)

    def generate_text(self, text: str, start_x: float = 0.0, start_y: float = 0.0) -> List[Stroke]:
        strokes = []
        current_x = start_x
        current_y = start_y
        last_point = None
        char_counter = 0

        for char in text:
            if char == '\n':
                current_x = start_x
                current_y -= self.line_height
                continue

            if char == ' ':
                current_x += self.word_spacing
                continue

            char_counter += 1

            # Sicherer Lookup ohne 'ß'.upper() -> 'SS' Zerstörung
            target_key = None
            if char in FONT_DICT:
                target_key = char
            elif char.upper() in FONT_DICT:
                target_key = char.upper()

            if target_key:
                # Prüfen auf Glyphen-Varianten
                if self.enable_variants and target_key in GLYPH_VARIANTS:
                    variants = GLYPH_VARIANTS[target_key]
                    v_base_s = self.seed if self.seed is not None else 54321
                    v_rng = random.Random(v_base_s + char_counter * 313)
                    char_paths = v_rng.choice(variants)
                else:
                    char_paths = FONT_DICT[target_key]

                for path_def in char_paths:
                    points = path_def['points']
                    # Handschriftliche Slant/Scale-Perturbation
                    if self.enable_variants:
                        points = self.style.perturb_glyph(points, char_counter)

                    if path_def.get('smooth', False):
                        points = chaikin_smooth(points, self.smooth_iterations)

                    offset_points = self._offset_path(points, current_x, current_y)

                    if last_point is not None and last_point != offset_points[0]:
                        strokes.append(Stroke(points=[last_point, offset_points[0]], pen_down=False))

                    strokes.append(Stroke(points=offset_points, pen_down=True))
                    last_point = offset_points[-1]

                # Proportionales Spacing verwenden
                adv = self._get_char_width(target_key)
                current_x += adv + self.char_spacing
            else:
                import sys
                if char not in self._warned_unsupported:
                    print(f"[WARNUNG] Zeichen '{char}' (U+{ord(char):04X}) wird von der Schrift-Engine nicht unterstützt und übersprungen.", file=sys.stderr)
                    self._warned_unsupported.add(char)
                current_x += self.word_spacing

        return strokes
