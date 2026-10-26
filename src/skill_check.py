"""
RPG-08-06: Skill Check System
Core dice-roll mechanics for skill checks, attack rolls, and saving throws.
Integrates with character attributes and skill tree effects.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from skill_tree import SkillNode

# ---------------------------------------------------------------------------
# Dice
# ---------------------------------------------------------------------------

def roll_dice(count: int = 1, sides: int = 20) -> list[int]:
    """Roll `count` dice with `sides` sides and return individual results."""
    return [random.randint(1, sides) for _ in range(count)]

def roll_d20() -> int:
    """Roll a single d20."""
    return random.randint(1, 20)

# ---------------------------------------------------------------------------
# Enums / Constants
# ---------------------------------------------------------------------------

class DifficultyClass:
    """Common DC presets."""
    VERY_EASY = 5
    EASY = 10
    MEDIUM = 15
    HARD = 20
    VERY_HARD = 25
    NEARLY_IMPOSSIBLE = 30

# ---------------------------------------------------------------------------
# Modifier Resolution
# ---------------------------------------------------------------------------

@dataclass
class SkillCheckContext:
    """
    All the ingredients needed to resolve a skill check.

    Attributes:
        character_id   : who is making the check
        skill_id       : optional skill tree node id (e.g. "thc.root") used to
                         look up effect-based bonuses
        base_attribute : primary attribute driving the check (e.g. "strength")
        misc_bonus     : flat additive bonus (magic items, temp buffs, etc.)
        advantage      : +1 die, take higher
        disadvantage   : +1 die, take lower
    """
    character_id: str
    base_attribute: str = "strength"
    skill_id: str | None = None
    misc_bonus: int = 0
    advantage: int = 0       # number of advantage dice (usually 0 or 1)
    disadvantage: int = 0    # number of disadvantage dice (usually 0 or 1)

@dataclass
class SkillCheckResult:
    """Outcome of a single skill check."""
    success: bool
    total: int
    dice: list[int]
    modifier_total: int
    dc: int
    critical_success: bool = False
    critical_failure: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "total": self.total,
            "dice": self.dice,
            "modifier_total": self.modifier_total,
            "dc": self.dc,
            "critical_success": self.critical_success,
            "critical_failure": self.critical_failure,
        }

# ---------------------------------------------------------------------------
# Resolver (stateless)
# ---------------------------------------------------------------------------

class SkillCheckResolver:
    """
    Resolves skill checks given a character's attributes and skill tree state.
    This class is intentionally stateless so it can be reused across combat,
    dialogue, and exploration contexts.
    """

    def __init__(self, trees: dict[str, Any] | None = None) -> None:
        # lazily loaded by consumers; not required for basic attribute checks
        self.trees: dict[str, Any] = trees or {}

    # --- public API ---------------------------------------------------------

    def resolve(
        self,
        context: SkillCheckContext,
        character_attributes: dict[str, int],
        skill_ranks: dict[str, int] | None = None,
        dc: int = DifficultyClass.MEDIUM,
        dc_modifier: int = 0,
    ) -> SkillCheckResult:
        """
        Compute the result of a skill check.

        Args:
            context             : check parameters
            character_attributes: e.g. {"strength": 16, "dexterity": 14}
            skill_ranks         : node_id -> rank mapping from skill trees
            dc                  : target number to meet or exceed
            dc_modifier         : flat modifier added to DC (from difficulty)

        Returns:
            SkillCheckResult with success flag, totals, and crit info.
        """
        skill_ranks = skill_ranks or {}

        # 1. Attribute modifier (D&D-style: (score - 10) // 2)
        attr_score = character_attributes.get(context.base_attribute, 10)
        attr_mod = (attr_score - 10) // 2

        # 2. Skill bonus from skill tree effects
        skill_bonus = self._resolve_skill_bonus(context.skill_id, skill_ranks)

        # 3. Proficient bonus: assume proficiency if skill rank > 0
        proficient = context.skill_id is not None and skill_ranks.get(context.skill_id, 0) > 0
        prof_bonus = 2 if proficient else 0

        # 4. Total modifier
        modifier_total = attr_mod + skill_bonus + prof_bonus + context.misc_bonus

        # 5. Dice rolls with advantage/disadvantage
        dice_count = 1 + context.advantage + context.disadvantage
        dice = roll_dice(count=dice_count, sides=20)

        if context.advantage > context.disadvantage:
            best = max(dice)
        elif context.disadvantage > context.advantage:
            best = min(dice)
        else:
            best = dice[0]

        # 6. Crits (natural 1 / natural 20)
        crit_success = best == 20
        crit_failure = best == 1

        total = best + modifier_total
        effective_dc = dc + dc_modifier
        success = total >= effective_dc

        # Natural 1 always fails, natural 20 always succeeds
        if crit_success:
            success = True
        if crit_failure:
            success = False

        return SkillCheckResult(
            success=success,
            total=total,
            dice=dice,
            modifier_total=modifier_total,
            dc=effective_dc,
            critical_success=crit_success,
            critical_failure=crit_failure,
        )

    # --- helpers ------------------------------------------------------------

    def _resolve_skill_bonus(self, skill_id: str | None, skill_ranks: dict[str, int]) -> int:
        """
        Sum numeric effect values from the skill tree that look like flat
        check bonuses. Convention: keys containing 'check', 'bonus', or
        'modifier' count, except combat/damage-specific keys like
        'damage_bonus', 'weapon_damage_bonus', 'armor_penetration'.
        """
        if not skill_id:
            return 0
        node = self._find_node(skill_id)
        if not node:
            return 0
        bonus = 0
        rank = skill_ranks.get(skill_id, 0)
        for key, value in node.effects.items():
            lower = key.lower()
            if not any(tag in lower for tag in ("check", "bonus", "modifier")):
                continue
            if any(exclude in lower for exclude in ("damage", "weapon", "armor", "aoe", "critical", "stun", "penetration")):
                continue
            if isinstance(value, (int, float)):
                bonus += int(value * rank)
        return bonus

    def _find_node(self, skill_id: str) -> SkillNode | None:
        """Search across all loaded trees for a node with the given id."""
        for tree in self.trees.values():
            node = tree.get_node(skill_id)
            if node:
                return node
        return None

# ---------------------------------------------------------------------------
# Combat Integration
# ---------------------------------------------------------------------------

@dataclass
class AttackRollContext(SkillCheckContext):
    """
    Extends SkillCheckContext with combat-specific fields.

    Attributes:
        target_ac        : Armor Class to beat
        weapon_die       : damage dice expression (e.g. 8 for d8)
        damage_bonus     : extra flat damage added after the hit
        crit_range       : minimum natural roll that counts as a crit (default 20)
    """
    target_ac: int = 10
    weapon_die: int = 6
    damage_bonus: int = 0
    crit_range: int = 20

@dataclass
class AttackRollResult:
    """Outcome of an attack roll, including damage on a hit."""
    hit: bool
    attack_total: int
    damage: int
    dice: list[int]
    modifier_total: int
    ac: int
    crit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "hit": self.hit,
            "attack_total": self.attack_total,
            "damage": self.damage,
            "dice": self.dice,
            "modifier_total": self.modifier_total,
            "ac": self.ac,
            "crit": self.crit,
        }

class CombatResolver:
    """
    Wraps SkillCheckResolver with attack-roll and damage logic.
    """

    def __init__(self, resolver: SkillCheckResolver | None = None) -> None:
        self.resolver = resolver or SkillCheckResolver()

    def attack(
        self,
        context: AttackRollContext,
        character_attributes: dict[str, int],
        skill_ranks: dict[str, int] | None = None,
        damage_dealt_multiplier: float = 1.0,
    ) -> AttackRollResult:
        skill_ranks = skill_ranks or {}

        # Resolve attack roll as a skill check against the target AC
        check = self.resolver.resolve(
            context=context,
            character_attributes=character_attributes,
            skill_ranks=skill_ranks,
            dc=context.target_ac,
        )

        # Damage roll
        damage_dice = roll_dice(count=1, sides=context.weapon_die)
        base_damage = damage_dice[0]
        total_damage = base_damage + context.damage_bonus + check.modifier_total

        # Double damage on crit (simplified: add another weapon die)
        if check.critical_success:
            extra = roll_dice(count=1, sides=context.weapon_die)[0]
            total_damage += extra

        total_damage = int(total_damage * damage_dealt_multiplier)

        return AttackRollResult(
            hit=check.success,
            attack_total=check.total,
            damage=total_damage,
            dice=check.dice,
            modifier_total=check.modifier_total,
            ac=context.target_ac,
            crit=check.critical_success,
        )
