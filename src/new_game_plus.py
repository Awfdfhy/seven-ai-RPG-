"""
RPG-12-07: New Game Plus System
Manages NG+ profiles, active runs, carry-over bonuses, and difficulty scaling
for post-game replayability.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

# Re-export NGPlusProfile and NGPlusRun for convenience
from endgame import (
    NGPlusProfile,
    NGPlusRun,
)


class NGPlusManager:
    """
    Manages New Game Plus profiles and active runs.

    Integrates with progression by providing XP curve modifiers and
    with world_session by marking sessions as NG+ runs.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, NGPlusProfile] = {}
        self._runs: dict[str, NGPlusRun] = {}

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def create_profile(
        self,
        name: str,
        difficulty_mult: float = 1.0,
        carried_over_stats: list[str] | None = None,
        carried_over_items: list[str] | None = None,
        unlocked_features: list[str] | None = None,
        world_seed: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> NGPlusProfile:
        profile_id = str(uuid.uuid4())
        profile = NGPlusProfile(
            profile_id=profile_id,
            name=name,
            difficulty_mult=difficulty_mult,
            carried_over_stats=carried_over_stats or [],
            carried_over_items=carried_over_items or [],
            unlocked_features=unlocked_features or [],
            world_seed=world_seed,
            metadata=metadata or {},
        )
        self._profiles[profile_id] = profile
        return profile

    def get_profile(self, profile_id: str) -> NGPlusProfile | None:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in sorted(self._profiles.values(), key=lambda p: p.difficulty_mult)]

    # ------------------------------------------------------------------
    # Run management
    # ------------------------------------------------------------------

    def start_run(
        self,
        character_id: str,
        base_world_id: str,
        profile_id: str,
        cycle: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> NGPlusRun | None:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None

        run_id = str(uuid.uuid4())
        effective_cycle = cycle if cycle is not None else (self._max_cycle_for_character(character_id) + 1)
        run = NGPlusRun(
            run_id=run_id,
            character_id=character_id,
            base_world_id=base_world_id,
            profile_id=profile_id,
            cycle=effective_cycle,
            metadata=metadata or {},
        )
        self._runs[run_id] = run
        return run

    def get_run(self, run_id: str) -> NGPlusRun | None:
        return self._runs.get(run_id)

    def list_runs(self, character_id: str | None = None) -> list[dict[str, Any]]:
        runs = list(self._runs.values())
        if character_id is not None:
            runs = [r for r in runs if r.character_id == character_id]
        return [r.to_dict() for r in sorted(runs, key=lambda r: r.cycle)]

    def complete_run(self, run_id: str) -> NGPlusRun | None:
        run = self._runs.get(run_id)
        if run is None or run.status != "active":
            return None
        run.status = "completed"
        run.completed_at = datetime.now(UTC).isoformat()
        return run

    def abandon_run(self, run_id: str) -> NGPlusRun | None:
        run = self._runs.get(run_id)
        if run is None or run.status != "active":
            return None
        run.status = "abandoned"
        return run

    def award_bonus_points(self, run_id: str, points: int) -> NGPlusRun | None:
        run = self._runs.get(run_id)
        if run is None or run.status != "active":
            return None
        run.bonus_points += points
        return run

    def get_active_run(self, character_id: str) -> NGPlusRun | None:
        for run in self._runs.values():
            if run.character_id == character_id and run.status == "active":
                return run
        return None

    def get_highest_cycle(self, character_id: str) -> int:
        return self._max_cycle_for_character(character_id)

    # ------------------------------------------------------------------
    # Carry-over logic
    # ------------------------------------------------------------------

    def get_carry_over_stats(
        self,
        character_id: str,
        current_stats: dict[str, int],
    ) -> dict[str, int]:
        """
        Return the subset of current_stats that should carry over into NG+
        based on the active run's profile.
        """
        run = self.get_active_run(character_id)
        if run is None:
            return {}
        profile = self._profiles.get(run.profile_id)
        if profile is None:
            return {}
        return {stat: current_stats.get(stat, 0) for stat in profile.carried_over_stats}

    def get_carry_over_items(
        self,
        character_id: str,
        current_inventory: list[str],
    ) -> list[str]:
        """
        Return the subset of current_inventory items that should carry over
        into NG+ based on the active run's profile.
        """
        run = self.get_active_run(character_id)
        if run is None:
            return []
        profile = self._profiles.get(run.profile_id)
        if profile is None:
            return []
        allowed = set(profile.carried_over_items)
        return [item for item in current_inventory if item in allowed]

    # ------------------------------------------------------------------
    # XP curve integration
    # ------------------------------------------------------------------

    def get_ng_xp_multiplier(self, character_id: str) -> float:
        """
        Return the XP curve multiplier to apply for NG+ runs.
        """
        run = self.get_active_run(character_id)
        if run is None:
            return 1.0
        profile = self._profiles.get(run.profile_id)
        if profile is None:
            return 1.0
        return profile.difficulty_mult

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "profiles": {pid: p.to_dict() for pid, p in self._profiles.items()},
            "runs": {rid: r.to_dict() for rid, r in self._runs.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._profiles.clear()
        self._runs.clear()
        for pid, pdata in state.get("profiles", {}).items():
            self._profiles[pid] = NGPlusProfile.from_dict(pdata)
        for rid, rdata in state.get("runs", {}).items():
            self._runs[rid] = NGPlusRun.from_dict(rdata)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _max_cycle_for_character(self, character_id: str) -> int:
        max_cycle = 0
        for run in self._runs.values():
            if run.character_id == character_id and run.status == "completed":
                if run.cycle > max_cycle:
                    max_cycle = run.cycle
        return max_cycle
