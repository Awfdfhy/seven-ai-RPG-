"""
RPG Session Timeline: chronological play history for a session.

Tracks what happened during a play session — quests, combat, travel,
progression, and so on — so it can be rendered as a timeline or exported
for save-game persistence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

class TimelineEventType:
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    QUEST_STARTED = "quest_started"
    QUEST_COMPLETED = "quest_completed"
    QUEST_FAILED = "quest_failed"
    QUEST_ABANDONED = "quest_abandoned"
    COMBAT_STARTED = "combat_started"
    COMBAT_ENDED = "combat_ended"
    LEVEL_UP = "level_up"
    TRAVEL_STARTED = "travel_started"
    TRAVEL_COMPLETED = "travel_completed"
    LOOT_RECEIVED = "loot_received"
    ABILITY_USED = "ability_used"
    NPC_INTERACTION = "npc_interaction"
    CRAFTING_COMPLETED = "crafting_completed"
    STATUS_APPLIED = "status_applied"
    CHECKPOINT_CREATED = "checkpoint_created"
    BRANCH_CREATED = "branch_created"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Timeline entry
# ---------------------------------------------------------------------------

@dataclass
class TimelineEntry:
    """
    One atomic event in a session timeline.

    Attributes:
        entry_id       : unique identifier
        session_id     : the play session this belongs to
        branch_id      : optional branch within the session
        event_type     : one of the TimelineEventType constants
        world_id       : world this occurred in
        character_id   : optional character identifier
        occurred_at    : ISO timestamp
        title          : human-readable headline
        description    : optional longer description
        data           : event-specific payload
        metadata       : opaque extra fields
    """

    event_type: str
    session_id: str
    world_id: str = ""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    branch_id: str | None = None
    character_id: str | None = None
    occurred_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    title: str = ""
    description: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "session_id": self.session_id,
            "branch_id": self.branch_id,
            "event_type": self.event_type,
            "world_id": self.world_id,
            "character_id": self.character_id,
            "occurred_at": self.occurred_at,
            "title": self.title,
            "description": self.description,
            "data": dict(self.data),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TimelineEntry:
        return TimelineEntry(
            entry_id=data["entry_id"],
            session_id=data["session_id"],
            branch_id=data.get("branch_id"),
            event_type=data["event_type"],
            world_id=data.get("world_id", ""),
            character_id=data.get("character_id"),
            occurred_at=data.get("occurred_at", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            data=dict(data.get("data", {})),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class SessionTimelineManager:
    """
    Creates, indexes, and queries timeline entries for play sessions.
    """

    def __init__(self) -> None:
        self._entries: dict[str, TimelineEntry] = {}
        self._session_entries: dict[str, list[str]] = {}
        self._branch_entries: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        event_type: str,
        session_id: str,
        world_id: str = "",
        branch_id: str | None = None,
        character_id: str | None = None,
        title: str = "",
        description: str = "",
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        occurred_at: str | None = None,
    ) -> TimelineEntry:
        """
        Record a new timeline entry.
        """
        entry = TimelineEntry(
            event_type=event_type,
            session_id=session_id,
            world_id=world_id,
            branch_id=branch_id,
            character_id=character_id,
            title=title,
            description=description,
            data=data or {},
            metadata=metadata or {},
            occurred_at=occurred_at or datetime.now(UTC).isoformat(),
        )
        self._entries[entry.entry_id] = entry
        self._session_entries.setdefault(session_id, []).append(entry.entry_id)
        if branch_id is not None:
            self._branch_entries.setdefault(branch_id, []).append(entry.entry_id)
        return entry

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_entry(self, entry_id: str) -> TimelineEntry | None:
        return self._entries.get(entry_id)

    def get_session_timeline(
        self,
        session_id: str,
        branch_id: str | None = None,
        event_type: str | None = None,
        limit: int = 500,
        reverse: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Return a chronological timeline for a session, optionally filtered
        by branch and event type.
        """
        entry_ids = self._session_entries.get(session_id, [])
        entries = [self._entries[eid] for eid in entry_ids if eid in self._entries]

        if branch_id is not None:
            branch_ids = set(self._branch_entries.get(branch_id, []))
            entries = [e for e in entries if e.entry_id in branch_ids]

        if event_type is not None:
            entries = [e for e in entries if e.event_type == event_type]

        entries.sort(key=lambda e: e.occurred_at, reverse=reverse)
        return [e.to_dict() for e in entries[:limit]]

    def get_branch_timeline(
        self,
        branch_id: str,
        event_type: str | None = None,
        limit: int = 500,
        reverse: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Return a chronological timeline for a specific branch.
        """
        entry_ids = self._branch_entries.get(branch_id, [])
        entries = [self._entries[eid] for eid in entry_ids if eid in self._entries]

        if event_type is not None:
            entries = [e for e in entries if e.event_type == event_type]

        entries.sort(key=lambda e: e.occurred_at, reverse=reverse)
        return [e.to_dict() for e in entries[:limit]]

    def get_world_timeline(
        self,
        world_id: str,
        session_id: str | None = None,
        branch_id: str | None = None,
        event_type: str | None = None,
        limit: int = 500,
        reverse: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Return a timeline scoped to a world, with optional session/branch
        filters.
        """
        entries = [e for e in self._entries.values() if e.world_id == world_id]

        if session_id is not None:
            entries = [e for e in entries if e.session_id == session_id]
        if branch_id is not None:
            branch_ids = set(self._branch_entries.get(branch_id, []))
            entries = [e for e in entries if e.entry_id in branch_ids]
        if event_type is not None:
            entries = [e for e in entries if e.event_type == event_type]

        entries.sort(key=lambda e: e.occurred_at, reverse=reverse)
        return [e.to_dict() for e in entries[:limit]]

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """
        Compute a summary of what happened in a session.
        """
        entries = self.get_session_timeline(session_id, limit=10_000)
        event_type_counts: dict[str, int] = {}
        for e in entries:
            event_type_counts[e["event_type"]] = event_type_counts.get(e["event_type"], 0) + 1

        character_ids = {e["character_id"] for e in entries if e.get("character_id")}
        world_ids = {e["world_id"] for e in entries if e.get("world_id")}

        if entries:
            first = entries[-1]["occurred_at"]
            last = entries[0]["occurred_at"]
            duration_seconds = (
                datetime.fromisoformat(last) - datetime.fromisoformat(first)
            ).total_seconds()
        else:
            duration_seconds = 0.0

        return {
            "session_id": session_id,
            "total_events": len(entries),
            "duration_seconds": duration_seconds,
            "active_characters": len(character_ids),
            "world_ids": sorted(world_ids),
            "event_type_counts": event_type_counts,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "entries": {eid: e.to_dict() for eid, e in self._entries.items()},
            "session_entries": {sid: list(eids) for sid, eids in self._session_entries.items()},
            "branch_entries": {bid: list(eids) for bid, eids in self._branch_entries.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._entries.clear()
        self._session_entries.clear()
        self._branch_entries.clear()

        for eid, edata in state.get("entries", {}).items():
            entry = TimelineEntry.from_dict(edata)
            self._entries[eid] = entry
            self._session_entries.setdefault(entry.session_id, []).append(eid)
            if entry.branch_id is not None:
                self._branch_entries.setdefault(entry.branch_id, []).append(eid)

        for sid, eids in state.get("session_entries", {}).items():
            self._session_entries[sid] = list(eids)

        for bid, eids in state.get("branch_entries", {}).items():
            self._branch_entries[bid] = list(eids)
