"""
Tests for RPG-09-04: Weather Fiction State.
Run with: python -m pytest tests/ -v
or:       python tests/test_weather_fiction.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from weather_fiction import (
    WeatherCondition,
    WeatherFictionManager,
    WeatherFictionState,
    WeatherIntensity,
)

# ---------------------------------------------------------------------------
# WeatherFictionState tests
# ---------------------------------------------------------------------------

class TestWeatherFictionState:
    def test_default_values(self):
        state = WeatherFictionState(
            world_id="w1",
            condition=WeatherCondition.RAIN,
            intensity=WeatherIntensity.MODERATE,
        )
        assert state.world_id == "w1"
        assert state.condition == WeatherCondition.RAIN
        assert state.intensity == WeatherIntensity.MODERATE
        assert state.session_id is None
        assert state.temperature_celsius is None
        assert state.wind_speed_kmh is None
        assert state.weather_id is not None
        assert state.ended_at is None

    def test_to_dict_roundtrip(self):
        state = WeatherFictionState(
            world_id="w1",
            condition=WeatherCondition.SNOW,
            intensity=WeatherIntensity.HEAVY,
            session_id="s1",
            temperature_celsius=-5.0,
            wind_speed_kmh=30.0,
            description_short="Heavy snow falls.",
            description_long="The snow falls heavily.",
            effects={"travel_speed_multiplier": 0.6},
        )
        restored = WeatherFictionState.from_dict(state.to_dict())
        assert restored.world_id == "w1"
        assert restored.condition == WeatherCondition.SNOW
        assert restored.intensity == WeatherIntensity.HEAVY
        assert restored.session_id == "s1"
        assert restored.temperature_celsius == -5.0
        assert restored.wind_speed_kmh == 30.0
        assert restored.description_short == "Heavy snow falls."
        assert restored.description_long == "The snow falls heavily."
        assert restored.effects == {"travel_speed_multiplier": 0.6}


# ---------------------------------------------------------------------------
# WeatherFictionManager tests
# ---------------------------------------------------------------------------

class TestWeatherFictionManager:
    def test_set_weather_creates_state(self):
        mgr = WeatherFictionManager()
        state = mgr.set_weather("w1", WeatherCondition.CLEAR, WeatherIntensity.LIGHT)
        assert state is not None
        assert state.world_id == "w1"
        assert state.condition == WeatherCondition.CLEAR
        assert state.intensity == WeatherIntensity.LIGHT

    def test_get_current_weather(self):
        mgr = WeatherFictionManager()
        mgr.set_weather("w1", WeatherCondition.RAIN, WeatherIntensity.MODERATE)
        current = mgr.get_current_weather("w1")
        assert current is not None
        assert current.condition == WeatherCondition.RAIN

    def test_get_current_weather_returns_none_for_unknown(self):
        mgr = WeatherFictionManager()
        assert mgr.get_current_weather("missing") is None

    def test_clear_weather(self):
        mgr = WeatherFictionManager()
        mgr.set_weather("w1", WeatherCondition.RAIN, WeatherIntensity.MODERATE)
        ok = mgr.clear_weather("w1")
        assert ok is True
        assert mgr.get_current_weather("w1") is None

    def test_clear_weather_returns_false_when_no_weather(self):
        mgr = WeatherFictionManager()
        assert mgr.clear_weather("w1") is False

    def test_set_weather_ends_previous(self):
        mgr = WeatherFictionManager()
        mgr.set_weather("w1", WeatherCondition.CLEAR, WeatherIntensity.LIGHT)
        mgr.set_weather("w1", WeatherCondition.RAIN, WeatherIntensity.HEAVY)
        current = mgr.get_current_weather("w1")
        assert current.condition == WeatherCondition.RAIN
        history = mgr.get_weather_history("w1")
        assert len(history) == 1
        assert history[0]["condition"] == WeatherCondition.CLEAR
        assert history[0]["ended_at"] is not None

    def test_get_effects_returns_defaults(self):
        mgr = WeatherFictionManager()
        mgr.set_weather("w1", WeatherCondition.THUNDERSTORM, WeatherIntensity.SEVERE)
        fx = mgr.get_effects("w1")
        assert fx["travel_speed_multiplier"] == 0.6
        assert fx["visibility"] == "poor"
        assert fx["survival_dc_modifier"] == 3

    def test_get_effects_returns_empty_for_no_weather(self):
        mgr = WeatherFictionManager()
        assert mgr.get_effects("w1") == {}

    def test_get_narration_short(self):
        mgr = WeatherFictionManager()
        mgr.set_weather("w1", WeatherCondition.FOG, WeatherIntensity.MODERATE)
        narration = mgr.get_narration("w1", long=False)
        assert narration != ""
        assert "Fog" in narration or "fog" in narration

    def test_get_narration_long(self):
        mgr = WeatherFictionManager()
        mgr.set_weather("w1", WeatherCondition.BLIZZARD, WeatherIntensity.HEAVY)
        narration = mgr.get_narration("w1", long=True)
        assert len(narration) > 20
        assert "white" in narration.lower() or "snow" in narration.lower() or "blizzard" in narration.lower()

    def test_get_narration_empty_for_no_weather(self):
        mgr = WeatherFictionManager()
        assert mgr.get_narration("w1") == ""
        assert mgr.get_narration("w1", long=True) == ""

    def test_get_weather_history_scoped_by_world(self):
        mgr = WeatherFictionManager()
        mgr.set_weather("w1", WeatherCondition.CLEAR, WeatherIntensity.LIGHT)
        mgr.clear_weather("w1")
        mgr.set_weather("w2", WeatherCondition.RAIN, WeatherIntensity.MODERATE)
        history_w1 = mgr.get_weather_history("w1")
        history_w2 = mgr.get_weather_history("w2")
        assert len(history_w1) == 1
        assert history_w1[0]["condition"] == WeatherCondition.CLEAR
        assert len(history_w2) == 0  # w2 still active

    def test_advance_time_does_not_mutate_by_default(self):
        mgr = WeatherFictionManager()
        mgr.set_weather("w1", WeatherCondition.CLEAR, WeatherIntensity.LIGHT)
        before = mgr.get_current_weather("w1")
        mgr.advance_time("w1", 3600.0)
        after = mgr.get_current_weather("w1")
        assert after is before

    def test_advance_time_returns_none_when_no_weather(self):
        mgr = WeatherFictionManager()
        assert mgr.advance_time("w1", 60.0) is None

    def test_export_import_roundtrip(self):
        mgr = WeatherFictionManager()
        mgr.set_weather("w1", WeatherCondition.RAIN, WeatherIntensity.HEAVY)
        mgr.set_weather("w2", WeatherCondition.SNOW, WeatherIntensity.LIGHT)
        mgr.clear_weather("w2")

        state = mgr.export_state()
        mgr2 = WeatherFictionManager()
        mgr2.import_state(state)

        assert mgr2.get_current_weather("w1").condition == WeatherCondition.RAIN
        assert mgr2.get_current_weather("w2") is None
        hist = mgr2.get_weather_history("w2")
        assert len(hist) == 1
        assert hist[0]["condition"] == WeatherCondition.SNOW

    def test_multiple_worlds_independent(self):
        mgr = WeatherFictionManager()
        mgr.set_weather("w1", WeatherCondition.CLEAR, WeatherIntensity.LIGHT)
        mgr.set_weather("w2", WeatherCondition.BLIZZARD, WeatherIntensity.SEVERE)
        assert mgr.get_current_weather("w1").condition == WeatherCondition.CLEAR
        assert mgr.get_current_weather("w2").condition == WeatherCondition.BLIZZARD
        assert mgr.get_effects("w1")["travel_speed_multiplier"] == 1.0
        assert mgr.get_effects("w2")["travel_speed_multiplier"] == 0.4

    def test_custom_effects_override_presets(self):
        mgr = WeatherFictionManager()
        mgr.set_weather(
            "w1",
            WeatherCondition.RAIN,
            WeatherIntensity.MODERATE,
            effects={"travel_speed_multiplier": 0.5, "custom_effect": 42},
        )
        fx = mgr.get_effects("w1")
        assert fx["travel_speed_multiplier"] == 0.5
        assert fx["custom_effect"] == 42

    def test_custom_descriptions_override_presets(self):
        mgr = WeatherFictionManager()
        mgr.set_weather(
            "w1",
            WeatherCondition.RAIN,
            WeatherIntensity.MODERATE,
            description_short="Custom short.",
            description_long="Custom long description.",
        )
        assert mgr.get_narration("w1") == "Custom short."
        assert mgr.get_narration("w1", long=True) == "Custom long description."


# ---------------------------------------------------------------------------
# Integration-style tests (cross-module behavior)
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_world_session_weather_integration(self):
        """
        Weather state should be attachable to a world session's snapshot.
        """
        from world_session import WorldSessionManager

        mgr = WeatherFictionManager()
        session_mgr = WorldSessionManager()
        session = session_mgr.create_session("w1", metadata={"hero": "Thrall"})

        mgr.set_weather("w1", WeatherCondition.HEAVY_RAIN, WeatherIntensity.HEAVY)
        fx = mgr.get_effects("w1")

        # Session snapshot can carry weather effects
        snapshot = {
            "hp": 100,
            "weather_effects": fx,
        }
        ok = session_mgr.update_snapshot(session.session_id, snapshot)
        assert ok is True
        assert session_mgr.get_session(session.session_id).snapshot["weather_effects"]["visibility"] == "poor"

    def test_travel_ledger_weather_impact(self):
        """
        Weather effects should be queryable alongside travel estimates.
        """
        from travel_ledger import LocationDefinition, TravelLedgerManager

        mgr = WeatherFictionManager()
        travel_mgr = TravelLedgerManager()
        travel_mgr.register_location(LocationDefinition(id="loc_a", name="A", region="R", danger_level=1))
        travel_mgr.register_location(LocationDefinition(id="loc_b", name="B", region="R", danger_level=1))

        mgr.set_weather("w1", WeatherCondition.SNOW, WeatherIntensity.HEAVY)
        fx = mgr.get_effects("w1")
        base_time = travel_mgr.estimate_travel_time("loc_a", "loc_b", travel_speed="normal")
        adjusted_time = base_time * fx["travel_speed_multiplier"]
        assert adjusted_time < base_time
        assert adjusted_time / 60.0 > 0.0


if __name__ == "__main__":
    suites = [
        TestWeatherFictionState,
        TestWeatherFictionManager,
        TestIntegration,
    ]
    passed = 0
    failed = 0
    for suite in suites:
        instance = suite()
        for method in dir(instance):
            if method.startswith("test_"):
                try:
                    getattr(instance, method)()
                    print(f"  PASS  {suite.__name__}.{method}")
                    passed += 1
                except Exception as exc:
                    print(f"  FAIL  {suite.__name__}.{method}: {exc}")
                    import traceback
                    traceback.print_exc()
                    failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
