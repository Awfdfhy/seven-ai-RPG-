"""
RPG-12-07: Endgame Systems
Provides post-game content tracking and New Game Plus (NG+) mechanics.
"""

from __future__ import annotations

import copy
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Post-game Content
# ---------------------------------------------------------------------------

@dataclass
class EndgameContentDefinition:
    """
    Static definition of a post-game content entry (raid, challenge, special quest).

    Attributes:
        id              : unique identifier (e.g. "void_raid")
        name            : human-readable display name
        description     : flavor / mechanical text
        category        : kind of content (raid | challenge | special_quest | bounties)
        difficulty      : intended difficulty (easy | medium | hard | nightmare)
        min_level       : minimum character level required
        prerequisites   : content ids that must be completed first
        rewards         : list of reward definitions
        world_effects   : list of world-state mutations to apply on completion
        metadata        : opaque extra data
    """

    id: str
    name: str
    description: str = ""
    category: str = "challenge"
    difficulty: str = "medium"
    min_level: int = 1
    prerequisites: list[str] = field(default_factory=list)
    rewards: list[dict[str, Any]] = field(default_factory=list)
    world_effects: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "difficulty": self.difficulty,
            "min_level": self.min_level,
            "prerequisites": list(self.prerequisites),
            "rewards": [copy.deepcopy(r) for r in self.rewards],
            "world_effects": [copy.deepcopy(e) for e in self.world_effects],
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> EndgameContentDefinition:
        return EndgameContentDefinition(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", "challenge"),
            difficulty=data.get("difficulty", "medium"),
            min_level=data.get("min_level", 1),
            prerequisites=list(data.get("prerequisites", [])),
            rewards=[copy.deepcopy(r) for r in data.get("rewards", [])],
            world_effects=[copy.deepcopy(e) for e in data.get("world_effects", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class EndgameContentState:
    """
    Tracks a character's progress on a specific endgame content entry.

    Attributes:
        character_id      : the character this state belongs to
        content_id        : references the EndgameContentDefinition
        status            : locked | available | in_progress | completed | failed
        best_score        : highest score achieved (if applicable)
        attempts          : number of times attempted
        completed_at      : ISO timestamp of first completion
        metadata          : opaque extra data (e.g. difficulty modifiers used)
    """

    character_id: str
    content_id: str
    status: str = "locked"
    best_score: int = 0
    attempts: int = 0
    completed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "content_id": self.content_id,
            "status": self.status,
            "best_score": self.best_score,
            "attempts": self.attempts,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> EndgameContentState:
        return EndgameContentState(
            character_id=data["character_id"],
            content_id=data["content_id"],
            status=data.get("status", "locked"),
            best_score=data.get("best_score", 0),
            attempts=data.get("attempts", 0),
            completed_at=data.get("completed_at"),
            metadata=dict(data.get("metadata", {})),
        )


class EndgameManager:
    """
    Manages post-game content definitions and per-character completion states.

    Integrates with world state by scoping progress to character_id and
    providing world effects that can be merged into world metadata.
    """

    def __init__(self, data_directory: str | None = None) -> None:
        self._definitions: dict[str, EndgameContentDefinition] = {}
        self._states: dict[str, EndgameContentState] = {}  # (character_id, content_id) -> state
        self._character_contents: dict[str, set[str]] = {}

        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self._load_endgame_content(data_directory)

    def _load_endgame_content(self, directory: str) -> None:
        import json
        import os

        path = os.path.join(directory, "endgame_content.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            entries = data if isinstance(data, list) else data.get("endgame_content", [])
            for entry in entries:
                d = EndgameContentDefinition.from_dict(entry)
                self.register_definition(d)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Definition management
    # ------------------------------------------------------------------

    def register_definition(self, definition: EndgameContentDefinition) -> None:
        self._definitions[definition.id] = definition

    def load_definitions(self, definitions: list[EndgameContentDefinition]) -> None:
        for d in definitions:
            self.register_definition(d)

    def get_definition(self, content_id: str) -> EndgameContentDefinition | None:
        return self._definitions.get(content_id)

    def list_definitions(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._definitions.values()]

    def get_available_definitions(self, character_level: int = 1) -> list[dict[str, Any]]:
        """
        Return endgame content definitions whose level prerequisites are met
        and that the character has not yet completed.
        """
        available = []
        for d in self._definitions.values():
            if d.min_level > character_level:
                continue
            if self._is_completed_for_any_character(d.id):
                # We still show it but mark as repeatable; filter logic is up to caller
                pass
            available.append(d.to_dict())
        return available

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _state_key(self, character_id: str, content_id: str) -> str:
        return f"{character_id}:{content_id}"

    def get_state(self, character_id: str, content_id: str) -> EndgameContentState | None:
        return self._states.get(self._state_key(character_id, content_id))

    def get_character_states(self, character_id: str) -> list[dict[str, Any]]:
        key_prefix = f"{character_id}:"
        states = [s for k, s in self._states.items() if k.startswith(key_prefix)]
        return sorted([s.to_dict() for s in states], key=lambda s: s["content_id"])

    def start_content(
        self,
        content_id: str,
        character_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> EndgameContentState | None:
        definition = self._definitions.get(content_id)
        if definition is None:
            return None

        key = self._state_key(character_id, content_id)
        state = self._states.get(key)
        if state is None:
            state = EndgameContentState(
                character_id=character_id,
                content_id=content_id,
                status="available",
                metadata=metadata or {},
            )
            self._states[key] = state
            self._character_contents.setdefault(character_id, set()).add(content_id)
            # Auto-start all other non-completed definitions for this character
            for cid, defn in self._definitions.items():
                if cid == content_id:
                    continue
                other_key = self._state_key(character_id, cid)
                if other_key not in self._states:
                    other_state = EndgameContentState(
                        character_id=character_id,
                        content_id=cid,
                        status="available",
                    )
                    self._states[other_key] = other_state
                    self._character_contents.setdefault(character_id, set()).add(cid)
        elif state.status == "locked":
            state.status = "available"

        return state

    def begin_attempt(
        self,
        content_id: str,
        character_id: str,
    ) -> EndgameContentState | None:
        state = self.get_state(character_id, content_id)
        if state is None:
            state = self.start_content(content_id, character_id)
        if state is None:
            return None
        if state.status == "locked":
            return None
        if state.status == "completed":
            state.status = "available"
        state.status = "in_progress"
        state.attempts += 1
        return state

    def complete_content(
        self,
        content_id: str,
        character_id: str,
        score: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> EndgameContentState | None:
        state = self.get_state(character_id, content_id)
        if state is None or state.status != "in_progress":
            return None
        state.status = "completed"
        state.completed_at = datetime.now(UTC).isoformat()
        if score > state.best_score:
            state.best_score = score
        if metadata:
            state.metadata.update(metadata)
        return state

    def fail_content(
        self,
        content_id: str,
        character_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> EndgameContentState | None:
        state = self.get_state(character_id, content_id)
        if state is None or state.status != "in_progress":
            return None
        state.status = "available"
        if metadata:
            state.metadata.update(metadata)
        return state

    def reset_progress(
        self,
        content_id: str,
        character_id: str,
    ) -> EndgameContentState | None:
        key = self._state_key(character_id, content_id)
        state = self._states.get(key)
        if state is None:
            return None
        state.status = "locked"
        state.best_score = 0
        state.attempts = 0
        state.completed_at = None
        state.metadata.clear()
        return state

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_completed_content(self, character_id: str) -> list[str]:
        key_prefix = f"{character_id}:"
        completed = []
        for k, s in self._states.items():
            if k.startswith(key_prefix) and s.status == "completed":
                completed.append(s.content_id)
        return sorted(completed)

    def get_content_stats(self, character_id: str) -> dict[str, Any]:
        key_prefix = f"{character_id}:"
        states = [s for k, s in self._states.items() if k.startswith(key_prefix)]
        total_attempts = sum(s.attempts for s in states)
        completed = sum(1 for s in states if s.status == "completed")
        return {
            "character_id": character_id,
            "total_attempts": total_attempts,
            "completed_count": completed,
            "in_progress_count": sum(1 for s in states if s.status == "in_progress"),
            "available_count": sum(1 for s in states if s.status == "available"),
            "locked_count": sum(1 for s in states if s.status == "locked"),
        }

    def get_world_effects(self, character_id: str) -> list[dict[str, Any]]:
        """
        Aggregate world effects from completed endgame content for a character.
        """
        effects: list[dict[str, Any]] = []
        key_prefix = f"{character_id}:"
        for k, s in self._states.items():
            if k.startswith(key_prefix) and s.status == "completed":
                definition = self._definitions.get(s.content_id)
                if definition:
                    effects.extend(copy.deepcopy(definition.world_effects))
        return effects

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "definitions": {cid: d.to_dict() for cid, d in self._definitions.items()},
            "states": {k: s.to_dict() for k, s in self._states.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._states.clear()
        self._character_contents.clear()
        for cid, ddata in state.get("definitions", {}).items():
            self._definitions[cid] = EndgameContentDefinition.from_dict(ddata)
        for k, sdata in state.get("states", {}).items():
            self._states[k] = EndgameContentState.from_dict(sdata)
            char_id = sdata["character_id"]
            self._character_contents.setdefault(char_id, set()).add(sdata["content_id"])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_completed_for_any_character(self, content_id: str) -> bool:
        for s in self._states.values():
            if s.content_id == content_id and s.status == "completed":
                return True
        return False


# ---------------------------------------------------------------------------
# New Game Plus
# ---------------------------------------------------------------------------

@dataclass
class NGPlusProfile:
    """
    Configuration for a New Game Plus run.

    Attributes:
        profile_id      : unique identifier
        name            : display name (e.g. "NG+ Cycle 2")
        difficulty_mult : multiplier applied to enemy stats / XP curve
        carried_over_stats : which character stats persist into NG+
        carried_over_items : which inventory items persist into NG+
        unlocked_features : special features unlocked in this NG+ cycle
        world_seed      : optional seed for deterministic world generation
        metadata        : opaque extra data
    """

    profile_id: str
    name: str
    difficulty_mult: float = 1.0
    carried_over_stats: list[str] = field(default_factory=list)
    carried_over_items: list[str] = field(default_factory=list)
    unlocked_features: list[str] = field(default_factory=list)
    world_seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "difficulty_mult": self.difficulty_mult,
            "carried_over_stats": list(self.carried_over_stats),
            "carried_over_items": list(self.carried_over_items),
            "unlocked_features": list(self.unlocked_features),
            "world_seed": self.world_seed,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NGPlusProfile:
        return NGPlusProfile(
            profile_id=data["profile_id"],
            name=data.get("name", ""),
            difficulty_mult=data.get("difficulty_mult", 1.0),
            carried_over_stats=list(data.get("carried_over_stats", [])),
            carried_over_items=list(data.get("carried_over_items", [])),
            unlocked_features=list(data.get("unlocked_features", [])),
            world_seed=data.get("world_seed"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class NGPlusRun:
    """
    Runtime record for an active or completed New Game Plus run.

    Attributes:
        run_id          : unique identifier
        character_id    : the character entering NG+
        base_world_id   : the original world being replayed
        profile_id      : references the NGPlusProfile used
        cycle           : which NG+ cycle number (1 = first NG+, 2 = second, etc.)
        started_at      : ISO timestamp
        status          : active | completed | abandoned
        bonus_points    : accumulated NG+ bonus points
        completed_at    : ISO timestamp if completed
        metadata        : opaque extra data
    """

    run_id: str
    character_id: str
    base_world_id: str
    profile_id: str
    cycle: int = 1
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "active"
    bonus_points: int = 0
    completed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "character_id": self.character_id,
            "base_world_id": self.base_world_id,
            "profile_id": self.profile_id,
            "cycle": self.cycle,
            "started_at": self.started_at,
            "status": self.status,
            "bonus_points": self.bonus_points,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NGPlusRun:
        return NGPlusRun(
            run_id=data["run_id"],
            character_id=data["character_id"],
            base_world_id=data["base_world_id"],
            profile_id=data["profile_id"],
            cycle=data.get("cycle", 1),
            started_at=data.get("started_at", ""),
            status=data.get("status", "active"),
            bonus_points=data.get("bonus_points", 0),
            completed_at=data.get("completed_at"),
            metadata=dict(data.get("metadata", {})),
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
        return sorted([r.to_dict() for r in runs], key=lambda r: r.cycle)

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
