"""
RPG World Library: manages the persistent library of worlds,
including rename and archive operations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class WorldEntry:
    """Metadata record for one world in the library."""

    world_id: str
    name: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "active"  # active | archived
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> WorldEntry:
        return WorldEntry(
            world_id=data["world_id"],
            name=data["name"],
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            status=data.get("status", "active"),
            metadata=dict(data.get("metadata", {})),
        )


class WorldLibrary:
    """
    Persistent library of worlds.

    Worlds can be renamed or archived. Archived worlds remain in the
    library but are hidden from the active list.
    """

    def __init__(self) -> None:
        self._worlds: dict[str, WorldEntry] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_world(self, name: str, description: str = "", metadata: dict[str, Any] | None = None) -> WorldEntry:
        world_id = str(uuid.uuid4())
        entry = WorldEntry(
            world_id=world_id,
            name=name,
            description=description,
            metadata=metadata or {},
        )
        self._worlds[world_id] = entry
        return entry

    def get_world(self, world_id: str) -> WorldEntry | None:
        return self._worlds.get(world_id)

    def list_worlds(self, include_archived: bool = False) -> list[dict[str, Any]]:
        worlds = [w.to_dict() for w in self._worlds.values()]
        if not include_archived:
            worlds = [w for w in worlds if w["status"] == "active"]
        return sorted(worlds, key=lambda w: w["name"].lower())

    # ------------------------------------------------------------------
    # Rename
    # ------------------------------------------------------------------

    def rename_world(self, world_id: str, new_name: str) -> bool:
        entry = self._worlds.get(world_id)
        if entry is None:
            return False
        entry.name = new_name.strip()
        entry.updated_at = datetime.now(UTC).isoformat()
        return True

    # ------------------------------------------------------------------
    # Archive / Unarchive
    # ------------------------------------------------------------------

    def archive_world(self, world_id: str) -> bool:
        entry = self._worlds.get(world_id)
        if entry is None or entry.status == "archived":
            return False
        entry.status = "archived"
        entry.updated_at = datetime.now(UTC).isoformat()
        return True

    def unarchive_world(self, world_id: str) -> bool:
        entry = self._worlds.get(world_id)
        if entry is None or entry.status == "active":
            return False
        entry.status = "active"
        entry.updated_at = datetime.now(UTC).isoformat()
        return True

    # ------------------------------------------------------------------
    # Import / Export helpers (persistence-agnostic)
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "worlds": {wid: w.to_dict() for wid, w in self._worlds.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._worlds.clear()
        for wid, wdata in state.get("worlds", {}).items():
            self._worlds[wid] = WorldEntry.from_dict(wdata)
