"""
RPG-XX: Character Progression System
Tracks experience points, level thresholds, stat increases,
and skill unlocks tied to character level.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LevelThreshold:
    """
    XP required to advance into a given level.
    """

    level: int
    xp_required: int

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "xp_required": self.xp_required}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LevelThreshold:
        return LevelThreshold(level=data["level"], xp_required=data["xp_required"])


@dataclass
class StatGrowth:
    """
    Defines how a character's attributes increase on level up.
    """

    attribute: str
    amount_per_level: int

    def to_dict(self) -> dict[str, Any]:
        return {"attribute": self.attribute, "amount_per_level": self.amount_per_level}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StatGrowth:
        return StatGrowth(
            attribute=data["attribute"], amount_per_level=data["amount_per_level"]
        )


@dataclass
class LevelUnlock:
    """
    A skill or ability node that becomes available (or is auto-unlocked)
    when a character reaches a specific level.
    """

    level: int
    node_id: str
    tree_id: str
    auto_unlock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "node_id": self.node_id,
            "tree_id": self.tree_id,
            "auto_unlock": self.auto_unlock,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LevelUnlock:
        return LevelUnlock(
            level=data["level"],
            node_id=data["node_id"],
            tree_id=data["tree_id"],
            auto_unlock=data.get("auto_unlock", False),
        )


@dataclass
class CharacterProgressionState:
    """
    Tracks a character's progression independent of skill/ability state.
    """

    character_id: str
    experience: int = 0
    level: int = 1
    unspent_stat_points: int = 0
    unspent_skill_points: int = 0
    unspent_ability_points: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "experience": self.experience,
            "level": self.level,
            "unspent_stat_points": self.unspent_stat_points,
            "unspent_skill_points": self.unspent_skill_points,
            "unspent_ability_points": self.unspent_ability_points,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CharacterProgressionState:
        return CharacterProgressionState(
            character_id=data["character_id"],
            experience=data.get("experience", 0),
            level=data.get("level", 1),
            unspent_stat_points=data.get("unspent_stat_points", 0),
            unspent_skill_points=data.get("unspent_skill_points", 0),
            unspent_ability_points=data.get("unspent_ability_points", 0),
        )


class ProgressionSystem:
    """
    Holds global progression configuration: XP curve, stat growth rules,
    and level-based unlock definitions.
    """

    def __init__(
        self,
        thresholds: list[LevelThreshold] | None = None,
        stat_growth: list[StatGrowth] | None = None,
        level_unlocks: list[LevelUnlock] | None = None,
        xp_per_level_base: int = 100,
        xp_per_level_multiplier: float = 1.5,
        skill_points_per_level: int = 1,
        ability_points_per_level: int = 1,
        stat_points_per_level: int = 1,
    ) -> None:
        self.thresholds = {t.level: t for t in (thresholds or [])}
        self.stat_growth = {s.attribute: s for s in (stat_growth or [])}
        self.level_unlocks: dict[int, list[LevelUnlock]] = {}
        for unlock in level_unlocks or []:
            self.level_unlocks.setdefault(unlock.level, []).append(unlock)

        self.xp_per_level_base = xp_per_level_base
        self.xp_per_level_multiplier = xp_per_level_multiplier
        self.skill_points_per_level = skill_points_per_level
        self.ability_points_per_level = ability_points_per_level
        self.stat_points_per_level = stat_points_per_level
        self._character_states: dict[str, CharacterProgressionState] = {}

    def xp_for_level(self, level: int) -> int:
        """
        XP required to reach `level` from `level - 1`.
        Falls back to an exponential curve if no explicit threshold is set.
        """
        if level in self.thresholds:
            return self.thresholds[level].xp_required
        if level <= 1:
            return 0
        return int(self.xp_per_level_base * (self.xp_per_level_multiplier ** (level - 1)))

    def total_xp_for_level(self, level: int) -> int:
        """
        Cumulative XP needed to reach `level` starting from 1.
        """
        total = 0
        for lvl in range(2, level + 1):
            total += self.xp_for_level(lvl)
        return total

    def stat_gain_for(self, attribute: str) -> int:
        return self.stat_growth.get(attribute, StatGrowth(attribute=attribute, amount_per_level=0)).amount_per_level

    def add_threshold(self, threshold: LevelThreshold) -> None:
        self.thresholds[threshold.level] = threshold

    def add_stat_growth(self, growth: StatGrowth) -> None:
        self.stat_growth[growth.attribute] = growth

    def add_level_unlock(self, unlock: LevelUnlock) -> None:
        self.level_unlocks.setdefault(unlock.level, []).append(unlock)

    def get_or_create_state(self, character_id: str) -> CharacterProgressionState:
        if character_id not in self._character_states:
            self._character_states[character_id] = CharacterProgressionState(character_id=character_id)
        return self._character_states[character_id]

    def process_xp(self, character_id: str, added_xp: int) -> list[dict[str, Any]]:
        """Add XP and process level-ups. Returns list of level-up reports."""
        state = self.get_or_create_state(character_id)
        state.experience += added_xp
        levelups: list[dict[str, Any]] = []
        while True:
            next_level = state.level + 1
            needed = self.xp_for_level(next_level)
            if state.experience < needed:
                break
            state.experience -= needed
            state.level += 1
            state.unspent_skill_points += self.skill_points_per_level
            state.unspent_ability_points += self.ability_points_per_level
            state.unspent_stat_points += self.stat_points_per_level
            levelups.append({
                "new_level": state.level,
                "skill_points_gained": self.skill_points_per_level,
                "ability_points_gained": self.ability_points_per_level,
                "stat_points_gained": self.stat_points_per_level,
            })
        return levelups

    def to_dict(self) -> dict[str, Any]:
        return {
            "thresholds": [t.to_dict() for t in self.thresholds.values()],
            "stat_growth": [s.to_dict() for s in self.stat_growth.values()],
            "level_unlocks": [
                u.to_dict()
                for unlocks in self.level_unlocks.values()
                for u in unlocks
            ],
            "xp_per_level_base": self.xp_per_level_base,
            "xp_per_level_multiplier": self.xp_per_level_multiplier,
            "skill_points_per_level": self.skill_points_per_level,
            "ability_points_per_level": self.ability_points_per_level,
            "stat_points_per_level": self.stat_points_per_level,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ProgressionSystem:
        thresholds = [LevelThreshold.from_dict(t) for t in data.get("thresholds", [])]
        stat_growth = [StatGrowth.from_dict(s) for s in data.get("stat_growth", [])]
        level_unlocks = [LevelUnlock.from_dict(u) for u in data.get("level_unlocks", [])]
        return ProgressionSystem(
            thresholds=thresholds,
            stat_growth=stat_growth,
            level_unlocks=level_unlocks,
            xp_per_level_base=data.get("xp_per_level_base", 100),
            xp_per_level_multiplier=data.get("xp_per_level_multiplier", 1.5),
            skill_points_per_level=data.get("skill_points_per_level", 1),
            ability_points_per_level=data.get("ability_points_per_level", 1),
            stat_points_per_level=data.get("stat_points_per_level", 1),
        )
