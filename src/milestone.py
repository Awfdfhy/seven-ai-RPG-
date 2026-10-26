"""
RPG-08-11: Milestones
Tracks major story milestones and world events that affect world state
and narration. Milestones act as permanent markers of significant
world progress and can unlock regions, modify NPC reactions, and
trigger narrative text.
"""

from __future__ import annotations

import copy
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

@dataclass
class MilestoneDefinition:
    """
    Static definition of a milestone.

    Attributes:
        id              : unique identifier (e.g. "defeat_dragon")
        name            : human-readable display name
        description     : flavor / mechanical text
        category        : kind of milestone (story | world | character | faction)
        world_effects   : list of world-state mutations to apply on trigger
                          e.g. [{"type": "unlock_region", "region": "ashlands"}]
        narration_hooks : list of narration templates to inject on trigger
                          e.g. [{"scope": "region", "target": "oakhaven",
                                  "template": "The village celebrates your victory."}]
        prerequisites   : milestone ids that must be achieved first
        metadata        : opaque extra data
    """

    id: str
    name: str
    description: str = ""
    category: str = "story"
    world_effects: list[dict[str, Any]] = field(default_factory=list)
    narration_hooks: list[dict[str, Any]] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "world_effects": [copy.deepcopy(e) for e in self.world_effects],
            "narration_hooks": [copy.deepcopy(h) for h in self.narration_hooks],
            "prerequisites": list(self.prerequisites),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MilestoneDefinition:
        return MilestoneDefinition(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", "story"),
            world_effects=[copy.deepcopy(e) for e in data.get("world_effects", [])],
            narration_hooks=[copy.deepcopy(h) for h in data.get("narration_hooks", [])],
            prerequisites=list(data.get("prerequisites", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class MilestoneEvent:
    """
    Runtime record for one milestone instance triggered within a world.

    Attributes:
        milestone_id   : references the MilestoneDefinition
        world_id       : the world this milestone belongs to
        session_id     : optional session that triggered it
        triggered_at   : ISO timestamp
        status         : achieved | failed | hidden
        effects_applied: snapshot of world_effects that were applied
        metadata       : opaque extra data
    """

    event_id: str
    milestone_id: str
    world_id: str
    triggered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    session_id: str | None = None
    status: str = "achieved"
    effects_applied: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "milestone_id": self.milestone_id,
            "world_id": self.world_id,
            "triggered_at": self.triggered_at,
            "session_id": self.session_id,
            "status": self.status,
            "effects_applied": [copy.deepcopy(e) for e in self.effects_applied],
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MilestoneEvent:
        return MilestoneEvent(
            event_id=data["event_id"],
            milestone_id=data["milestone_id"],
            world_id=data["world_id"],
            triggered_at=data.get("triggered_at", ""),
            session_id=data.get("session_id"),
            status=data.get("status", "achieved"),
            effects_applied=[copy.deepcopy(e) for e in data.get("effects_applied", [])],
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class MilestoneManager:
    """
    Manages milestone definitions and runtime events across worlds/sessions.

    Integrates with world state by scoping milestones to a world_id and
    providing world effects that can be merged into world metadata.
    """

    def __init__(self, data_directory: str | None = None) -> None:
        self._events: dict[str, MilestoneEvent] = {}
        self._definitions: dict[str, MilestoneDefinition] = {}
        self._session_milestones: dict[str, set[str]] = {}
        self._world_milestones: dict[str, set[str]] = {}

        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self._load_milestones(data_directory)

    def _load_milestones(self, directory: str) -> None:
        import json

        path = os.path.join(directory, "milestones.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            entries = data if isinstance(data, list) else data.get("milestones", [])
            for entry in entries:
                d = MilestoneDefinition.from_dict(entry)
                self.register_definition(d)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Definition loading
    # ------------------------------------------------------------------

    def register_definition(self, definition: MilestoneDefinition) -> None:
        self._definitions[definition.id] = definition

    def load_definitions(self, definitions: list[MilestoneDefinition]) -> None:
        for d in definitions:
            self.register_definition(d)

    def get_definition(self, milestone_id: str) -> MilestoneDefinition | None:
        return self._definitions.get(milestone_id)

    def list_definitions(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._definitions.values()]

    # ------------------------------------------------------------------
    # Triggering
    # ------------------------------------------------------------------

    def _prerequisites_met(self, milestone_id: str, world_id: str) -> bool:
        definition = self._definitions.get(milestone_id)
        if definition is None:
            return False
        for prereq_id in definition.prerequisites:
            found = any(
                e.milestone_id == prereq_id and e.world_id == world_id and e.status == "achieved"
                for e in self._events.values()
            )
            if not found:
                return False
        return True

    def trigger_milestone(
        self,
        milestone_id: str,
        world_id: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MilestoneEvent | None:
        """
        Trigger a milestone in a world. Returns None if prerequisites are
        not met or the definition does not exist. If the milestone was
        already triggered, returns the existing event.
        """
        definition = self._definitions.get(milestone_id)
        if definition is None:
            return None

        existing = self._get_existing_event(milestone_id, world_id)
        if existing is not None:
            return existing

        if not self._prerequisites_met(milestone_id, world_id):
            return None

        event = MilestoneEvent(
            event_id=str(uuid.uuid4()),
            milestone_id=milestone_id,
            world_id=world_id,
            session_id=session_id,
            status="achieved",
            effects_applied=[
                copy.deepcopy(e) for e in definition.world_effects
            ],
            metadata=metadata or {},
        )
        self._events[event.event_id] = event
        self._world_milestones.setdefault(world_id, set()).add(milestone_id)
        if session_id:
            self._session_milestones.setdefault(session_id, set()).add(milestone_id)
        return event

    def _get_existing_event(self, milestone_id: str, world_id: str) -> MilestoneEvent | None:
        for event in self._events.values():
            if event.milestone_id == milestone_id and event.world_id == world_id:
                return event
        return None

    def fail_milestone(self, event_id: str, reason: str = "") -> MilestoneEvent | None:
        event = self._events.get(event_id)
        if event is None or event.status != "achieved":
            return None
        event.status = "failed"
        if reason:
            event.metadata.setdefault("failure_reasons", []).append(reason)
        return event

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_event(self, event_id: str) -> MilestoneEvent | None:
        return self._events.get(event_id)

    def get_world_milestone_event(self, milestone_id: str, world_id: str) -> MilestoneEvent | None:
        return self._get_existing_event(milestone_id, world_id)

    def list_events(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        events = list(self._events.values())
        if world_id is not None:
            events = [e for e in events if e.world_id == world_id]
        if session_id is not None:
            events = [e for e in events if e.session_id == session_id]
        if status is not None:
            events = [e for e in events if e.status == status]
        return [e.to_dict() for e in sorted(events, key=lambda e: e.triggered_at)]

    def list_achieved(self, world_id: str | None = None) -> list[dict[str, Any]]:
        return self.list_events(world_id=world_id, status="achieved")

    def list_failed(self, world_id: str | None = None) -> list[dict[str, Any]]:
        return self.list_events(world_id=world_id, status="failed")

    # ------------------------------------------------------------------
    # World state integration
    # ------------------------------------------------------------------

    def get_world_effects(self, world_id: str) -> list[dict[str, Any]]:
        """
        Aggregate all world effects from achieved milestones for a world.
        """
        effects: list[dict[str, Any]] = []
        for event in self._events.values():
            if event.world_id == world_id and event.status == "achieved":
                effects.extend(event.effects_applied)
        return effects

    def get_narration_hooks(self, world_id: str, scope: str | None = None) -> list[dict[str, Any]]:
        """
        Collect narration hooks from achieved milestones, optionally
        filtered by scope (e.g. "region", "global").
        """
        hooks: list[dict[str, Any]] = []
        for event in self._events.values():
            if event.world_id != world_id or event.status != "achieved":
                continue
            definition = self._definitions.get(event.milestone_id)
            if definition is None:
                continue
            for hook in definition.narration_hooks:
                if scope is None or hook.get("scope") == scope:
                    hooks.append(copy.deepcopy(hook))
        return hooks

    def get_available_milestones(self, world_id: str) -> list[dict[str, Any]]:
        """
        Return milestone definitions whose prerequisites are met in the
        given world but that have not yet been triggered.
        """
        available = []
        for mid, definition in self._definitions.items():
            if self._get_existing_event(mid, world_id) is not None:
                continue
            if self._prerequisites_met(mid, world_id):
                available.append(definition.to_dict())
        return available

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "events": {eid: e.to_dict() for eid, e in self._events.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._events.clear()
        self._session_milestones.clear()
        self._world_milestones.clear()
        for eid, edata in state.get("events", {}).items():
            event = MilestoneEvent.from_dict(edata)
            self._events[eid] = event
            self._world_milestones.setdefault(event.world_id, set()).add(event.milestone_id)
            if event.session_id:
                self._session_milestones.setdefault(event.session_id, set()).add(event.milestone_id)
