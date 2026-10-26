"""
RPG-10-13: Character Stats System
Manages base attributes (strength, dexterity, intelligence, vitality, charisma, luck),
derived stats (HP, MP, stamina, defense, etc.), stat point allocation, and
temporary modifiers.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Canonical stat names
# ---------------------------------------------------------------------------

BASE_STATS = ("strength", "dexterity", "intelligence", "vitality", "charisma", "luck")

STAT_NAMES = {
    "strength": "Strength",
    "dexterity": "Dexterity",
    "intelligence": "Intelligence",
    "vitality": "Vitality",
    "charisma": "Charisma",
    "luck": "Luck",
}

STAT_ABBREVIATIONS = {
    "strength": "STR",
    "dexterity": "DEX",
    "intelligence": "INT",
    "vitality": "VIT",
    "charisma": "CHA",
    "luck": "LCK",
}


# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

@dataclass
class StatDefinition:
    """Definition of a single base stat."""

    id: str
    name: str
    abbreviation: str
    description: str = ""
    min: int = 1
    max: int = 100
    default: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "abbreviation": self.abbreviation,
            "description": self.description,
            "min": self.min,
            "max": self.max,
            "default": self.default,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StatDefinition:
        return StatDefinition(
            id=data["id"],
            name=data.get("name", data["id"].title()),
            abbreviation=data.get("abbreviation", data["id"][:3].upper()),
            description=data.get("description", ""),
            min=data.get("min", 1),
            max=data.get("max", 100),
            default=data.get("default", 10),
        )


@dataclass
class DerivedStatRule:
    """A derived stat computed from base stats via a formula."""

    id: str
    name: str
    formula: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "formula": self.formula,
            "description": self.description,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DerivedStatRule:
        return DerivedStatRule(
            id=data["id"],
            name=data.get("name", data["id"].title().replace("_", " ")),
            formula=data["formula"],
            description=data.get("description", ""),
        )

    def compute(self, base_stats: dict[str, int]) -> float:
        """
        Evaluate the formula against the provided base stats.

        Only known base stat names are injected; missing ones default to 0.
        """
        safe_names = {k: base_stats.get(k, 0) for k in BASE_STATS}
        safe_names["sqrt"] = math.sqrt
        safe_names["abs"] = abs
        safe_names["max"] = max
        safe_names["min"] = min
        safe_names["round"] = round
        try:
            return float(eval(self.formula, {"__builtins__": {}}, safe_names))
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# Character stat state
# ---------------------------------------------------------------------------

@dataclass
class CharacterStatsState:
    """
    Holds a character's current base stats, temp modifiers, and
    cached derived stats.
    """

    character_id: str
    base_stats: dict[str, int] = field(default_factory=dict)
    temp_modifiers: dict[str, int] = field(default_factory=dict)
    derived_stats: dict[str, float] = field(default_factory=dict)

    def effective_stats(self) -> dict[str, int]:
        """
        Return base stats plus temp modifiers, clamped to [min, max].
        """
        result: dict[str, int] = {}
        for stat in BASE_STATS:
            base = self.base_stats.get(stat, 0)
            mod = self.temp_modifiers.get(stat, 0)
            val = base + mod
            result[stat] = max(0, val)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "base_stats": dict(self.base_stats),
            "temp_modifiers": dict(self.temp_modifiers),
            "derived_stats": dict(self.derived_stats),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CharacterStatsState:
        return CharacterStatsState(
            character_id=data["character_id"],
            base_stats=data.get("base_stats", {}),
            temp_modifiers=data.get("temp_modifiers", {}),
            derived_stats=data.get("derived_stats", {}),
        )


# ---------------------------------------------------------------------------
# Stats System configuration
# ---------------------------------------------------------------------------

class StatsSystem:
    """
    Global configuration: stat definitions, bounds, and derived stat formulas.
    """

    def __init__(
        self,
        stat_definitions: list[StatDefinition] | None = None,
        derived_rules: list[DerivedStatRule] | None = None,
    ) -> None:
        self.stat_definitions: dict[str, StatDefinition] = {}
        self.derived_rules: dict[str, DerivedStatRule] = {}

        for sdef in stat_definitions or []:
            self.stat_definitions[sdef.id] = sdef

        for rule in derived_rules or []:
            self.derived_rules[rule.id] = rule

        # Ensure canonical base stats always exist even if data is empty.
        for sid in BASE_STATS:
            if sid not in self.stat_definitions:
                self.stat_definitions[sid] = StatDefinition(
                    id=sid,
                    name=STAT_NAMES.get(sid, sid.title()),
                    abbreviation=STAT_ABBREVIATIONS.get(sid, sid[:3].upper()),
                )
        self._character_states: dict[str, CharacterStatsState] = {}

    def get_definition(self, stat_id: str) -> StatDefinition | None:
        return self.stat_definitions.get(stat_id)

    def get_derived_rule(self, stat_id: str) -> DerivedStatRule | None:
        return self.derived_rules.get(stat_id)

    def compute_derived(self, base_stats: dict[str, int]) -> dict[str, float]:
        """
        Compute all derived stats from the given base stats.
        """
        result: dict[str, float] = {}
        for rule_id, rule in self.derived_rules.items():
            result[rule_id] = rule.compute(base_stats)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "stat_definitions": [s.to_dict() for s in self.stat_definitions.values()],
            "derived_rules": [r.to_dict() for r in self.derived_rules.values()],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StatsSystem:
        stat_defs = [StatDefinition.from_dict(s) for s in data.get("stat_definitions", [])]
        derived = [DerivedStatRule.from_dict(r) for r in data.get("derived_rules", [])]
        return StatsSystem(stat_definitions=stat_defs, derived_rules=derived)

    # --- Character state integration -------------------------------------------

    def register_state(self, state: CharacterStatsState) -> None:
        """Register a character stat state for derived-stat lookup."""
        self._character_states[state.character_id] = state

    def get_derived_stats(self, character_id: str) -> dict[str, float]:
        """Return computed derived stats for a registered character state."""
        state = self._character_states.get(character_id)
        if state is None:
            return {}
        return self.compute_derived(state.effective_stats())


# ---------------------------------------------------------------------------
# Stats Manager
# ---------------------------------------------------------------------------

class StatsManager:
    """
    Manages per-character stats, point allocation, temp modifiers,
    and derived stat recalculation.
    """

    def __init__(self, system: StatsSystem | None = None) -> None:
        self.system = system or StatsSystem()
        self.character_states: dict[str, CharacterStatsState] = {}

    # --- State management ---------------------------------------------------

    def get_state(self, character_id: str) -> CharacterStatsState:
        if character_id not in self.character_states:
            self.character_states[character_id] = CharacterStatsState(
                character_id=character_id
            )
        return self.character_states[character_id]

    # --- Base stats ---------------------------------------------------------

    def set_base_stats(self, character_id: str, stats: dict[str, int]) -> dict[str, Any]:
        """
        Replace a character's base stats (validated and clamped).
        Returns the effective stats after clamping.
        """
        state = self.get_state(character_id)
        invalid = [s for s in stats if s not in BASE_STATS]
        if invalid:
            return {
                "success": False,
                "reason": f"Invalid stat(s): {', '.join(invalid)}. Valid: {', '.join(BASE_STATS)}",
            }

        clamped: dict[str, int] = {}
        for stat, val in stats.items():
            sdef = self.system.get_definition(stat)
            low = sdef.min if sdef else 0
            high = sdef.max if sdef else 999
            clamped[stat] = max(low, min(high, val))

        state.base_stats.update(clamped)
        self._recalc_derived(state)
        return {"success": True, "stats": dict(state.base_stats)}

    def get_base_stats(self, character_id: str) -> dict[str, int]:
        return dict(self.get_state(character_id).base_stats)

    def get_effective_stats(self, character_id: str) -> dict[str, int]:
        return self.get_state(character_id).effective_stats()

    def get_derived_stats(self, character_id: str) -> dict[str, float]:
        return dict(self.get_state(character_id).derived_stats)

    # --- Point allocation ---------------------------------------------------

    def allocate_stat_point(
        self, character_id: str, attribute: str, unspent_points: int
    ) -> tuple[bool, str]:
        """
        Spend one unspent stat point to increase an attribute by 1.

        Requires the caller to track unspent points; `unspent_points` is the
        current count, updated by the caller after success.
        """
        if attribute not in BASE_STATS:
            return False, f"Invalid stat '{attribute}'."
        if unspent_points <= 0:
            return False, "No unspent stat points."

        state = self.get_state(character_id)
        sdef = self.system.get_definition(attribute)
        max_val = sdef.max if sdef else 999
        current = state.base_stats.get(attribute, 0)

        if current >= max_val:
            return False, f"'{attribute}' is already at maximum ({max_val})."

        state.base_stats[attribute] = current + 1
        self._recalc_derived(state)
        return True, ""

    # --- Temporary modifiers -------------------------------------------------

    def add_temp_modifier(self, character_id: str, stat: str, amount: int) -> dict[str, Any]:
        """
        Apply a temporary modifier to a stat (e.g., buff/debuff).
        Modifiers stack and persist until removed.
        """
        if stat not in BASE_STATS:
            return {"success": False, "reason": f"Invalid stat '{stat}'."}

        state = self.get_state(character_id)
        state.temp_modifiers[stat] = state.temp_modifiers.get(stat, 0) + amount
        self._recalc_derived(state)
        return {
            "success": True,
            "stat": stat,
            "temp_modifier": state.temp_modifiers[stat],
            "effective_stats": state.effective_stats(),
        }

    def remove_temp_modifier(self, character_id: str, stat: str, amount: int) -> dict[str, Any]:
        """
        Remove a temporary modifier from a stat.
        """
        if stat not in BASE_STATS:
            return {"success": False, "reason": f"Invalid stat '{stat}'."}

        state = self.get_state(character_id)
        current = state.temp_modifiers.get(stat, 0)
        state.temp_modifiers[stat] = max(0, current - amount)
        self._recalc_derived(state)
        return {
            "success": True,
            "stat": stat,
            "temp_modifier": state.temp_modifiers.get(stat, 0),
            "effective_stats": state.effective_stats(),
        }

    def clear_temp_modifiers(self, character_id: str) -> dict[str, Any]:
        state = self.get_state(character_id)
        state.temp_modifiers.clear()
        self._recalc_derived(state)
        return {"success": True, "temp_modifiers": {}}

    # --- Derived stats helpers -----------------------------------------------

    def _recalc_derived(self, state: CharacterStatsState) -> None:
        effective = state.effective_stats()
        state.derived_stats = self.system.compute_derived(effective)

    def get_derived(self, character_id: str, derived_id: str) -> float:
        return self.get_state(character_id).derived_stats.get(derived_id, 0.0)

    # --- Summaries -----------------------------------------------------------

    def get_character_stats_summary(self, character_id: str) -> dict[str, Any]:
        state = self.get_state(character_id)
        base = dict(state.base_stats)
        effective = state.effective_stats()
        derived = dict(state.derived_stats)

        stat_details: list[dict[str, Any]] = []
        for sid in BASE_STATS:
            sdef = self.system.get_definition(sid)
            stat_details.append({
                "id": sid,
                "name": sdef.name if sdef else sid,
                "abbreviation": sdef.abbreviation if sdef else sid[:3].upper(),
                "base": base.get(sid, 0),
                "temp_modifier": state.temp_modifiers.get(sid, 0),
                "effective": effective.get(sid, 0),
            })

        derived_details: list[dict[str, Any]] = []
        for did, dval in derived.items():
            rule = self.system.get_derived_rule(did)
            derived_details.append({
                "id": did,
                "name": rule.name if rule else did,
                "value": round(dval, 2),
            })

        return {
            "character_id": character_id,
            "base_stats": base,
            "effective_stats": effective,
            "derived_stats": derived,
            "stat_details": stat_details,
            "derived_details": derived_details,
        }

    # --- Data loading -------------------------------------------------------

    def load_from_json(self, data_directory: str | None = None) -> None:
        """
        Load stat definitions and derived rules from character_stats.json.
        """
        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        path = os.path.join(data_directory, "character_stats.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        stat_defs = [StatDefinition.from_dict(s) for s in data.get("base_stats", [])]
        derived = [DerivedStatRule.from_dict(r) for r in data.get("derived_stats", [])]
        self.system = StatsSystem(stat_definitions=stat_defs, derived_rules=derived)

    # --- Serialization ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system.to_dict(),
            "character_states": {
                cid: s.to_dict() for cid, s in self.character_states.items()
            },
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StatsManager:
        mgr = StatsManager.__new__(StatsManager)
        mgr.system = StatsSystem.from_dict(data.get("system", {}))
        mgr.character_states = {}
        for cid, entry in data.get("character_states", {}).items():
            mgr.character_states[cid] = CharacterStatsState.from_dict(entry)
        return mgr
