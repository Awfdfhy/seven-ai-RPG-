"""
RPG-09-01: Locations Directory
Catalog of locations with descriptions and connections.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class LocationDirectoryEntry:
    """
    A catalog entry for a location.

    Attributes:
        id              : unique identifier (e.g. "oakhaven")
        name            : human-readable display name
        region_id       : parent region identifier
        description     : flavor / mechanical text
        location_type   : kind of location (town, dungeon, wilderness, etc.)
        x, y            : map coordinates
        danger_level    : 1-10 threat rating
        connections     : list of travel connections
                          [{"to": "loc_id", "distance": N, "travel_time_hours": N}]
    """

    id: str
    name: str
    region_id: str = ""
    description: str = ""
    location_type: str = "generic"
    x: int = 0
    y: int = 0
    danger_level: int = 1
    connections: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "region_id": self.region_id,
            "description": self.description,
            "location_type": self.location_type,
            "x": self.x,
            "y": self.y,
            "danger_level": self.danger_level,
            "connections": [dict(c) for c in self.connections],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LocationDirectoryEntry:
        return LocationDirectoryEntry(
            id=data["id"],
            name=data["name"],
            region_id=data.get("region_id", ""),
            description=data.get("description", ""),
            location_type=data.get("location_type", "generic"),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            danger_level=int(data.get("danger_level", 1)),
            connections=[dict(c) for c in data.get("connections", [])],
        )


# ---------------------------------------------------------------------------
# Location Directory
# ---------------------------------------------------------------------------

class LocationDirectory:
    """
    Read/write catalog of locations loaded from world_locations.json.

    Provides lookup, filtering, search, and connection enumeration.
    """

    def __init__(
        self,
        locations: list[LocationDirectoryEntry] | None = None,
    ) -> None:
        self._locations: dict[str, LocationDirectoryEntry] = {
            l.id: l for l in (locations or [])
        }

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_location(self, location_id: str) -> dict[str, Any] | None:
        """Return the full catalog entry for a location, or None."""
        loc = self._locations.get(location_id)
        return loc.to_dict() if loc else None

    def get_description(self, location_id: str) -> str | None:
        """Return just the description text for a location, or None."""
        loc = self._locations.get(location_id)
        return loc.description if loc else None

    # ------------------------------------------------------------------
    # Listing / Filtering
    # ------------------------------------------------------------------

    def list_locations(self) -> list[dict[str, Any]]:
        """Return all locations sorted by name."""
        return [
            l.to_dict() for l in sorted(self._locations.values(), key=lambda l: l.name.lower())
        ]

    def list_by_region(self, region_id: str) -> list[dict[str, Any]]:
        """Return all locations in a given region, preserving catalog order."""
        return [l.to_dict() for l in self._locations.values() if l.region_id == region_id]

    def list_by_type(self, location_type: str) -> list[dict[str, Any]]:
        """Return all locations of a given type, preserving catalog order."""
        return [l.to_dict() for l in self._locations.values() if l.location_type == location_type]

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------

    def get_connections(self, location_id: str) -> list[dict[str, Any]]:
        """
        Return travel connections from a location.

        Each entry includes the original connection fields plus an
        enriched "to_name" field when the target location exists.
        """
        loc = self._locations.get(location_id)
        if not loc:
            return []
        result = []
        for conn in loc.connections:
            entry = dict(conn)
            target_id = conn.get("to", "")
            target = self._locations.get(target_id)
            if target:
                entry["to_name"] = target.name
            result.append(entry)
        return result

    def get_connected_locations(self, location_id: str) -> list[dict[str, Any]]:
        """Return full catalog entries for all directly connected locations."""
        loc = self._locations.get(location_id)
        if not loc:
            return []
        result = []
        for conn in loc.connections:
            target_id = conn.get("to", "")
            target = self._locations.get(target_id)
            if target:
                result.append(target.to_dict())
        return result

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str) -> list[dict[str, Any]]:
        """Return locations whose name or description contains `query` (case-insensitive)."""
        q = query.lower()
        return [
            l.to_dict()
            for l in self._locations.values()
            if q in l.name.lower() or q in l.description.lower()
        ]

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_location(self, location: LocationDirectoryEntry) -> None:
        """Register or replace a location in the catalog."""
        self._locations[location.id] = location

    def remove_location(self, location_id: str) -> bool:
        """Remove a location by id. Returns True if it existed."""
        if location_id in self._locations:
            del self._locations[location_id]
            return True
        return False

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {"locations": [l.to_dict() for l in self._locations.values()]}

    def import_state(self, data: dict[str, Any]) -> None:
        self._locations.clear()
        for loc_data in data.get("locations", []):
            loc = LocationDirectoryEntry.from_dict(loc_data)
            self._locations[loc.id] = loc


# ---------------------------------------------------------------------------
# Data Loader
# ---------------------------------------------------------------------------

def load_locations_from_data_dir(base_path: str | None = None) -> LocationDirectory:
    """
    Load locations from world_locations.json in the data directory.

    Falls back to an empty directory if the file is missing.
    """
    base = base_path or os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    path = os.path.join(base, "world_locations.json")
    if not os.path.exists(path):
        return LocationDirectory()
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    entries = [LocationDirectoryEntry.from_dict(item) for item in raw]
    return LocationDirectory(locations=entries)
