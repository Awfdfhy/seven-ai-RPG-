"""
Tests for RPG-XX Character Progression System.
Run with: python -m pytest tests/test_progression.py -v
or:       python tests/test_progression.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from progression import (
    LevelThreshold,
    LevelUnlock,
    ProgressionSystem,
    StatGrowth,
)
from progression_manager import ProgressionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_system() -> ProgressionSystem:
    return ProgressionSystem(
        xp_per_level_base=100,
        xp_per_level_multiplier=1.5,
        skill_points_per_level=1,
        ability_points_per_level=1,
        stat_points_per_level=1,
        stat_growth=[
            StatGrowth(attribute="strength", amount_per_level=2),
            StatGrowth(attribute="dexterity", amount_per_level=2),
            StatGrowth(attribute="intelligence", amount_per_level=2),
        ],
    )


# ---------------------------------------------------------------------------
# ProgressionSystem tests
# ---------------------------------------------------------------------------

class TestProgressionSystem:
    def test_xp_for_level_default_curve(self):
        system = _default_system()
        # level 2: 100 * 1.5^1 = 150
        assert system.xp_for_level(2) == 150
        # level 3: 100 * 1.5^2 = 225
        assert system.xp_for_level(3) == 225

    def test_total_xp_for_level(self):
        system = _default_system()
        # To reach level 3: 150 + 225 = 375
        assert system.total_xp_for_level(3) == 375

    def test_explicit_threshold_overrides_curve(self):
        system = _default_system()
        system.add_threshold(LevelThreshold(level=2, xp_required=999))
        assert system.xp_for_level(2) == 999

    def test_stat_gain_for(self):
        system = _default_system()
        assert system.stat_gain_for("strength") == 2
        assert system.stat_gain_for("missing") == 0

    def test_level_unlocks(self):
        system = _default_system()
        system.add_level_unlock(LevelUnlock(level=5, node_id="fire.fireball", tree_id="fire_magic", auto_unlock=True))
        unlocks = system.level_unlocks.get(5, [])
        assert len(unlocks) == 1
        assert unlocks[0].node_id == "fire.fireball"

    def test_round_trip_serialization(self):
        system = _default_system()
        system.add_threshold(LevelThreshold(level=2, xp_required=999))
        system.add_stat_growth(StatGrowth(attribute="vitality", amount_per_level=3))
        system.add_level_unlock(LevelUnlock(level=3, node_id="x.y", tree_id="t", auto_unlock=False))

        data = system.to_dict()
        restored = ProgressionSystem.from_dict(data)

        assert restored.xp_for_level(2) == 999
        assert restored.stat_gain_for("vitality") == 3
        assert restored.xp_per_level_base == 100
        assert restored.xp_per_level_multiplier == 1.5


# ---------------------------------------------------------------------------
# ProgressionManager tests
# ---------------------------------------------------------------------------

class TestProgressionManager:
    def test_initial_state(self):
        mgr = ProgressionManager(_default_system())
        state = mgr.get_state("hero")
        assert state.level == 1
        assert state.experience == 0
        assert state.unspent_skill_points == 0

    def test_add_experience_no_level_up(self):
        mgr = ProgressionManager(_default_system())
        report = mgr.add_experience("hero", 50)
        assert report["level_ups"] == []
        state = mgr.get_state("hero")
        assert state.experience == 50
        assert state.level == 1

    def test_add_experience_single_level_up(self):
        mgr = ProgressionManager(_default_system())
        report = mgr.add_experience("hero", 150)
        assert len(report["level_ups"]) == 1
        assert report["level_ups"][0]["new_level"] == 2
        state = mgr.get_state("hero")
        assert state.level == 2
        assert state.unspent_skill_points == 1
        assert state.unspent_ability_points == 1
        assert state.unspent_stat_points == 1

    def test_add_experience_multiple_level_ups(self):
        mgr = ProgressionManager(_default_system())
        # 150 (to lvl 2) + 225 (to lvl 3) = 375
        report = mgr.add_experience("hero", 375)
        assert len(report["level_ups"]) == 2
        assert report["level_ups"][0]["new_level"] == 2
        assert report["level_ups"][1]["new_level"] == 3
        state = mgr.get_state("hero")
        assert state.level == 3
        assert state.unspent_skill_points == 2

    def test_apply_stat_growth(self):
        mgr = ProgressionManager(_default_system())
        mgr.add_experience("hero", 375)  # reach level 3
        gains = mgr.apply_stat_growth("hero")
        assert gains["strength"] == 6  # 2 per level * 3 levels
        assert gains["dexterity"] == 6

    def test_allocate_stat_point(self):
        mgr = ProgressionManager(_default_system())
        mgr.add_experience("hero", 150)  # level 2, 1 stat point
        ok, _ = mgr.allocate_stat_point("hero", "strength")
        assert ok is True
        assert mgr.get_state("hero").unspent_stat_points == 0

    def test_allocate_stat_point_no_points(self):
        mgr = ProgressionManager(_default_system())
        ok, reason = mgr.allocate_stat_point("hero", "strength")
        assert ok is False
        assert "No unspent stat points" in reason

    def test_allocate_stat_point_invalid_attribute(self):
        mgr = ProgressionManager(_default_system())
        mgr.add_experience("hero", 150)
        ok, reason = mgr.allocate_stat_point("hero", "luck")
        assert ok is False
        assert "does not allow point allocation" in reason

    def test_grant_and_spend_skill_points(self):
        mgr = ProgressionManager(_default_system())
        mgr.add_experience("hero", 150)
        mgr.grant_skill_points("hero", 5)
        assert mgr.get_state("hero").unspent_skill_points == 6  # 1 from level up + 5

    def test_get_level_unlocks(self):
        mgr = ProgressionManager(_default_system())
        mgr.system.add_level_unlock(
            LevelUnlock(level=2, node_id="a.b", tree_id="t1", auto_unlock=True)
        )
        mgr.add_experience("hero", 150)  # level 2
        unlocks = mgr.get_level_unlocks("hero")
        assert len(unlocks) == 1
        assert unlocks[0]["node_id"] == "a.b"

    def test_pending_auto_unlocks(self):
        mgr = ProgressionManager(_default_system())
        mgr.system.add_level_unlock(
            LevelUnlock(level=2, node_id="a.b", tree_id="t1", auto_unlock=True)
        )
        mgr.system.add_level_unlock(
            LevelUnlock(level=2, node_id="c.d", tree_id="t2", auto_unlock=False)
        )
        mgr.add_experience("hero", 150)
        pending = mgr.get_pending_auto_unlocks("hero")
        assert len(pending) == 1
        assert pending[0].node_id == "a.b"

    def test_sync_with_skill_manager(self):
        mgr = ProgressionManager(_default_system())
        mgr.add_experience("hero", 150)  # 1 skill point

        class FakeSkillManager:
            def __init__(self):
                self.granted = 0
            def grant_points(self, cid, pts):
                self.granted += pts
            def get_tree(self, tid):
                return None
            def unlock_node(self, cid, tid, nid):
                return {"success": True}

        fake = FakeSkillManager()
        mgr.sync_with_skill_manager("hero", fake)
        assert fake.granted == 1
        assert mgr.get_state("hero").unspent_skill_points == 0

    def test_sync_with_ability_manager(self):
        mgr = ProgressionManager(_default_system())
        mgr.add_experience("hero", 150)  # 1 ability point

        class FakeAbilityManager:
            def __init__(self):
                self.granted = 0
            def grant_ability_points(self, cid, pts):
                self.granted += pts
            def get_tree(self, tid):
                return None
            def unlock_ability_node(self, cid, tid, nid):
                return {"success": True}

        fake = FakeAbilityManager()
        mgr.sync_with_ability_manager("hero", fake)
        assert fake.granted == 1
        assert mgr.get_state("hero").unspent_ability_points == 0

    def test_character_summary(self):
        mgr = ProgressionManager(_default_system())
        mgr.add_experience("hero", 50)
        summary = mgr.get_character_summary("hero")
        assert summary["level"] == 1
        assert summary["experience"] == 50
        assert summary["experience_to_next_level"] == 150

        mgr.add_experience("hero", 100)  # total 150 -> exactly enough for level 2
        summary = mgr.get_character_summary("hero")
        assert summary["level"] == 2
        assert summary["experience"] == 0
        assert summary["experience_to_next_level"] == 225


if __name__ == "__main__":
    suites = [
        TestProgressionSystem,
        TestProgressionManager,
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
