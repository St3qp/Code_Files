# #HASH# V12 — Lance Dash Refinement

A Python 3.12 Turtle/Tkinter top-down boss battler. **Python's standard library is sufficient to play.**

## How to play

1. Extract the ZIP and open `HASH_Battler/main.py` (or double-click `play_HASH.bat` on Windows).
2. Choose **New Run** / **Continue**, then choose **Level 1** (the square labeled `1`) on the map.
3. Select **Lance**. The other two cards are future placeholders.
4. Select **one** element and assign all **10 points** across the six stats (at most **7** per stat).
5. Press **ENTER TRAINING**. Press **1** to dash toward the nearest available dummy and strike at the end of the lunge. The Lance is only visible during the ability animation; it no longer recoils backward. Target dummies regenerate after a few seconds. Click **MAP** at the top right to return and try another configuration.

Level 0 / The Greeter remains playable from the first map node. Intro dialogue and tutorials advance with **Enter only**.

## Item stats

- **Damage:** increases direct Lance damage.
- **Attack Speed:** lowers the cooldown between Lance attacks.
- **Effect Power:** strengthens your chosen element.
- **Knockback:** increases the push on the enemy.
- **Reach:** increases the maximum distance from which a dash-strike can connect.
- **Dash Speed:** makes the Lance lunge faster.

## Effects

- **Fire:** burst bonus damage upon impact.
- **Thunder:** stuns the target for a short period.
- **Ice:** temporarily slows moving targets.
- **Poison:** deals damage over time.
- **Air:** greatly increases target knockback.

The training room includes **three gently moving practice dummies** with health bars, visible effects, damage tracking, and automatic respawns. Regular timing-based shots also damage the dummies, for comparison. Lance appears only while its ability is active. Pressing the ability makes the player dash toward the nearest target and strike; there is no idle spear and no backward recoil.

## Combat controls

| Input | Action |
| --- | --- |
| WASD | Move |
| Shift | Long invulnerable dash |
| Left-click | Shoot on the yellow segment of the rotating timing ring |
| Ctrl | Chestplate guard |
| **1** | **Lance in the training room** |
| P or Esc in combat | Pause / Settings |
| Enter | Advance boss dialogue and Quick Tips |
| F11 | Toggle fullscreen |
| F3 | Debug view |

Lance appears in ability slot 1; slots 2–4 remain empty. Input bindings can be changed under Settings.

## Preserved Level 0 balancing

HASH pickups in the Level 0 Greeter fight now spawn more frequently when you have fewer than four lives: an initial spawn window of **6–9 seconds**, and **11–16 seconds** after a pickup expires or is collected. Only one pickup can exist at a time. All Level 0 laser and Hunter limits from V10.1 are retained; their patterns were not changed.

## Files

- `items.py`: builds, elements, 10-point/7-point validation, Lance formulas.
- `combat.py`: gameplay including the spear dash-strike, elemental effects, and training targets.
- `game.py`: screens, transitions, inputs, saves.
- `visuals.py`: menus, customization UI, training dummy / spear rendering, cursor.
- `config.py`, `storage.py`: settings and persistence.
- `tests/test_items.py`, `tests/test_combat.py`: **48 automated unit tests**.
- `tests/smoke_v12.py`: graphical flow test (Pillow and a graphical environment required only for screenshots).

To run the automated tests from the `HASH_Battler` folder:

```sh
python -m unittest discover -s tests -v
```

**Note:** The game has been tested graphically in Linux/Xvfb, not on an actual Windows monitor, so Windows-only cursor hiding remains unverified.
