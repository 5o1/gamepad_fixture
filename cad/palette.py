"""Authoritative fixture color reference shared by manufacturing and URDF."""
import json
from pathlib import Path
PALETTE_PATH=Path(__file__).resolve().parents[1]/'config/colors.json'

def load_palette(path=PALETTE_PATH):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def rgb(hex_color):
    return tuple(int(hex_color[i:i+2],16) for i in (1,3,5))

def rgba(hex_color):
    return tuple(v/255 for v in rgb(hex_color))+(1.,)

def part_color(palette,name,is_printed):
    return palette['printed_parts'][name] if is_printed else palette['purchased_parts']
