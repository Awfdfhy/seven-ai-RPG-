"""
RPG-12-02: Dynamic World Events

Random events, world changes, and emergent stories that can be triggered
through travel, arrival, time-of-day, weather changes, or pure chance.

Events are defined in data/world_events.json and managed at runtime by
WorldEventManager. They integrate with WorldMapManager, WeatherFictionManager,
MilestoneManager, and NarrationManager for full world simulation.

Concepts
--------
WorldEventDefinition  : static blueprint loaded from JSON
WorldEventInstance    : runtime record of one triggered event
WorldEventManager     : owns definitions + instances, evaluates triggers,
                        applies effects, and exposes narration hooks.
"""

from __future__ import annotations

import copy
import json
import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

# ---------------------------------------------------------------------------
# Constants / enums
# ---------------------------------------------------------------------------

class EventCategory:
    RANDOM = "random"
    WEATHER = "weather"
    STORY = "story"
    WORLD = "world"
    AMBIENT = "ambient"


class EventStatus:
    PENDING = "pending"
    ACTIVE = "active"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Definitions (static data)
# ---------------------------------------------------------------------------

@dataclass
class EventTrigger:
    """
    One trigger condition for an event definition.

    Supported trigger types:
      random_chance   : {"type": "random_chance", "weight": float, "min_level": int}
      time_of_day     : {"type": "time_of_day", "hours": [int]}
      weather         : {"type": "weather", "condition": str, "min_intensity": str}
      location        : {"type": "location", "location_ids": [str], "location_types": [str]}
      region          : {"type": "region", "region_ids": [str]}
      on_travel       : {"type": "on_travel"}
      on_arrival      : {"type": "on_arrival"}
      after_event     : {"type": "after_event", "event_id": str, "probability": float}
      after_milestone : {"type": "after_milestone", "milestone_id": str}
    """
    trigger_type: str
    location_ids: list[str] = field(default_factory=list)
    location_types: list[str] = field(default_factory=list)
    region_ids: list[str] = field(default_factory=list)
    hours: list[int] = field(default_factory=list)
    condition: str = ""
    min_intensity: str = ""
    weight: float = 1.0
    min_level: int = 1
    probability: float = 1.0
    event_id: str = ""
    milestone_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.trigger_type,
            "location_ids": list(self.location_ids),
            "location_types": list(self.location_types),
            "region_ids": list(self.region_ids),
            "hours": list(self.hours),
            "condition": self.condition,
            "min_intensity": self.min_intensity,
            "weight": self.weight,
            "min_level": self.min_level,
            "probability": self.probability,
            "event_id": self.event_id,
            "milestone_id": self.milestone_id,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> EventTrigger:
        return EventTrigger(
            trigger_type=data.get("type", ""),
            location_ids=list(data.get("location_ids", [])),
            location_types=list(data.get("location_types", [])),
            region_ids=list(data.get("region_ids", [])),
            hours=[int(h) for h in data.get("hours", [])],
            condition=data.get("condition", ""),
            min_intensity=data.get("min_intensity", ""),
            weight=float(data.get("weight", 1.0)),
            min_level=int(data.get("min_level", 1)),
            probability=float(data.get("probability", 1.0)),
            event_id=data.get("event_id", ""),
            milestone_id=data.get("milestone_id", ""),
        )


@dataclass
class WorldEventDefinition:
    """
    Static blueprint for a world event.

    Attributes:
        id              : unique identifier
        name            : display name
        description     : flavor / mechanical text
        category        : kind of event (random | weather | story | world | ambient)
        triggers        : list of EventTrigger conditions
        narration       : template text rendered when the event fires
        effects         : list of world-state mutations to apply
        follow_up_events: event definition ids that can chain from this one
        duration_hours  : how long the event lasts (0 = instant)
        metadata        : opaque extra data
    """
    id: str
    name: str
    description: str = ""
    category: str = EventCategory.RANDOM
    triggers: list[EventTrigger] = field(default_factory=list)
    narration: str = ""
    effects: list[dict[str, Any]] = field(default_factory=list)
    follow_up_events: list[str] = field(default_factory=list)
    duration_hours: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "triggers": [t.to_dict() for t in self.triggers],
            "narration": self.narration,
            "effects": [copy.deepcopy(e) for e in self.effects],
            "follow_up_events": list(self.follow_up_events),
            "duration_hours": self.duration_hours,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> WorldEventDefinition:
        return WorldEventDefinition(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", EventCategory.RANDOM),
            triggers=[EventTrigger.from_dict(t) for t in data.get("triggers", [])],
            narration=data.get("narration", ""),
            effects=[copy.deepcopy(e) for e in data.get("effects", [])],
            follow_up_events=list(data.get("follow_up_events", [])),
            duration_hours=int(data.get("duration_hours", 0)),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Runtime instances
# ---------------------------------------------------------------------------

@dataclass
class WorldEventInstance:
    """
    Runtime record for one triggered event within a world/session.

    Attributes:
        instance_id    : unique identifier
        definition_id  : references the WorldEventDefinition
        world_id       : the world this event belongs to
        session_id     : optional session that triggered it
        status         : pending | active | resolved | expired | failed
        triggered_at   : ISO timestamp
        expires_at     : ISO timestamp when the event expires, or None
        effects_applied: snapshot of effects that were applied
        trigger_context: snapshot of what triggered the event (location, etc.)
        metadata       : opaque extra data
    """
    instance_id: str
    definition_id: str
    world_id: str
    triggered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    session_id: str | None = None
    status: str = EventStatus.ACTIVE
    expires_at: str | None = None
    effects_applied: list[dict[str, Any]] = field(default_factory=list)
    trigger_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "definition_id": self.definition_id,
            "world_id": self.world_id,
            "session_id": self.session_id,
            "status": self.status,
            "triggered_at": self.triggered_at,
            "expires_at": self.expires_at,
            "effects_applied": [copy.deepcopy(e) for e in self.effects_applied],
            "trigger_context": dict(self.trigger_context),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> WorldEventInstance:
        return WorldEventInstance(
            instance_id=data["instance_id"],
            definition_id=data["definition_id"],
            world_id=data["world_id"],
            triggered_at=data.get("triggered_at", ""),
            session_id=data.get("session_id"),
            status=data.get("status", EventStatus.ACTIVE),
            expires_at=data.get("expires_at"),
            effects_applied=[copy.deepcopy(e) for e in data.get("effects_applied", [])],
            trigger_context=dict(data.get("trigger_context", {})),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class WorldEventManager:
    """
    Manages world event definitions and runtime instances.

    Integrates with:
      - WorldMapManager   : location/region lookups for trigger evaluation
      - WeatherFictionManager : weather trigger checks
      - MilestoneManager  : after_milestone trigger checks
      - NarrationManager  : provides narration hooks for active events
    """

    def __init__(self, data_directory: str | None = None) -> None:
        self._events: dict[str, WorldEventInstance] = {}
        self._definitions: dict[str, WorldEventDefinition] = {}
        self._world_events: dict[str, set[str]] = {}      # world_id -> instance_ids
        self._session_events: dict[str, set[str]] = {}    # session_id -> instance_ids
        self._cooldowns: dict[str, dict[str, int]] = {}   # world_id -> {definition_id: day}

        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self._load_definitions(data_directory)

    # ------------------------------------------------------------------
    # Definition loading
    # ------------------------------------------------------------------

    def _load_definitions(self, directory: str) -> None:
        path = os.path.join(directory, "world_events.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            entries = data if isinstance(data, list) else data.get("events", [])
            for entry in entries:
                d = WorldEventDefinition.from_dict(entry)
                self.register_definition(d)
        except Exception:
            pass

    def register_definition(self, definition: WorldEventDefinition) -> None:
        self._definitions[definition.id] = definition

    def load_definitions(self, definitions: list[WorldEventDefinition]) -> None:
        for d in definitions:
            self.register_definition(d)

    def get_definition(self, event_id: str) -> WorldEventDefinition | None:
        return self._definitions.get(event_id)

    def list_definitions(self, category: str = "") -> list[dict[str, Any]]:
        defs = list(self._definitions.values())
        if category:
            defs = [d for d in defs if d.category == category]
        return [d.to_dict() for d in sorted(defs, key=lambda d: d.id)]

    # ------------------------------------------------------------------
    # Triggering
    # ------------------------------------------------------------------

    def _is_on_cooldown(self, world_id: str, definition_id: str, current_day: int) -> bool:
        world_cooldowns = self._cooldowns.get(world_id, {})
        last_day = world_cooldowns.get(definition_id, -9999)
        # Cooldown is 3 days for random/ambient, 7 days for story/world
        definition = self._definitions.get(definition_id)
        if definition is None:
            return False
        cooldown = 7 if definition.category in (EventCategory.STORY, EventCategory.WORLD) else 3
        return (current_day - last_day) < cooldown

    def _set_cooldown(self, world_id: str, definition_id: str, current_day: int) -> None:
        self._cooldowns.setdefault(world_id, {})[definition_id] = current_day

    def _check_trigger(self, trigger: EventTrigger, context: dict[str, Any]) -> bool:
        """Evaluate a single trigger against the given context."""

        # Random chance
        if trigger.trigger_type == "random_chance":
            if context.get("party_level", 1) < trigger.min_level:
                return False
            return random.random() <= (1.0 / max(trigger.weight, 0.01))

        # Time of day
        if trigger.trigger_type == "time_of_day":
            if not trigger.hours:
                return False
            return context.get("current_hour") in trigger.hours

        # Weather
        if trigger.trigger_type == "weather":
            if trigger.condition and context.get("weather_condition") != trigger.condition:
                return False
            if trigger.min_intensity:
                intensity_order = ["light", "moderate", "heavy", "severe"]
                current_idx = intensity_order.index(context.get("weather_intensity", "moderate"))
                min_idx = intensity_order.index(trigger.min_intensity)
                if current_idx < min_idx:
                    return False
            return True

        # Location
        if trigger.trigger_type == "location":
            loc_id = context.get("current_location_id", "")
            loc_type = context.get("current_location_type", "")
            if trigger.location_ids and loc_id not in trigger.location_ids:
                return False
            if trigger.location_types and loc_type not in trigger.location_types:
                return False
            return True

        # Region
        if trigger.trigger_type == "region":
            region_id = context.get("current_region_id", "")
            if trigger.region_ids and region_id not in trigger.region_ids:
                return False
            return True

        # On travel
        if trigger.trigger_type == "on_travel":
            return context.get("action") == "travel"

        # On arrival
        if trigger.trigger_type == "on_arrival":
            return context.get("action") == "arrival"

        # After event
        if trigger.trigger_type == "after_event":
            if trigger.event_id and context.get("triggering_event_id") != trigger.event_id:
                return False
            return random.random() <= trigger.probability

        # After milestone
        if trigger.trigger_type == "after_milestone":
            if trigger.milestone_id and context.get("triggering_milestone_id") != trigger.milestone_id:
                return False
            return True

        return False

    def evaluate_triggers(
        self,
        world_id: str,
        definition: WorldEventDefinition,
        context: dict[str, Any],
    ) -> bool:
        """
        Return True if the event definition's triggers are satisfied.
        Requires ALL triggers to match (AND semantics).
        """
        current_day = context.get("current_day", 1)
        if self._is_on_cooldown(world_id, definition.id, current_day):
            return False

        for trigger in definition.triggers:
            if not self._check_trigger(trigger, context):
                return False
        return True

    def trigger_event(
        self,
        definition_id: str,
        world_id: str,
        session_id: str | None = None,
        trigger_context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorldEventInstance | None:
        """
        Manually trigger a specific event definition in a world.

        Returns None if the definition does not exist.
        """
        definition = self._definitions.get(definition_id)
        if definition is None:
            return None

        return self._create_instance(definition, world_id, session_id, trigger_context, metadata)

    def _create_instance(
        self,
        definition: WorldEventDefinition,
        world_id: str,
        session_id: str | None,
        trigger_context: dict[str, Any] | None,
        metadata: dict[str, Any] | None,
    ) -> WorldEventInstance:
        instance_id = str(uuid.uuid4())
        ctx = dict(trigger_context or {})

        now = datetime.now(UTC).isoformat()
        expires_at = None
        if definition.duration_hours > 0:
            expires_dt = datetime.now(UTC)
            expires_dt = expires_dt + timedelta(hours=definition.duration_hours)
            expires_at = expires_dt.isoformat()

        instance = WorldEventInstance(
            instance_id=instance_id,
            definition_id=definition.id,
            world_id=world_id,
            session_id=session_id,
            status=EventStatus.ACTIVE,
            triggered_at=now,
            expires_at=expires_at,
            effects_applied=[copy.deepcopy(e) for e in definition.effects],
            trigger_context=ctx,
            metadata=metadata or {},
        )

        self._events[instance_id] = instance
        self._world_events.setdefault(world_id, set()).add(instance_id)
        if session_id:
            self._session_events.setdefault(session_id, set()).add(instance_id)

        # Set cooldown
        current_day = ctx.get("current_day", 1)
        self._set_cooldown(world_id, definition.id, current_day)

        return instance

    def check_and_trigger(
        self,
        world_id: str,
        context: dict[str, Any],
        session_id: str | None = None,
    ) -> list[WorldEventInstance]:
        """
        Evaluate all definitions and trigger any whose conditions are met.

        Returns list of newly created instances.
        """
        triggered: list[WorldEventInstance] = []
        for definition in self._definitions.values():
            if self.evaluate_triggers(world_id, definition, context):
                instance = self._create_instance(
                    definition, world_id, session_id, context, None
                )
                triggered.append(instance)
        return triggered

    def try_chain(
        self,
        parent_instance_id: str,
    ) -> WorldEventInstance | None:
        """
        Try to spawn a follow-up event from a parent instance.

        Checks the parent definition's follow_up_events list and randomly
        picks one to evaluate (probability is baked into the follow-up
        ordering; first entry has highest chance).
        """
        parent = self._events.get(parent_instance_id)
        if parent is None or parent.status != EventStatus.ACTIVE:
            return None

        definition = self._definitions.get(parent.definition_id)
        if definition is None or not definition.follow_up_events:
            return None

        # Build context from parent
        ctx = dict(parent.trigger_context)
        ctx["action"] = "follow_up"
        ctx["triggering_event_id"] = parent.definition_id
        ctx["triggering_instance_id"] = parent.instance_id
        ctx["current_day"] = parent.trigger_context.get("current_day", 1)

        for follow_up_id in definition.follow_up_events:
            follow_up_def = self._definitions.get(follow_up_id)
            if follow_up_def is None:
                continue
            if self.evaluate_triggers(parent.world_id, follow_up_def, ctx):
                return self._create_instance(
                    follow_up_def,
                    parent.world_id,
                    parent.session_id,
                    ctx,
                    {"chained_from": parent.instance_id},
                )
        return None

    def resolve_event(self, instance_id: str, status: str = EventStatus.RESOLVED) -> WorldEventInstance | None:
        """Mark an event instance as resolved, expired, or failed."""
        instance = self._events.get(instance_id)
        if instance is None:
            return None
        instance.status = status
        return instance

    def get_instance(self, instance_id: str) -> WorldEventInstance | None:
        return self._events.get(instance_id)

    def get_active_events(self, world_id: str) -> list[dict[str, Any]]:
        """Return all active/pending events for a world."""
        instances = []
        for iid in self._world_events.get(world_id, set()):
            instance = self._events.get(iid)
            if instance and instance.status in (EventStatus.ACTIVE, EventStatus.PENDING):
                instances.append(instance)
        return [self._serialize_instance(i) for i in sorted(
            instances, key=lambda x: x.triggered_at, reverse=True
        )]

    def get_events_for_location(self, world_id: str, location_id: str) -> list[dict[str, Any]]:
        """Return active events whose trigger_context matches the location."""
        results = []
        for iid in self._world_events.get(world_id, set()):
            instance = self._events.get(iid)
            if instance and instance.status in (EventStatus.ACTIVE, EventStatus.PENDING):
                if instance.trigger_context.get("current_location_id") == location_id:
                    results.append(self._serialize_instance(instance))
        return results

    def list_instances(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query instances with optional filters."""
        instances = list(self._events.values())
        if world_id is not None:
            instances = [i for i in instances if i.world_id == world_id]
        if session_id is not None:
            instances = [i for i in instances if i.session_id == session_id]
        if status is not None:
            instances = [i for i in instances if i.status == status]
        return [self._serialize_instance(i) for i in sorted(
            instances, key=lambda x: x.triggered_at, reverse=True
        )]

    def get_narration_hooks(self, world_id: str, scope: str | None = None) -> list[dict[str, Any]]:
        """
        Collect narration templates from active events, optionally
        filtered by scope (event | region | location | global).
        """
        hooks = []
        for iid in self._world_events.get(world_id, set()):
            instance = self._events.get(iid)
            if instance is None or instance.status != EventStatus.ACTIVE:
                continue
            definition = self._definitions.get(instance.definition_id)
            if definition is None or not definition.narration:
                continue
            hook = {
                "text": definition.narration,
                "source": f"event:{definition.id}",
                "instance_id": instance.instance_id,
                "category": definition.category,
                "trigger_context": dict(instance.trigger_context),
            }
            if scope:
                # Derive scope from trigger context
                ctx_scope = "global"
                if instance.trigger_context.get("current_location_id"):
                    ctx_scope = "location"
                elif instance.trigger_context.get("current_region_id"):
                    ctx_scope = "region"
                if ctx_scope != scope:
                    continue
            hooks.append(hook)
        return hooks

    def get_world_effects(self, world_id: str) -> list[dict[str, Any]]:
        """
        Aggregate all effects from active events for a world.
        """
        effects: list[dict[str, Any]] = []
        for iid in self._world_events.get(world_id, set()):
            instance = self._events.get(iid)
            if instance and instance.status == EventStatus.ACTIVE:
                effects.extend(copy.deepcopy(e) for e in instance.effects_applied)
        return effects

    def tick(self, world_id: str, current_hour: int = 0, current_day: int = 1) -> list[dict[str, Any]]:
        """
        Advance the event clock. Expire any events whose expiry has passed.

        Returns list of expired instances.
        """
        now_str = datetime.now(UTC).isoformat()
        expired = []
        for iid in list(self._world_events.get(world_id, set())):
            instance = self._events.get(iid)
            if instance is None or instance.status != EventStatus.ACTIVE:
                continue
            if instance.expires_at and instance.expires_at <= now_str:
                instance.status = EventStatus.EXPIRED
                expired.append(self._serialize_instance(instance))

        # Also resolve any events whose trigger_context indicated a short
        # relative duration from a past hour.
        for iid in list(self._world_events.get(world_id, set())):
            instance = self._events.get(iid)
            if instance is None or instance.status != EventStatus.ACTIVE:
                continue
            definition = self._definitions.get(instance.definition_id)
            if definition is None:
                continue
            triggered_hour = instance.trigger_context.get("triggered_hour")
            if triggered_hour is not None and definition.duration_hours > 0:
                if (current_hour - triggered_hour) % 24 >= definition.duration_hours:
                    instance.status = EventStatus.EXPIRED
                    if self._serialize_instance(instance) not in expired:
                        expired.append(self._serialize_instance(instance))

        return expired

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize_instance(self, instance: WorldEventInstance) -> dict[str, Any]:
        return {
            **instance.to_dict(),
            "definition": self._definitions[instance.definition_id].to_dict()
            if instance.definition_id in self._definitions else None,
        }

    def export_state(self) -> dict[str, Any]:
        return {
            "events": {eid: e.to_dict() for eid, e in self._events.items()},
            "cooldowns": {wid: dict(cd) for wid, cd in self._cooldowns.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._events.clear()
        self._world_events.clear()
        self._session_events.clear()
        for eid, edata in state.get("events", {}).items():
            event = WorldEventInstance.from_dict(edata)
            self._events[eid] = event
            self._world_events.setdefault(event.world_id, set()).add(eid)
            if event.session_id:
                self._session_events.setdefault(event.session_id, set()).add(eid)
        self._cooldowns.clear()
        for wid, cd in state.get("cooldowns", {}).items():
            self._cooldowns[wid] = dict(cd)
