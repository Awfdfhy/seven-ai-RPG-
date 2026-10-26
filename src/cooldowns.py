"""
RPG-08-07: Cooldowns
Core cooldown tracking for abilities, skills, and actions.

Supports:
  - Per-ability cooldowns
  - Shared cooldown groups (e.g. all fire spells share a group timer)
  - Global cooldown shared across all abilities
  - Cooldown reduction modifiers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CooldownEntry:
    """A single tracked cooldown."""

    ability_id: str
    ready_at: float = 0.0
    started_at: float = 0.0

    def is_ready(self, current_time: float) -> bool:
        return current_time >= self.ready_at

    def remaining(self, current_time: float) -> float:
        return max(0.0, self.ready_at - current_time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ability_id": self.ability_id,
            "ready_at": self.ready_at,
            "started_at": self.started_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CooldownEntry:
        return CooldownEntry(
            ability_id=data["ability_id"],
            ready_at=data.get("ready_at", 0.0),
            started_at=data.get("started_at", 0.0),
        )


@dataclass
class CooldownManager:
    """
    Per-character cooldown tracker.

    Tracks individual ability cooldowns, shared group cooldowns, and an
    optional global cooldown that blocks all ability use.
    """

    character_id: str
    entries: dict[str, CooldownEntry] = field(default_factory=dict)
    group_entries: dict[str, CooldownEntry] = field(default_factory=dict)
    global_cooldown_until: float = 0.0
    reduction: float = 0.0  # 0.0 – 1.0 fraction to reduce cooldowns by

    def _apply_reduction(self, seconds: float) -> float:
        if self.reduction > 0:
            return seconds * (1.0 - self.reduction)
        return seconds

    def start_cooldown(
        self,
        ability_id: str,
        cooldown_seconds: float,
        current_time: float,
        group: str | None = None,
    ) -> None:
        adjusted = self._apply_reduction(cooldown_seconds)
        self.entries[ability_id] = CooldownEntry(
            ability_id=ability_id,
            ready_at=current_time + adjusted,
            started_at=current_time,
        )
        if group:
            # Take the longest remaining group cooldown
            existing = self.group_entries.get(group)
            new_ready_at = current_time + adjusted
            if existing is None or new_ready_at > existing.ready_at:
                self.group_entries[group] = CooldownEntry(
                    ability_id=ability_id,
                    ready_at=new_ready_at,
                    started_at=current_time,
                )

    def start_global_cooldown(self, cooldown_seconds: float, current_time: float) -> None:
        self.global_cooldown_until = current_time + self._apply_reduction(cooldown_seconds)

    def is_on_cooldown(self, ability_id: str, current_time: float) -> bool:
        entry = self.entries.get(ability_id)
        if entry is not None and not entry.is_ready(current_time):
            return True
        return current_time < self.global_cooldown_until

    def get_cooldown_remaining(self, ability_id: str, current_time: float) -> float:
        entry = self.entries.get(ability_id)
        individual = entry.remaining(current_time) if entry else 0.0
        global_remaining = max(0.0, self.global_cooldown_until - current_time)
        return max(individual, global_remaining)

    def get_cooldown_ready_at(self, ability_id: str) -> float:
        entry = self.entries.get(ability_id)
        return entry.ready_at if entry else 0.0

    def is_group_on_cooldown(self, group: str, current_time: float) -> bool:
        entry = self.group_entries.get(group)
        return entry is not None and not entry.is_ready(current_time)

    def get_group_cooldown_remaining(self, group: str, current_time: float) -> float:
        entry = self.group_entries.get(group)
        return entry.remaining(current_time) if entry else 0.0

    def can_use(
        self,
        ability_id: str,
        current_time: float,
        group: str | None = None,
    ) -> tuple[bool, str]:
        if self.is_on_cooldown(ability_id, current_time):
            remaining = self.get_cooldown_remaining(ability_id, current_time)
            return False, f"On cooldown ({remaining:.1f}s remaining)."
        if group and self.is_group_on_cooldown(group, current_time):
            remaining = self.get_group_cooldown_remaining(group, current_time)
            return False, f"Group on cooldown ({remaining:.1f}s remaining)."
        return True, ""

    def use(
        self,
        ability_id: str,
        cooldown_seconds: float,
        current_time: float,
        group: str | None = None,
    ) -> tuple[bool, str]:
        ok, reason = self.can_use(ability_id, current_time, group)
        if not ok:
            return False, reason
        self.start_cooldown(ability_id, cooldown_seconds, current_time, group)
        return True, ""

    def clear_cooldown(self, ability_id: str) -> None:
        self.entries.pop(ability_id, None)

    def clear_group_cooldown(self, group: str) -> None:
        self.group_entries.pop(group, None)

    def clear_all_cooldowns(self) -> None:
        self.entries.clear()
        self.group_entries.clear()
        self.global_cooldown_until = 0.0

    def tick(self, current_time: float) -> list[str]:
        """Remove expired cooldowns. Returns list of expired ability_ids."""
        expired = []
        for ability_id, entry in list(self.entries.items()):
            if entry.is_ready(current_time):
                expired.append(ability_id)
                del self.entries[ability_id]
        return expired

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "entries": {aid: e.to_dict() for aid, e in self.entries.items()},
            "group_entries": {g: e.to_dict() for g, e in self.group_entries.items()},
            "global_cooldown_until": self.global_cooldown_until,
            "reduction": self.reduction,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CooldownManager:
        mgr = CooldownManager(
            character_id=data["character_id"],
            global_cooldown_until=data.get("global_cooldown_until", 0.0),
            reduction=data.get("reduction", 0.0),
        )
        for aid, edata in data.get("entries", {}).items():
            mgr.entries[aid] = CooldownEntry.from_dict(edata)
        for g, edata in data.get("group_entries", {}).items():
            mgr.group_entries[g] = CooldownEntry.from_dict(edata)
        return mgr
