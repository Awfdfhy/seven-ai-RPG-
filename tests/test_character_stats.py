"""
RPG-10-13: Character Stats System Tests
Run with: python -m pytest tests/test_character_stats.py -v
or:       python tests/test_character_stats.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from character_stats import (
    BASE_STATS,
    CharacterStatsState,
    DerivedStatRule,
    StatDefinition,
    StatsManager,
    StatsSystem,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_system() -> StatsSystem:
    return StatsSystem(
        stat_definitions=[
            StatDefinition(id=s, name=s.title(), abbreviation=s[:3].upper())
            for s in BASE_STATS
        ],
        derived_rules=[
            DerivedStatRule(id="max_hp", name="Maximum HP", formula="vitality * 10 + strength * 2"),
            DerivedStatRule(id="max_mp", name="Maximum MP", formula="intelligence * 8"),
            DerivedStatRule(
                id="max_stamina",
                name="Maximum Stamina",
                formula="vitality * 5 + dexterity * 3",
            ),
            DerivedStatRule(
                id="physical_power",
                name="Physical Power",
                formula="strength * 2",
            ),
            DerivedStatRule(
                id="magic_power",
                name="Magic Power",
                formula="intelligence * 2",
            ),
            DerivedStatRule(
                id="physical_defense",
                name="Physical Defense",
                formula="vitality * 1.5 + strength * 0.5",
            ),
            DerivedStatRule(
                id="magic_defense",
                name="Magic Defense",
                formula="intelligence * 1 + vitality * 1",
            ),
            DerivedStatRule(
                id="accuracy",
                name="Accuracy",
                formula="dexterity * 2 + luck * 0.5",
            ),
            DerivedStatRule(
                id="critical_chance",
                name="Critical Chance",
                formula="dexterity * 0.3 + luck * 0.5",
            ),
            DerivedStatRule(
                id="carry_weight",
                name="Carry Weight",
                formula="strength * 5",
            ),
        ],
    )


def _manager() -> StatsManager:
    mgr = StatsManager(system=_default_system())
    return mgr


# ---------------------------------------------------------------------------
# Constants and definitions
# ---------------------------------------------------------------------------

class TestBaseStatsConstant:
    def test_contains_expected_stats(self):
        assert "strength" in BASE_STATS
        assert "dexterity" in BASE_STATS
        assert "intelligence" in BASE_STATS
        assert "vitality" in BASE_STATS
        assert "charisma" in BASE_STATS
        assert "luck" in BASE_STATS

    def test_count(self):
        assert len(BASE_STATS) == 6


class TestStatDefinition:
    def test_to_from_dict_roundtrip(self):
        data = {
            "id": "strength",
            "name": "Strength",
            "abbreviation": "STR",
            "description": "Physical power.",
            "min": 1,
            "max": 100,
            "default": 10,
        }
        sdef = StatDefinition.from_dict(data)
        assert sdef.id == "strength"
        assert sdef.name == "Strength"
        assert sdef.abbreviation == "STR"
        assert sdef.max == 100
        assert sdef.to_dict()["description"] == "Physical power."

    def test_defaults(self):
        sdef = StatDefinition(id="test_stat", name="Test Stat", abbreviation="TST")
        assert sdef.description == ""
        assert sdef.min == 1
        assert sdef.max == 100
        assert sdef.default == 10


class TestDerivedStatRule:
    def test_compute_max_hp(self):
        rule = DerivedStatRule(id="max_hp", name="Max HP", formula="vitality * 10 + strength * 2")
        assert rule.compute({"vitality": 10, "strength": 5}) == 110.0

    def test_compute_missing_stat_defaults_to_zero(self):
        rule = DerivedStatRule(id="test", name="Test", formula="dexterity * 2")
        assert rule.compute({}) == 0.0

    def test_compute_with_non_base_ignored(self):
        rule = DerivedStatRule(id="test", name="Test", formula="dexterity * 2")
        # non-base keys should not affect evaluation
        assert rule.compute({"dexterity": 5, "weird_key": 100}) == 10.0

    def test_to_from_dict_roundtrip(self):
        data = {
            "id": "max_mp",
            "name": "Maximum MP",
            "formula": "intelligence * 8",
            "description": "Mana pool.",
        }
        rule = DerivedStatRule.from_dict(data)
        assert rule.id == "max_mp"
        assert rule.compute({"intelligence": 12}) == 96.0
        assert rule.to_dict()["formula"] == "intelligence * 8"


# ---------------------------------------------------------------------------
# StatsSystem tests
# ---------------------------------------------------------------------------

class TestStatsSystem:
    def test_canonical_base_stats_always_present(self):
        system = StatsSystem()
        for sid in BASE_STATS:
            assert sid in system.stat_definitions

    def test_derived_compute(self):
        system = _default_system()
        result = system.compute_derived({
            "strength": 10,
            "dexterity": 12,
            "intelligence": 8,
            "vitality": 15,
            "charisma": 6,
            "luck": 4,
        })
        assert result["max_hp"] == 15 * 10 + 10 * 2
        assert result["max_mp"] == 8 * 8
        assert result["physical_power"] == 10 * 2

    def test_roundtrip_serialization(self):
        system = _default_system()
        data = system.to_dict()
        restored = StatsSystem.from_dict(data)
        assert restored.get_definition("strength") is not None
        assert restored.get_derived_rule("max_hp") is not None
        assert restored.compute_derived({"vitality": 10})["max_hp"] == 100.0


# ---------------------------------------------------------------------------
# CharacterStatsState tests
# ---------------------------------------------------------------------------

class TestCharacterStatsState:
    def test_defaults(self):
        state = CharacterStatsState(character_id="c1")
        assert state.base_stats == {}
        assert state.temp_modifiers == {}
        assert state.derived_stats == {}

    def test_effective_stats_no_modifiers(self):
        state = CharacterStatsState(character_id="c1", base_stats={"strength": 10, "vitality": 8})
        eff = state.effective_stats()
        assert eff["strength"] == 10
        assert eff["vitality"] == 8

    def test_effective_stats_with_modifiers(self):
        state = CharacterStatsState(
            character_id="c1",
            base_stats={"strength": 10},
            temp_modifiers={"strength": 5},
        )
        eff = state.effective_stats()
        assert eff["strength"] == 15

    def test_roundtrip(self):
        state = CharacterStatsState(
            character_id="c1",
            base_stats={"strength": 12, "vitality": 14},
            temp_modifiers={"strength": 3},
            derived_stats={"max_hp": 180.0},
        )
        restored = CharacterStatsState.from_dict(state.to_dict())
        assert restored.base_stats["strength"] == 12
        assert restored.temp_modifiers["strength"] == 3
        assert restored.derived_stats["max_hp"] == 180.0


# ---------------------------------------------------------------------------
# StatsManager tests
# ---------------------------------------------------------------------------

class TestStatsManager:
    def test_get_state_creates_default(self):
        mgr = _manager()
        state = mgr.get_state("new_char")
        assert state.character_id == "new_char"
        assert state.base_stats == {}

    def test_set_base_stats_success(self):
        mgr = _manager()
        result = mgr.set_base_stats("c1", {"strength": 15, "vitality": 12})
        assert result["success"] is True
        assert result["stats"]["strength"] == 15
        assert mgr.get_base_stats("c1")["strength"] == 15

    def test_set_base_stats_invalid_stat(self):
        mgr = _manager()
        result = mgr.set_base_stats("c1", {"invalid_stat": 5})
        assert result["success"] is False
        assert "Invalid stat" in result["reason"]

    def test_set_base_stats_clamps_max(self):
        mgr = _manager()
        result = mgr.set_base_stats("c1", {"strength": 999})
        assert result["success"] is True
        assert result["stats"]["strength"] == 100

    def test_set_base_stats_clamps_min(self):
        mgr = _manager()
        result = mgr.set_base_stats("c1", {"strength": -5})
        assert result["success"] is True
        assert result["stats"]["strength"] >= 1

    def test_allocate_stat_point_success(self):
        mgr = _manager()
        mgr.set_base_stats("c1", {"dexterity": 10})
        ok, reason = mgr.allocate_stat_point("c1", "dexterity", unspent_points=1)
        assert ok is True
        assert mgr.get_base_stats("c1")["dexterity"] == 11

    def test_allocate_stat_point_no_points(self):
        mgr = _manager()
        ok, reason = mgr.allocate_stat_point("c1", "strength", unspent_points=0)
        assert ok is False
        assert "No unspent" in reason

    def test_allocate_stat_point_invalid_stat(self):
        mgr = _manager()
        ok, reason = mgr.allocate_stat_point("c1", "invalid_stat", unspent_points=1)
        assert ok is False
        assert "Invalid stat" in reason

    def test_allocate_stat_point_at_max(self):
        mgr = _manager()
        mgr.set_base_stats("c1", {"strength": 100})
        ok, reason = mgr.allocate_stat_point("c1", "strength", unspent_points=1)
        assert ok is False
        assert "maximum" in reason

    def test_allocate_stat_point_recalculates_derived(self):
        mgr = _manager()
        mgr.set_base_stats("c1", {"vitality": 10, "strength": 10})
        before = mgr.get_derived("c1", "max_hp")
        mgr.allocate_stat_point("c1", "vitality", unspent_points=1)
        after = mgr.get_derived("c1", "max_hp")
        assert after - before == 10.0

    def test_add_temp_modifier(self):
        mgr = _manager()
        mgr.set_base_stats("c1", {"dexterity": 10})
        result = mgr.add_temp_modifier("c1", "dexterity", 5)
        assert result["success"] is True
        assert result["effective_stats"]["dexterity"] == 15

    def test_remove_temp_modifier(self):
        mgr = _manager()
        mgr.set_base_stats("c1", {"dexterity": 10})
        mgr.add_temp_modifier("c1", "dexterity", 5)
        result = mgr.remove_temp_modifier("c1", "dexterity", 3)
        assert result["success"] is True
        assert result["effective_stats"]["dexterity"] == 12

    def test_clear_temp_modifiers(self):
        mgr = _manager()
        mgr.set_base_stats("c1", {"strength": 10})
        mgr.add_temp_modifier("c1", "strength", 4)
        mgr.clear_temp_modifiers("c1")
        assert mgr.get_state("c1").temp_modifiers == {}

    def test_add_invalid_temp_modifier(self):
        mgr = _manager()
        result = mgr.add_temp_modifier("c1", "invalid_stat", 5)
        assert result["success"] is False
        assert "Invalid stat" in result["reason"]

    def test_derived_stats_populated(self):
        mgr = _manager()
        mgr.set_base_stats("c1", {
            "strength": 10,
            "dexterity": 12,
            "intelligence": 8,
            "vitality": 15,
            "charisma": 6,
            "luck": 4,
        })
        derived = mgr.get_derived_stats("c1")
        assert derived["max_hp"] == 170.0
        assert derived["max_mp"] == 64.0
        assert derived["carry_weight"] == 50.0

    def test_stats_summary(self):
        mgr = _manager()
        mgr.set_base_stats("c1", {"strength": 14, "vitality": 12})
        summary = mgr.get_character_stats_summary("c1")
        assert summary["character_id"] == "c1"
        assert summary["base_stats"]["strength"] == 14
        assert "stat_details" in summary
        assert "derived_details" in summary
        # derived should have entries
        assert len(summary["derived_details"]) > 0

    def test_serialization_roundtrip(self):
        mgr = _manager()
        mgr.set_base_stats("c1", {"strength": 16, "dexterity": 12})
        mgr.add_temp_modifier("c1", "dexterity", 4)
        data = mgr.to_dict()
        restored = StatsManager.from_dict(data)
        assert restored.get_base_stats("c1")["strength"] == 16
        assert restored.get_state("c1").temp_modifiers["dexterity"] == 4
        assert restored.get_derived_stats("c1")["max_hp"] > 0

    def test_load_from_json(self):
        mgr = StatsManager()
        mgr.load_from_json()
        # After loading, the system should have canonical stats + derived rules
        assert "strength" in mgr.system.stat_definitions
        assert "max_hp" in mgr.system.derived_rules
        assert mgr.system.get_definition("strength").name == "Strength"

    def test_character_sheet_integration(self):
        from character_sheet import CharacterSheet

        sheet = CharacterSheet()
        result = sheet.render_sheet("hero", "Aldric")
        assert result["character_id"] == "hero"
        assert "stats_summary" in result
        assert result["stats_summary"]["base_stats"] is not None


if __name__ == "__main__":
    suites = [
        TestBaseStatsConstant,
        TestStatDefinition,
        TestDerivedStatRule,
        TestStatsSystem,
        TestCharacterStatsState,
        TestStatsManager,
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
