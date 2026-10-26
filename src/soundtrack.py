"""
RPG-10-09: Soundtrack System

Adaptive music, ambient sounds, and battle themes.
Integrates with world location, weather, and session state.

Concepts
--------
SoundtrackCategory : the type of audio track (ambient, battle, exploration, etc.)
TrackIntensity     : tension level (low, medium, high) for adaptive layering
SoundtrackTrack    : definition of a single audio asset
SoundtrackLayer    : a layer within a category that activates at a given intensity
SoundtrackState    : runtime record of what is currently playing
SoundtrackManager  : owns state per world/session, transitions tracks, and
                     auto-adapts to location, weather, and danger level.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class SoundtrackCategory:
    """Well-known soundtrack categories."""
    AMBIENT = "ambient"
    BATTLE = "battle"
    EXPLORATION = "exploration"
    TOWN = "town"
    DUNGEON = "dungeon"
    CUTSCENE = "cutscene"
    UI = "ui"


class TrackIntensity:
    """Tension buckets used for adaptive layering."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Default track registry
# ---------------------------------------------------------------------------

_DEFAULT_TRACKS: dict[str, dict[str, list[dict[str, Any]]]] = {
    SoundtrackCategory.AMBIENT: {
        "default": [
            {"name": "Silence", "file_path": "", "default_volume": 0.0, "loop": False, "tags": ["none"]},
            {"name": "Forest Day", "file_path": "audio/ambient/forest_day.ogg", "default_volume": 0.6, "loop": True, "tags": ["forest", "day"]},
            {"name": "Forest Night", "file_path": "audio/ambient/forest_night.ogg", "default_volume": 0.6, "loop": True, "tags": ["forest", "night"]},
            {"name": "Rain", "file_path": "audio/ambient/rain.ogg", "default_volume": 0.5, "loop": True, "tags": ["rain"]},
            {"name": "Wind", "file_path": "audio/ambient/wind.ogg", "default_volume": 0.4, "loop": True, "tags": ["wind"]},
            {"name": "Drip Cave", "file_path": "audio/ambient/drip_cave.ogg", "default_volume": 0.5, "loop": True, "tags": ["cave", "dungeon"]},
            {"name": "Fire Crackle", "file_path": "audio/ambient/fire_crackle.ogg", "default_volume": 0.4, "loop": True, "tags": ["fire", "camp"]},
        ]
    },
    SoundtrackCategory.EXPLORATION: {
        "default": [
            {"name": "Peaceful Meadow", "file_path": "audio/exploration/peaceful_meadow.ogg", "default_volume": 0.7, "loop": True, "tags": ["plains", "day"]},
            {"name": "Mountain Trail", "file_path": "audio/exploration/mountain_trail.ogg", "default_volume": 0.7, "loop": True, "tags": ["mountain", "pass"]},
            {"name": "Wasteland", "file_path": "audio/exploration/wasteland.ogg", "default_volume": 0.7, "loop": True, "tags": ["wasteland", "volcanic"]},
            {"name": "Snowfield", "file_path": "audio/exploration/snowfield.ogg", "default_volume": 0.7, "loop": True, "tags": ["snow", "ice"]},
        ]
    },
    SoundtrackCategory.BATTLE: {
        "default": [
            {"name": "Encounter Low", "file_path": "audio/battle/encounter_low.ogg", "default_volume": 0.8, "loop": True, "tags": ["random", "low"]},
            {"name": "Encounter Medium", "file_path": "audio/battle/encounter_medium.ogg", "default_volume": 0.8, "loop": True, "tags": ["random", "medium"]},
            {"name": "Encounter High", "file_path": "audio/battle/encounter_high.ogg", "default_volume": 0.8, "loop": True, "tags": ["random", "high"]},
            {"name": "Boss Low", "file_path": "audio/battle/boss_low.ogg", "default_volume": 0.9, "loop": True, "tags": ["boss", "low"]},
            {"name": "Boss Medium", "file_path": "audio/battle/boss_medium.ogg", "default_volume": 0.9, "loop": True, "tags": ["boss", "medium"]},
            {"name": "Boss High", "file_path": "audio/battle/boss_high.ogg", "default_volume": 0.9, "loop": True, "tags": ["boss", "high"]},
        ]
    },
    SoundtrackCategory.TOWN: {
        "default": [
            {"name": "Village Day", "file_path": "audio/town/village_day.ogg", "default_volume": 0.6, "loop": True, "tags": ["village", "day"]},
            {"name": "Village Evening", "file_path": "audio/town/village_evening.ogg", "default_volume": 0.6, "loop": True, "tags": ["village", "evening"]},
            {"name": "Outpost", "file_path": "audio/town/outpost.ogg", "default_volume": 0.6, "loop": True, "tags": ["outpost"]},
        ]
    },
    SoundtrackCategory.DUNGEON: {
        "default": [
            {"name": "Cave Low", "file_path": "audio/dungeon/cave_low.ogg", "default_volume": 0.7, "loop": True, "tags": ["cave", "low"]},
            {"name": "Cave Medium", "file_path": "audio/dungeon/cave_medium.ogg", "default_volume": 0.7, "loop": True, "tags": ["cave", "medium"]},
            {"name": "Ruins High", "file_path": "audio/dungeon/ruins_high.ogg", "default_volume": 0.75, "loop": True, "tags": ["ruins", "high"]},
        ]
    },
    SoundtrackCategory.CUTSCENE: {
        "default": [
            {"name": "Tension", "file_path": "audio/cutscene/tension.ogg", "default_volume": 0.8, "loop": True, "tags": ["tension"]},
            {"name": "Tragedy", "file_path": "audio/cutscene/tragedy.ogg", "default_volume": 0.8, "loop": True, "tags": ["tragedy"]},
            {"name": "Triumph", "file_path": "audio/cutscene/triumph.ogg", "default_volume": 0.8, "loop": True, "tags": ["triumph"]},
        ]
    },
    SoundtrackCategory.UI: {
        "default": [
            {"name": "Menu", "file_path": "audio/ui/menu.ogg", "default_volume": 0.5, "loop": True, "tags": ["menu"]},
            {"name": "Click", "file_path": "audio/ui/click.ogg", "default_volume": 0.6, "loop": False, "tags": ["click"]},
            {"name": "Notification", "file_path": "audio/ui/notification.ogg", "default_volume": 0.6, "loop": False, "tags": ["notification"]},
        ]
    },
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class SoundtrackTrack:
    """
    Definition of a single audio asset.

    Attributes:
        track_id     : unique identifier
        name         : human-readable name
        category     : SoundtrackCategory slug
        file_path    : path to the audio file
        default_volume : 0.0 to 1.0
        loop         : whether the track repeats
        tags         : list of descriptive tags for matching
    """
    track_id: str
    name: str
    category: str
    file_path: str = ""
    default_volume: float = 0.7
    loop: bool = True
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "name": self.name,
            "category": self.category,
            "file_path": self.file_path,
            "default_volume": self.default_volume,
            "loop": self.loop,
            "tags": list(self.tags),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SoundtrackTrack:
        return SoundtrackTrack(
            track_id=data["track_id"],
            name=data["name"],
            category=data["category"],
            file_path=data.get("file_path", ""),
            default_volume=float(data.get("default_volume", 0.7)),
            loop=bool(data.get("loop", True)),
            tags=list(data.get("tags", [])),
        )


@dataclass
class SoundtrackLayer:
    """
    A layer within a category that activates at a given intensity threshold.

    Attributes:
        layer_id          : unique identifier
        category          : SoundtrackCategory slug
        track_id          : the track to play when this layer is active
        intensity         : TrackIntensity this layer responds to
        volume            : layer-specific volume multiplier (0.0 to 1.0)
        fade_ms           : fade-in time when layer activates
    """
    layer_id: str
    category: str
    track_id: str
    intensity: str = TrackIntensity.LOW
    volume: float = 0.7
    fade_ms: int = 2000

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "category": self.category,
            "track_id": self.track_id,
            "intensity": self.intensity,
            "volume": self.volume,
            "fade_ms": self.fade_ms,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SoundtrackLayer:
        return SoundtrackLayer(
            layer_id=data["layer_id"],
            category=data["category"],
            track_id=data["track_id"],
            intensity=data.get("intensity", TrackIntensity.LOW),
            volume=float(data.get("volume", 0.7)),
            fade_ms=int(data.get("fade_ms", 2000)),
        )


@dataclass
class SoundtrackState:
    """
    Runtime record of a currently playing (or recently stopped) track.

    Attributes:
        state_id    : unique identifier
        world_id    : the world this state belongs to
        session_id  : optional active session binding
        category    : SoundtrackCategory slug
        track_id    : the active track
        intensity   : current intensity
        volume      : current volume 0.0 to 1.0
        is_playing  : whether audio is currently outputting
        layers      : list of active layer track_ids
        started_at  : ISO timestamp when playback began
        ended_at    : ISO timestamp when playback stopped, or None
    """
    world_id: str
    category: str
    track_id: str
    session_id: str | None = None
    intensity: str = TrackIntensity.LOW
    volume: float = 0.7
    is_playing: bool = True
    layers: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    ended_at: str | None = None
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "world_id": self.world_id,
            "session_id": self.session_id,
            "category": self.category,
            "track_id": self.track_id,
            "intensity": self.intensity,
            "volume": self.volume,
            "is_playing": self.is_playing,
            "layers": list(self.layers),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SoundtrackState:
        return SoundtrackState(
            state_id=data["state_id"],
            world_id=data["world_id"],
            session_id=data.get("session_id"),
            category=data["category"],
            track_id=data["track_id"],
            intensity=data.get("intensity", TrackIntensity.LOW),
            volume=float(data.get("volume", 0.7)),
            is_playing=bool(data.get("is_playing", True)),
            layers=list(data.get("layers", [])),
            started_at=data.get("started_at", ""),
            ended_at=data.get("ended_at"),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class SoundtrackManager:
    """
    Manages soundtrack state per world and session.

    Usage:
        mgr = SoundtrackManager()
        mgr.register_defaults()
        mgr.play("w1", SoundtrackCategory.TOWN, fade_ms=1500)
        state = mgr.get_current("w1", SoundtrackCategory.TOWN)
        mgr.set_intensity("w1", SoundtrackCategory.BATTLE, TrackIntensity.HIGH)
        mgr.adapt_to_context("w1", location_type="town", danger_level=1, weather="clear")
    """

    def __init__(self) -> None:
        self._tracks: dict[str, SoundtrackTrack] = {}
        self._layers: dict[str, list[SoundtrackLayer]] = {}
        self._current: dict[str, dict[str, SoundtrackState]] = {}
        self._history: list[SoundtrackState] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_track(self, track: SoundtrackTrack) -> None:
        """Add or replace a track definition."""
        self._tracks[track.track_id] = track

    def register_layer(self, layer: SoundtrackLayer) -> None:
        """Add a layer to a category."""
        key = layer.category
        self._layers.setdefault(key, [])
        # Replace existing layer with same category+intensity
        self._layers[key] = [
            l for l in self._layers[key]
            if not (l.category == layer.category and l.intensity == layer.intensity)
        ]
        self._layers[key].append(layer)

    def register_defaults(self, data_directory: str | None = None) -> None:
        """
        Populate built-in track and layer defaults.
        When `data_directory` is provided, loads from `soundtrack.json` there;
        otherwise falls back to the embedded defaults.
        """
        loaded_from_file = False
        if data_directory is None:
            data_directory = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data"
            )
        path = os.path.join(data_directory, "soundtrack.json")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    payload = json.load(fh)
                loaded_from_file = True
                for category, groups in payload.get("tracks", {}).items():
                    for group_name, entries in groups.items():
                        for entry in entries:
                            track_id = entry.get("track_id") or f"{category}.{group_name}.{entry['name'].lower().replace(' ', '_')}"
                            track = SoundtrackTrack(
                                track_id=track_id,
                                name=entry["name"],
                                category=category,
                                file_path=entry.get("file_path", ""),
                                default_volume=float(entry.get("default_volume", 0.7)),
                                loop=bool(entry.get("loop", True)),
                                tags=list(entry.get("tags", [])),
                            )
                            self.register_track(track)
                for layer_list in payload.get("layers", {}).values():
                    for layer_data in layer_list:
                        layer = SoundtrackLayer(
                            layer_id=layer_data["layer_id"],
                            category=layer_data["category"],
                            track_id=layer_data["track_id"],
                            intensity=layer_data.get("intensity", TrackIntensity.LOW),
                            volume=float(layer_data.get("volume", 0.7)),
                            fade_ms=int(layer_data.get("fade_ms", 2000)),
                        )
                        self.register_layer(layer)
            except (OSError, json.JSONDecodeError):
                loaded_from_file = False

        if not loaded_from_file:
            for category, groups in _DEFAULT_TRACKS.items():
                for group_name, entries in groups.items():
                    for entry in entries:
                        track_id = f"{category}.{group_name}.{entry['name'].lower().replace(' ', '_')}"
                        track = SoundtrackTrack(
                            track_id=track_id,
                            name=entry["name"],
                            category=category,
                            file_path=entry["file_path"],
                            default_volume=float(entry["default_volume"]),
                            loop=bool(entry["loop"]),
                            tags=list(entry.get("tags", [])),
                        )
                        self.register_track(track)

            # Register adaptive layers for battle and dungeon
            for category in (SoundtrackCategory.BATTLE, SoundtrackCategory.DUNGEON):
                for intensity in (TrackIntensity.LOW, TrackIntensity.MEDIUM, TrackIntensity.HIGH):
                    candidates = [
                        t.track_id for t in self._tracks.values()
                        if t.category == category and intensity in t.tags
                    ]
                    if candidates:
                        self.register_layer(SoundtrackLayer(
                            layer_id=f"{category}.layer.{intensity}",
                            category=category,
                            track_id=candidates[0],
                            intensity=intensity,
                            volume=0.8 if category == SoundtrackCategory.BATTLE else 0.7,
                            fade_ms=2000 if intensity == TrackIntensity.LOW else 1000,
                        ))

    # ------------------------------------------------------------------
    # State mutations
    # ------------------------------------------------------------------

    def play(
        self,
        world_id: str,
        category: str,
        track_id: str | None = None,
        session_id: str | None = None,
        volume: float | None = None,
        intensity: str = TrackIntensity.LOW,
        fade_ms: int = 1500,
    ) -> SoundtrackState:
        """
        Start playback for a category. When track_id is None, the manager
        picks the best default track for the category.
        """
        if track_id is None:
            candidates = [
                t.track_id for t in self._tracks.values()
                if t.category == category
            ]
            track_id = candidates[0] if candidates else ""

        track = self._tracks.get(track_id)
        if track is None:
            track = SoundtrackTrack(
                track_id=track_id or f"{category}.unknown",
                name="Unknown",
                category=category,
                file_path="",
                default_volume=volume or 0.7,
            )
            self.register_track(track)

        # End previous active state for this world+category
        prev = self._current.get(world_id, {}).get(category)
        if prev is not None and prev.ended_at is None:
            prev.ended_at = datetime.now(UTC).isoformat()
            prev.is_playing = False
            self._history.append(prev)

        vol = volume if volume is not None else track.default_volume
        layers = self._resolve_layers(category, intensity)

        state = SoundtrackState(
            world_id=world_id,
            session_id=session_id,
            category=category,
            track_id=track_id,
            intensity=intensity,
            volume=vol,
            is_playing=True,
            layers=layers,
            started_at=datetime.now(UTC).isoformat(),
        )
        self._current.setdefault(world_id, {})[category] = state
        return state

    def stop(
        self,
        world_id: str,
        category: str,
        fade_ms: int = 1500,
    ) -> bool:
        """Stop playback for a category in a world."""
        bucket = self._current.get(world_id, {})
        state = bucket.get(category)
        if state is None or state.ended_at is not None:
            return False
        state.ended_at = datetime.now(UTC).isoformat()
        state.is_playing = False
        self._history.append(state)
        return True

    def set_intensity(
        self,
        world_id: str,
        category: str,
        intensity: str,
    ) -> SoundtrackState | None:
        """
        Change the adaptive intensity for a category. When a matching
        layer exists, the track switches to the layer's track_id.
        """
        bucket = self._current.get(world_id, {})
        state = bucket.get(category)
        if state is None or state.ended_at is not None:
            return None
        state.intensity = intensity
        layers = self._resolve_layers(category, intensity)
        state.layers = layers
        # If a layer has a different track, switch to it
        layer = self._find_layer(category, intensity)
        if layer is not None and layer.track_id != state.track_id:
            state.track_id = layer.track_id
        return state

    def adapt_to_context(
        self,
        world_id: str,
        session_id: str | None = None,
        location_type: str = "",
        danger_level: int = 1,
        weather: str = "clear",
        in_combat: bool = False,
    ) -> dict[str, SoundtrackState]:
        """
        Auto-select soundtrack categories and intensities based on world
        context. Returns the states that were changed.

        Rules:
        - in_combat -> battle (intensity based on danger_level)
        - dungeon/pass/outpost -> dungeon/exploration theme
        - town -> town theme
        - wilderness -> exploration theme
        - weather adjustments: rain/wind/thunderstorm add ambient layers
        """
        changes: dict[str, SoundtrackState] = {}

        # Stop cutscene/UI when entering normal play
        for cat in (SoundtrackCategory.CUTSCENE, SoundtrackCategory.UI):
            if self.stop(world_id, cat):
                pass  # changes tracked by return later

        if in_combat:
            intensity = TrackIntensity.LOW
            if danger_level >= 5:
                intensity = TrackIntensity.HIGH
            elif danger_level >= 3:
                intensity = TrackIntensity.MEDIUM
            state = self.play(world_id, SoundtrackCategory.BATTLE, intensity=intensity, session_id=session_id)
            changes[SoundtrackCategory.BATTLE] = state
            return changes

        # Non-combat: choose exploration/dungeon/town based on location
        if location_type in ("dungeon",):
            state = self.play(world_id, SoundtrackCategory.DUNGEON, session_id=session_id)
            changes[SoundtrackCategory.DUNGEON] = state
        elif location_type in ("town", "village"):
            state = self.play(world_id, SoundtrackCategory.TOWN, session_id=session_id)
            changes[SoundtrackCategory.TOWN] = state
        elif location_type in ("pass", "outpost"):
            state = self.play(world_id, SoundtrackCategory.EXPLORATION, session_id=session_id)
            changes[SoundtrackCategory.EXPLORATION] = state
        else:
            # wilderness / generic
            state = self.play(world_id, SoundtrackCategory.EXPLORATION, session_id=session_id)
            changes[SoundtrackCategory.EXPLORATION] = state

        # Ambient layer for weather
        if weather in ("rain", "heavy_rain", "thunderstorm"):
            ambient_track = self._find_track_by_tag(SoundtrackCategory.AMBIENT, "rain")
            if ambient_track:
                state = self.play(world_id, SoundtrackCategory.AMBIENT, track_id=ambient_track.track_id, session_id=session_id, volume=0.4)
                changes[SoundtrackCategory.AMBIENT] = state
        elif weather in ("snow", "blizzard"):
            ambient_track = self._find_track_by_tag(SoundtrackCategory.AMBIENT, "wind")
            if ambient_track:
                state = self.play(world_id, SoundtrackCategory.AMBIENT, track_id=ambient_track.track_id, session_id=session_id, volume=0.35)
                changes[SoundtrackCategory.AMBIENT] = state
        elif weather in ("fog", "haze"):
            ambient_track = self._find_track_by_tag(SoundtrackCategory.AMBIENT, "wind")
            if ambient_track:
                state = self.play(world_id, SoundtrackCategory.AMBIENT, track_id=ambient_track.track_id, session_id=session_id, volume=0.3)
                changes[SoundtrackCategory.AMBIENT] = state

        return changes

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_current(self, world_id: str, category: str) -> SoundtrackState | None:
        bucket = self._current.get(world_id, {})
        state = bucket.get(category)
        if state is not None and state.ended_at is None:
            return state
        return None

    def get_all_current(self, world_id: str) -> dict[str, SoundtrackState]:
        bucket = self._current.get(world_id, {})
        return {
            cat: state for cat, state in bucket.items()
            if state.ended_at is None
        }

    def get_track(self, track_id: str) -> SoundtrackTrack | None:
        return self._tracks.get(track_id)

    def get_layers(self, category: str) -> list[SoundtrackLayer]:
        return list(self._layers.get(category, []))

    def get_history(self, world_id: str | None = None) -> list[dict[str, Any]]:
        history = list(self._history)
        if world_id is not None:
            history = [h for h in history if h.world_id == world_id]
        return [h.to_dict() for h in sorted(history, key=lambda h: h.started_at)]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "current": {
                wid: {cat: s.to_dict() for cat, s in cats.items()}
                for wid, cats in self._current.items()
            },
            "history": [s.to_dict() for s in self._history],
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._current.clear()
        self._history.clear()
        for wid, cats in state.get("current", {}).items():
            self._current[wid] = {
                cat: SoundtrackState.from_dict(s)
                for cat, s in cats.items()
            }
        for data in state.get("history", []):
            self._history.append(SoundtrackState.from_dict(data))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_layers(self, category: str, intensity: str) -> list[str]:
        """Return track_ids for layers at or below the given intensity."""
        order = [TrackIntensity.LOW, TrackIntensity.MEDIUM, TrackIntensity.HIGH]
        try:
            idx = order.index(intensity)
        except ValueError:
            return []
        layers = self._layers.get(category, [])
        active = []
        for layer in layers:
            try:
                li = order.index(layer.intensity)
                if li <= idx:
                    active.append(layer.track_id)
            except ValueError:
                continue
        return active

    def _find_layer(self, category: str, intensity: str) -> SoundtrackLayer | None:
        for layer in self._layers.get(category, []):
            if layer.intensity == intensity:
                return layer
        return None

    def _find_track_by_tag(self, category: str, tag: str) -> SoundtrackTrack | None:
        for track in self._tracks.values():
            if track.category == category and tag in track.tags:
                return track
        return None
