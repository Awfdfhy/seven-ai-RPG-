"""
RPG World Session: tracks an active play session bound to a single world.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from difficulty_settings import GameSettings


@dataclass
class WorldSession:
    """
    Represents an active play session for a specific world.

    Attributes:
        session_id : unique identifier for the session
        world_id   : the world this session is playing
        started_at : ISO timestamp of session start
        status     : active | paused | ended
        snapshot   : optional game-state snapshot (engine-specific)
        metadata   : arbitrary session metadata
        settings   : game settings (difficulty + accessibility)
    """

    session_id: str
    world_id: str
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "active"
    snapshot: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    settings: GameSettings | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "world_id": self.world_id,
            "started_at": self.started_at,
            "status": self.status,
            "snapshot": dict(self.snapshot),
            "metadata": dict(self.metadata),
            "settings": self.settings.to_dict() if self.settings else None,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> WorldSession:
        return WorldSession(
            session_id=data["session_id"],
            world_id=data["world_id"],
            started_at=data.get("started_at", ""),
            status=data.get("status", "active"),
            snapshot=dict(data.get("snapshot", {})),
            metadata=dict(data.get("metadata", {})),
            settings=GameSettings.from_dict(data["settings"]) if data.get("settings") else None,
        )


class WorldSessionManager:
    """
    Creates and tracks WorldSession instances.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, WorldSession] = {}

    def create_session(self, world_id: str, metadata: dict[str, Any] | None = None, settings: GameSettings | None = None) -> WorldSession:
        session_id = str(uuid.uuid4())
        session = WorldSession(
            session_id=session_id,
            world_id=world_id,
            metadata=metadata or {},
            settings=settings,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> WorldSession | None:
        return self._sessions.get(session_id)

    def get_sessions_for_world(self, world_id: str) -> list[WorldSession]:
        return [s for s in self._sessions.values() if s.world_id == world_id]

    def list_active_sessions(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._sessions.values() if s.status == "active"]

    def end_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None or session.status == "ended":
            return False
        session.status = "ended"
        return True

    def update_snapshot(self, session_id: str, snapshot: dict[str, Any]) -> bool:
        session = self._sessions.get(session_id)
        if session is None or session.status != "active":
            return False
        session.snapshot = dict(snapshot)
        return True

    def update_settings(self, session_id: str, settings: GameSettings) -> bool:
        session = self._sessions.get(session_id)
        if session is None or session.status != "active":
            return False
        session.settings = settings
        return True

