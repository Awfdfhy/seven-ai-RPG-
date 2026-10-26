"""
Tests for RPG World Simulation: ecosystems, weather patterns, day/night cycles.
Run with: python -m pytest tests/ -v
or:       python tests/test_world_simulation.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from world_simulation import (
    DayNightPhase,
    DayNightState,
    Season,
    WorldSimulationManager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(data_dir=None):
    return WorldSimulationManager(data_directory=data_dir)


# ---------------------------------------------------------------------------
# DayNightState tests
# ---------------------------------------------------------------------------

class TestDayNightState(unittest.TestCase):
    def test_default_values(self):
        s = DayNightState(world_id="w1")
        assert s.world_id == "w1"
        assert s.phase == DayNightPhase.DAY
        assert s.illumination == 1.0
        assert s.temperature_modifier == 0.0
        assert s.hour == 6
        assert s.day == 1

    def test_to_dict_roundtrip(self):
        s = DayNightState(world_id="w1", phase=DayNightPhase.NIGHT, illumination=0.0,
                          temperature_modifier=-4.0, hour=22, day=5)
        d = s.to_dict()
        assert d["phase"] == DayNightPhase.NIGHT
        assert d["illumination"] == 0.0
        assert d["hour"] == 22
        assert d["day"] == 5


# ---------------------------------------------------------------------------
# WorldSimulationManager tests
# ---------------------------------------------------------------------------

class TestWorldSimulationManager(unittest.TestCase):
    def test_ensure_world_creates_state(self):
        mgr = _make_manager()
        snap = mgr.ensure_world("w1")
        assert snap["day_night"]["world_id"] == "w1"
        assert snap["day_night"]["hour"] == 10
        assert snap["day_night"]["phase"] == DayNightPhase.DAY

    def test_ensure_world_custom_start(self):
        mgr = _make_manager()
        snap = mgr.ensure_world("w1", start_hour=20, start_day=3)
        assert snap["day_night"]["hour"] == 20
        assert snap["day_night"]["day"] == 3
        assert snap["day_night"]["phase"] == DayNightPhase.NIGHT

    def test_advance_time_changes_hour_and_day(self):
        mgr = _make_manager()
        mgr.ensure_world("w1", start_hour=22, start_day=1)
        changes = mgr.advance_time("w1", 4)
        assert changes["day_night"]["after"]["hour"] == 2
        assert changes["day_night"]["after"]["day"] == 2

    def test_advance_time_updates_day_night_phase(self):
        mgr = _make_manager()
        mgr.ensure_world("w1", start_hour=5)
        changes = mgr.advance_time("w1", 1)
        assert changes["day_night"]["after"]["phase"] == DayNightPhase.DAWN
        assert changes["day_night"]["after"]["illumination"] == 0.4

    def test_advance_time_returns_changes_structure(self):
        mgr = _make_manager()
        mgr.ensure_world("w1")
        changes = mgr.advance_time("w1", 24)
        assert "day_night" in changes
        assert "weather_changes" in changes
        assert "ecosystem_changes" in changes

    def test_get_day_night_state(self):
        mgr = _make_manager()
        mgr.ensure_world("w1")
        state = mgr.get_day_night_state("w1")
        assert state is not None
        assert state["world_id"] == "w1"

    def test_get_day_night_state_missing(self):
        mgr = _make_manager()
        assert mgr.get_day_night_state("nonexistent") is None

    def test_get_season_spring(self):
        mgr = _make_manager()
        mgr.ensure_world("w1", start_day=1)
        assert mgr.get_season("w1") == Season.SPRING

    def test_get_season_summer(self):
        mgr = _make_manager()
        mgr.ensure_world("w1", start_day=100)
        assert mgr.get_season("w1") == Season.SUMMER

    def test_get_season_autumn(self):
        mgr = _make_manager()
        mgr.ensure_world("w1", start_day=200)
        assert mgr.get_season("w1") == Season.AUTUMN

    def test_get_season_winter(self):
        mgr = _make_manager()
        mgr.ensure_world("w1", start_day=300)
        assert mgr.get_season("w1") == Season.WINTER

    def test_get_biome_known_location(self):
        mgr = _make_manager()
        assert mgr.get_biome("oakhaven") == "village"
        assert mgr.get_biome("oakhaven_outskirts") == "wilderness"
        assert mgr.get_biome("northern_pass") == "pass"

    def test_get_biome_unknown_falls_back_to_wilderness(self):
        mgr = _make_manager()
        assert mgr.get_biome("unknown_place") == "wilderness"

    def test_ensure_location_ecosystem_creates_state(self):
        mgr = _make_manager()
        mgr.ensure_world("w1")
        eco = mgr.ensure_location_ecosystem("w1", "oakhaven")
        assert eco.world_id == "w1"
        assert eco.location_id == "oakhaven"
        assert eco.biome == "village"

    def test_ensure_location_ecosystem_returns_existing(self):
        mgr = _make_manager()
        mgr.ensure_world("w1")
        first = mgr.ensure_location_ecosystem("w1", "oakhaven")
        second = mgr.ensure_location_ecosystem("w1", "oakhaven")
        assert first is second

    def test_get_ecosystem_state_specific_location(self):
        mgr = _make_manager()
        mgr.ensure_world("w1")
        mgr.ensure_location_ecosystem("w1", "oakhaven")
        state = mgr.get_ecosystem_state("w1", "oakhaven")
        assert state["location_id"] == "oakhaven"
        assert "populations" in state
        assert "resources" in state

    def test_get_ecosystem_state_all_locations(self):
        mgr = _make_manager()
        mgr.ensure_world("w1")
        mgr.ensure_location_ecosystem("w1", "oakhaven")
        mgr.ensure_location_ecosystem("w1", "oakhaven_outskirts")
        all_eco = mgr.get_ecosystem_state("w1")
        assert "oakhaven" in all_eco
        assert "oakhaven_outskirts" in all_eco

    def test_get_weather_evolution_rules(self):
        mgr = _make_manager()
        rules = mgr.get_weather_evolution_rules()
        assert "clear" in rules
        assert "rain" in rules

    def test_get_world_snapshot(self):
        mgr = _make_manager()
        mgr.ensure_world("w1")
        snap = mgr.get_world_snapshot("w1")
        assert snap["world_id"] == "w1"
        assert "day_night" in snap
        assert "season" in snap
        assert "ecosystems" in snap
        assert "narration" in snap
        assert snap["narration"] != ""

    def test_export_import_roundtrip(self):
        mgr = _make_manager()
        mgr.ensure_world("w1", start_hour=10, start_day=5)
        mgr.ensure_location_ecosystem("w1", "oakhaven")
        mgr.advance_time("w1", 24)

        state = mgr.export_state()

        mgr2 = _make_manager()
        mgr2.import_state(state)

        assert mgr2.get_day_night_state("w1")["hour"] == 10
        assert mgr2.get_day_night_state("w1")["day"] == 6
        assert mgr2.get_ecosystem_state("w1", "oakhaven")["biome"] == "village"
        assert mgr2.get_season("w1") == mgr.get_season("w1")

    def test_advance_time_triggers_ecosystem_update(self):
        mgr = _make_manager()
        mgr.ensure_world("w1")
        mgr.ensure_location_ecosystem("w1", "oakhaven")
        # Advance 10 days
        changes = mgr.advance_time("w1", 240)
        # Ecosystem should be updated
        eco = mgr.get_ecosystem_state("w1", "oakhaven")
        assert eco["last_updated_day"] > 1


# ---------------------------------------------------------------------------
# Integration tests (with weather_manager)
# ---------------------------------------------------------------------------

class TestWorldSimulationWeatherIntegration(unittest.TestCase):
    def test_advance_time_with_weather_manager(self):
        from weather_fiction import WeatherCondition, WeatherFictionManager, WeatherIntensity
        weather = WeatherFictionManager()
        weather.set_weather("w1", WeatherCondition.CLEAR, WeatherIntensity.LIGHT, temperature_celsius=20.0)
        mgr = _make_manager()
        mgr.weather_manager = weather
        mgr.ensure_world("w1")
        changes = mgr.advance_time("w1", 24)
        # Weather may or may not change (probabilistic), but should be a list
        assert isinstance(changes["weather_changes"], list)

    def test_advance_time_without_weather_manager_no_changes(self):
        mgr = _make_manager()
        mgr.ensure_world("w1")
        changes = mgr.advance_time("w1", 24)
        assert changes["weather_changes"] == []


if __name__ == "__main__":
    unittest.main()
