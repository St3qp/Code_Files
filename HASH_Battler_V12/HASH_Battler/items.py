"""Item configuration: validation and level-scaled Lance combat parameters."""
from dataclasses import dataclass, field

STATS = ('Damage', 'Attack Speed', 'Effect Power', 'Knockback', 'Reach', 'Dash Speed')
ELEMENTS = ('Fire', 'Thunder', 'Ice', 'Poison', 'Air')
POINT_BUDGET = 10
MAX_PER_STAT = 7


@dataclass
class ItemBuild:
    name: str = 'Lance'
    element: str = 'Fire'
    stats: dict = field(default_factory=lambda: {key: 0 for key in STATS})

    @property
    def spent(self):
        return sum(self.stats.values())

    @property
    def remaining(self):
        return POINT_BUDGET - self.spent

    def change(self, stat, amount):
        if stat not in STATS or amount not in (-1, 1):
            return False
        value = self.stats[stat] + amount
        if value < 0 or value > MAX_PER_STAT or self.spent + amount > POINT_BUDGET:
            return False
        self.stats[stat] = value
        return True

    def set_element(self, element):
        if element not in ELEMENTS:
            return False
        self.element = element
        return True

    def valid(self):
        return self.name == 'Lance' and self.element in ELEMENTS and self.spent == POINT_BUDGET and all(
            type(self.stats.get(key)) is int and 0 <= self.stats[key] <= MAX_PER_STAT
            for key in STATS
        ) and set(self.stats) == set(STATS)

    def to_dict(self):
        return {'name': self.name, 'element': self.element, 'stats': dict(self.stats)}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            return cls()
        try:
            old_stats = value.get('stats', {})
            if not isinstance(old_stats, dict):
                old_stats = {}
            migrated = dict(old_stats)
            if 'Reach' not in migrated and 'Range' in migrated:
                migrated['Reach'] = migrated['Range']
            if 'Dash Speed' not in migrated and 'Projectile Speed' in migrated:
                migrated['Dash Speed'] = migrated['Projectile Speed']
            candidate = cls(name=value.get('name', 'Lance'),
                            element=value.get('element', 'Fire'),
                            stats={key: migrated.get(key, 0) for key in STATS})
            if (candidate.name != 'Lance' or candidate.element not in ELEMENTS or
                    any(type(number) is not int or number < 0 or number > MAX_PER_STAT
                        for number in candidate.stats.values()) or candidate.spent > POINT_BUDGET):
                return cls()
            return candidate
        except (TypeError, AttributeError):
            return cls()

    def lance_stats(self):
        """Combat values for the melee dash-strike Lance."""
        s = self.stats
        return {
            'damage': 26 + 7*s['Damage'],
            'cooldown': max(.55, 2.35/(1 + .17*s['Attack Speed'])),
            'reach': 175 + 23*s['Reach'],
            'dash_distance': 130,
            'dash_duration': max(.075, .18/(1 + .14*s['Dash Speed'])),
            'knockback': 32 + 18*s['Knockback'],
            'effect_power': s['Effect Power'],
        }
