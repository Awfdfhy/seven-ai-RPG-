"""
RPG-12-03: Advanced Combat System
Implements combos, finishers, and tactical positioning for combat encounters.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ability import Ability, AbilityEffect
from ability_manager import AbilityManager
from status_conditions import ActiveStatusCondition, StatusCondition, StatusConditionType
from status_manager import StatusManager

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CombatPosition(Enum):
    """Tactical positions a combatant can occupy on the battlefield."""

    FRONTLINE = "frontline"
    FLANK = "flank"
    BACKLINE = "backline"
    ELEVATED = "elevated"
    GROUNDED = "grounded"
    COVER = "cover"


class ComboTier(Enum):
    """Strength of the current combo chain."""

    NONE = 0
    BASIC = 1
    ADVANCED = 2
    EXPERT = 3
    MASTER = 4


class FinisherTrigger(Enum):
    """Condition that enables a finisher."""

    LOW_HEALTH = "low_health"
    HIGH_COMBO = "high_combo"
    BEHIND_TARGET = "behind_target"
    TARGET_STUNNED = "target_stunned"
    TARGET_BURNING = "target_burning"
    SELF_LOW_HEALTH = "self_low_health"
    POSITION_ADVANTAGE = "position_advantage"


class ActionResultType(Enum):
    """Outcome category of a combat action."""

    HIT = "hit"
    MISS = "miss"
    CRITICAL = "critical"
    BLOCKED = "blocked"
    DODGED = "dodged"
    RESISTED = "resisted"


class CombatantTeam(Enum):
    """Which side a combatant fights for."""

    PLAYER = "player"
    ENEMY = "enemy"
    ALLY = "ally"


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------


@dataclass
class PositionModifier:
    """Modifiers applied by a specific battlefield position."""

    position: CombatPosition
    attack_bonus: float = 0.0
    defense_bonus: float = 0.0
    crit_chance_bonus: float = 0.0
    dodge_chance_bonus: float = 0.0
    damage_taken_multiplier: float = 1.0
    range_bonus: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": self.position.value,
            "attack_bonus": self.attack_bonus,
            "defense_bonus": self.defense_bonus,
            "crit_chance_bonus": self.crit_chance_bonus,
            "dodge_chance_bonus": self.dodge_chance_bonus,
            "damage_taken_multiplier": self.damage_taken_multiplier,
            "range_bonus": self.range_bonus,
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PositionModifier:
        return PositionModifier(
            position=CombatPosition(data.get("position", "frontline")),
            attack_bonus=data.get("attack_bonus", 0.0),
            defense_bonus=data.get("defense_bonus", 0.0),
            crit_chance_bonus=data.get("crit_chance_bonus", 0.0),
            dodge_chance_bonus=data.get("dodge_chance_bonus", 0.0),
            damage_taken_multiplier=data.get("damage_taken_multiplier", 1.0),
            range_bonus=data.get("range_bonus", 0.0),
            extra=data.get("extra", {}),
        )


@dataclass
class ComboNode:
    """
    One step in a combo chain. Defines which ability must be used and
    what ability it enables next.
    """

    combo_id: str
    sequence_index: int
    ability_id: str
    next_combo_ability_id: str | None = None
    combo_point_gain: int = 1
    required_combo_tier: ComboTier = ComboTier.BASIC
    window_seconds: float = 3.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "combo_id": self.combo_id,
            "sequence_index": self.sequence_index,
            "ability_id": self.ability_id,
            "next_combo_ability_id": self.next_combo_ability_id,
            "combo_point_gain": self.combo_point_gain,
            "required_combo_tier": self.required_combo_tier.value,
            "window_seconds": self.window_seconds,
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ComboNode:
        return ComboNode(
            combo_id=data["combo_id"],
            sequence_index=data["sequence_index"],
            ability_id=data["ability_id"],
            next_combo_ability_id=data.get("next_combo_ability_id"),
            combo_point_gain=data.get("combo_point_gain", 1),
            required_combo_tier=ComboTier(data.get("required_combo_tier", 1)),
            window_seconds=data.get("window_seconds", 3.0),
            extra=data.get("extra", {}),
        )


@dataclass
class FinisherDefinition:
    """
    Definition of a finisher ability: what it requires and what it does.
    """

    ability_id: str
    name: str
    description: str = ""
    triggers: list[FinisherTrigger] = field(default_factory=list)
    combo_points_required: int = 0
    positional_requirements: list[CombatPosition] = field(default_factory=list)
    target_health_max_percent: float = 100.0
    target_health_min_percent: float = 0.0
    effects: list[AbilityEffect] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ability_id": self.ability_id,
            "name": self.name,
            "description": self.description,
            "triggers": [t.value for t in self.triggers],
            "combo_points_required": self.combo_points_required,
            "positional_requirements": [p.value for p in self.positional_requirements],
            "target_health_max_percent": self.target_health_max_percent,
            "target_health_min_percent": self.target_health_min_percent,
            "effects": [e.to_dict() for e in self.effects],
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> FinisherDefinition:
        return FinisherDefinition(
            ability_id=data["ability_id"],
            name=data["name"],
            description=data.get("description", ""),
            triggers=[FinisherTrigger(t) for t in data.get("triggers", [])],
            combo_points_required=data.get("combo_points_required", 0),
            positional_requirements=[CombatPosition(p) for p in data.get("positional_requirements", [])],
            target_health_max_percent=data.get("target_health_max_percent", 100.0),
            target_health_min_percent=data.get("target_health_min_percent", 0.0),
            effects=[AbilityEffect.from_dict(e) for e in data.get("effects", [])],
            extra=data.get("extra", {}),
        )


@dataclass
class CombatComboState:
    """Tracks combo progress for a single combatant."""

    combatant_id: str
    active_combo_id: str | None = None
    current_step_index: int = -1
    combo_points: int = 0
    last_combo_time: float = 0.0
    combo_tier: ComboTier = ComboTier.NONE
    completed_combos: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def is_in_combo(self) -> bool:
        return self.active_combo_id is not None and self.current_step_index >= 0

    def is_combo_window_expired(self, current_time: float, window_seconds: float = 3.0) -> bool:
        if not self.is_in_combo():
            return True
        return (current_time - self.last_combo_time) > window_seconds

    def reset(self) -> None:
        self.active_combo_id = None
        self.current_step_index = -1
        self.combo_tier = ComboTier.NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "combatant_id": self.combatant_id,
            "active_combo_id": self.active_combo_id,
            "current_step_index": self.current_step_index,
            "combo_points": self.combo_points,
            "last_combo_time": self.last_combo_time,
            "combo_tier": self.combo_tier.value,
            "completed_combos": list(self.completed_combos),
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CombatComboState:
        return CombatComboState(
            combatant_id=data["combatant_id"],
            active_combo_id=data.get("active_combo_id"),
            current_step_index=data.get("current_step_index", -1),
            combo_points=data.get("combo_points", 0),
            last_combo_time=data.get("last_combo_time", 0.0),
            combo_tier=ComboTier(data.get("combo_tier", 0)),
            completed_combos=list(data.get("completed_combos", [])),
            extra=data.get("extra", {}),
        )


@dataclass
class CombatantStats:
    """Combat-relevant stats for a combatant."""

    health: int = 100
    max_health: int = 100
    attack_power: int = 10
    defense: int = 5
    crit_chance: float = 0.05
    dodge_chance: float = 0.02
    accuracy: float = 0.9
    speed: float = 1.0
    extra: dict[str, Any] = field(default_factory=dict)

    def is_alive(self) -> bool:
        return self.health > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "health": self.health,
            "max_health": self.max_health,
            "attack_power": self.attack_power,
            "defense": self.defense,
            "crit_chance": self.crit_chance,
            "dodge_chance": self.dodge_chance,
            "accuracy": self.accuracy,
            "speed": self.speed,
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CombatantStats:
        return CombatantStats(
            health=data.get("health", 100),
            max_health=data.get("max_health", 100),
            attack_power=data.get("attack_power", 10),
            defense=data.get("defense", 5),
            crit_chance=data.get("crit_chance", 0.05),
            dodge_chance=data.get("dodge_chance", 0.02),
            accuracy=data.get("accuracy", 0.9),
            speed=data.get("speed", 1.0),
            extra=data.get("extra", {}),
        )


@dataclass
class Combatant:
    """
    A participant in a combat encounter. Wraps a character or companion
    with combat-specific state.
    """

    combatant_id: str
    name: str
    team: CombatantTeam = CombatantTeam.PLAYER
    position: CombatPosition = CombatPosition.FRONTLINE
    stats: CombatantStats = field(default_factory=CombatantStats)
    status_manager: StatusManager = field(default=None)
    combo_state: CombatComboState = field(default=None)
    ability_manager: AbilityManager | None = None
    character_id: str | None = None
    companion_id: str | None = None
    behavior_flags: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status_manager is None:
            self.status_manager = StatusManager()
        if self.combo_state is None:
            self.combo_state = CombatComboState(combatant_id=self.combatant_id)

    def is_alive(self) -> bool:
        return self.stats.is_alive()

    def effective_position(self) -> CombatPosition:
        if self.position == CombatPosition.COVER:
            return CombatPosition.COVER
        if self._has_status_type(StatusConditionType.ROOT):
            return CombatPosition.GROUNDED
        if self._has_status_type(StatusConditionType.PARALYZE):
            return CombatPosition.GROUNDED
        return self.position

    def _has_status_type(self, cond_type: StatusConditionType) -> bool:
        for (cid, cond_id), active in self.status_manager.active.items():
            if cid != self.combatant_id:
                continue
            definition = self.status_manager.definitions.get(cond_id)
            if definition and definition.condition_type == cond_type:
                return True
        return False

    def has_condition_type(self, cond_type: StatusConditionType) -> bool:
        return self._has_status_type(cond_type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "combatant_id": self.combatant_id,
            "name": self.name,
            "team": self.team.value,
            "position": self.position.value,
            "stats": self.stats.to_dict(),
            "status_manager": self.status_manager.to_dict(),
            "combo_state": self.combo_state.to_dict(),
            "ability_manager": self.ability_manager.to_dict() if self.ability_manager else None,
            "character_id": self.character_id,
            "companion_id": self.companion_id,
            "behavior_flags": dict(self.behavior_flags),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Combatant:
        return Combatant(
            combatant_id=data["combatant_id"],
            name=data["name"],
            team=CombatantTeam(data.get("team", "player")),
            position=CombatPosition(data.get("position", "frontline")),
            stats=CombatantStats.from_dict(data.get("stats", {})),
            status_manager=StatusManager.from_dict(data.get("status_manager", {})),
            combo_state=CombatComboState.from_dict(data.get("combo_state", {})) if data.get("combo_state") else None,
            ability_manager=AbilityManager.from_dict(data["ability_manager"]) if data.get("ability_manager") else None,
            character_id=data.get("character_id"),
            companion_id=data.get("companion_id"),
            behavior_flags=data.get("behavior_flags", {}),
        )


@dataclass
class CombatActionResult:
    """Outcome of a single combat action."""

    action_id: str
    attacker_id: str
    target_id: str
    result_type: ActionResultType
    damage: float = 0.0
    healing: float = 0.0
    combo_points_gained: int = 0
    status_effects_applied: list[ActiveStatusCondition] = field(default_factory=list)
    triggered_finisher: str | None = None
    narration: str = ""
    timestamp: float = field(default_factory=time.time)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "attacker_id": self.attacker_id,
            "target_id": self.target_id,
            "result_type": self.result_type.value,
            "damage": self.damage,
            "healing": self.healing,
            "combo_points_gained": self.combo_points_gained,
            "status_effects_applied": [s.to_dict() for s in self.status_effects_applied],
            "triggered_finisher": self.triggered_finisher,
            "narration": self.narration,
            "timestamp": self.timestamp,
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CombatActionResult:
        return CombatActionResult(
            action_id=data["action_id"],
            attacker_id=data["attacker_id"],
            target_id=data["target_id"],
            result_type=ActionResultType(data.get("result_type", "hit")),
            damage=data.get("damage", 0.0),
            healing=data.get("healing", 0.0),
            combo_points_gained=data.get("combo_points_gained", 0),
            status_effects_applied=[ActiveStatusCondition.from_dict(s) for s in data.get("status_effects_applied", [])],
            triggered_finisher=data.get("triggered_finisher"),
            narration=data.get("narration", ""),
            timestamp=data.get("timestamp", 0.0),
            extra=data.get("extra", {}),
        )


# ---------------------------------------------------------------------------
# Tactical Positioning
# ---------------------------------------------------------------------------


class TacticalPositioning:
    """
    Calculates position-based modifiers for combatants.
    Supports relative advantages (flank vs backline, elevated vs grounded).
    """

    _DEFAULT_MODIFIERS: dict[CombatPosition, PositionModifier] = {
        CombatPosition.FRONTLINE: PositionModifier(
            position=CombatPosition.FRONTLINE,
            attack_bonus=0.0,
            defense_bonus=0.10,
            crit_chance_bonus=-0.02,
            dodge_chance_bonus=-0.03,
            damage_taken_multiplier=1.10,
        ),
        CombatPosition.FLANK: PositionModifier(
            position=CombatPosition.FLANK,
            attack_bonus=0.15,
            defense_bonus=0.0,
            crit_chance_bonus=0.05,
            dodge_chance_bonus=0.05,
            damage_taken_multiplier=1.0,
        ),
        CombatPosition.BACKLINE: PositionModifier(
            position=CombatPosition.BACKLINE,
            attack_bonus=-0.05,
            defense_bonus=-0.10,
            crit_chance_bonus=0.08,
            dodge_chance_bonus=0.10,
            damage_taken_multiplier=0.90,
        ),
        CombatPosition.ELEVATED: PositionModifier(
            position=CombatPosition.ELEVATED,
            attack_bonus=0.20,
            defense_bonus=0.05,
            crit_chance_bonus=0.10,
            dodge_chance_bonus=0.05,
            damage_taken_multiplier=0.85,
            range_bonus=2.0,
        ),
        CombatPosition.GROUNDED: PositionModifier(
            position=CombatPosition.GROUNDED,
            attack_bonus=-0.10,
            defense_bonus=-0.05,
            crit_chance_bonus=-0.05,
            dodge_chance_bonus=-0.10,
            damage_taken_multiplier=1.15,
        ),
        CombatPosition.COVER: PositionModifier(
            position=CombatPosition.COVER,
            attack_bonus=-0.15,
            defense_bonus=0.25,
            crit_chance_bonus=-0.05,
            dodge_chance_bonus=0.15,
            damage_taken_multiplier=0.60,
        ),
    }

    _RELATIVE_ADVANTAGES: dict[tuple[CombatPosition, CombatPosition], float] = {
        (CombatPosition.FLANK, CombatPosition.FRONTLINE): 0.15,
        (CombatPosition.FLANK, CombatPosition.BACKLINE): -0.05,
        (CombatPosition.ELEVATED, CombatPosition.GROUNDED): 0.20,
        (CombatPosition.ELEVATED, CombatPosition.FRONTLINE): 0.10,
        (CombatPosition.BACKLINE, CombatPosition.FRONTLINE): -0.10,
        (CombatPosition.COVER, CombatPosition.FRONTLINE): 0.05,
        (CombatPosition.COVER, CombatPosition.FLANK): -0.05,
        (CombatPosition.FRONTLINE, CombatPosition.BACKLINE): 0.15,
    }

    def __init__(self, custom_modifiers: dict[CombatPosition, PositionModifier] | None = None) -> None:
        self.modifiers = dict(self._DEFAULT_MODIFIERS)
        if custom_modifiers:
            self.modifiers.update(custom_modifiers)

    def get_modifier(self, position: CombatPosition) -> PositionModifier:
        return self.modifiers.get(position, PositionModifier(position=position))

    def calculate_attack_bonus(self, attacker: Combatant, defender: Combatant) -> float:
        attacker_pos = attacker.effective_position()
        defender_pos = defender.effective_position()
        mod = self.get_modifier(attacker_pos)
        bonus = mod.attack_bonus
        bonus += self._RELATIVE_ADVANTAGES.get((attacker_pos, defender_pos), 0.0)
        for (cid, cond_id), active in defender.status_manager.active.items():
            if cid != defender.combatant_id:
                continue
            definition = defender.status_manager.definitions.get(cond_id)
            if definition and definition.condition_type == StatusConditionType.BLIND:
                bonus += 0.15
        return bonus

    def calculate_defense_bonus(self, defender: Combatant, attacker: Combatant) -> float:
        defender_pos = defender.effective_position()
        mod = self.get_modifier(defender_pos)
        bonus = mod.defense_bonus
        bonus += self._RELATIVE_ADVANTAGES.get((attacker.effective_position(), defender_pos), 0.0) * -0.5
        return bonus

    def calculate_crit_chance_bonus(self, combatant: Combatant) -> float:
        return self.get_modifier(combatant.effective_position()).crit_chance_bonus

    def calculate_dodge_chance_bonus(self, combatant: Combatant) -> float:
        return self.get_modifier(combatant.effective_position()).dodge_chance_bonus

    def calculate_damage_taken_multiplier(self, defender: Combatant) -> float:
        return self.get_modifier(defender.effective_position()).damage_taken_multiplier

    def has_positional_advantage(self, attacker: Combatant, defender: Combatant) -> bool:
        attacker_pos = attacker.effective_position()
        defender_pos = defender.effective_position()
        if attacker_pos == CombatPosition.ELEVATED and defender_pos in (
            CombatPosition.GROUNDED,
            CombatPosition.FRONTLINE,
        ):
            return True
        if attacker_pos == CombatPosition.FLANK and defender_pos == CombatPosition.BACKLINE:
            return True
        if attacker_pos == CombatPosition.FRONTLINE and defender_pos == CombatPosition.BACKLINE:
            return True
        if attacker_pos == CombatPosition.COVER and defender_pos in (
            CombatPosition.FRONTLINE,
            CombatPosition.FLANK,
        ):
            return True
        return False

    def can_strike_from_behind(self, attacker: Combatant, defender: Combatant) -> bool:
        return (
            attacker.effective_position() == CombatPosition.FLANK
            and defender.effective_position() == CombatPosition.BACKLINE
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "modifiers": {p.value: m.to_dict() for p, m in self.modifiers.items()},
            "relative_advantages": {
                f"{k[0].value},{k[1].value}": v for k, v in self._RELATIVE_ADVANTAGES.items()
            },
        }


# ---------------------------------------------------------------------------
# Combo System
# ---------------------------------------------------------------------------


class ComboSystem:
    """
    Manages combo chains for combatants. Tracks active combos,
    validates steps, awards combo points, and escalates tiers.
    """

    def __init__(self, combo_definitions: dict[str, list[ComboNode]] | None = None) -> None:
        self.definitions: dict[str, list[ComboNode]] = combo_definitions or {}
        for combo_nodes in self.definitions.values():
            combo_nodes.sort(key=lambda n: n.sequence_index)

    def register_combo(self, combo_nodes: list[ComboNode]) -> None:
        combo_nodes.sort(key=lambda n: n.sequence_index)
        self.definitions[combo_nodes[0].combo_id] = combo_nodes

    def start_combo(self, combo_state: CombatComboState, combo_id: str, current_time: float) -> bool:
        nodes = self.definitions.get(combo_id)
        if not nodes or len(nodes) < 1:
            return False
        combo_state.active_combo_id = combo_id
        combo_state.current_step_index = 0
        combo_state.last_combo_time = current_time
        combo_state.combo_tier = ComboTier.BASIC
        return True

    def validate_step(
        self, combo_state: CombatComboState, ability_id: str, current_time: float
    ) -> tuple[bool, ComboNode | None]:
        if not combo_state.is_in_combo():
            return False, None
        if combo_state.is_combo_window_expired(current_time):
            combo_state.reset()
            return False, None
        combo_id = combo_state.active_combo_id
        nodes = self.definitions.get(combo_id, [])
        if combo_state.current_step_index >= len(nodes):
            combo_state.reset()
            return False, None
        expected = nodes[combo_state.current_step_index]
        if expected.ability_id != ability_id:
            combo_state.reset()
            return False, None
        return True, expected

    def advance_combo(
        self, combo_state: CombatComboState, ability_id: str, current_time: float
    ) -> tuple[bool, ComboNode | None, int]:
        ok, node = self.validate_step(combo_state, ability_id, current_time)
        if not ok or node is None:
            return False, None, 0
        combo_state.last_combo_time = current_time
        combo_state.combo_points += node.combo_point_gain
        combo_state.current_step_index += 1
        combo_id = combo_state.active_combo_id
        nodes = self.definitions.get(combo_id, [])
        if combo_state.current_step_index >= len(nodes):
            combo_state.completed_combos.append(combo_id)
            self._escalate_tier(combo_state)
            combo_state.reset()
            return True, node, combo_state.combo_points
        next_node = nodes[combo_state.current_step_index]
        combo_state.combo_tier = next_node.required_combo_tier
        return True, node, combo_state.combo_points

    def _escalate_tier(self, combo_state: CombatComboState) -> None:
        tier_order = [
            ComboTier.BASIC,
            ComboTier.ADVANCED,
            ComboTier.EXPERT,
            ComboTier.MASTER,
        ]
        try:
            idx = tier_order.index(combo_state.combo_tier)
            if idx < len(tier_order) - 1:
                combo_state.combo_tier = tier_order[idx + 1]
        except ValueError:
            pass

    def get_available_finishers(
        self,
        combo_state: CombatComboState,
        finishers: list[FinisherDefinition],
        attacker: Combatant,
        defender: Combatant,
    ) -> list[FinisherDefinition]:
        available: list[FinisherDefinition] = []
        for finisher in finishers:
            if combo_state.combo_points < finisher.combo_points_required:
                continue
            if not self._check_triggers(finisher, attacker, defender):
                continue
            if not self._check_position(finisher, attacker, defender):
                continue
            if not self._check_health(finisher, defender):
                continue
            available.append(finisher)
        return available

    def _check_triggers(
        self, finisher: FinisherDefinition, attacker: Combatant, defender: Combatant
    ) -> bool:
        if FinisherTrigger.LOW_HEALTH in finisher.triggers and not self._target_low_health(defender):
            return False
        if FinisherTrigger.HIGH_COMBO in finisher.triggers and not self._high_combo(attacker):
            return False
        if FinisherTrigger.BEHIND_TARGET in finisher.triggers and not self._is_behind_target(attacker, defender):
            return False
        if FinisherTrigger.TARGET_STUNNED in finisher.triggers and not self._target_stunned(defender):
            return False
        if FinisherTrigger.TARGET_BURNING in finisher.triggers and not self._target_burning(defender):
            return False
        if FinisherTrigger.SELF_LOW_HEALTH in finisher.triggers and not self._self_low_health(attacker):
            return False
        if FinisherTrigger.POSITION_ADVANTAGE in finisher.triggers and not self._has_position_advantage(attacker, defender):
            return False
        return True

    def _check_position(
        self, finisher: FinisherDefinition, attacker: Combatant, defender: Combatant
    ) -> bool:
        if not finisher.positional_requirements:
            return True
        return attacker.effective_position() in finisher.positional_requirements

    def _check_health(self, finisher: FinisherDefinition, defender: Combatant) -> bool:
        if defender.stats.max_health <= 0:
            return True
        health_percent = (defender.stats.health / defender.stats.max_health) * 100.0
        return finisher.target_health_min_percent <= health_percent <= finisher.target_health_max_percent

    @staticmethod
    def _target_low_health(combatant: Combatant) -> bool:
        if combatant.stats.max_health <= 0:
            return False
        return (combatant.stats.health / combatant.stats.max_health) <= 0.25

    @staticmethod
    def _high_combo(combatant: Combatant) -> bool:
        return combatant.combo_state.combo_points >= 5

    @staticmethod
    def _is_behind_target(attacker: Combatant, defender: Combatant) -> bool:
        return attacker.effective_position() == CombatPosition.FLANK and defender.effective_position() == CombatPosition.BACKLINE

    @staticmethod
    def _target_stunned(combatant: Combatant) -> bool:
        return combatant.has_condition_type(StatusConditionType.STUN)

    @staticmethod
    def _target_burning(combatant: Combatant) -> bool:
        return combatant.has_condition_type(StatusConditionType.BURN)

    @staticmethod
    def _self_low_health(combatant: Combatant) -> bool:
        if combatant.stats.max_health <= 0:
            return False
        return (combatant.stats.health / combatant.stats.max_health) <= 0.30

    @staticmethod
    def _has_position_advantage(attacker: Combatant, defender: Combatant) -> bool:
        return TacticalPositioning().has_positional_advantage(attacker, defender)


# ---------------------------------------------------------------------------
# Combat Encounter
# ---------------------------------------------------------------------------


@dataclass
class CombatEncounter:
    """
    A single combat encounter session. Manages participants, turn order,
    ability resolution, combos, finishers, and positioning.
    """

    encounter_id: str
    combatants: list[Combatant] = field(default_factory=list)
    turn_order: list[str] = field(default_factory=list)
    current_turn_index: int = 0
    round_number: int = 1
    is_active: bool = False
    positioning: TacticalPositioning = field(default_factory=TacticalPositioning)
    combo_system: ComboSystem = field(default_factory=ComboSystem)
    finishers: list[FinisherDefinition] = field(default_factory=list)
    action_history: list[CombatActionResult] = field(default_factory=list)
    encounter_log: list[str] = field(default_factory=list)
    started_at: float = 0.0
    ended_at: float = 0.0
    winner_team: CombatantTeam | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def get_combatant(self, combatant_id: str) -> Combatant | None:
        for c in self.combatants:
            if c.combatant_id == combatant_id:
                return c
        return None

    def get_team(self, team: CombatantTeam) -> list[Combatant]:
        return [c for c in self.combatants if c.team == team and c.is_alive()]

    def start_encounter(self, current_time: float | None = None) -> None:
        self.is_active = True
        self.started_at = current_time if current_time is not None else time.time()
        self.round_number = 1
        self.current_turn_index = 0
        self._build_turn_order()
        self.encounter_log.append("Encounter started.")

    def end_encounter(self, current_time: float | None = None) -> None:
        self.is_active = False
        self.ended_at = current_time if current_time is not None else time.time()
        players = self.get_team(CombatantTeam.PLAYER)
        enemies = self.get_team(CombatantTeam.ENEMY)
        if players and not enemies:
            self.winner_team = CombatantTeam.PLAYER
            self.encounter_log.append("Victory! All enemies defeated.")
        elif enemies and not players:
            self.winner_team = CombatantTeam.ENEMY
            self.encounter_log.append("Defeat. All party members fallen.")
        else:
            self.winner_team = None
            self.encounter_log.append("Encounter ended inconclusively.")

    def next_turn(self, current_time: float) -> Combatant | None:
        if not self.is_active:
            return None
        if not self.turn_order:
            return None
        alive_ids = {c.combatant_id for c in self.combatants if c.is_alive()}
        alive_order = [cid for cid in self.turn_order if cid in alive_ids]
        if not alive_order:
            self.end_encounter(current_time)
            return None
        turn_combatant_id = alive_order[self.current_turn_index % len(alive_order)]
        self.current_turn_index += 1
        if self.current_turn_index > 0 and self.current_turn_index % len(alive_order) == 0:
            self.round_number += 1
            self.encounter_log.append(f"Round {self.round_number} begins.")
        return self.get_combatant(turn_combatant_id)

    def resolve_action(
        self,
        attacker: Combatant,
        ability: Ability,
        target: Combatant | None,
        current_time: float,
    ) -> CombatActionResult:
        action_id = f"action_{int(current_time * 1000)}_{attacker.combatant_id}"
        if target is None:
            return CombatActionResult(
                action_id=action_id,
                attacker_id=attacker.combatant_id,
                target_id="",
                result_type=ActionResultType.MISS,
                narration=f"{attacker.name} has no target.",
            )
        result = self._resolve_hit(attacker, ability, target, current_time)
        self.action_history.append(result)
        if result.damage > 0:
            target.stats.health = max(0, target.stats.health - int(result.damage))
            if not target.is_alive():
                self.encounter_log.append(f"{target.name} is defeated.")
        if result.healing > 0:
            attacker.stats.health = min(attacker.stats.max_health, attacker.stats.health + int(result.healing))
        for active_cond in result.status_effects_applied:
            attacker.status_manager.apply_condition(active_cond, current_time)
        if result.triggered_finisher:
            self.encounter_log.append(f"Finisher triggered: {result.triggered_finisher}")
        return result

    def _resolve_hit(
        self, attacker: Combatant, ability: Ability, target: Combatant, current_time: float
    ) -> CombatActionResult:
        action_id = f"action_{int(current_time * 1000)}_{attacker.combatant_id}"
        if not self._check_hit(attacker, target):
            return CombatActionResult(
                action_id=action_id,
                attacker_id=attacker.combatant_id,
                target_id=target.combatant_id,
                result_type=ActionResultType.MISS,
                narration=f"{attacker.name}'s attack missed {target.name}.",
            )
        if self._check_dodge(target):
            return CombatActionResult(
                action_id=action_id,
                attacker_id=attacker.combatant_id,
                target_id=target.combatant_id,
                result_type=ActionResultType.DODGED,
                narration=f"{target.name} dodged {attacker.name}'s attack.",
            )
        is_crit = self._check_crit(attacker, target)
        result_type = ActionResultType.CRITICAL if is_crit else ActionResultType.HIT
        base_damage = self._calculate_damage(attacker, target, ability, is_crit)
        combo_result = self._process_combo(attacker, ability.id, current_time)
        available_finishers = self.combo_system.get_available_finishers(
            attacker.combo_state, self.finishers, attacker, target
        )
        triggered_finisher = self._execute_finisher(attacker, target, available_finishers, current_time)
        if triggered_finisher:
            base_damage *= 1.5
        active_conditions = self._apply_ability_effects(attacker, target, ability, current_time)
        narration = self._build_narration(attacker, target, ability, result_type, base_damage, triggered_finisher)
        return CombatActionResult(
            action_id=action_id,
            attacker_id=attacker.combatant_id,
            target_id=target.combatant_id,
            result_type=result_type,
            damage=base_damage,
            combo_points_gained=combo_result[2],
            status_effects_applied=active_conditions,
            triggered_finisher=triggered_finisher,
            narration=narration,
        )

    def _check_hit(self, attacker: Combatant, target: Combatant) -> bool:
        accuracy = attacker.stats.accuracy + self.positioning.calculate_attack_bonus(attacker, target)
        for (cid, cond_id), active in target.status_manager.active.items():
            if cid != target.combatant_id:
                continue
            definition = target.status_manager.definitions.get(cond_id)
            if definition and definition.condition_type == StatusConditionType.BLIND:
                accuracy += 0.15
        return accuracy >= 0.5

    def _check_dodge(self, target: Combatant) -> bool:
        dodge = target.stats.dodge_chance + self.positioning.calculate_dodge_chance_bonus(target)
        for (cid, cond_id), active in target.status_manager.active.items():
            if cid != target.combatant_id:
                continue
            definition = target.status_manager.definitions.get(cond_id)
            if definition and definition.condition_type == StatusConditionType.PARALYZE:
                dodge = max(0.0, dodge - 0.25)
        return dodge > 0.0 and __import__("random").random() < dodge

    def _check_crit(self, attacker: Combatant, target: Combatant) -> bool:
        crit = attacker.stats.crit_chance + self.positioning.calculate_crit_chance_bonus(attacker)
        if attacker.position == CombatPosition.FLANK and target.position == CombatPosition.BACKLINE:
            crit += 0.05
        return crit > 0.0 and __import__("random").random() < crit

    def _calculate_damage(
        self, attacker: Combatant, target: Combatant, ability: Ability, is_crit: bool
    ) -> float:
        attack = attacker.stats.attack_power + self.positioning.calculate_attack_bonus(attacker, target) * attacker.stats.attack_power
        defense = target.stats.defense + self.positioning.calculate_defense_bonus(target, attacker) * target.stats.defense
        base = max(1.0, attack - defense * 0.5)
        multiplier = 2.0 if is_crit else 1.0
        multiplier *= self.positioning.calculate_damage_taken_multiplier(target)
        for (cid, cond_id), active in target.status_manager.active.items():
            if cid != target.combatant_id:
                continue
            definition = target.status_manager.definitions.get(cond_id)
            if definition and definition.condition_type == StatusConditionType.SHIELD:
                multiplier *= 0.5
        return base * multiplier

    def _process_combo(
        self, attacker: Combatant, ability_id: str, current_time: float
    ) -> tuple[bool, ComboNode | None, int]:
        if not attacker.combo_state.is_in_combo():
            for combo_id, nodes in self.combo_system.definitions.items():
                if nodes and nodes[0].ability_id == ability_id:
                    self.combo_system.start_combo(attacker.combo_state, combo_id, current_time)
                    break
            return False, None, 0
        ok, node, points = self.combo_system.advance_combo(attacker.combo_state, ability_id, current_time)
        return ok, node, points

    def _execute_finisher(
        self,
        attacker: Combatant,
        target: Combatant,
        finishers: list[FinisherDefinition],
        current_time: float,
    ) -> str | None:
        if not finishers:
            return None
        finisher = finishers[0]
        for effect_data in finisher.effects:
            if effect_data.effect_type == "damage":
                dmg = effect_data.value * (1 + self.positioning.calculate_attack_bonus(attacker, target))
                target.stats.health = max(0, target.stats.health - int(dmg))
            elif effect_data.effect_type == "healing":
                heal = effect_data.value
                attacker.stats.health = min(attacker.stats.max_health, attacker.stats.health + int(heal))
        attacker.combo_state.combo_points = max(0, attacker.combo_state.combo_points - finisher.combo_points_required)
        attacker.combo_state.reset()
        return finisher.ability_id

    def _apply_ability_effects(
        self, attacker: Combatant, target: Combatant, ability: Ability, current_time: float
    ) -> list[ActiveStatusCondition]:
        applied: list[ActiveStatusCondition] = []
        for effect in ability.effects:
            if __import__("random").random() > effect.chance:
                continue
            if effect.effect_type == "dot":
                cond = StatusCondition(
                    id=f"dot_{effect.extra.get('source_ability', ability.id)}",
                    name="Damage Over Time",
                    condition_type=StatusConditionType.DAMAGE_OVER_TIME,
                    duration_seconds=effect.duration_seconds,
                    tick_interval_seconds=1.0,
                    effects=[],
                    extra=effect.extra,
                )
                active = ActiveStatusCondition(
                    condition_id=cond.id,
                    character_id=target.combatant_id,
                    remaining_duration=effect.duration_seconds,
                    applied_at=current_time,
                    last_tick_at=current_time,
                    source_ability_id=ability.id,
                    source_character_id=attacker.combatant_id,
                    extra=effect.extra,
                )
                applied.append(active)
            elif effect.effect_type == "hot":
                cond = StatusCondition(
                    id=f"hot_{effect.extra.get('source_ability', ability.id)}",
                    name="Heal Over Time",
                    condition_type=StatusConditionType.HEAL_OVER_TIME,
                    duration_seconds=effect.duration_seconds,
                    tick_interval_seconds=1.0,
                    effects=[],
                    extra=effect.extra,
                )
                active = ActiveStatusCondition(
                    condition_id=cond.id,
                    character_id=target.combatant_id,
                    remaining_duration=effect.duration_seconds,
                    applied_at=current_time,
                    last_tick_at=current_time,
                    source_ability_id=ability.id,
                    source_character_id=attacker.combatant_id,
                    extra=effect.extra,
                )
                applied.append(active)
            elif effect.effect_type == "stun":
                cond = StatusCondition(
                    id=f"stun_{effect.extra.get('source_ability', ability.id)}",
                    name="Stunned",
                    condition_type=StatusConditionType.STUN,
                    duration_seconds=effect.duration_seconds,
                    effects=[],
                    prevents_actions=True,
                    extra=effect.extra,
                )
                active = ActiveStatusCondition(
                    condition_id=cond.id,
                    character_id=target.combatant_id,
                    remaining_duration=effect.duration_seconds,
                    applied_at=current_time,
                    last_tick_at=current_time,
                    source_ability_id=ability.id,
                    source_character_id=attacker.combatant_id,
                    extra=effect.extra,
                )
                applied.append(active)
            elif effect.effect_type == "burn":
                cond = StatusCondition(
                    id=f"burn_{effect.extra.get('source_ability', ability.id)}",
                    name="Burning",
                    condition_type=StatusConditionType.BURN,
                    duration_seconds=effect.duration_seconds,
                    tick_interval_seconds=1.0,
                    effects=[],
                    extra=effect.extra,
                )
                active = ActiveStatusCondition(
                    condition_id=cond.id,
                    character_id=target.combatant_id,
                    remaining_duration=effect.duration_seconds,
                    applied_at=current_time,
                    last_tick_at=current_time,
                    source_ability_id=ability.id,
                    source_character_id=attacker.combatant_id,
                    extra=effect.extra,
                )
                applied.append(active)
        return applied

    def _build_narration(
        self,
        attacker: Combatant,
        target: Combatant,
        ability: Ability,
        result_type: ActionResultType,
        damage: float,
        finisher: str | None,
    ) -> str:
        parts = [f"{attacker.name} uses {ability.name} on {target.name}"]
        if result_type == ActionResultType.CRITICAL:
            parts.append("Critical hit!")
        if result_type == ActionResultType.MISS:
            parts.append("It misses.")
        if result_type == ActionResultType.DODGED:
            parts.append("The target dodges.")
        if damage > 0:
            parts.append(f"Deals {int(damage)} damage.")
        if finisher:
            parts.append(f"Finisher executed: {finisher}")
        return " ".join(parts)

    def _build_turn_order(self) -> None:
        alive = [c for c in self.combatants if c.is_alive()]
        alive.sort(key=lambda c: c.stats.speed, reverse=True)
        self.turn_order = [c.combatant_id for c in alive]

    def to_dict(self) -> dict[str, Any]:
        return {
            "encounter_id": self.encounter_id,
            "combatants": [c.to_dict() for c in self.combatants],
            "turn_order": list(self.turn_order),
            "current_turn_index": self.current_turn_index,
            "round_number": self.round_number,
            "is_active": self.is_active,
            "positioning": self.positioning.to_dict(),
            "combo_system": {
                "definitions": {
                    cid: [n.to_dict() for n in nodes]
                    for cid, nodes in self.combo_system.definitions.items()
                }
            },
            "finishers": [f.to_dict() for f in self.finishers],
            "action_history": [a.to_dict() for a in self.action_history],
            "encounter_log": list(self.encounter_log),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "winner_team": self.winner_team.value if self.winner_team else None,
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CombatEncounter:
        encounter = CombatEncounter(
            encounter_id=data["encounter_id"],
            combatants=[Combatant.from_dict(c) for c in data.get("combatants", [])],
            turn_order=data.get("turn_order", []),
            current_turn_index=data.get("current_turn_index", 0),
            round_number=data.get("round_number", 1),
            is_active=data.get("is_active", False),
            started_at=data.get("started_at", 0.0),
            ended_at=data.get("ended_at", 0.0),
            winner_team=CombatantTeam(data["winner_team"]) if data.get("winner_team") else None,
            encounter_log=data.get("encounter_log", []),
            action_history=[CombatActionResult.from_dict(a) for a in data.get("action_history", [])],
            extra=data.get("extra", {}),
        )
        combo_data = data.get("combo_system", {})
        definitions: dict[str, list[ComboNode]] = {}
        for cid, nodes_data in combo_data.get("definitions", {}).items():
            definitions[cid] = [ComboNode.from_dict(n) for n in nodes_data]
        encounter.combo_system = ComboSystem(combo_definitions=definitions)
        encounter.finishers = [FinisherDefinition.from_dict(f) for f in data.get("finishers", [])]
        return encounter
