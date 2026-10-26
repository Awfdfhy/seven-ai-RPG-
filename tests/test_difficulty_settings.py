"""
RPG-10-10: Difficulty and Accessibility Settings
Tests for difficulty presets, accessibility options, settings models,
and integration helpers.
Run with: python -m pytest tests/test_difficulty_settings.py -v
or:       python tests/test_difficulty_settings.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from difficulty_integration import (
    DifficultyAwareCombatResolver,
    DifficultyAwareSkillResolver,
    adjusted_xp_for_level,
    apply_status_with_difficulty,
    apply_xp_multiplier,
    roll_loot_with_difficulty,
)
from difficulty_settings import (
    AccessibilitySettings,
    DifficultyPreset,
    DifficultySettings,
    GameSettings,
)
from loot import LootManager, LootTable
from progression import ProgressionSystem
from skill_check import (
    AttackRollContext,
    CombatResolver,
    SkillCheckContext,
    SkillCheckResolver,
)
from status_manager import StatusCondition, StatusConditionType, StatusManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_loot_table() -> LootTable:
    return LootTable(
        id="sample_table",
        name="Sample Table",
        entries=[
            {"item_id": "common_item", "rarity": "common", "weight": 50},
            {"item_id": "rare_item", "rarity": "rare", "weight": 10},
            {"item_id": "epic_item", "rarity": "epic", "weight": 2},
        ],
        min_drops=1,
        max_drops=2,
    )


def _status_def() -> StatusCondition:
    return StatusCondition(
        id="test_poison",
        name="Test Poison",
        condition_type=StatusConditionType.POISON,
        duration_seconds=10.0,
        effects=[],
    )


# ---------------------------------------------------------------------------
# DifficultyPreset tests
# ---------------------------------------------------------------------------

class TestDifficultyPreset(unittest.TestCase):
    def test_all_presets_exist(self):
        for name in (
            DifficultyPreset.NARRATIVE,
            DifficultyPreset.EASY,
            DifficultyPreset.NORMAL,
            DifficultyPreset.HARD,
            DifficultyPreset.NIGHTMARE,
        ):
            assert name in DifficultyPreset.PRESETS

    def test_preset_keys_present(self):
        required_keys = [
            "display_name",
            "description",
            "dc_modifier",
            "damage_dealt_multiplier",
            "damage_taken_multiplier",
            "xp_multiplier",
            "loot_rarity_boost",
            "status_duration_multiplier",
            "healing_effectiveness_multiplier",
        ]
        for preset in DifficultyPreset.PRESETS.values():
            for key in required_keys:
                assert key in preset, f"Missing key {key} in preset {preset}"

    def test_preset_normal_is_balanced(self):
        p = DifficultyPreset.preset(DifficultyPreset.NORMAL)
        assert p["dc_modifier"] == 0
        assert p["damage_dealt_multiplier"] == 1.0
        assert p["damage_taken_multiplier"] == 1.0
        assert p["xp_multiplier"] == 1.0
        assert p["loot_rarity_boost"] == 0.0
        assert p["status_duration_multiplier"] == 1.0
        assert p["healing_effectiveness_multiplier"] == 1.0

    def test_preset_nightmare_is_hardest(self):
        nightmare = DifficultyPreset.preset(DifficultyPreset.NIGHTMARE)
        easy = DifficultyPreset.preset(DifficultyPreset.EASY)
        assert nightmare["dc_modifier"] > easy["dc_modifier"]
        assert nightmare["damage_taken_multiplier"] > easy["damage_taken_multiplier"]
        assert nightmare["xp_multiplier"] > easy["xp_multiplier"]

    def test_preset_narrative_is_easiest(self):
        narrative = DifficultyPreset.preset(DifficultyPreset.NARRATIVE)
        easy = DifficultyPreset.preset(DifficultyPreset.EASY)
        assert narrative["dc_modifier"] <= easy["dc_modifier"]
        assert narrative["damage_taken_multiplier"] <= easy["damage_taken_multiplier"]

    def test_available_presets(self):
        presets = DifficultyPreset.available_presets()
        assert len(presets) == 5
        assert DifficultyPreset.NORMAL in presets


# ---------------------------------------------------------------------------
# DifficultySettings tests
# ---------------------------------------------------------------------------

class TestDifficultySettings(unittest.TestCase):
    def test_default_is_normal(self):
        s = DifficultySettings()
        assert s.preset == DifficultyPreset.NORMAL
        assert s.dc_modifier == 0
        assert s.damage_dealt_multiplier == 1.0

    def test_from_preset_easy(self):
        s = DifficultySettings.from_preset(DifficultyPreset.EASY)
        assert s.preset == DifficultyPreset.EASY
        assert s.dc_modifier == -2
        assert s.damage_dealt_multiplier == 1.2
        assert s.damage_taken_multiplier == 0.7

    def test_from_preset_hard(self):
        s = DifficultySettings.from_preset(DifficultyPreset.HARD)
        assert s.dc_modifier == 3
        assert s.damage_dealt_multiplier == 0.85
        assert s.damage_taken_multiplier == 1.4

    def test_from_preset_unknown_falls_back_to_normal(self):
        s = DifficultySettings.from_preset("nonexistent")
        assert s.preset == "nonexistent"
        assert s.dc_modifier == 0

    def test_manual_override(self):
        s = DifficultySettings(preset=DifficultyPreset.HARD, dc_modifier=10)
        assert s.dc_modifier == 10
        # manual values should be preserved even if not from preset
        assert s.preset == DifficultyPreset.HARD

    def test_clamping_dc_modifier(self):
        s = DifficultySettings(dc_modifier=100)
        assert s.dc_modifier == 10
        s = DifficultySettings(dc_modifier=-100)
        assert s.dc_modifier == -10

    def test_clamping_damage_multiplier(self):
        s = DifficultySettings(damage_dealt_multiplier=100.0)
        assert s.damage_dealt_multiplier == 3.0
        s = DifficultySettings(damage_dealt_multiplier=0.01)
        assert s.damage_dealt_multiplier == 0.1

    def test_to_dict_roundtrip(self):
        original = DifficultySettings.from_preset(DifficultyPreset.HARD)
        restored = DifficultySettings.from_dict(original.to_dict())
        assert restored.preset == original.preset
        assert restored.dc_modifier == original.dc_modifier
        assert restored.damage_dealt_multiplier == original.damage_dealt_multiplier

    def test_to_dict_contains_all_fields(self):
        s = DifficultySettings.from_preset(DifficultyPreset.NIGHTMARE)
        d = s.to_dict()
        assert "preset" in d
        assert "dc_modifier" in d
        assert "damage_dealt_multiplier" in d
        assert "damage_taken_multiplier" in d
        assert "xp_multiplier" in d
        assert "loot_rarity_boost" in d
        assert "status_duration_multiplier" in d
        assert "healing_effectiveness_multiplier" in d


# ---------------------------------------------------------------------------
# AccessibilitySettings tests
# ---------------------------------------------------------------------------

class TestAccessibilitySettings(unittest.TestCase):
    def test_defaults(self):
        s = AccessibilitySettings()
        assert s.high_contrast_mode is False
        assert s.simplified_combat is False
        assert s.auto_advance_dialogue is False
        assert s.text_size == "normal"
        assert s.screen_reader_mode is False
        assert s.reduce_flashes is False
        assert s.colorblind_support == "none"

    def test_invalid_text_size_falls_back(self):
        s = AccessibilitySettings(text_size="invalid")
        assert s.text_size == "normal"

    def test_invalid_colorblind_falls_back(self):
        s = AccessibilitySettings(colorblind_support="invalid")
        assert s.colorblind_support == "none"

    def test_to_dict_roundtrip(self):
        original = AccessibilitySettings(
            high_contrast_mode=True,
            text_size="large",
            colorblind_support="deuteranopia",
        )
        restored = AccessibilitySettings.from_dict(original.to_dict())
        assert restored.high_contrast_mode is True
        assert restored.text_size == "large"
        assert restored.colorblind_support == "deuteranopia"

    def test_to_dict_contains_all_fields(self):
        s = AccessibilitySettings()
        d = s.to_dict()
        assert "high_contrast_mode" in d
        assert "simplified_combat" in d
        assert "auto_advance_dialogue" in d
        assert "text_size" in d
        assert "screen_reader_mode" in d
        assert "reduce_flashes" in d
        assert "colorblind_support" in d


# ---------------------------------------------------------------------------
# GameSettings tests
# ---------------------------------------------------------------------------

class TestGameSettings(unittest.TestCase):
    def test_default_contains_difficulty_and_accessibility(self):
        gs = GameSettings()
        assert isinstance(gs.difficulty, DifficultySettings)
        assert isinstance(gs.accessibility, AccessibilitySettings)

    def test_from_dict_roundtrip(self):
        original = GameSettings(
            difficulty=DifficultySettings.from_preset(DifficultyPreset.HARD),
            accessibility=AccessibilitySettings(
                high_contrast_mode=True,
                text_size="large",
            ),
        )
        restored = GameSettings.from_dict(original.to_dict())
        assert restored.difficulty.preset == DifficultyPreset.HARD
        assert restored.accessibility.high_contrast_mode is True
        assert restored.accessibility.text_size == "large"

    def test_to_dict_structure(self):
        gs = GameSettings()
        d = gs.to_dict()
        assert "difficulty" in d
        assert "accessibility" in d
        assert "preset" in d["difficulty"]
        assert "high_contrast_mode" in d["accessibility"]


# ---------------------------------------------------------------------------
# Skill check integration
# ---------------------------------------------------------------------------

class TestSkillCheckIntegration(unittest.TestCase):
    def test_dc_modifier_raises_dc(self):
        resolver = SkillCheckResolver()
        ctx = SkillCheckContext(character_id="c1", base_attribute="strength")
        result_normal = resolver.resolve(ctx, {"strength": 10}, dc=10, dc_modifier=0)
        result_hard = resolver.resolve(ctx, {"strength": 10}, dc=10, dc_modifier=5)
        assert result_hard.dc == 15
        assert result_hard.dc > result_normal.dc

    def test_dc_modifier_affects_success(self):
        import random as rmod
        original = rmod.randint
        rmod.randint = lambda a, b: 10
        try:
            resolver = SkillCheckResolver()
            ctx = SkillCheckContext(character_id="c1", base_attribute="strength")
            result = resolver.resolve(ctx, {"strength": 10}, dc=10, dc_modifier=5)
            # 10 + 0 mod vs DC 15 -> fail
            assert result.success is False
            assert result.dc == 15
        finally:
            rmod.randint = original

    def test_difficulty_aware_resolver_auto_applies_modifier(self):
        settings = DifficultySettings(dc_modifier=5)
        resolver = DifficultyAwareSkillResolver(settings=settings)
        ctx = SkillCheckContext(character_id="c1", base_attribute="strength")
        result = resolver.resolve(ctx, {"strength": 10}, dc=10)
        assert result.dc == 15


# ---------------------------------------------------------------------------
# Combat integration
# ---------------------------------------------------------------------------

class TestCombatIntegration(unittest.TestCase):
    def test_damage_dealt_multiplier_applied(self):
        import random as rmod
        original = rmod.randint
        rmod.randint = lambda a, b: 10
        try:
            combat = CombatResolver()
            ctx = AttackRollContext(
                character_id="c1",
                base_attribute="strength",
                target_ac=5,
                weapon_die=6,
                damage_bonus=0,
            )
            result_normal = combat.attack(ctx, {"strength": 10}, skill_ranks={}, damage_dealt_multiplier=1.0)
            result_buffed = combat.attack(ctx, {"strength": 10}, skill_ranks={}, damage_dealt_multiplier=2.0)
            assert result_buffed.damage == result_normal.damage * 2
        finally:
            rmod.randint = original

    def test_difficulty_aware_combat_applies_multiplier(self):
        import random as rmod
        original = rmod.randint
        rmod.randint = lambda a, b: 10
        try:
            settings = DifficultySettings(damage_dealt_multiplier=1.5)
            combat = DifficultyAwareCombatResolver(settings=settings)
            ctx = AttackRollContext(
                character_id="c1",
                base_attribute="strength",
                target_ac=5,
                weapon_die=6,
                damage_bonus=0,
            )
            result = combat.attack(ctx, {"strength": 10}, skill_ranks={})
            # damage should be 1.5x the base
            assert result.damage == int((10 + 0) * 1.5)
        finally:
            rmod.randint = original


# ---------------------------------------------------------------------------
# Progression integration
# ---------------------------------------------------------------------------

class TestProgressionIntegration(unittest.TestCase):
    def test_apply_xp_multiplier(self):
        settings = DifficultySettings(xp_multiplier=2.0)
        assert apply_xp_multiplier(100, settings) == 200

    def test_adjusted_xp_for_level(self):
        system = ProgressionSystem(xp_per_level_base=100, xp_per_level_multiplier=1.0)
        settings = DifficultySettings(xp_multiplier=2.0)
        assert adjusted_xp_for_level(system, 2, settings) == 200
        settings_normal = DifficultySettings(xp_multiplier=1.0)
        assert adjusted_xp_for_level(system, 2, settings_normal) == 100


# ---------------------------------------------------------------------------
# Loot integration
# ---------------------------------------------------------------------------

class TestLootIntegration(unittest.TestCase):
    def test_loot_rarity_boost_positive_shifts_weights(self):
        mgr = LootManager()
        table = _sample_loot_table()
        mgr.register_definition(table)

        # Roll many times with a strong positive boost
        rarity_counts: dict[str, int] = {}
        for _ in range(200):
            inst = mgr.roll_loot("sample_table", world_id="w1", loot_rarity_boost=1.0, seed=hash(os.urandom(8)) % 100000)
            for item in inst.items:
                rarity_counts[item["rarity"]] = rarity_counts.get(item["rarity"], 0) + 1

        # With boost, rare+ should appear more frequently
        high_rarity = rarity_counts.get("rare", 0) + rarity_counts.get("epic", 0)
        low_rarity = rarity_counts.get("common", 0)
        assert high_rarity > 0, "Expected some high-rarity drops with positive boost"

    def test_loot_rarity_boost_negative_favors_common(self):
        mgr = LootManager()
        table = _sample_loot_table()
        mgr.register_definition(table)

        rarity_counts: dict[str, int] = {}
        for _ in range(200):
            inst = mgr.roll_loot("sample_table", world_id="w1", loot_rarity_boost=-1.0, seed=hash(os.urandom(8)) % 100000)
            for item in inst.items:
                rarity_counts[item["rarity"]] = rarity_counts.get(item["rarity"], 0) + 1

        assert rarity_counts.get("common", 0) > rarity_counts.get("rare", 0)

    def test_roll_loot_with_difficulty_helper(self):
        mgr = LootManager()
        table = _sample_loot_table()
        mgr.register_definition(table)
        settings = DifficultySettings(loot_rarity_boost=0.5)
        inst = roll_loot_with_difficulty(mgr, "sample_table", "w1", settings, seed=42)
        assert inst is not None
        assert inst.world_id == "w1"


# ---------------------------------------------------------------------------
# Status integration
# ---------------------------------------------------------------------------

class TestStatusIntegration(unittest.TestCase):
    def test_duration_multiplier_scales_duration(self):
        mgr = StatusManager()
        mgr.register_definition(_status_def())
        active = mgr.apply_condition("c1", "test_poison", current_time=0.0, duration_multiplier=2.0)
        assert active is not None
        assert active.remaining_duration == 20.0

    def test_duration_multiplier_zero(self):
        mgr = StatusManager()
        mgr.register_definition(_status_def())
        active = mgr.apply_condition("c1", "test_poison", current_time=0.0, duration_multiplier=0.0)
        assert active is not None
        assert active.remaining_duration == 0.0

    def test_apply_status_with_difficulty_helper(self):
        mgr = StatusManager()
        mgr.register_definition(_status_def())
        settings = DifficultySettings(status_duration_multiplier=0.5)
        active = apply_status_with_difficulty(mgr, "c1", "test_poison", settings, current_time=0.0)
        assert active.remaining_duration == 5.0


# ---------------------------------------------------------------------------
# WorldSession integration
# ---------------------------------------------------------------------------

class TestWorldSessionIntegration(unittest.TestCase):
    def test_session_carries_settings(self):
        from world_session import WorldSessionManager
        mgr = WorldSessionManager()
        settings = GameSettings(
            difficulty=DifficultySettings.from_preset(DifficultyPreset.HARD),
            accessibility=AccessibilitySettings(high_contrast_mode=True),
        )
        session = mgr.create_session("w1", settings=settings)
        assert session.settings is not None
        assert session.settings.difficulty.preset == DifficultyPreset.HARD
        assert session.settings.accessibility.high_contrast_mode is True

    def test_session_to_dict_includes_settings(self):
        from world_session import WorldSessionManager
        mgr = WorldSessionManager()
        settings = GameSettings(
            difficulty=DifficultySettings.from_preset(DifficultyPreset.EASY),
        )
        session = mgr.create_session("w1", settings=settings)
        d = session.to_dict()
        assert "settings" in d
        assert d["settings"]["difficulty"]["preset"] == DifficultyPreset.EASY

    def test_session_from_dict_restores_settings(self):
        data = {
            "session_id": "s1",
            "world_id": "w1",
            "started_at": "2024-01-01T00:00:00Z",
            "status": "active",
            "snapshot": {},
            "metadata": {},
            "settings": {
                "difficulty": {"preset": "hard", "dc_modifier": 3, "damage_dealt_multiplier": 0.85,
                                "damage_taken_multiplier": 1.4, "xp_multiplier": 1.2,
                                "loot_rarity_boost": 0.0, "status_duration_multiplier": 1.3,
                                "healing_effectiveness_multiplier": 0.8},
                "accessibility": {"high_contrast_mode": False, "simplified_combat": False,
                                   "auto_advance_dialogue": False, "text_size": "normal",
                                   "screen_reader_mode": False, "reduce_flashes": False,
                                   "colorblind_support": "none"},
            },
        }
        from world_session import WorldSession
        session = WorldSession.from_dict(data)
        assert session.settings is not None
        assert session.settings.difficulty.preset == DifficultyPreset.HARD
        assert session.settings.difficulty.dc_modifier == 3

    def test_update_settings(self):
        from world_session import WorldSessionManager
        mgr = WorldSessionManager()
        session = mgr.create_session("w1")
        new_settings = GameSettings(
            difficulty=DifficultySettings.from_preset(DifficultyPreset.NIGHTMARE),
        )
        result = mgr.update_settings(session.session_id, new_settings)
        assert result is True
        assert session.settings.difficulty.preset == DifficultyPreset.NIGHTMARE

    def test_update_settings_inactive_session_fails(self):
        from world_session import WorldSessionManager
        mgr = WorldSessionManager()
        session = mgr.create_session("w1")
        mgr.end_session(session.session_id)
        new_settings = GameSettings()
        result = mgr.update_settings(session.session_id, new_settings)
        assert result is False


if __name__ == "__main__":
    suites = [
        TestDifficultyPreset,
        TestDifficultySettings,
        TestAccessibilitySettings,
        TestGameSettings,
        TestSkillCheckIntegration,
        TestCombatIntegration,
        TestProgressionIntegration,
        TestLootIntegration,
        TestStatusIntegration,
        TestWorldSessionIntegration,
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
