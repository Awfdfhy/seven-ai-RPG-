"""
RPG-09-02: Interactive World Map

Provides regions, locations, travel routes, region discovery,
NPC schedules, and game clock integration for world sessions.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

from enum import Enum


class LocationType(str, Enum):
    VILLAGE = "village"
    TOWN = "town"
    DUNGEON = "dungeon"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    PLAINS = "plains"
    WATER = "water"
    RUINS = "ruins"


@dataclass
class Region:
    """A named region on the world map."""

    id: str
    name: str
    description: str = ""
    color: str = "#888888"
    x: int = 0
    y: int = 0
    location_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "x": self.x,
            "y": self.y,
            "location_ids": list(self.location_ids),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Region:
        return Region(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            color=data.get("color", "#888888"),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            location_ids=list(data.get("location_ids", [])),
        )


@dataclass
class Location:
    """A point of interest on the map."""

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
            "connections": copy.deepcopy(self.connections),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Location:
        return Location(
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


@dataclass
class TravelRoute:
    """One directed travel connection between two locations."""

    from_location_id: str
    to_location_id: str
    distance: int = 1
    travel_time_hours: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_location_id": self.from_location_id,
            "to_location_id": self.to_location_id,
            "distance": self.distance,
            "travel_time_hours": self.travel_time_hours,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TravelRoute:
        return TravelRoute(
            from_location_id=data["from_location_id"],
            to_location_id=data["to_location_id"],
            distance=int(data.get("distance", 1)),
            travel_time_hours=int(data.get("travel_time_hours", 1)),
        )


@dataclass
class NPCScheduleEntry:
    """One entry in an NPC's daily schedule."""

    hour: int
    activity: str
    location_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "hour": self.hour,
            "activity": self.activity,
            "location_id": self.location_id,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCScheduleEntry:
        return NPCScheduleEntry(
            hour=int(data["hour"]),
            activity=data.get("activity", ""),
            location_id=data.get("location_id", ""),
        )


@dataclass
class NPCSchedule:
    """Daily schedule for an NPC."""

    id: str
    name: str
    default_location_id: str
    schedule: list[NPCScheduleEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "default_location_id": self.default_location_id,
            "schedule": [s.to_dict() for s in self.schedule],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCSchedule:
        return NPCSchedule(
            id=data["id"],
            name=data["name"],
            default_location_id=data.get("default_location_id", ""),
            schedule=[NPCScheduleEntry.from_dict(s) for s in data.get("schedule", [])],
        )

    def get_location_at_hour(self, hour: int) -> str:
        """Return the location_id for this NPC at the given in-game hour."""
        current = self.default_location_id
        for entry in sorted(self.schedule, key=lambda s: s.hour):
            if entry.hour <= hour:
                current = entry.location_id
            else:
                break
        return current


# ---------------------------------------------------------------------------
# Game Clock
# ---------------------------------------------------------------------------

class GameClock:
    """
    Minimal in-game clock. Tracks hours (0-23) and days.

    Each travel action advances time by the route's travel_time_hours.
    """

    def __init__(self, hour: int = 6, day: int = 1) -> None:
        self.hour = max(0, min(23, hour))
        self.day = max(1, day)

    def advance(self, hours: int) -> dict[str, int]:
        """Advance the clock by `hours` in-game hours. Returns new hour/day."""
        total = self.hour + hours
        day_delta = total // 24
        self.hour = total % 24
        self.day += day_delta
        return {"hour": self.hour, "day": self.day}

    def current_hour(self) -> int:
        return self.hour

    def current_day(self) -> int:
        return self.day

    def to_dict(self) -> dict[str, int]:
        return {"hour": self.hour, "day": self.day}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> GameClock:
        return GameClock(hour=int(data.get("hour", 6)), day=int(data.get("day", 1)))


# ---------------------------------------------------------------------------
# World Map
# ---------------------------------------------------------------------------

class WorldMap:
    """
    Holds all static map data: regions, locations, and routes.
    """

    def __init__(
        self,
        regions: list[Region] | None = None,
        locations: list[Location] | None = None,
        routes: list[TravelRoute] | None = None,
        npc_schedules: list[NPCSchedule] | None = None,
    ) -> None:
        self._regions: dict[str, Region] = {r.id: r for r in (regions or [])}
        self._locations: dict[str, Location] = {l.id: l for l in (locations or [])}
        self._routes: list[TravelRoute] = list(routes or [])
        self._npc_schedules: dict[str, NPCSchedule] = {n.id: n for n in (npc_schedules or [])}

    # ------------------------------------------------------------------
    # Static data access
    # ------------------------------------------------------------------

    def get_region(self, region_id: str) -> Region | None:
        return self._regions.get(region_id)

    def get_location(self, location_id: str) -> Location | None:
        return self._locations.get(location_id)

    def list_regions(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._regions.values()]

    def list_locations(self) -> list[dict[str, Any]]:
        return [l.to_dict() for l in self._locations.values()]

    def list_routes(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._routes]

    def get_routes_from(self, location_id: str) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._routes if r.from_location_id == location_id]

    def get_routes_to(self, location_id: str) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._routes if r.to_location_id == location_id]

    def get_npc_schedule(self, npc_id: str) -> NPCSchedule | None:
        return self._npc_schedules.get(npc_id)

    def list_npc_schedules(self) -> list[dict[str, Any]]:
        return [n.to_dict() for n in self._npc_schedules.values()]

    def get_npcs_at_location(self, location_id: str, hour: int) -> list[dict[str, Any]]:
        """Return all NPCs present at the given location and hour."""
        results = []
        for schedule in self._npc_schedules.values():
            current_loc = schedule.get_location_at_hour(hour)
            if current_loc == location_id:
                results.append(
                    {
                        "npc_id": schedule.id,
                        "name": schedule.name,
                        "activity": self._activity_at_hour(schedule, hour),
                    }
                )
        return results

    def _activity_at_hour(self, schedule: NPCSchedule, hour: int) -> str:
        for entry in sorted(schedule.schedule, key=lambda s: s.hour):
            if entry.hour <= hour:
                return entry.activity
        return "idle"

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "regions": [r.to_dict() for r in self._regions.values()],
            "locations": [l.to_dict() for l in self._locations.values()],
            "routes": [r.to_dict() for r in self._routes],
            "npc_schedules": [n.to_dict() for n in self._npc_schedules.values()],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> WorldMap:
        regions = [Region.from_dict(r) for r in data.get("regions", [])]
        locations = [Location.from_dict(l) for l in data.get("locations", [])]
        routes = [TravelRoute.from_dict(r) for r in data.get("routes", [])]
        npc_schedules = [NPCSchedule.from_dict(n) for n in data.get("npc_schedules", [])]
        return WorldMap(
            regions=regions,
            locations=locations,
            routes=routes,
            npc_schedules=npc_schedules,
        )

    def export_state(self) -> dict[str, Any]:
        return self.to_dict()

    def import_state(self, data: dict[str, Any]) -> None:
        self._regions.clear()
        self._locations.clear()
        self._routes.clear()
        self._npc_schedules.clear()
        loaded = WorldMap.from_dict(data)
        self._regions = loaded._regions
        self._locations = loaded._locations
        self._routes = loaded._routes
        self._npc_schedules = loaded._npc_schedules


# ---------------------------------------------------------------------------
# World Map Manager (runtime state per world/session)
# ---------------------------------------------------------------------------

class WorldMapManager:
    """
    Runtime manager that attaches to a world session.

    Tracks:
      - current location
      - discovered regions/locations (per world_id)
      - travel history
      - in-game clock
    """

    def __init__(self, world_map: WorldMap | None = None) -> None:
        self.world_map = world_map or WorldMap()
        # Per-world runtime state
        self._world_state: dict[str, dict[str, Any]] = {}

    def ensure_world(self, world_id: str, start_location_id: str | None = None) -> dict[str, Any]:
        """
        Initialize map state for a world. If `start_location_id` is given,
        the party starts there; otherwise the first defined location is used.
        """
        if world_id not in self._world_state:
            start = start_location_id
            if start is None and self.world_map._locations:
                start = next(iter(self.world_map._locations.keys()))
            self._world_state[world_id] = {
                "current_location_id": start,
                "discovered_locations": {start} if start else set(),
                "discovered_regions": set(),
                "travel_history": [],
                "clock": GameClock().to_dict(),
            }
        if start and start not in self._world_state[world_id]["discovered_locations"]:
            self._world_state[world_id]["discovered_locations"].add(start)
        state = self.get_world_state(world_id)
        return state

    def get_world_state(self, world_id: str) -> dict[str, Any]:
        state = self._world_state.get(world_id)
        if not state:
            return {}
        # Build derived info without mutating
        current = self.world_map.get_location(state["current_location_id"])
        region = self.world_map.get_region(current.region_id) if current else None
        return {
            "world_id": world_id,
            "current_location": current.to_dict() if current else None,
            "current_region": region.to_dict() if region else None,
            "discovered_locations": sorted(list(state["discovered_locations"])),
            "discovered_regions": sorted(list(state["discovered_regions"])),
            "travel_history": list(state["travel_history"]),
            "clock": dict(state["clock"]),
        }

    def get_current_location(self, world_id: str) -> dict[str, Any] | None:
        state = self._world_state.get(world_id)
        if not state:
            return None
        return self.world_map.get_location(state["current_location_id"]).to_dict() or None

    def discover_location(self, world_id: str, location_id: str) -> dict[str, Any]:
        state = self._world_state.get(world_id)
        if not state:
            state = self.ensure_world(world_id)
        state["discovered_locations"].add(location_id)
        loc = self.world_map.get_location(location_id)
        if loc:
            state["discovered_regions"].add(loc.region_id)
        return self.get_world_state(world_id)

    def discover_region(self, world_id: str, region_id: str) -> dict[str, Any]:
        state = self._world_state.get(world_id)
        if not state:
            state = self.ensure_world(world_id)
        state["discovered_regions"].add(region_id)
        return self.get_world_state(world_id)

    def travel(self, world_id: str, to_location_id: str) -> dict[str, Any]:
        """
        Travel from current location to `to_location_id`.

        Validates the route exists, advances the game clock,
        records history, and discovers the destination.
        """
        state = self._world_state.get(world_id)
        if not state:
            state = self.ensure_world(world_id)
        current_id = state["current_location_id"]
        route = self._find_route(current_id, to_location_id)
        if route is None:
            return {
                "success": False,
                "reason": f"No route from '{current_id}' to '{to_location_id}'.",
                "world_state": self.get_world_state(world_id),
            }
        # Advance clock
        clock = GameClock.from_dict(state["clock"])
        clock.advance(route.travel_time_hours)
        state["clock"] = clock.to_dict()
        # Update position
        state["current_location_id"] = to_location_id
        state["discovered_locations"].add(to_location_id)
        state["travel_history"].append(
            {
                "from": current_id,
                "to": to_location_id,
                "hours": route.travel_time_hours,
                "day": clock.day,
                "hour": clock.hour,
            }
        )
        loc = self.world_map.get_location(to_location_id)
        if loc:
            state["discovered_regions"].add(loc.region_id)
        return {"success": True, "route": route.to_dict(), "world_state": self.get_world_state(world_id)}

    def fast_travel(self, world_id: str, to_location_id: str) -> dict[str, Any]:
        """
        Travel instantly if both locations are already discovered.
        Otherwise falls back to normal travel.
        """
        state = self._world_state.get(world_id)
        if not state:
            state = self.ensure_world(world_id)
        if to_location_id in state["discovered_locations"]:
            current_id = state["current_location_id"]
            route = self._find_route(current_id, to_location_id)
            if route:
                clock = GameClock.from_dict(state["clock"])
                clock.advance(1)
                state["clock"] = clock.to_dict()
                state["current_location_id"] = to_location_id
                state["travel_history"].append(
                    {
                        "from": current_id,
                        "to": to_location_id,
                        "hours": 1,
                        "day": clock.day,
                        "hour": clock.hour,
                        "fast_travel": True,
                    }
                )
                return {"success": True, "fast_travel": True, "world_state": self.get_world_state(world_id)}
        return self.travel(world_id, to_location_id)

    def get_available_travel(self, world_id: str) -> list[dict[str, Any]]:
        state = self._world_state.get(world_id)
        if not state:
            state = self.ensure_world(world_id)
        current = state["current_location_id"]
        return self.world_map.get_routes_from(current)

    def get_npcs_here(self, world_id: str) -> list[dict[str, Any]]:
        state = self._world_state.get(world_id)
        if not state:
            return []
        current = state["current_location_id"]
        hour = GameClock.from_dict(state["clock"]).current_hour()
        return self.world_map.get_npcs_at_location(current, hour)

    def get_clock(self, world_id: str) -> dict[str, int]:
        state = self._world_state.get(world_id)
        if not state:
            return {"hour": 6, "day": 1}
        return dict(state["clock"])

    def set_clock(self, world_id: str, hour: int, day: int) -> dict[str, Any]:
        state = self._world_state.get(world_id)
        if not state:
            state = self.ensure_world(world_id)
        clock = GameClock(hour=hour, day=day)
        state["clock"] = clock.to_dict()
        return dict(state["clock"])

    def sync_to_session_snapshot(self, world_id: str) -> dict[str, Any]:
        """
        Package the world map state into a snapshot-compatible dict
        that can be stored in a WorldSession.
        """
        state = self._world_state.get(world_id)
        if not state:
            return {}
        return {
            "current_location_id": state["current_location_id"],
            "discovered_locations": sorted(list(state["discovered_locations"])),
            "discovered_regions": sorted(list(state["discovered_regions"])),
            "clock": dict(state["clock"]),
        }

    def restore_from_session_snapshot(self, world_id: str, snapshot: dict[str, Any]) -> None:
        if world_id not in self._world_state:
            self.ensure_world(world_id)
        state = self._world_state[world_id]
        if "current_location_id" in snapshot:
            state["current_location_id"] = snapshot["current_location_id"]
        if "discovered_locations" in snapshot:
            state["discovered_locations"] = set(snapshot["discovered_locations"])
        if "discovered_regions" in snapshot:
            state["discovered_regions"] = set(snapshot["discovered_regions"])
        if "clock" in snapshot:
            state["clock"] = dict(snapshot["clock"])

    def export_state(self) -> dict[str, Any]:
        return {
            wid: {
                "current_location_id": s["current_location_id"],
                "discovered_locations": sorted(list(s["discovered_locations"])),
                "discovered_regions": sorted(list(s["discovered_regions"])),
                "travel_history": list(s["travel_history"]),
                "clock": dict(s["clock"]),
            }
            for wid, s in self._world_state.items()
        }

    def import_state(self, data: dict[str, Any]) -> None:
        self._world_state.clear()
        for wid, s in data.items():
            self._world_state[wid] = {
                "current_location_id": s.get("current_location_id", ""),
                "discovered_locations": set(s.get("discovered_locations", [])),
                "discovered_regions": set(s.get("discovered_regions", [])),
                "travel_history": list(s.get("travel_history", [])),
                "clock": dict(s.get("clock", {"hour": 6, "day": 1})),
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_route(self, from_id: str, to_id: str) -> TravelRoute | None:
        for route in self.world_map._routes:
            if route.from_location_id == from_id and route.to_location_id == to_id:
                return route
        return None


# ---------------------------------------------------------------------------
# Data Loaders
# ---------------------------------------------------------------------------

def load_world_map_from_data_dir(base_path: str | None = None) -> WorldMap:
    """
    Load regions, locations, routes, and NPC schedules from the data dir.
    Falls back gracefully if any file is missing.
    """
    base = base_path or os.path.join(os.path.dirname(__file__), "..", "data")

    def _load_json(filename: str) -> Any:
        path = os.path.join(base, filename)
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    regions = [Region.from_dict(r) for r in _load_json("world_map.json")]
    locations = [Location.from_dict(l) for l in _load_json("world_locations.json")]
    npc_schedules = [NPCSchedule.from_dict(n) for n in _load_json("npc_schedules.json")]

    # Build routes from location connections
    routes: list[TravelRoute] = []
    for loc in locations:
        for conn in loc.connections:
            routes.append(
                TravelRoute(
                    from_location_id=loc.id,
                    to_location_id=conn["to"],
                    distance=int(conn.get("distance", 1)),
                    travel_time_hours=int(conn.get("travel_time_hours", 1)),
                )
            )

    return WorldMap(
        regions=regions,
        locations=locations,
        routes=routes,
        npc_schedules=npc_schedules,
    )
