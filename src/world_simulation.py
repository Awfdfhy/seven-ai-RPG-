"""
RPG World Simulation: ecosystems, weather patterns, day/night cycles.
Integrates with WorldMap, WeatherFiction, and WorldEvent systems.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class DayNightPhase:
    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"


class Season:
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


# ---------------------------------------------------------------------------
# State dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DayNightState:
    """
    Day/night cycle state for a world.
    """
    world_id: str
    phase: str = DayNightPhase.DAY
    illumination: float = 1.0
    temperature_modifier: float = 0.0
    hour: int = 6
    day: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "phase": self.phase,
            "illumination": self.illumination,
            "temperature_modifier": self.temperature_modifier,
            "hour": self.hour,
            "day": self.day,
        }


@dataclass
class SpeciesPopulation:
    """
    Runtime population record for a species at a location.
    """
    species_id: str
    location_id: str
    population: int = 0
    health: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "species_id": self.species_id,
            "location_id": self.location_id,
            "population": self.population,
            "health": self.health,
        }


@dataclass
class ResourceNode:
    """
    A resource node at a location (herbs, ore, wood, etc.).
    """
    node_id: str
    location_id: str
    resource_type: str
    abundance: float = 1.0
    depleted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "location_id": self.location_id,
            "resource_type": self.resource_type,
            "abundance": self.abundance,
            "depleted": self.depleted,
        }


@dataclass
class EcosystemState:
    """
    Ecosystem state for a single location within a world.
    """
    world_id: str
    location_id: str
    biome: str = ""
    season: str = Season.SPRING
    populations: list[dict[str, Any]] = field(default_factory=list)
    resources: list[dict[str, Any]] = field(default_factory=list)
    last_updated_day: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "location_id": self.location_id,
            "biome": self.biome,
            "season": self.season,
            "populations": [dict(p) for p in self.populations],
            "resources": [dict(r) for r in self.resources],
            "last_updated_day": self.last_updated_day,
        }


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class WorldSimulationManager:
    """
    Owns world simulation state: day/night, ecosystems, weather evolution.
    Designed to integrate with WorldBridge and existing weather/world systems.
    """

    def __init__(self, data_directory: str | None = None, calendar=None, weather_manager=None) -> None:
        self.calendar = calendar
        self.weather_manager = weather_manager

        base = data_directory or os.path.join(os.path.dirname(__file__), "..", "data")
        self._load_definitions(base)

        # world_id -> DayNightState
        self._day_night: dict[str, DayNightState] = {}
        # world_id -> location_id -> EcosystemState
        self._ecosystems: dict[str, dict[str, EcosystemState]] = {}

    # ------------------------------------------------------------------
    # Definition loading
    # ------------------------------------------------------------------

    def _load_definitions(self, base: str) -> None:
        path = os.path.join(base, "ecosystems.json")
        self._defs: dict[str, Any] = {}
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    self._defs = json.load(fh)
            except Exception:
                self._defs = {}

    # ------------------------------------------------------------------
    # World initialization
    # ------------------------------------------------------------------

    def ensure_world(self, world_id: str, start_hour: int = 10, start_day: int = 1) -> dict[str, Any]:
        """
        Initialize simulation state for a world if not already present.
        Returns the world snapshot.
        """
        if world_id not in self._day_night:
            self._day_night[world_id] = DayNightState(
                world_id=world_id, hour=start_hour, day=start_day
            )
            phase, illum, temp = self._compute_day_night(start_hour)
            self._day_night[world_id].phase = phase
            self._day_night[world_id].illumination = illum
            self._day_night[world_id].temperature_modifier = temp
        if world_id not in self._ecosystems:
            self._ecosystems[world_id] = {}
        return self.get_world_snapshot(world_id)

    def get_or_create_state(self, world_id: str) -> dict[str, Any]:
        """Alias for ensure_world (test convenience)."""
        return self.ensure_world(world_id)

    # ------------------------------------------------------------------
    # Time advancement
    # ------------------------------------------------------------------

    def advance_time(self, world_id: str, hours: int) -> dict[str, Any]:
        """
        Advance simulation by `hours` in-game hours.
        Updates day/night, evolves weather, and updates ecosystems.
        Returns a dict of changes.
        """
        if world_id not in self._day_night:
            self.ensure_world(world_id)

        dn = self._day_night[world_id]
        changes: dict[str, Any] = {
            "day_night": {"before": dn.to_dict()},
            "weather_changes": [],
            "ecosystem_changes": [],
        }

        # Advance clock
        total = dn.hour + hours
        day_delta = total // 24
        old_day = dn.day
        dn.hour = total % 24
        dn.day += day_delta
        dn.phase, dn.illumination, dn.temperature_modifier = self._compute_day_night(dn.hour)

        changes["day_night"]["after"] = dn.to_dict()

        # Evolve weather via weather_manager if available
        if self.weather_manager is not None:
            evolution = self._evolve_weather(world_id, hours, dn.day)
            changes["weather_changes"] = evolution

        # Update ecosystems if day changed
        if dn.day > old_day or day_delta > 0:
            eco_changes = self._update_ecosystems(world_id, old_day, dn.day)
            changes["ecosystem_changes"] = eco_changes

        return changes

    def _compute_day_night(self, hour: int) -> tuple[str, float, float]:
        """
        Return (phase, illumination, temperature_modifier) for the given hour.
        """
        if 5 <= hour < 7:
            return DayNightPhase.DAWN, 0.4, -2.0
        elif 7 <= hour < 17:
            return DayNightPhase.DAY, 1.0, 0.0
        elif 17 <= hour < 19:
            return DayNightPhase.DUSK, 0.3, -1.0
        else:
            return DayNightPhase.NIGHT, 0.0, -4.0

    # ------------------------------------------------------------------
    # Weather evolution
    # ------------------------------------------------------------------

    def _evolve_weather(self, world_id: str, hours: int, current_day: int) -> list[dict[str, Any]]:
        changes = []
        if hasattr(self.weather_manager, "advance_time"):
            rules = self._build_evolution_rules(world_id, current_day)
            checks = max(1, hours // 4)
            for _ in range(checks):
                new_state = self.weather_manager.advance_time(
                    world_id, 4 * 3600.0, evolution_rules=rules
                )
                if new_state is not None:
                    changes.append(new_state.to_dict())
        return changes

    def _build_evolution_rules(self, world_id: str, current_day: int) -> dict[str, Any]:
        rules: dict[str, Any] = {}
        if not self._defs.get("weather_transitions"):
            return rules

        season = self._get_season_for_day(current_day)
        seasonal = self._defs.get("seasonal_modifiers", {}).get(season, {})
        rules["transitions"] = self._defs["weather_transitions"]
        rules["season"] = season
        rules["temperature_delta"] = seasonal.get("temperature_delta", 0)
        rules["biome_weights"] = {}
        return rules

    # ------------------------------------------------------------------
    # Ecosystem simulation
    # ------------------------------------------------------------------

    def _update_ecosystems(self, world_id: str, old_day: int, new_day: int) -> list[dict[str, Any]]:
        changes = []
        eco_map = self._ecosystems.get(world_id, {})
        for loc_id, eco in eco_map.items():
            if eco.last_updated_day >= new_day:
                continue
            days_passed = new_day - eco.last_updated_day
            season = self._get_season_for_day(new_day)
            eco.season = season

            seasonal = self._defs.get("seasonal_modifiers", {}).get(season, {})
            activity_mod = seasonal.get("wildlife_activity", 1.0)

            # Update populations
            for pop in eco.populations:
                sid = pop["species_id"]
                species = self._defs.get("species", {}).get(sid, {})
                base_pop = species.get("base_population", 10)
                repro = species.get("reproduction_rate", 0.01)

                w = None
                if self.weather_manager is not None:
                    w = self.weather_manager.get_current_weather(world_id)
                weather_effects = species.get("weather_effects", {}) if w else {}

                weather_mod = weather_effects.get(w.condition if w else "", 0.0)

                target = base_pop * activity_mod * (1.0 + weather_mod)
                diff = target - pop["population"]
                move = diff * 0.1 * days_passed
                pop["population"] = max(0, int(pop["population"] + move))
                pop["health"] = max(0.0, min(1.0, pop["health"] + random.uniform(-0.05, 0.05) * days_passed))

                if move != 0:
                    changes.append({
                        "location_id": loc_id,
                        "species_id": sid,
                        "new_population": pop["population"],
                        "trend": "increasing" if move > 0 else "decreasing",
                    })

            # Regenerate resources
            res_mult = seasonal.get("resource_multiplier", 1.0)
            for res in eco.resources:
                if not res["depleted"]:
                    res["abundance"] = min(1.0, res["abundance"] + 0.05 * res_mult * days_passed)
                    if res["abundance"] <= 0:
                        res["depleted"] = True

            eco.last_updated_day = new_day
        return changes

    # ------------------------------------------------------------------
    # Ecosystem initialization
    # ------------------------------------------------------------------

    def initialize_ecosystem_for_location(self, world_id: str, location_id: str, biome: str) -> EcosystemState:
        """
        Create a fresh ecosystem state for a location.
        """
        if world_id not in self._ecosystems:
            self._ecosystems[world_id] = {}

        biome_data = self._defs.get("biomes", {}).get(biome, {})
        species_ids = biome_data.get("wildlife", [])

        populations = []
        for sid in species_ids:
            species = self._defs.get("species", {}).get(sid, {})
            populations.append({
                "species_id": sid,
                "population": species.get("base_population", 10),
                "health": 1.0,
            })

        resources = []
        for rid in biome_data.get("resource_nodes", []):
            resources.append({
                "node_id": f"{location_id}_{rid}",
                "resource_type": rid,
                "abundance": 1.0,
                "depleted": False,
            })

        eco = EcosystemState(
            world_id=world_id,
            location_id=location_id,
            biome=biome,
            populations=populations,
            resources=resources,
        )
        self._ecosystems[world_id][location_id] = eco
        return eco

    def ensure_location_ecosystem(self, world_id: str, location_id: str) -> EcosystemState:
        """
        Return existing ecosystem or create one based on location_biomes mapping.
        """
        existing = self._ecosystems.get(world_id, {}).get(location_id)
        if existing:
            return existing
        biome = self._defs.get("location_biomes", {}).get(location_id, "wilderness")
        return self.initialize_ecosystem_for_location(world_id, location_id, biome)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_day_night_state(self, world_id: str) -> dict[str, Any] | None:
        dn = self._day_night.get(world_id)
        return dn.to_dict() if dn else None

    def get_ecosystem_state(self, world_id: str, location_id: str | None = None) -> dict[str, Any]:
        eco_map = self._ecosystems.get(world_id, {})
        if location_id:
            eco = eco_map.get(location_id)
            return eco.to_dict() if eco else {}
        return {lid: eco.to_dict() for lid, eco in eco_map.items()}

    def get_biome(self, location_id: str) -> str:
        return self._defs.get("location_biomes", {}).get(location_id, "wilderness")

    def get_season(self, world_id: str) -> str:
        dn = self._day_night.get(world_id)
        day = dn.day if dn else 1
        return self._get_season_for_day(day)

    def _get_season_for_day(self, day: int) -> str:
        cycle = day % 360
        if cycle < 90:
            return Season.SPRING
        elif cycle < 180:
            return Season.SUMMER
        elif cycle < 270:
            return Season.AUTUMN
        else:
            return Season.WINTER

    def get_world_snapshot(self, world_id: str) -> dict[str, Any]:
        dn = self.get_day_night_state(world_id)
        eco = self.get_ecosystem_state(world_id)
        season = self.get_season(world_id)
        narration = self._get_narration_for_state(world_id)
        return {
            "world_id": world_id,
            "day_night": dn,
            "season": season,
            "ecosystems": eco,
            "narration": narration,
        }

    def _get_narration_for_state(self, world_id: str) -> str:
        dn = self._day_night.get(world_id)
        if not dn:
            return ""
        narrations = self._defs.get("day_night_narration", {}).get(dn.phase, [])
        if not narrations:
            return ""
        return random.choice(narrations)

    def get_weather_evolution_rules(self) -> dict[str, Any]:
        return self._defs.get("weather_transitions", {})

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "day_night": {wid: s.to_dict() for wid, s in self._day_night.items()},
            "ecosystems": {
                wid: {lid: eco.to_dict() for lid, eco in locs.items()}
                for wid, locs in self._ecosystems.items()
            },
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._day_night.clear()
        self._ecosystems.clear()
        for wid, data in state.get("day_night", {}).items():
            self._day_night[wid] = DayNightState(**data)
        for wid, locs in state.get("ecosystems", {}).items():
            self._ecosystems[wid] = {}
            for lid, eco in locs.items():
                self._ecosystems[wid][lid] = EcosystemState(**eco)
