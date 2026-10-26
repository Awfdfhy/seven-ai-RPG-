"""
RPG-10-10: Difficulty Integration Helpers
Convenience functions and wrapper classes that apply DifficultySettings
and AccessibilitySettings to existing game systems.
"""

from __future__ import annotations

from typing import Any

from difficulty_settings import DifficultySettings
from loot import LootManager
from skill_check import CombatResolver, SkillCheckResolver
from status_manager import StatusManager

# ---------------------------------------------------------------------------
# Skill checks / combat
# ---------------------------------------------------------------------------

class DifficultyAwareSkillResolver(SkillCheckResolver):
    """
    Extends SkillCheckResolver to automatically apply dc_modifier
    from difficulty settings when resolving checks.
    """

    def __init__(self, settings: DifficultySettings | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings = settings or DifficultySettings()

    def resolve(
        self,
        context: Any,
        character_attributes: dict[str, int],
        skill_ranks: dict[str, int] | None = None,
        dc: int = None,
    ) -> Any:
        if dc is None:
            from skill_check import DifficultyClass
            dc = DifficultyClass.MEDIUM
        return super().resolve(
            context=context,
            character_attributes=character_attributes,
            skill_ranks=skill_ranks,
            dc=dc,
            dc_modifier=self.settings.dc_modifier,
        )


class DifficultyAwareCombatResolver(CombatResolver):
    """
    Extends CombatResolver to apply damage_dealt_multiplier
    from difficulty settings.
    """

    def __init__(self, settings: DifficultySettings | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings = settings or DifficultySettings()

    def attack(
        self,
        context: Any,
        character_attributes: dict[str, int],
        skill_ranks: dict[str, int] | None = None,
    ) -> Any:
        return super().attack(
            context=context,
            character_attributes=character_attributes,
            skill_ranks=skill_ranks,
            damage_dealt_multiplier=self.settings.damage_dealt_multiplier,
        )


# ---------------------------------------------------------------------------
# Progression
# ---------------------------------------------------------------------------

def apply_xp_multiplier(base_xp: int, settings: DifficultySettings) -> int:
    """
    Apply the difficulty XP multiplier to a base XP reward.
    """
    return int(base_xp * settings.xp_multiplier)


def adjusted_xp_for_level(system: Any, level: int, settings: DifficultySettings) -> int:
    """
    Return the XP required for `level`, scaled by difficulty.
    Higher difficulties increase the curve; lower decrease it.
    """
    base = system.xp_for_level(level)
    return int(base * settings.xp_multiplier)


# ---------------------------------------------------------------------------
# Loot
# ---------------------------------------------------------------------------

def roll_loot_with_difficulty(
    loot_manager: LootManager,
    loot_table_id: str,
    world_id: str,
    settings: DifficultySettings,
    **kwargs: Any,
) -> Any:
    """
    Roll loot using the rarity boost from difficulty settings.
    """
    return loot_manager.roll_loot(
        loot_table_id=loot_table_id,
        world_id=world_id,
        loot_rarity_boost=settings.loot_rarity_boost,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Status conditions
# ---------------------------------------------------------------------------

def apply_status_with_difficulty(
    status_manager: StatusManager,
    character_id: str,
    condition_id: str,
    settings: DifficultySettings,
    **kwargs: Any,
) -> Any:
    """
    Apply a status condition with duration scaled by difficulty.
    """
    return status_manager.apply_condition(
        character_id=character_id,
        condition_id=condition_id,
        duration_multiplier=settings.status_duration_multiplier,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Damage / healing helpers
# ---------------------------------------------------------------------------

def apply_damage_with_difficulty(base_damage: float, settings: DifficultySettings) -> float:
    """
    Scale incoming damage by the difficulty's damage_taken_multiplier.
    """
    return base_damage * settings.damage_taken_multiplier


def apply_healing_with_difficulty(base_healing: float, settings: DifficultySettings) -> float:
    """
    Scale healing by the difficulty's healing_effectiveness_multiplier.
    """
    return base_healing * settings.healing_effectiveness_multiplier
