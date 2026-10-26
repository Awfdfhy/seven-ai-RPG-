"""
RPG-09-04: Weather Fiction State
Dynamic weather descriptions that affect narration and gameplay.
Integrates with world simulation and time system.

Concepts
--------
WeatherCondition : the type of weather (clear, rain, snow, etc.)
WeatherIntensity : how strong the weather is (light, moderate, heavy, severe)
WeatherFictionState : runtime state for a world's current weather, including
                      fiction descriptions and gameplay effect modifiers.
WeatherFictionManager : owns weather state per world, transitions weather
                        over time, and exposes effects + narration strings.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class WeatherCondition:
    """Well-known weather conditions."""
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    BLIZZARD = "blizzard"
    FOG = "fog"
    HAZE = "haze"
    WINDY = "windy"
    DRIZZLE = "drizzle"


class WeatherIntensity:
    """Well-known intensity buckets."""
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    SEVERE = "severe"


# ---------------------------------------------------------------------------
# Fiction templates
# ---------------------------------------------------------------------------

_SHORT_DESCRIPTIONS: dict[str, dict[str, str]] = {
    WeatherCondition.CLEAR: {
        WeatherIntensity.LIGHT: "The sky is clear and bright.",
        WeatherIntensity.MODERATE: "A pleasant, cloudless sky.",
        WeatherIntensity.HEAVY: "The sun beats down relentlessly.",
        WeatherIntensity.SEVERE: "A blistering, cloudless day.",
    },
    WeatherCondition.PARTLY_CLOUDY: {
        WeatherIntensity.LIGHT: "A few wispy clouds drift overhead.",
        WeatherIntensity.MODERATE: "Scattered clouds dot an otherwise bright sky.",
        WeatherIntensity.HEAVY: "The sun fights through a thick blanket of clouds.",
        WeatherIntensity.SEVERE: "Grey clouds swirl, barely holding back the storm.",
    },
    WeatherCondition.OVERCAST: {
        WeatherIntensity.LIGHT: "The sky is uniformly grey and still.",
        WeatherIntensity.MODERATE: "A thick overcast blankets the land.",
        WeatherIntensity.HEAVY: "The heavy cloud cover presses down.",
        WeatherIntensity.SEVERE: "The world is swallowed by oppressive grey.",
    },
    WeatherCondition.DRIZZLE: {
        WeatherIntensity.LIGHT: "A gentle drizzle taps the ground.",
        WeatherIntensity.MODERATE: "Steady drizzle dampens the air.",
        WeatherIntensity.HEAVY: "Rain falls in a fine, relentless mist.",
        WeatherIntensity.SEVERE: "The drizzle soaks through everything.",
    },
    WeatherCondition.RAIN: {
        WeatherIntensity.LIGHT: "A steady rain falls from the sky.",
        WeatherIntensity.MODERATE: "Rain pours down steadily.",
        WeatherIntensity.HEAVY: "The rain comes down hard and cold.",
        WeatherIntensity.SEVERE: "Torrential rain lashes the land.",
    },
    WeatherCondition.HEAVY_RAIN: {
        WeatherIntensity.LIGHT: "The rain is heavier now; the ground is mud.",
        WeatherIntensity.MODERATE: "Sheet rain turns paths to rivers.",
        WeatherIntensity.HEAVY: "The downpour makes visibility poor.",
        WeatherIntensity.SEVERE: "Rain hammers the earth; thunder growls.",
    },
    WeatherCondition.THUNDERSTORM: {
        WeatherIntensity.LIGHT: "Distant thunder rumbles over light rain.",
        WeatherIntensity.MODERATE: "Lightning splits the sky as rain falls.",
        WeatherIntensity.HEAVY: "A fierce thunderstorm rages overhead.",
        WeatherIntensity.SEVERE: "The storm is violent and unrelenting.",
    },
    WeatherCondition.SNOW: {
        WeatherIntensity.LIGHT: "Soft snowflakes drift down lazily.",
        WeatherIntensity.MODERATE: "Snow falls steadily, blanketing the ground.",
        WeatherIntensity.HEAVY: "Heavy snow piles up quickly.",
        WeatherIntensity.SEVERE: "The blizzard conditions are setting in.",
    },
    WeatherCondition.BLIZZARD: {
        WeatherIntensity.LIGHT: "A bitter wind drives stinging snow.",
        WeatherIntensity.MODERATE: "White-out conditions make travel treacherous.",
        WeatherIntensity.HEAVY: "The blizzard rages with full force.",
        WeatherIntensity.SEVERE: "The storm is deadly; shelter is essential.",
    },
    WeatherCondition.FOG: {
        WeatherIntensity.LIGHT: "A thin mist clings to the ground.",
        WeatherIntensity.MODERATE: "Fog softens edges and muffles sound.",
        WeatherIntensity.HEAVY: "The fog is thick; shapes become uncertain.",
        WeatherIntensity.SEVERE: "A dense, disorienting fog swallows everything.",
    },
    WeatherCondition.HAZE: {
        WeatherIntensity.LIGHT: "A warm haze softens the horizon.",
        WeatherIntensity.MODERATE: "The air shimmers with heat and dust.",
        WeatherIntensity.HEAVY: "Haze blurs the landscape.",
        WeatherIntensity.SEVERE: "Thick haze makes distance impossible to judge.",
    },
    WeatherCondition.WINDY: {
        WeatherIntensity.LIGHT: "A steady breeze stirs the air.",
        WeatherIntensity.MODERATE: "Wind whips through trees and structures.",
        WeatherIntensity.HEAVY: "Gale-force winds strain against everything.",
        WeatherIntensity.SEVERE: "The wind howls like a living thing.",
    },
}

_LONG_DESCRIPTIONS: dict[str, dict[str, str]] = {
    WeatherCondition.CLEAR: {
        WeatherIntensity.LIGHT: "Morning light spills across the land in warm, golden hues. The air is crisp and clean, carrying the scent of earth and growing things. It is a good day for travel.",
        WeatherIntensity.MODERATE: "High clouds have vanished, leaving an unbroken dome of blue. Shadows are sharp. Every step feels lighter under the open sky.",
        WeatherIntensity.HEAVY: "There is no shelter from the sun. The road glimmers, and the heat rises in shimmering waves. Rest often, or risk exhaustion.",
        WeatherIntensity.SEVERE: "The world burns under an unforgiving sun. The horizon wavers. Only the foolhardy travel at midday.",
    },
    WeatherCondition.PARTLY_CLOUDY: {
        WeatherIntensity.LIGHT: "Clouds move like thoughts across the blue. One moment sun-warmed, the next cool shade passes over. The day feels balanced and alive.",
        WeatherIntensity.MODERATE: "The sky is a patchwork of sun and cloud. The changing light keeps the eye moving, always expecting the next break.",
        WeatherIntensity.HEAVY: "Clouds mass and break, and with each change the wind shifts. There is energy in the air, the promise of something to come.",
        WeatherIntensity.SEVERE: "The clouds churn darkly, racing across the sky. Even the wind seems to hold its breath, waiting.",
    },
    WeatherCondition.OVERCAST: {
        WeatherIntensity.LIGHT: "The world is wrapped in soft grey. Sounds travel farther, colors are muted, and there is a gentle, expectant quiet.",
        WeatherIntensity.MODERATE: "The overcast presses down like a held breath. There is no shadow, no glare, only the steady, weighty sky.",
        WeatherIntensity.HEAVY: "The cloud layer is thick and low. It feels almost indoor, as though the roof of the world has lowered.",
        WeatherIntensity.SEVERE: "The oppressive grey drains the land of warmth and hope. Every step feels heavier under the weight of the sky.",
    },
    WeatherCondition.DRIZZLE: {
        WeatherIntensity.LIGHT: "A fine mist cools the face and darkens stone. The world smells of wet dust and distant rain. Small things glisten.",
        WeatherIntensity.MODERATE: "The drizzle is persistent. Cloaks grow damp, roads slick, and eyes half-close against the gentle sting.",
        WeatherIntensity.HEAVY: "The mist clings to everything. Leather softens, paper swells, and a quiet rhythm drums on every surface.",
        WeatherIntensity.SEVERE: "The drizzle penetrates the stoutest gear. A cold, wet monotony settles into the bones.",
    },
    WeatherCondition.RAIN: {
        WeatherIntensity.LIGHT: "Rain taps a steady beat on roofs and leaves. Puddles begin to form, reflecting the world in fractured mirrors.",
        WeatherIntensity.MODERATE: "The rain is honest and thorough. Voices carry less far. Mud claims the verges of every path.",
        WeatherIntensity.HEAVY: "The downpour hammers the ground. Visibility drops, and every conversation becomes a shout against the roar.",
        WeatherIntensity.SEVERE: "The rain is a wall of water. It finds every gap, soaks every soul, and turns rivers into torrents.",
    },
    WeatherCondition.HEAVY_RAIN: {
        WeatherIntensity.LIGHT: "The rain intensifies; runoff streams down lanes. Footing grows unsure, and every step splashes.",
        WeatherIntensity.MODERATE: "Sheet rain turns the road into a river. Gear must be lashed tight, and fire becomes precious.",
        WeatherIntensity.HEAVY: "The world has become water. The sky merges with the earth, and navigation relies on memory more than sight.",
        WeatherIntensity.SEVERE: "Only the desperate move in this deluge. The land is drowning.",
    },
    WeatherCondition.THUNDERSTORM: {
        WeatherIntensity.LIGHT: "Thunder rolls in the distance. The first bright fork of lightning illuminates the clouds, then vanishes.",
        WeatherIntensity.MODERATE: "Lightning cracks overhead, and the thunderclap shakes the ground. Rain falls in gusts between flashes.",
        WeatherIntensity.HEAVY: "The storm is immediate and violent. Every flash freezes the world in stark relief before darkness returns.",
        WeatherIntensity.SEVERE: "The storm is a living beast. Wind, rain, lightning, and thunder combine into a single deafening roar.",
    },
    WeatherCondition.SNOW: {
        WeatherIntensity.LIGHT: "The first flakes settle on shoulders and sleeves. The world grows quieter, softer, whiter.",
        WeatherIntensity.MODERATE: "Snow piles on sills and branches. Footprints are quickly erased, and breath makes little clouds.",
        WeatherIntensity.HEAVY: "The snow falls so thick that the horizon blurs. Each step is effort, and the cold seeps inward.",
        WeatherIntensity.SEVERE: "The snow is relentless. The world turns white, then grey with dusk. Shelter is not a luxury; it is survival.",
    },
    WeatherCondition.BLIZZARD: {
        WeatherIntensity.LIGHT: "The wind drives stinging snow. It is hard to tell where the ground ends and the drifts begin.",
        WeatherIntensity.MODERATE: "White-out conditions erase landmarks. The wind bites through layers, and direction becomes guesswork.",
        WeatherIntensity.HEAVY: "The blizzard rages. To move is to risk never finding the way back.",
        WeatherIntensity.SEVERE: "This is a killing storm. The world is nothing but snow and wind. Stay hidden or perish.",
    },
    WeatherCondition.FOG: {
        WeatherIntensity.LIGHT: "Low mist pools in hollows and smooths the world. Familiar places take on an eerie, quiet character.",
        WeatherIntensity.MODERATE: "The fog muffles and softens. Shapes at the edge of sight become ambiguous; imagination fills the gaps.",
        WeatherIntensity.HEAVY: "The fog is thick enough to taste. Distance collapses, and every shadow becomes a potential threat or promise.",
        WeatherIntensity.SEVERE: "The fog is disorienting and relentless. It is easy to walk in circles, to lose track of where one stands.",
    },
    WeatherCondition.HAZE: {
        WeatherIntensity.LIGHT: "A warm, dry haze blurs the horizon. Colors run together, and the far hills look like dreams.",
        WeatherIntensity.MODERATE: "The air shimmers. Even nearby objects lose edge, and the sun becomes a pale coin in the sky.",
        WeatherIntensity.HEAVY: "Haze thickens the air. Breath feels heavy, and the world has the quality of a painting seen from too close.",
        WeatherIntensity.SEVERE: "The haze is suffocating. Every step is an effort, and the endless blur wears on the spirit.",
    },
    WeatherCondition.WINDY: {
        WeatherIntensity.LIGHT: "The breeze is refreshing, carrying scents from far away. Flags stir, and leaves dance.",
        WeatherIntensity.MODERATE: "The wind is insistent. Hoods flap, cloaks billow, and loose items need securing.",
        WeatherIntensity.HEAVY: "The gale tears at gear and resolve. Speech is hard; balance is harder.",
        WeatherIntensity.SEVERE: "The wind howls like a living thing. To stand is to fight; to move is to be battered.",
    },
}


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@dataclass
class WeatherFictionState:
    """
    Runtime record of one weather period for a world/session.

    Attributes:
        world_id            : the world this weather belongs to
        session_id          : optional active session binding
        condition           : weather condition slug (see WeatherCondition)
        intensity           : intensity slug (see WeatherIntensity)
        temperature_celsius : approximate temperature, or None
        wind_speed_kmh      : approximate wind speed, or None
        description_short   : one-line narration string
        description_long    : multi-line narration string
        effects             : gameplay effect modifiers (dict, schema below)
        started_at          : ISO timestamp when this weather period began
        ended_at            : ISO timestamp when it ended, or None if active
        weather_id          : unique identifier for this state entry

    effects schema:
        {
            "travel_speed_multiplier": float,    # 1.0 = normal
            "visibility": str,                   # clear | reduced | poor | none
            "ability_check_modifier": dict[str, int],  # attribute -> bonus/penalty
            "survival_dc_modifier": int,         # added to survival DCs
            "fire_risk_multiplier": float,       # 1.0 = normal
        }
    """

    world_id: str
    condition: str
    intensity: str
    session_id: str | None = None
    temperature_celsius: float | None = None
    wind_speed_kmh: float | None = None
    description_short: str = ""
    description_long: str = ""
    effects: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    ended_at: str | None = None
    weather_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "weather_id": self.weather_id,
            "world_id": self.world_id,
            "session_id": self.session_id,
            "condition": self.condition,
            "intensity": self.intensity,
            "temperature_celsius": self.temperature_celsius,
            "wind_speed_kmh": self.wind_speed_kmh,
            "description_short": self.description_short,
            "description_long": self.description_long,
            "effects": dict(self.effects),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> WeatherFictionState:
        return WeatherFictionState(
            weather_id=data["weather_id"],
            world_id=data["world_id"],
            session_id=data.get("session_id"),
            condition=data["condition"],
            intensity=data["intensity"],
            temperature_celsius=data.get("temperature_celsius"),
            wind_speed_kmh=data.get("wind_speed_kmh"),
            description_short=data.get("description_short", ""),
            description_long=data.get("description_long", ""),
            effects=dict(data.get("effects", {})),
            started_at=data.get("started_at", ""),
            ended_at=data.get("ended_at"),
        )


# ---------------------------------------------------------------------------
# Effect presets
# ---------------------------------------------------------------------------

_EFFECT_PRESETS: dict[str, dict[str, Any]] = {
    WeatherCondition.CLEAR: {
        "travel_speed_multiplier": 1.0,
        "visibility": "clear",
        "ability_check_modifier": {},
        "survival_dc_modifier": -2,
        "fire_risk_multiplier": 0.8,
    },
    WeatherCondition.PARTLY_CLOUDY: {
        "travel_speed_multiplier": 1.0,
        "visibility": "clear",
        "ability_check_modifier": {},
        "survival_dc_modifier": -1,
        "fire_risk_multiplier": 0.9,
    },
    WeatherCondition.OVERCAST: {
        "travel_speed_multiplier": 1.0,
        "visibility": "clear",
        "ability_check_modifier": {},
        "survival_dc_modifier": 0,
        "fire_risk_multiplier": 1.0,
    },
    WeatherCondition.DRIZZLE: {
        "travel_speed_multiplier": 0.9,
        "visibility": "reduced",
        "ability_check_modifier": {"dexterity": -1},
        "survival_dc_modifier": 0,
        "fire_risk_multiplier": 1.2,
    },
    WeatherCondition.RAIN: {
        "travel_speed_multiplier": 0.85,
        "visibility": "reduced",
        "ability_check_modifier": {"dexterity": -2, "perception": -2},
        "survival_dc_modifier": 1,
        "fire_risk_multiplier": 1.5,
    },
    WeatherCondition.HEAVY_RAIN: {
        "travel_speed_multiplier": 0.7,
        "visibility": "poor",
        "ability_check_modifier": {"dexterity": -3, "perception": -3},
        "survival_dc_modifier": 2,
        "fire_risk_multiplier": 2.0,
    },
    WeatherCondition.THUNDERSTORM: {
        "travel_speed_multiplier": 0.6,
        "visibility": "poor",
        "ability_check_modifier": {"dexterity": -4, "perception": -4},
        "survival_dc_modifier": 3,
        "fire_risk_multiplier": 3.0,
    },
    WeatherCondition.SNOW: {
        "travel_speed_multiplier": 0.8,
        "visibility": "reduced",
        "ability_check_modifier": {"dexterity": -2, "constitution": -1},
        "survival_dc_modifier": 2,
        "fire_risk_multiplier": 1.3,
    },
    WeatherCondition.BLIZZARD: {
        "travel_speed_multiplier": 0.4,
        "visibility": "none",
        "ability_check_modifier": {"dexterity": -5, "constitution": -3},
        "survival_dc_modifier": 5,
        "fire_risk_multiplier": 2.5,
    },
    WeatherCondition.FOG: {
        "travel_speed_multiplier": 0.75,
        "visibility": "none",
        "ability_check_modifier": {"perception": -4},
        "survival_dc_modifier": 1,
        "fire_risk_multiplier": 1.4,
    },
    WeatherCondition.HAZE: {
        "travel_speed_multiplier": 0.95,
        "visibility": "reduced",
        "ability_check_modifier": {"perception": -1},
        "survival_dc_modifier": 1,
        "fire_risk_multiplier": 1.6,
    },
    WeatherCondition.WINDY: {
        "travel_speed_multiplier": 0.9,
        "visibility": "reduced",
        "ability_check_modifier": {"strength": -1},
        "survival_dc_modifier": 1,
        "fire_risk_multiplier": 2.0,
    },
}


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class WeatherFictionManager:
    """
    Manages weather state per world and integrates with a CalendarProvider.

    Usage:
        mgr = WeatherFictionManager()
        mgr.set_weather("world-1", WeatherCondition.RAIN, WeatherIntensity.HEAVY)
        state = mgr.get_current_weather("world-1")
        print(state.description_long)
        effects = mgr.get_effects("world-1")
    """

    def __init__(self, calendar=None) -> None:
        # Lazy import to avoid circular deps
        if calendar is None:
            from travel_ledger import CalendarProvider
            calendar = CalendarProvider()
        self.calendar = calendar
        self._current: dict[str, WeatherFictionState] = {}
        self._history: list[WeatherFictionState] = []

    # ------------------------------------------------------------------
    # State mutations
    # ------------------------------------------------------------------

    def set_weather(
        self,
        world_id: str,
        condition: str,
        intensity: str,
        session_id: str | None = None,
        temperature_celsius: float | None = None,
        wind_speed_kmh: float | None = None,
        description_short: str = "",
        description_long: str = "",
        effects: dict[str, Any] | None = None,
        started_at: str | None = None,
    ) -> WeatherFictionState:
        """
        Set the current weather for a world. Ends any active weather period.
        """
        now = datetime.now(UTC)
        now_str = now.isoformat()
        started = started_at or now_str

        # End previous active state for this world
        prev = self._current.get(world_id)
        if prev is not None and prev.ended_at is None:
            prev.ended_at = now_str
            self._history.append(prev)

        short = description_short or _SHORT_DESCRIPTIONS.get(condition, {}).get(intensity, "The weather shifts.")
        long = description_long or _LONG_DESCRIPTIONS.get(condition, {}).get(intensity, "")
        fx = dict(effects) if effects else dict(_EFFECT_PRESETS.get(condition, {}))

        # Apply intensity scaling to effects
        fx = self._apply_intensity_scaling(condition, intensity, fx)

        state = WeatherFictionState(
            world_id=world_id,
            condition=condition,
            intensity=intensity,
            session_id=session_id,
            temperature_celsius=temperature_celsius,
            wind_speed_kmh=wind_speed_kmh,
            description_short=short,
            description_long=long,
            effects=fx,
            started_at=started,
        )
        self._current[world_id] = state
        return state

    def clear_weather(self, world_id: str) -> bool:
        """
        Remove the current weather state for a world (returns to no weather).
        """
        prev = self._current.pop(world_id, None)
        if prev is not None and prev.ended_at is None:
            prev.ended_at = datetime.now(UTC).isoformat()
            self._history.append(prev)
            return True
        return False

    def advance_time(self, world_id: str, seconds: float, evolution_rules: dict[str, Any] | None = None) -> WeatherFictionState | None:
        """
        Optionally transition weather based on elapsed in-game time.

        If `evolution_rules` is provided, performs probabilistic transitions
        using the transition matrix and biome/season weights.
        """
        current = self._current.get(world_id)
        if current is None or current.ended_at is not None:
            return None
        if evolution_rules is None:
            return current

        transitions = evolution_rules.get("transitions", {})
        condition_transitions = transitions.get(current.condition, {})
        if not condition_transitions:
            return current

        # Build weighted choices
        choices = []
        weights = []
        for cond, weight in condition_transitions.items():
            w = float(weight)
            season = evolution_rules.get("season", "")
            if season == "winter" and cond in ("snow", "blizzard", "overcast"):
                w *= 1.5
            elif season == "summer" and cond in ("clear", "partly_cloudy", "haze"):
                w *= 1.3
            elif season == "spring" and cond in ("rain", "drizzle", "fog") or season == "autumn" and cond in ("overcast", "windy", "fog"):
                w *= 1.2
            choices.append(cond)
            weights.append(w)

        if not choices:
            return current

        total = sum(weights)
        if total <= 0:
            return current

        pick = random.uniform(0, total)
        cumulative = 0.0
        new_condition = current.condition
        for cond, w in zip(choices, weights):
            cumulative += w
            if pick <= cumulative:
                new_condition = cond
                break

        # Determine intensity based on condition
        new_intensity = current.intensity
        if new_condition in ("thunderstorm", "blizzard", "heavy_rain"):
            new_intensity = WeatherIntensity.HEAVY
        elif new_condition in ("snow", "rain", "fog", "haze") or new_condition in ("overcast", "windy"):
            new_intensity = WeatherIntensity.MODERATE
        elif new_condition == "clear":
            new_intensity = WeatherIntensity.LIGHT

        # Update temperature with seasonal influence
        new_temp = current.temperature_celsius
        seasonal_temp = evolution_rules.get("temperature_delta", 0)
        if new_temp is not None and seasonal_temp:
            new_temp = round(new_temp + random.uniform(-1, 1) + seasonal_temp * 0.1, 1)

        return self.set_weather(
            world_id=world_id,
            condition=new_condition,
            intensity=new_intensity,
            session_id=current.session_id,
            temperature_celsius=new_temp,
            wind_speed_kmh=current.wind_speed_kmh,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_current_weather(self, world_id: str) -> WeatherFictionState | None:
        state = self._current.get(world_id)
        if state is not None and state.ended_at is None:
            return state
        return None

    def get_effects(self, world_id: str) -> dict[str, Any]:
        state = self._current.get(world_id)
        if state is not None and state.ended_at is None:
            return dict(state.effects)
        return {}

    def get_narration(self, world_id: str, long: bool = False) -> str:
        state = self._current.get(world_id)
        if state is None or state.ended_at is not None:
            return ""
        if long:
            return state.description_long
        return state.description_short

    def get_weather_history(self, world_id: str | None = None) -> list[dict[str, Any]]:
        history = list(self._history)
        if world_id is not None:
            history = [h for h in history if h.world_id == world_id]
        return [h.to_dict() for h in sorted(history, key=lambda h: h.started_at)]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "current": {wid: s.to_dict() for wid, s in self._current.items()},
            "history": [s.to_dict() for s in self._history],
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._current.clear()
        self._history.clear()
        for wid, data in state.get("current", {}).items():
            self._current[wid] = WeatherFictionState.from_dict(data)
        for data in state.get("history", []):
            self._history.append(WeatherFictionState.from_dict(data))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _apply_intensity_scaling(
        self, condition: str, intensity: str, effects: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Adjust effect values based on intensity. Heavy/severe weather should
        feel worse than light/moderate, but the presets already encode that.
        This method provides a hook for fine-tuning.
        """
        return effects
