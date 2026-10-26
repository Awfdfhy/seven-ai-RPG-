"""
RPG-08-08: Status Conditions System
Core data model for status conditions including buffs, debuffs,
poison, stun, and other timed effects. Supports stacking, ticking,
and stat modification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StatusConditionType(Enum):
    """
    Broad category of status effect.
    """

    BUFF = "buff"
    DEBUFF = "debuff"
    POISON = "poison"
    STUN = "stun"
    BURN = "burn"
    FREEZE = "freeze"
    PARALYZE = "paralyze"
    HEAL_OVER_TIME = "heal_over_time"
    DAMAGE_OVER_TIME = "damage_over_time"
    SHIELD = "shield"
    ROOT = "root"
    SILENCE = "silence"
    INVISIBLE = "invisible"
    BLIND = "blind"


class StatOperator(Enum):
    """
    How a status condition modifies a stat.
    """

    ADD = "add"
    MULTIPLY = "multiply"
    SET = "set"
    OVERRIDE = "override"


@dataclass
class StatusConditionEffect:
    """
    A single numeric effect a status condition applies to a stat or value.
    """

    stat: str = ""
    value: float = 0.0
    operator: StatOperator = StatOperator.ADD
    tick_value: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stat": self.stat,
            "value": self.value,
            "operator": self.operator.value,
            "tick_value": self.tick_value,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StatusConditionEffect:
        return StatusConditionEffect(
            stat=data.get("stat", ""),
            value=data.get("value", 0.0),
            operator=StatOperator(data.get("operator", "add")),
            tick_value=data.get("tick_value", 0.0),
        )


@dataclass
class StatusCondition:
    """
    Definition of a status condition type (the blueprint).
    This is shared across characters.
    """

    id: str
    name: str
    condition_type: StatusConditionType = StatusConditionType.DEBUFF
    description: str = ""
    duration_seconds: float = 0.0
    max_stacks: int = 1
    effects: list[StatusConditionEffect] = field(default_factory=list)
    tick_interval_seconds: float = 0.0
    can_be_cleansed: bool = True
    prevents_actions: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "condition_type": self.condition_type.value,
            "description": self.description,
            "duration_seconds": self.duration_seconds,
            "max_stacks": self.max_stacks,
            "effects": [e.to_dict() for e in self.effects],
            "tick_interval_seconds": self.tick_interval_seconds,
            "can_be_cleansed": self.can_be_cleansed,
            "prevents_actions": self.prevents_actions,
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StatusCondition:
        return StatusCondition(
            id=data["id"],
            name=data["name"],
            condition_type=StatusConditionType(data.get("condition_type", "debuff")),
            description=data.get("description", ""),
            duration_seconds=data.get("duration_seconds", 0.0),
            max_stacks=data.get("max_stacks", 1),
            effects=[StatusConditionEffect.from_dict(e) for e in data.get("effects", [])],
            tick_interval_seconds=data.get("tick_interval_seconds", 0.0),
            can_be_cleansed=data.get("can_be_cleansed", True),
            prevents_actions=data.get("prevents_actions", False),
            extra=data.get("extra", {}),
        )


@dataclass
class ActiveStatusCondition:
    """
    A running instance of a status condition on a specific character.
    """

    condition_id: str
    character_id: str
    stacks: int = 1
    remaining_duration: float = 0.0
    applied_at: float = 0.0
    last_tick_at: float = 0.0
    source_ability_id: str = ""
    source_character_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, current_time: float) -> bool:
        return self.remaining_duration <= 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "character_id": self.character_id,
            "stacks": self.stacks,
            "remaining_duration": self.remaining_duration,
            "applied_at": self.applied_at,
            "last_tick_at": self.last_tick_at,
            "source_ability_id": self.source_ability_id,
            "source_character_id": self.source_character_id,
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ActiveStatusCondition:
        return ActiveStatusCondition(
            condition_id=data["condition_id"],
            character_id=data["character_id"],
            stacks=data.get("stacks", 1),
            remaining_duration=data.get("remaining_duration", 0.0),
            applied_at=data.get("applied_at", 0.0),
            last_tick_at=data.get("last_tick_at", 0.0),
            source_ability_id=data.get("source_ability_id", ""),
            source_character_id=data.get("source_character_id", ""),
            extra=data.get("extra", {}),
        )


@dataclass
class StatusConditionTickResult:
    """
    Outcome of a single tick for one active condition.
    """

    condition_id: str
    character_id: str
    damage: float = 0.0
    healing: float = 0.0
    expired: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "character_id": self.character_id,
            "damage": self.damage,
            "healing": self.healing,
            "expired": self.expired,
        }
