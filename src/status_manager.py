"""
RPG-08-08: Status Conditions Manager
Orchestrates applying, ticking, and cleaning up status conditions
on characters.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from status_conditions import (
    ActiveStatusCondition,
    StatusCondition,
    StatusConditionTickResult,
    StatusConditionType,
)


class StatusManager:
    """
    Manages active status conditions per character.

    Stores active conditions, supports stacking, ticking over time,
    and querying which conditions are currently in effect.
    """

    def __init__(self, data_directory: str | None = None) -> None:
        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self.definitions: dict[str, StatusCondition] = {}
        self.active: dict[tuple[str, str], ActiveStatusCondition] = {}
        self._load_definitions(data_directory)

    # --- definition management --------------------------------------------------

    def register_definition(self, condition: StatusCondition) -> None:
        self.definitions[condition.id] = condition

    def get_definition(self, condition_id: str) -> StatusCondition | None:
        return self.definitions.get(condition_id)

    def load_definitions_from_dicts(self, data: list[dict[str, Any]]) -> None:
        for item in data:
            condition = StatusCondition.from_dict(item)
            self.register_definition(condition)

    def _load_definitions(self, directory: str) -> None:
        path = os.path.join(directory, "status_conditions.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for item in data.get("conditions", []):
            condition = StatusCondition.from_dict(item)
            self.register_definition(condition)

    # --- querying ---------------------------------------------------------------

    def get_active_conditions(self, character_id: str) -> list[ActiveStatusCondition]:
        return [
            active for (cid, _), active in self.active.items() if cid == character_id
        ]

    def has_condition(self, character_id: str, condition_id: str) -> bool:
        return (character_id, condition_id) in self.active

    def count_stacks(self, character_id: str, condition_id: str) -> int:
        active = self.active.get((character_id, condition_id))
        return active.stacks if active else 0

    def is_action_prevented(self, character_id: str) -> bool:
        for (cid, cond_id), active in self.active.items():
            if cid != character_id:
                continue
            definition = self.definitions.get(cond_id)
            if definition and definition.prevents_actions:
                return True
        return False

    def is_stunned(self, character_id: str) -> bool:
        return self.has_condition(character_id, "stun") or self.has_condition(
            character_id, "paralyze"
        )

    def get_prevented_action_types(self, character_id: str) -> list[str]:
        prevented: list[str] = []
        for (cid, cond_id), active in self.active.items():
            if cid != character_id:
                continue
            definition = self.definitions.get(cond_id)
            if not definition or not definition.prevents_actions:
                continue
            if cond_id in ("stun", "paralyze", "freeze"):
                prevented.append("all")
            elif cond_id == "silence":
                prevented.append("magic")
            elif cond_id == "root":
                prevented.append("movement")
            elif cond_id == "blind":
                prevented.append("attack")
        return prevented

    # --- applying / removing ---------------------------------------------------

    def apply_condition(
        self,
        character_id: str,
        condition_id: str,
        current_time: float | None = None,
        stacks: int = 1,
        source_ability_id: str = "",
        source_character_id: str = "",
        extra: dict[str, Any] | None = None,
        duration_multiplier: float = 1.0,
    ) -> ActiveStatusCondition | None:
        definition = self.definitions.get(condition_id)
        if definition is None:
            return None

        if current_time is None:
            current_time = time.time()

        key = (character_id, condition_id)
        existing = self.active.get(key)

        scaled_duration = definition.duration_seconds * duration_multiplier

        if existing is not None:
            # refresh duration and add stacks up to max
            existing.remaining_duration = scaled_duration
            existing.stacks = min(existing.stacks + stacks, definition.max_stacks)
            existing.last_tick_at = current_time
            if extra:
                existing.extra.update(extra)
            return existing

        active = ActiveStatusCondition(
            condition_id=condition_id,
            character_id=character_id,
            stacks=min(stacks, definition.max_stacks),
            remaining_duration=scaled_duration,
            applied_at=current_time,
            last_tick_at=current_time,
            source_ability_id=source_ability_id,
            source_character_id=source_character_id,
            extra=extra or {},
        )
        self.active[key] = active
        return active

    def remove_condition(self, character_id: str, condition_id: str) -> bool:
        key = (character_id, condition_id)
        if key in self.active:
            del self.active[key]
            return True
        return False

    def remove_conditions_by_type(
        self, character_id: str, condition_type: StatusConditionType
    ) -> list[str]:
        removed = []
        for key in list(self.active.keys()):
            cid, cond_id = key
            if cid == character_id:
                definition = self.definitions.get(cond_id)
                if definition and definition.condition_type == condition_type:
                    del self.active[key]
                    removed.append(cond_id)
        return removed

    def cleanse(self, character_id: str) -> list[str]:
        cleansed = []
        for key in list(self.active.keys()):
            cid, cond_id = key
            if cid != character_id:
                continue
            definition = self.definitions.get(cond_id)
            if definition and definition.can_be_cleansed:
                del self.active[key]
                cleansed.append(cond_id)
        return cleansed

    def clear_all(self, character_id: str) -> None:
        for key in list(self.active.keys()):
            if key[0] == character_id:
                del self.active[key]

    # --- ticking / time advancement ---------------------------------------------

    def tick(
        self, character_id: str, current_time: float | None = None
    ) -> list[StatusConditionTickResult]:
        if current_time is None:
            current_time = time.time()

        tick_results: list[StatusConditionTickResult] = []

        for key, active in list(self.active.items()):
            cid, cond_id = key
            if cid != character_id:
                continue

            definition = self.definitions.get(cond_id)
            if definition is None:
                continue

            # advance time
            dt = current_time - active.last_tick_at if active.last_tick_at else 0.0
            active.remaining_duration -= dt
            active.last_tick_at = current_time

            # process tick effects
            if (
                definition.tick_interval_seconds > 0
                and active.remaining_duration > 0
                and active.last_tick_at - active.applied_at > 0
            ):
                # simplified tick: if we crossed a tick interval boundary
                tick_damage = 0.0
                tick_healing = 0.0
                for effect in definition.effects:
                    if effect.tick_value != 0.0:
                        if cond_id in ("poison", "burn"):
                            tick_damage += effect.tick_value * active.stacks
                        elif cond_id == "heal_over_time":
                            tick_healing += effect.tick_value * active.stacks
                if tick_damage or tick_healing:
                    tick_results.append(
                        StatusConditionTickResult(
                            condition_id=cond_id,
                            character_id=character_id,
                            damage=tick_damage,
                            healing=tick_healing,
                            expired=active.remaining_duration <= 0,
                        )
                    )

            if active.remaining_duration <= 0:
                tick_results.append(
                    StatusConditionTickResult(
                        condition_id=cond_id,
                        character_id=character_id,
                        expired=True,
                    )
                )
                del self.active[key]

        return tick_results

    def tick_all(
        self, current_time: float | None = None
    ) -> dict[str, list[StatusConditionTickResult]]:
        if current_time is None:
            current_time = time.time()

        character_ids = {cid for cid, _ in self.active.keys()}
        results: dict[str, list[StatusConditionTickResult]] = {}
        for character_id in character_ids:
            results[character_id] = self.tick(character_id, current_time)
        return results

    # --- serialization ----------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "definitions": {k: v.to_dict() for k, v in self.definitions.items()},
            "active": [
                active.to_dict() for active in self.active.values()
            ],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StatusManager:
        manager = StatusManager()
        for defn_data in data.get("definitions", {}).values():
            condition = StatusCondition.from_dict(defn_data)
            manager.register_definition(condition)
        for active_data in data.get("active", []):
            active = ActiveStatusCondition.from_dict(active_data)
            manager.active[(active.character_id, active.condition_id)] = active
        return manager
