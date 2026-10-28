"""Game constants and the default editable input bindings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CONTROLS_FILE = DATA_DIR / "controls.json"
SAVE_FILE = DATA_DIR / "run_save.json"

BG = "#050505"
PANEL = "#101010"
PANEL_DARK = "#080808"
BUTTON = "#252525"
HOVER = "#404040"
BORDER = "#777777"
TEXT = "#ffffff"
MUTED = "#aaaaaa"
CYAN = "#ffdf00"
RED = "#ffffff"
GOLD = "#ffffff"
GREEN = "#ffffff"
PURPLE = "#ffffff"

WORLD_W, WORLD_H = 1600, 900  # Never change aspect ratio when resizing.
PLAYER_RADIUS = 15  # Slightly smaller player; same dimensions for rendering and collision
DUMMY_RADIUS = 292
MOVE_SPEED = 290.0  # World units / second
DASH_LENGTH = 205.0
ABILITY_COOLDOWN = 1.0  # Default; timed shots use a shorter recovery window.

DEFAULT_BINDINGS = {
    "Move Up": "w",
    "Move Down": "s",
    "Move Left": "a",
    "Move Right": "d",
    "Dash": "Shift_L",
    "Shoot": "Mouse1",
    "Chestplate": "Control_L",
    "Item 1": "1",
    "Item 2": "2",
    "Item 3": "3",
    "Item 4": "4",
}

# Always available so the player can't lock themselves out of the menus.
FIXED_KEYS = {"p", "j", "F3", "F11", "Escape"}
ACTION_NAMES = ("Dash", "Shoot", "Chestplate",
                "Item 1", "Item 2", "Item 3", "Item 4")

KEY_LABELS = {
    "Mouse1": "LEFT CLICK", "Mouse2": "MIDDLE CLICK", "Mouse3": "RIGHT CLICK",
    "Shift_L": "L-SHIFT", "Shift_R": "R-SHIFT",
    "Control_L": "L-CTRL", "Control_R": "R-CTRL",
    "space": "SPACE", "Return": "ENTER", "Tab": "TAB",
    "Up": "UP", "Down": "DOWN", "Left": "LEFT", "Right": "RIGHT",
}


def pretty_key(key):
    return KEY_LABELS.get(key, key.upper() if len(key) == 1 else key)
