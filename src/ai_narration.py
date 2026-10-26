"""
RPG-10-02: AI Narration System
Dynamic storytelling engine that composes contextual narration from
templates, world state, weather, milestones, locations, and character data.

Concepts
--------
NarrationScope      : where narration applies (global, region, location, ...)
NarrationTemplate   : a fillable text template with variable slots
NarrationContext    : the snapshot of world/session/character/weather/etc.
NarrationEvent      : a rendered narration instance with timestamp and scope
NarrationManager    : owns templates, renders them against context, and
                      composes multi-source narration for a world/session.
"""

from __future__ import annotations

import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class NarrationScope:
    """Well-known narration scopes."""
    GLOBAL = "global"
    REGION = "region"
    LOCATION = "location"
    EVENT = "event"
    WEATHER = "weather"
    MILESTONE = "milestone"
    CHARACTER = "character"
    COMBAT = "combat"
    TRAVEL = "travel"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

@dataclass
class NarrationTemplate:
    """
    A fillable narration template.

    Attributes:
        template_id   : unique identifier
        scope         : narration scope (see NarrationScope)
        text          : template string with {variable} slots
        variables     : list of expected variable names for documentation/validation
        weight        : relative weight when picking among templates (higher = more likely)
        tags          : optional labels for filtering
        metadata      : opaque extra data
    """
    template_id: str
    scope: str
    text: str = ""
    variables: list[str] = field(default_factory=list)
    weight: float = 1.0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "scope": self.scope,
            "text": self.text,
            "variables": list(self.variables),
            "weight": self.weight,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NarrationTemplate:
        return NarrationTemplate(
            template_id=data["template_id"],
            scope=data.get("scope", NarrationScope.CUSTOM),
            text=data.get("text", ""),
            variables=list(data.get("variables", [])),
            weight=float(data.get("weight", 1.0)),
            tags=list(data.get("tags", [])),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

@dataclass
class NarrationContext:
    """
    Snapshot of everything relevant for narration generation.

    All fields are optional; missing values are treated as empty strings or
    empty collections when filling templates.
    """
    world_id: str = ""
    session_id: str = ""
    character_id: str = ""
    character_name: str = ""
    location_id: str = ""
    location_name: str = ""
    region_id: str = ""
    region_name: str = ""
    weather_condition: str = ""
    weather_intensity: str = ""
    time_of_day: str = ""       # morning | midday | afternoon | evening | night
    season: str = ""            # spring | summer | autumn | winter
    event_type: str = ""
    event_data: dict[str, Any] = field(default_factory=dict)
    character_stats: dict[str, Any] = field(default_factory=dict)
    party_members: list[str] = field(default_factory=list)
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "session_id": self.session_id,
            "character_id": self.character_id,
            "character_name": self.character_name,
            "location_id": self.location_id,
            "location_name": self.location_name,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "weather_condition": self.weather_condition,
            "weather_intensity": self.weather_intensity,
            "time_of_day": self.time_of_day,
            "season": self.season,
            "event_type": self.event_type,
            "event_data": dict(self.event_data),
            "character_stats": dict(self.character_stats),
            "party_members": list(self.party_members),
            "recent_events": [dict(e) for e in self.recent_events],
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NarrationContext:
        return NarrationContext(
            world_id=data.get("world_id", ""),
            session_id=data.get("session_id", ""),
            character_id=data.get("character_id", ""),
            character_name=data.get("character_name", ""),
            location_id=data.get("location_id", ""),
            location_name=data.get("location_name", ""),
            region_id=data.get("region_id", ""),
            region_name=data.get("region_name", ""),
            weather_condition=data.get("weather_condition", ""),
            weather_intensity=data.get("weather_intensity", ""),
            time_of_day=data.get("time_of_day", ""),
            season=data.get("season", ""),
            event_type=data.get("event_type", ""),
            event_data=dict(data.get("event_data", {})),
            character_stats=dict(data.get("character_stats", {})),
            party_members=list(data.get("party_members", [])),
            recent_events=[dict(e) for e in data.get("recent_events", [])],
            extra=dict(data.get("extra", {})),
        )

    def as_fill_dict(self) -> dict[str, Any]:
        """Return a flat dict suitable for template variable substitution."""
        # Convenience aliases so templates can use either name
        possessive = {
            "he": "his",
            "she": "her",
            "they": "their",
            "it": "its",
        }.get(self.character_name.lower(), "their") if self.character_name else "their"

        d: dict[str, Any] = {
            "world_id": self.world_id,
            "session_id": self.session_id,
            "character_id": self.character_id,
            "character_name": self.character_name or "the traveler",
            "character_possessive": possessive,
            "location_id": self.location_id,
            "location_name": self.location_name or "the road",
            "region_id": self.region_id,
            "region_name": self.region_name or "the wilds",
            "weather_condition": self.weather_condition or "clear",
            "weather_intensity": self.weather_intensity or "moderate",
            "weather_condition_intensity": self.weather_intensity or "moderate",
            "time_of_day": self.time_of_day or "midday",
            "season": self.season or "summer",
            "event_type": self.event_type,
            "party_size": len(self.party_members),
        }
        # flatten character stats
        for k, v in self.character_stats.items():
            d[f"stat_{k}"] = v
        # include extra
        d.update(self.extra)
        return d


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@dataclass
class NarrationEvent:
    """
    One rendered narration output.

    Attributes:
        event_id      : unique identifier
        world_id      : the world this narration belongs to
        session_id    : optional session binding
        scope         : narration scope
        text          : rendered narration text
        source        : what produced this narration (template_id, "weather", etc.)
        priority      : higher priority renders first when composing blocks
        tags          : optional labels
        created_at    : ISO timestamp
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    world_id: str = ""
    session_id: str = ""
    scope: str = NarrationScope.GLOBAL
    text: str = ""
    source: str = ""
    priority: int = 0
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "world_id": self.world_id,
            "session_id": self.session_id,
            "scope": self.scope,
            "text": self.text,
            "source": self.source,
            "priority": self.priority,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NarrationEvent:
        return NarrationEvent(
            event_id=data.get("event_id", str(uuid.uuid4())),
            world_id=data.get("world_id", ""),
            session_id=data.get("session_id", ""),
            scope=data.get("scope", NarrationScope.GLOBAL),
            text=data.get("text", ""),
            source=data.get("source", ""),
            priority=int(data.get("priority", 0)),
            tags=list(data.get("tags", [])),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
        )


# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------

_BUILTIN_TEMPLATES: list[NarrationTemplate] = [
    # Weather arrival
    NarrationTemplate(
        template_id="weather_arrival_light",
        scope=NarrationScope.WEATHER,
        text="The {weather_condition} begins to fall. {character_name} pulls {character_possessive} cloak tighter.",
        variables=["weather_condition", "character_name", "character_possessive"],
        weight=1.0,
        tags=["weather", "arrival"],
    ),
    NarrationTemplate(
        template_id="weather_arrival_moderate",
        scope=NarrationScope.WEATHER,
        text="{weather_condition_intensity} {weather_condition} sets in. The air grows heavy, and every step demands more care.",
        variables=["weather_condition_intensity", "weather_condition"],
        weight=2.0,
        tags=["weather", "arrival"],
    ),
    NarrationTemplate(
        template_id="weather_arrival_severe",
        scope=NarrationScope.WEATHER,
        text="A severe {weather_condition} breaks over {location_name}. Nature shows its teeth; only the cautious survive.",
        variables=["weather_condition", "location_name"],
        weight=3.0,
        tags=["weather", "arrival", "severe"],
    ),
    NarrationTemplate(
        template_id="weather_clear_after_storm",
        scope=NarrationScope.WEATHER,
        text="The storm passes. Sunlight returns to {location_name}, and the world smells of wet stone and renewal.",
        variables=["location_name"],
        weight=1.5,
        tags=["weather", "clear"],
    ),
    # Travel
    NarrationTemplate(
        template_id="travel_departure",
        scope=NarrationScope.TRAVEL,
        text="{character_name} leaves {location_name} behind, heading toward {destination_name}.",
        variables=["character_name", "location_name", "destination_name"],
        weight=1.0,
        tags=["travel", "departure"],
    ),
    NarrationTemplate(
        template_id="travel_arrival",
        scope=NarrationScope.TRAVEL,
        text="The road finally leads to {destination_name}. {character_name} takes in the sight of {destination_description}.",
        variables=["destination_name", "character_name", "destination_description"],
        weight=1.0,
        tags=["travel", "arrival"],
    ),
    NarrationTemplate(
        template_id="travel_fatigue",
        scope=NarrationScope.TRAVEL,
        text="Fatigue weighs on {character_name}. The miles to {destination_name} seem longer than the map promised.",
        variables=["character_name", "destination_name"],
        weight=1.0,
        tags=["travel", "fatigue"],
    ),
    # Location entry
    NarrationTemplate(
        template_id="location_enter_town",
        scope=NarrationScope.LOCATION,
        text="The gates of {location_name} welcome {character_name}. The sounds of daily life fill the air.",
        variables=["location_name", "character_name"],
        weight=1.0,
        tags=["location", "town"],
    ),
    NarrationTemplate(
        template_id="location_enter_dungeon",
        scope=NarrationScope.LOCATION,
        text="Darkness swallows {character_name} as {location_name} opens before them. The air is cold and still.",
        variables=["location_name", "character_name"],
        weight=1.0,
        tags=["location", "dungeon"],
    ),
    NarrationTemplate(
        template_id="location_enter_wilderness",
        scope=NarrationScope.LOCATION,
        text="{location_name} stretches out in wild beauty. The wind carries the scent of pine and distant rain.",
        variables=["location_name"],
        weight=1.0,
        tags=["location", "wilderness"],
    ),
    # Milestones
    NarrationTemplate(
        template_id="milestone_achieved",
        scope=NarrationScope.MILESTONE,
        text="A new chapter begins: {milestone_name}. {character_name} feels the weight of this moment settle into history.",
        variables=["milestone_name", "character_name"],
        weight=2.0,
        tags=["milestone", "achieved"],
    ),
    NarrationTemplate(
        template_id="milestone_failed",
        scope=NarrationScope.MILESTONE,
        text="{milestone_name} slips through {character_name}'s fingers. Not all stories end as hoped.",
        variables=["milestone_name", "character_name"],
        weight=1.0,
        tags=["milestone", "failed"],
    ),
    # Character
    NarrationTemplate(
        template_id="character_level_up",
        scope=NarrationScope.CHARACTER,
        text="{character_name} grows stronger. The world seems just a little more conquerable.",
        variables=["character_name"],
        weight=1.0,
        tags=["character", "progression"],
    ),
    NarrationTemplate(
        template_id="character_rest",
        scope=NarrationScope.CHARACTER,
        text="{character_name} rests by the fire. Wounds close and spirits lift under the warmth.",
        variables=["character_name"],
        weight=1.0,
        tags=["character", "rest"],
    ),
    # Combat
    NarrationTemplate(
        template_id="combat_start",
        scope=NarrationScope.COMBAT,
        text="Hostility erupts! {character_name} readies {character_possessive} stance.",
        variables=["character_name", "character_possessive"],
        weight=1.0,
        tags=["combat", "start"],
    ),
    NarrationTemplate(
        template_id="combat_victory",
        scope=NarrationScope.COMBAT,
        text="The last foe falls. {character_name} stands victorious, breathing hard but unbroken.",
        variables=["character_name"],
        weight=1.0,
        tags=["combat", "victory"],
    ),
    NarrationTemplate(
        template_id="combat_defeat",
        scope=NarrationScope.COMBAT,
        text="Darkness closes in. {character_name} has been overcome... but the story may not end here.",
        variables=["character_name"],
        weight=1.0,
        tags=["combat", "defeat"],
    ),
    # Generic
    NarrationTemplate(
        template_id="generic_idle",
        scope=NarrationScope.GLOBAL,
        text="The world turns. {character_name} considers the path ahead.",
        variables=["character_name"],
        weight=0.5,
        tags=["idle"],
    ),
    NarrationTemplate(
        template_id="generic_discovery",
        scope=NarrationScope.GLOBAL,
        text="Something catches {character_name}'s eye. A small discovery in {location_name} that might lead to greater things.",
        variables=["character_name", "location_name"],
        weight=1.0,
        tags=["discovery"],
    ),
]


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class NarrationManager:
    """
    Manages narration templates and generates contextual narration blocks.

    Usage:
        mgr = NarrationManager()
        ctx = NarrationContext(world_id="w1", character_name="Aria")
        block = mgr.compose_narration("w1", NarrationScope.WEATHER, ctx)
        print(block)
    """

    def __init__(self, data_directory: str | None = None) -> None:
        self._templates: dict[str, NarrationTemplate] = {}
        self._events: dict[str, NarrationEvent] = {}
        self._world_events: dict[str, list[str]] = {}
        self._session_events: dict[str, list[str]] = {}
        self._custom_sources: dict[str, Any] = {}

        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self._data_directory = data_directory
        self._load_templates()

    # ------------------------------------------------------------------
    # Template management
    # ------------------------------------------------------------------

    def _load_templates(self) -> None:
        for tmpl in _BUILTIN_TEMPLATES:
            self.register_template(tmpl)

    def register_template(self, template: NarrationTemplate) -> None:
        self._templates[template.template_id] = template

    def get_template(self, template_id: str) -> NarrationTemplate | None:
        return self._templates.get(template_id)

    def list_templates(
        self,
        scope: str | None = None,
        tags: list[str] | None = None,
    ) -> list[NarrationTemplate]:
        results = list(self._templates.values())
        if scope is not None:
            results = [t for t in results if t.scope == scope]
        if tags:
            results = [t for t in results if any(tag in t.tags for tag in tags)]
        return results

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_template(self, template_id: str, context: NarrationContext) -> str:
        """
        Render a template by filling its variables from the context.

        Returns the rendered string, or the raw template text on mismatch.
        """
        template = self._templates.get(template_id)
        if template is None:
            return ""
        fill = context.as_fill_dict()
        try:
            return template.text.format(**fill)
        except (KeyError, IndexError, ValueError):
            # Fallback: return template text for unknown variables
            return template.text

    def render_custom(self, text: str, context: NarrationContext) -> str:
        """Render an arbitrary string against a context."""
        fill = context.as_fill_dict()
        try:
            return text.format(**fill)
        except (KeyError, IndexError, ValueError):
            return text

    # ------------------------------------------------------------------
    # Narration composition
    # ------------------------------------------------------------------

    def compose_narration(
        self,
        world_id: str,
        scope: str,
        context: NarrationContext,
        mode: str = "auto",
        max_blocks: int = 3,
    ) -> str:
        """
        Generate a narration block for a world/scope/context.

        Modes:
            auto     - pick templates by weight + random, combine with system sources
            template - pick a template only
            system   - compose from weather/milestone/location sources only
            full     - template + system sources combined

        Returns a composed narration string.
        """
        blocks: list[tuple[int, str]] = []  # (priority, text)

        if mode in ("auto", "full", "template"):
            template_text = self._pick_and_render_template(scope, context)
            if template_text:
                blocks.append((0, template_text))

        if mode in ("auto", "full", "system"):
            system_blocks = self._compose_system_sources(world_id, scope, context)
            for sb in system_blocks:
                blocks.append((sb["priority"], sb["text"]))

        # Sort by priority descending, keep top N
        blocks.sort(key=lambda x: x[0], reverse=True)
        selected = [b[1] for b in blocks[:max_blocks]]

        # Join with paragraph breaks
        return "\n\n".join(selected)

    def _pick_and_render_template(self, scope: str, context: NarrationContext) -> str:
        candidates = [t for t in self._templates.values() if t.scope == scope]
        if not candidates:
            return ""
        # Weighted random selection
        weights = [max(t.weight, 0.1) for t in candidates]
        try:
            template = random.choices(candidates, weights=weights, k=1)[0]
        except Exception:
            template = candidates[0]
        return self.render_template(template.template_id, context)

    def _compose_system_sources(
        self, world_id: str, scope: str, context: NarrationContext
    ) -> list[dict[str, Any]]:
        """
        Query other systems (weather, milestones, locations) and produce
        narration text from them.
        """
        results: list[dict[str, Any]] = []

        if scope == NarrationScope.WEATHER:
            # Try to get weather narration from WeatherFictionManager
            try:
                from weather_fiction import WeatherFictionManager
                wm = WeatherFictionManager()
                wm.calendar = None
                short = wm.get_narration(world_id, long=False)
                long = wm.get_narration(world_id, long=True)
                if short:
                    results.append({"text": short, "priority": 5, "source": "weather_fiction"})
                if long and long != short:
                    results.append({"text": long, "priority": 3, "source": "weather_fiction"})
            except Exception:
                pass

        if scope == NarrationScope.MILESTONE:
            # Try to get milestone narration hooks
            try:
                from milestone import MilestoneManager
                mm = MilestoneManager(data_directory=self._data_directory)
                hooks = mm.get_narration_hooks(world_id)
                for hook in hooks:
                    text = self.render_custom(hook.get("template", ""), context)
                    if text:
                        results.append({
                            "text": text,
                            "priority": hook.get("priority", 2),
                            "source": "milestone",
                        })
            except Exception:
                pass

        if scope == NarrationScope.LOCATION and context.location_id:
            try:
                from locations import LocationDirectory
                loc_dir = LocationDirectory()
                desc = loc_dir.get_description(context.location_id)
                if desc:
                    results.append({
                        "text": f"{context.location_name}: {desc}",
                        "priority": 4,
                        "source": "location_directory",
                    })
            except Exception:
                pass

        return results

    # ------------------------------------------------------------------
    # Queued events
    # ------------------------------------------------------------------

    def queue_narration(
        self,
        world_id: str,
        scope: str,
        text: str,
        session_id: str = "",
        source: str = "",
        priority: int = 0,
        tags: list[str] | None = None,
    ) -> NarrationEvent:
        event = NarrationEvent(
            world_id=world_id,
            session_id=session_id,
            scope=scope,
            text=text,
            source=source,
            priority=priority,
            tags=tags or [],
        )
        self._events[event.event_id] = event
        self._world_events.setdefault(world_id, []).append(event.event_id)
        if session_id:
            self._session_events.setdefault(session_id, []).append(event.event_id)
        return event

    def get_world_events(
        self,
        world_id: str,
        scope: str | None = None,
        limit: int = 50,
    ) -> list[NarrationEvent]:
        eids = self._world_events.get(world_id, [])
        events = [self._events[eid] for eid in eids if eid in self._events]
        if scope is not None:
            events = [e for e in events if e.scope == scope]
        events.sort(key=lambda e: e.created_at, reverse=True)
        return events[:limit]

    def get_session_events(
        self,
        session_id: str,
        scope: str | None = None,
        limit: int = 50,
    ) -> list[NarrationEvent]:
        eids = self._session_events.get(session_id, [])
        events = [self._events[eid] for eid in eids if eid in self._events]
        if scope is not None:
            events = [e for e in events if e.scope == scope]
        events.sort(key=lambda e: e.created_at, reverse=True)
        return events[:limit]

    # ------------------------------------------------------------------
    # Custom sources (integration hook)
    # ------------------------------------------------------------------

    def register_source(self, name: str, source: Any) -> None:
        """Register an external narration source by name."""
        self._custom_sources[name] = source

    def get_source(self, name: str) -> Any | None:
        return self._custom_sources.get(name)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "templates": {tid: t.to_dict() for tid, t in self._templates.items()},
            "events": {eid: e.to_dict() for eid, e in self._events.items()},
            "world_events": {wid: list(eids) for wid, eids in self._world_events.items()},
            "session_events": {sid: list(eids) for sid, eids in self._session_events.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._templates.clear()
        self._events.clear()
        self._world_events.clear()
        self._session_events.clear()
        for tid, tdata in state.get("templates", {}).items():
            self._templates[tid] = NarrationTemplate.from_dict(tdata)
        for eid, edata in state.get("events", {}).items():
            self._events[eid] = NarrationEvent.from_dict(edata)
        for wid, eids in state.get("world_events", {}).items():
            self._world_events[wid] = list(eids)
        for sid, eids in state.get("session_events", {}).items():
            self._session_events[sid] = list(eids)
