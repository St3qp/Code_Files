"""Boss ideation generator for #HASH#.

This module is intentionally separate from the main game loop. It does not
contain gameplay logic or boss behavior. It only proposes boss identities,
visual themes, move families, dialogue, and difficulty profiles that can later
be translated into actual in-game boss objects.

The generator is rules-based rather than API-based, so it works offline with no
API keys or external dependencies.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Shared design axes
# ---------------------------------------------------------------------------

ARCHETYPES = {
    "Beast": {
        "summary": "Feral monster with natural, primal force.",
        "move_sources": ["natural", "mythic"],
        "moods": ["wild", "humanoid"],
    },
    "Godly": {
        "summary": "Divine or mythic being with impossible authority.",
        "move_sources": ["divine", "magical"],
        "moods": ["calm", "angry"],
    },
    "Arcane": {
        "summary": "Wizard-like caster with illusion, teleportation, and ritual force.",
        "move_sources": ["magical", "divine"],
        "moods": ["joyful", "wise"],
    },
    "Laser": {
        "summary": "Precision hazard boss built around red timing and angular pressure.",
        "move_sources": ["laser", "divine"],
        "moods": ["humanoid", "calm"],
    },
    "Horde": {
        "summary": "Boss who uses swarm logic, minions, and layered pressure.",
        "move_sources": ["minion", "magical"],
        "moods": ["insane", "angry"],
    },
    "Corrupt": {
        "summary": "Rot, decay, and broken holy or natural forms.",
        "move_sources": ["divine", "minion"],
        "moods": ["insane", "angry"],
    },
    "Celestial": {
        "summary": "Bright, holy, or cosmic being with radiant authority.",
        "move_sources": ["divine", "laser"],
        "moods": ["calm", "joyful"],
    },
    "Abyssal": {
        "summary": "Shadow entity built from void and impossible geometry.",
        "move_sources": ["minion", "magical"],
        "moods": ["wise", "insane"],
    },
    "Guardian": {
        "summary": "Protector or executor with heavy, ritualized pressure.",
        "move_sources": ["natural", "divine"],
        "moods": ["calm", "humanoid"],
    },
    "Ritual": {
        "summary": "Boss rooted in ceremony, marks, and repeated sigil logic.",
        "move_sources": ["magical", "minion"],
        "moods": ["wise", "angry"],
    },
}

PALETTES = {
    "dark_natural": {
        "description": "More dark colors and more natural colors.",
        "colors": ["#1c1c1a", "#4a3b2a", "#5f4f2a", "#2d4a3d", "#7a5a3d"],
    },
    "bright_divine": {
        "description": "Very light and bright colors or very dark and blackish colors.",
        "colors": ["#f4f1d0", "#d7f6ff", "#f9d8ff", "#c6ffeb", "#2a2a2a"],
    },
    "accented_base": {
        "description": "Base colors with one focused accent color such as purple, blue, green, or red.",
        "colors": ["#2d2d36", "#4d5d8a", "#2a6f5e", "#6f3b7a", "#8b2d2d"],
    },
    "red_white": {
        "description": "Strong red and white visual language.",
        "colors": ["#f1f1f1", "#ff2d2d", "#d83333", "#ffffff", "#8a1414"],
    },
    "rotted_disordered": {
        "description": "Rotten, disorted, or unstable color combinations.",
        "colors": ["#423326", "#564a32", "#4b3c3c", "#29432f", "#5d3b44"],
    },
}

SILHOUETTES = {
    "beast": {
        "description": "Usually a monster or beast silhouette.",
        "traits": ["massive frame", "clawed limbs", "horned crown", "fanged face"],
    },
    "divine": {
        "description": "Normally a strange godly, divine, or demonic silhouette.",
        "traits": ["ringed halo", "split wings", "broken crown", "mirror face"],
    },
    "trinket": {
        "description": "A normal shape with one extra trinket or item.",
        "traits": ["floating relic", "orbital charm", "chain sigil", "spiked halo"],
    },
    "defaulted": {
        "description": "Usually a default abstract humanoid with an added item.",
        "traits": ["humanoid core", "belt of shards", "armored shoulders", "extra limb"],
    },
    "minion_fitted": {
        "description": "Any design that matches a minion theme and can include an extra item.",
        "traits": ["swarm-linked body", "attached drones", "cradle of eyes", "wisp core"],
    },
}

MOVE_SOURCES = {
    "natural": {
        "description": "Natural attacks: scratches, slams, breath, or mythological beast abuse.",
        "families": ["claw swipes", "stomp slam", "breath cone", "body slam"],
    },
    "divine": {
        "description": "Divine or demonic abilities like holy beams or ritual hazards.",
        "families": ["radiant sigils", "sunder beam", "halo pulse", "judgement arc"],
    },
    "magical": {
        "description": "Magical moves like teleportation, illusions, and spellcraft.",
        "families": ["blink step", "illusion clone", "teleport burst", "hex field"],
    },
    "laser": {
        "description": "Red laser, red dots, red hazards, timing patterns, and precise pressure.",
        "families": ["red sweep", "laser fan", "orbiting dots", "tracking line"],
    },
    "minion": {
        "description": "Minion-driven abilities, support attacks, and projectile storms.",
        "families": ["hive burst", "summon wave", "spawner ring", "minion support"],
    },
}

MOODS = {
    "wild": {
        "description": "Wild and animal-like.",
        "intro": ["The land itself is hungry.", "You are in the path of a predator."],
        "phase": ["It snaps at the rhythm of your footsteps.", "The beast is learning your timing."],
        "victory": ["The hunt ends here.", "You survived the storm of teeth."],
        "defeat": ["The wilderness claimed another soul.", "You were not quick enough."],
    },
    "calm": {
        "description": "Calm, angelic, or serene but threatening.",
        "intro": ["Silence falls when it looks at you.", "Its gaze is older than the arena."],
        "phase": ["The calm begins to bend.", "Even stillness can become a weapon."],
        "victory": ["The heavens are not impressed.", "A calm end is still an end."],
        "defeat": ["You were too loud for the quiet.", "It never moved, and still you lost."],
    },
    "joyful": {
        "description": "Playful, cheerful, or almost delighted in violence.",
        "intro": ["It laughs before the first strike.", "Your fear amuses it."],
        "phase": ["The smile gets sharper.", "It begins to dance around your mistakes."],
        "victory": ["A grin, then a collapse.", "Even joy can become cruel."],
        "defeat": ["The laughter never stopped.", "It enjoyed seeing you fail."],
    },
    "humanoid": {
        "description": "Human-like, grounded, and emotionally readable.",
        "intro": ["It speaks in the language of control.", "You are being judged in real time."],
        "phase": ["The tone turns brittle.", "Its patience is running out."],
        "victory": ["The judgment is complete.", "The final verdict is yours."],
        "defeat": ["You were measured and found lacking.", "It expected more from you."],
    },
    "insane": {
        "description": "Crazy, unstable, or intensely chaotic and intelligent.",
        "intro": ["The world bends around its thoughts.", "It speaks like a broken prophecy."],
        "phase": ["A thought fractures into a storm.", "Its patterns collapse into noise."],
        "victory": ["The noise finally stops.", "The last idea was yours."],
        "defeat": ["The idea escaped you.", "Chaos closed around your rhythm."],
    },
    "angry": {
        "description": "Visibly hostile and furious.",
        "intro": ["It is already enraged by your presence.", "Its wrath is immediate and heavy."],
        "phase": ["Its rage grows sharper.", "The floor trembles with anger."],
        "victory": ["The fury has no voice left.", "The chamber is silent again."],
        "defeat": ["Rage was stronger than precision.", "Its fury outlasted your movement."],
    },
    "wise": {
        "description": "Ancient, patient, and eerily knowledgeable.",
        "intro": ["It studies your steps before acting.", "This feeling is older than you."],
        "phase": ["It teaches the pattern by force.", "A lesson becomes a hazard."],
        "victory": ["Knowledge was not enough.", "You earned the right to leave."],
        "defeat": ["Some lessons are not survivable.", "Wisdom was never fair."],
    },
}

NAME_PREFIXES = [
    "Ash",
    "Hollow",
    "Thorn",
    "Iron",
    "Lantern",
    "Prism",
    "Void",
    "Warden",
    "Pale",
    "Red",
    "Aether",
    "Glass",
    "Bone",
    "Moon",
    "Feral",
    "Raven",
    "Ember",
    "Storm",
    "Brass",
    "Pyre",
]

NAME_SUFFIXES = [
    "Warden",
    "Reaver",
    "Singer",
    "Sentinel",
    "Oracle",
    "Hunter",
    "Howler",
    "Ascendant",
    "Leviathan",
    "Chariot",
    "Caller",
    "Maw",
    "Throne",
    "Bloom",
    "Glass",
    "Sovereign",
    "Harrow",
    "Priest",
    "Eclipse",
    "Ruin",
]


@dataclass
class BossIdea:
    """A high-level boss concept that can later be converted into a game boss."""

    name: str
    archetype: str
    palette: str
    silhouette: str
    move_source: str
    mood: str
    color_theme: List[str] = field(default_factory=list)
    visual_description: str = ""
    move_families: List[str] = field(default_factory=list)
    intro_line: str = ""
    phase_lines: List[str] = field(default_factory=list)
    victory_line: str = ""
    defeat_line: str = ""
    difficulty: int = 3
    boss_hp: int = 1200
    phase_count: int = 2
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _pick_mood(archetype: str, preferred: Optional[List[str]] = None) -> str:
    options = preferred or ARCHETYPES[archetype]["moods"]
    return random.choice(options)


def _pick_move_source(archetype: str, preferred: Optional[List[str]] = None) -> str:
    options = preferred or ARCHETYPES[archetype]["move_sources"]
    return random.choice(options)


def _pick_palette() -> str:
    return random.choice(list(PALETTES.keys()))


def _pick_silhouette() -> str:
    return random.choice(list(SILHOUETTES.keys()))


def _pick_name(archetype: str) -> str:
    prefix = random.choice(NAME_PREFIXES)
    suffix = random.choice(NAME_SUFFIXES)
    if random.random() < 0.5:
        return f"{prefix} {suffix}"
    return f"{archetype} {suffix}"


def _difficulty_bias(difficulty: Optional[int] = None) -> int:
    if difficulty is None:
        difficulty = random.randint(1, 5)
    return max(1, min(5, difficulty))


def _generate_visual_description(archetype: str, palette_name: str, silhouette_name: str) -> str:
    palette = PALETTES[palette_name]
    silhouette = SILHOUETTES[silhouette_name]
    archetype_info = ARCHETYPES[archetype]
    primary = random.choice(palette["colors"])
    accent = random.choice(palette["colors"])
    trait = random.choice(silhouette["traits"])
    return (
        f"{archetype_info['summary']} "
        f"Palette: {palette['description']}. "
        f"Silhouette: {silhouette['description']}. "
        f"Key feature: {trait}. "
        f"Main colors are {primary} and {accent}."
    )


def _generate_move_families(move_source: str, archetype: str) -> List[str]:
    source = MOVE_SOURCES[move_source]
    families = list(source["families"])
    if random.random() < 0.35:
        families.append(random.choice(ARCHETYPES[archetype]["move_sources"]))
    return families[:4]


def _generate_phase_lines(mood: str) -> List[str]:
    mood_data = MOODS[mood]
    return [random.choice(mood_data["phase"]) for _ in range(2)]


def generate_boss_idea(
    archetype: Optional[str] = None,
    palette: Optional[str] = None,
    silhouette: Optional[str] = None,
    move_source: Optional[str] = None,
    mood: Optional[str] = None,
    difficulty: Optional[int] = None,
) -> BossIdea:
    """Create a single boss concept for the game.

    This is a concept generator only. It does not decide exact attack timing,
    hitboxes, or the exact boss battle code. That logic stays in the game.
    """

    chosen_archetype = archetype or random.choice(list(ARCHETYPES.keys()))
    chosen_palette = palette or _pick_palette()
    chosen_silhouette = silhouette or _pick_silhouette()
    chosen_move_source = move_source or _pick_move_source(chosen_archetype)
    chosen_mood = mood or _pick_mood(chosen_archetype)
    difficulty_level = _difficulty_bias(difficulty)

    palette_data = PALETTES[chosen_palette]
    mood_data = MOODS[chosen_mood]
    name = _pick_name(chosen_archetype)

    boss = BossIdea(
        name=name,
        archetype=chosen_archetype,
        palette=chosen_palette,
        silhouette=chosen_silhouette,
        move_source=chosen_move_source,
        mood=chosen_mood,
        color_theme=palette_data["colors"],
        visual_description=_generate_visual_description(chosen_archetype, chosen_palette, chosen_silhouette),
        move_families=_generate_move_families(chosen_move_source, chosen_archetype),
        intro_line=random.choice(mood_data["intro"]),
        phase_lines=_generate_phase_lines(chosen_mood),
        victory_line=random.choice(mood_data["victory"]),
        defeat_line=random.choice(mood_data["defeat"]),
        difficulty=difficulty_level,
        boss_hp=1200,
        phase_count=max(2, min(5, difficulty_level + 1)),
        notes=[
            f"Base HP matches Greeter baseline: {1200}.",
            f"Theme: {ARCHETYPES[chosen_archetype]['summary']}",
            f"Move source: {MOVE_SOURCES[chosen_move_source]['description']}",
        ],
    )
    return boss


def generate_boss_pack(count: int = 3) -> List[BossIdea]:
    """Create a small pack of boss ideas for quick brainstorming."""
    return [generate_boss_idea() for _ in range(max(1, count))]


if __name__ == "__main__":
    sample = generate_boss_idea()
    print(sample.name)
    print(sample.archetype, sample.palette, sample.silhouette)
    print(sample.visual_description)
    print("Move families:", ", ".join(sample.move_families))
    print("Intro:", sample.intro_line)
    print("Phase lines:", sample.phase_lines)
    print("Difficulty:", sample.difficulty)
    print("HP:", sample.boss_hp)
