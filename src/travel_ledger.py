"""
RPG Travel Ledger: tracks player movements between locations, travel
time, and journey events. Integrates with world simulation and calendar.

Concepts
--------
Location  : a named place in the world with optional metadata (region,
            danger, terrain, etc.).
Journey   : a single travel event from one location to another. A journey
            may contain multiple JourneyEvents.
Calendar  : abstract source of time; default implementation uses real UTC
            but a world-simulation clock can be injected.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Calendar abstraction
# ---------------------------------------------------------------------------

class CalendarProvider:
    """
    Source of time for the travel ledger.

    Override ``now`` to plug in a world-simulation clock so that travel
    advances an in-game calendar rather than wall-clock time.
    """

    def now(self) -> datetime:
        return datetime.now(UTC)

    def add_time(self, base: datetime, seconds: float) -> datetime:
        return datetime.fromtimestamp(base.timestamp() + seconds, tz=UTC)


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

@dataclass
class LocationDefinition:
    """Static definition of a place the player can travel to."""

    id: str
    name: str
    region: str = ""
    danger_level: int = 0
    terrain: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "region": self.region,
            "danger_level": self.danger_level,
            "terrain": self.terrain,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LocationDefinition:
        return LocationDefinition(
            id=data["id"],
            name=data["name"],
            region=data.get("region", ""),
            danger_level=data.get("danger_level", 0),
            terrain=data.get("terrain", ""),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class JourneyEvent:
    """Something that happened while traveling."""

    id: str
    event_type: str
    description: str
    occurred_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "description": self.description,
            "occurred_at": self.occurred_at,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> JourneyEvent:
        return JourneyEvent(
            id=data["id"],
            event_type=data["event_type"],
            description=data.get("description", ""),
            occurred_at=data.get("occurred_at", ""),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Runtime state
# ---------------------------------------------------------------------------

@dataclass
class TravelEntry:
    """
    Runtime record of one completed or active journey.
    """

    travel_id: str
    world_id: str
    session_id: str | None = None
    from_location_id: str = ""
    to_location_id: str = ""
    status: str = "in_progress"  # in_progress | completed | cancelled
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    cancelled_at: str | None = None
    distance_units: float = 0.0
    travel_speed: str = "normal"  # slow | normal | fast
    expected_duration_seconds: float = 0.0
    actual_duration_seconds: float | None = None
    events: list[JourneyEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "travel_id": self.travel_id,
            "world_id": self.world_id,
            "session_id": self.session_id,
            "from_location_id": self.from_location_id,
            "to_location_id": self.to_location_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "cancelled_at": self.cancelled_at,
            "distance_units": self.distance_units,
            "travel_speed": self.travel_speed,
            "expected_duration_seconds": self.expected_duration_seconds,
            "actual_duration_seconds": self.actual_duration_seconds,
            "events": [e.to_dict() for e in self.events],
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TravelEntry:
        return TravelEntry(
            travel_id=data["travel_id"],
            world_id=data["world_id"],
            session_id=data.get("session_id"),
            from_location_id=data.get("from_location_id", ""),
            to_location_id=data.get("to_location_id", ""),
            status=data.get("status", "in_progress"),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            cancelled_at=data.get("cancelled_at"),
            distance_units=data.get("distance_units", 0.0),
            travel_speed=data.get("travel_speed", "normal"),
            expected_duration_seconds=data.get("expected_duration_seconds", 0.0),
            actual_duration_seconds=data.get("actual_duration_seconds"),
            events=[JourneyEvent.from_dict(e) for e in data.get("events", [])],
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class TravelLedgerManager:
    """
    Manages journeys and travel events, scoped to worlds and sessions.

    Integrates with a ``CalendarProvider`` so that travel can advance an
    in-game clock instead of wall-clock time.
    """

    SPEED_MULTIPLIERS: dict[str, float] = {
        "slow": 1.5,
        "normal": 1.0,
        "fast": 0.6,
    }

    def __init__(self, calendar: CalendarProvider | None = None) -> None:
        self.calendar = calendar or CalendarProvider()
        self._travels: dict[str, TravelEntry] = {}
        self._locations: dict[str, LocationDefinition] = {}
        self._session_travels: dict[str, set[str]] = {}
        self._world_travels: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------

    def register_location(self, location: LocationDefinition) -> None:
        self._locations[location.id] = location

    def load_locations(self, locations: list[LocationDefinition]) -> None:
        for loc in locations:
            self.register_location(loc)

    def get_location(self, location_id: str) -> LocationDefinition | None:
        return self._locations.get(location_id)

    def list_locations(self) -> list[dict[str, Any]]:
        return [loc.to_dict() for loc in sorted(self._locations.values(), key=lambda l: l.name.lower())]

    # ------------------------------------------------------------------
    # Travel CRUD
    # ------------------------------------------------------------------

    def start_journey(
        self,
        world_id: str,
        from_location_id: str,
        to_location_id: str,
        session_id: str | None = None,
        travel_speed: str = "normal",
        metadata: dict[str, Any] | None = None,
    ) -> TravelEntry | None:
        """
        Begin a new journey from one location to another.

        Returns None if either location is unknown.
        """
        if from_location_id not in self._locations:
            return None
        if to_location_id not in self._locations:
            return None

        travel_id = str(uuid.uuid4())
        now = self.calendar.now()
        distance = self._estimate_distance(from_location_id, to_location_id)
        base_duration = self._base_duration_for_distance(distance)
        expected = self._apply_speed(base_duration, travel_speed)

        entry = TravelEntry(
            travel_id=travel_id,
            world_id=world_id,
            session_id=session_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            status="in_progress",
            started_at=now.isoformat(),
            distance_units=distance,
            travel_speed=travel_speed,
            expected_duration_seconds=expected,
            metadata=metadata or {},
        )
        self._travels[travel_id] = entry
        if session_id:
            self._session_travels.setdefault(session_id, set()).add(travel_id)
        self._world_travels.setdefault(world_id, set()).add(travel_id)
        return entry

    def get_travel(self, travel_id: str) -> TravelEntry | None:
        return self._travels.get(travel_id)

    def list_travels(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        travels = list(self._travels.values())
        if world_id is not None:
            travels = [t for t in travels if t.world_id == world_id]
        if session_id is not None:
            travels = [t for t in travels if t.session_id == session_id]
        if status is not None:
            travels = [t for t in travels if t.status == status]
        return [t.to_dict() for t in sorted(travels, key=lambda t: t.started_at)]

    # ------------------------------------------------------------------
    # Journey lifecycle
    # ------------------------------------------------------------------

    def add_event(
        self,
        travel_id: str,
        event_type: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> JourneyEvent | None:
        """
        Log an event for an in-progress journey.

        Returns None if the travel does not exist or is no longer in progress.
        """
        travel = self._travels.get(travel_id)
        if travel is None or travel.status != "in_progress":
            return None

        event = JourneyEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            description=description,
            occurred_at=self.calendar.now().isoformat(),
            metadata=metadata or {},
        )
        travel.events.append(event)
        return event

    def complete_journey(self, travel_id: str) -> TravelEntry | None:
        """
        Mark a journey as completed.  Actual duration is computed from the
        calendar (or wall clock) and stored.
        """
        travel = self._travels.get(travel_id)
        if travel is None or travel.status != "in_progress":
            return None

        now = self.calendar.now()
        started = datetime.fromisoformat(travel.started_at)
        elapsed = (now - started).total_seconds()
        travel.status = "completed"
        travel.completed_at = now.isoformat()
        travel.actual_duration_seconds = max(0.0, elapsed)
        return travel

    def cancel_journey(self, travel_id: str, reason: str = "") -> TravelEntry | None:
        """
        Cancel an in-progress journey and record why.
        """
        travel = self._travels.get(travel_id)
        if travel is None or travel.status != "in_progress":
            return None

        now = self.calendar.now()
        travel.status = "cancelled"
        travel.cancelled_at = now.isoformat()
        if reason:
            travel.metadata.setdefault("cancel_reasons", []).append(reason)
        return travel

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_journey_events(self, travel_id: str) -> list[dict[str, Any]]:
        travel = self._travels.get(travel_id)
        if travel is None:
            return []
        return [e.to_dict() for e in travel.events]

    def get_travel_log(self, world_id: str | None = None) -> list[dict[str, Any]]:
        """
        Return every journey entry with its events, optionally filtered
        by world_id.
        """
        travels = list(self._travels.values())
        if world_id is not None:
            travels = [t for t in travels if t.world_id == world_id]
        result = []
        for t in sorted(travels, key=lambda t: t.started_at):
            d = t.to_dict()
            result.append(d)
        return result

    def get_location_stats(self, location_id: str) -> dict[str, Any]:
        """Return journey counts for a specific location (as origin or destination)."""
        as_origin = 0
        as_dest = 0
        total_distance = 0.0
        total_events = 0
        for t in self._travels.values():
            if t.from_location_id == location_id:
                as_origin += 1
                total_distance += t.distance_units
                total_events += len(t.events)
            if t.to_location_id == location_id:
                as_dest += 1
        return {
            "location_id": location_id,
            "journeys_as_origin": as_origin,
            "journeys_as_destination": as_dest,
            "total_distance_traveled": total_distance,
            "total_events_logged": total_events,
        }

    def estimate_travel_time(
        self,
        from_location_id: str,
        to_location_id: str,
        travel_speed: str = "normal",
    ) -> float | None:
        """
        Return expected duration in seconds, or None if a location is missing.
        """
        if from_location_id not in self._locations or to_location_id not in self._locations:
            return None
        distance = self._estimate_distance(from_location_id, to_location_id)
        base = self._base_duration_for_distance(distance)
        return self._apply_speed(base, travel_speed)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "travels": {tid: t.to_dict() for tid, t in self._travels.items()},
            "locations": {lid: loc.to_dict() for lid, loc in self._locations.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._travels.clear()
        self._locations.clear()
        self._session_travels.clear()
        self._world_travels.clear()
        for lid, loc_data in state.get("locations", {}).items():
            self._locations[lid] = LocationDefinition.from_dict(loc_data)
        for tid, travel_data in state.get("travels", {}).items():
            travel = TravelEntry.from_dict(travel_data)
            self._travels[tid] = travel
            if travel.session_id:
                self._session_travels.setdefault(travel.session_id, set()).add(tid)
            if travel.world_id:
                self._world_travels.setdefault(travel.world_id, set()).add(tid)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _estimate_distance(self, from_id: str, to_id: str) -> float:
        """
        Placeholder distance estimator.  Production implementations can
        replace this with a graph lookup or coordinate math.
        """
        from_loc = self._locations[from_id]
        to_loc = self._locations[to_id]
        if from_loc.region != to_loc.region:
            return 100.0
        return 10.0

    def _base_duration_for_distance(self, distance: float) -> float:
        return distance * 60.0  # 1 unit per minute

    def _apply_speed(self, base_seconds: float, travel_speed: str) -> float:
        multiplier = self.SPEED_MULTIPLIERS.get(travel_speed, 1.0)
        return base_seconds * multiplier
