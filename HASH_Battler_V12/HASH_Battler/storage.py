"""Load/save settings and training progress; missing or corrupt files are safe."""
import json
from config import CONTROLS_FILE, SAVE_FILE, DEFAULT_BINDINGS


def _read(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            result = json.load(handle)
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
    temporary.replace(path)


def load_settings():
    stored = _read(CONTROLS_FILE)
    bindings = DEFAULT_BINDINGS.copy()
    assigned = set()
    provided = stored.get("bindings", {})
    # V7 used Sword for the left-click control. Carry customized bindings
    # forward without asking players to delete their controls.json file.
    if isinstance(provided, dict):
        provided = provided.copy()
        if "Shoot" not in provided and "Sword" in provided:
            provided["Shoot"] = provided["Sword"]
    if isinstance(provided, dict):
        from config import FIXED_KEYS
        for action, key in provided.items():
            if (action in bindings and isinstance(key, str)
                    and key and key not in FIXED_KEYS and key not in assigned
                    and (not action.startswith("Move ") or not key.startswith("Mouse"))):
                bindings[action] = key
                assigned.add(key)
    # If a saved customization introduced a collision with a default key,
    # restore that default safely rather than leaving two actions bound.
    if len(set(bindings.values())) != len(bindings):
        bindings = DEFAULT_BINDINGS.copy()
    return {
        "bindings": bindings,
        "sound": stored.get("sound", True) is not False,
        "debug": stored.get("debug", False) is True,
        "fullscreen": stored.get("fullscreen", True) is not False,
    }


def save_settings(settings):
    _write(CONTROLS_FILE, settings)


def load_run():
    return _read(SAVE_FILE)


def save_run(payload):
    _write(SAVE_FILE, payload)
