"""
Tests for RPG-12-07 Endgame Systems.

Post-game content (endgame.py) and New Game Plus (new_game_plus.py).
Run with: python -m pytest tests/test_endgame.py -v
or:       python tests/test_endgame.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endgame import (
    EndgameContentDefinition,
    EndgameContentState,
    EndgameManager,
)
from new_game_plus import (
    NGPlusManager,
    NGPlusProfile,
    NGPlusRun,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_endgame_definitions() -> list[EndgameContentDefinition]:
    return [
        EndgameContentDefinition(
            id="void_raid",
            name="Void Raid",
            description="A high-stakes raid in the void dimension.",
            category="raid",
            difficulty="hard",
            min_level=50,
            prerequisites=[],
            rewards=[{"type": "legendary_item", "item_id": "void_blade"}],
            world_effects=[{"type": "unlock_region", "region": "void_temple"}],
        ),
        EndgameContentDefinition(
            id="shadow_challenge",
            name="Shadow Trial",
            description="A solo challenge in the shadow realm.",
            category="challenge",
            difficulty="medium",
            min_level=30,
            prerequisites=["void_raid"],
            rewards=[{"type": "currency", "amount": 500}],
            world_effects=[],
        ),
        EndgameContentDefinition(
            id="eternal_bounties",
            name="Eternal Bounties",
            description="Endless bounty board for veteran adventurers.",
            category="bounties",
            difficulty="easy",
            min_level=10,
            prerequisites=[],
            rewards=[{"type": "currency", "amount": 100}],
            world_effects=[],
        ),
    ]


def _make_endgame_manager() -> EndgameManager:
    mgr = EndgameManager(data_directory="")
    mgr.load_definitions(_sample_endgame_definitions())
    return mgr


# ---------------------------------------------------------------------------
# EndgameContentDefinition tests
# ---------------------------------------------------------------------------

class TestEndgameContentDefinition(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "id": "test",
            "name": "Test Content",
            "description": "desc",
            "category": "raid",
            "difficulty": "hard",
            "min_level": 40,
            "prerequisites": ["a", "b"],
            "rewards": [{"type": "gold"}],
            "world_effects": [{"type": "unlock"}],
            "metadata": {"key": "val"},
        }
        d = EndgameContentDefinition.from_dict(data)
        assert d.id == "test"
        assert d.category == "raid"
        assert d.difficulty == "hard"
        assert d.min_level == 40
        assert d.prerequisites == ["a", "b"]
        assert len(d.rewards) == 1
        assert len(d.world_effects) == 1

    def test_to_dict(self):
        d = EndgameContentDefinition(
            id="test",
            name="Test",
            description="desc",
            category="challenge",
            difficulty="nightmare",
            min_level=60,
            prerequisites=["p"],
            rewards=[{"type": "gold"}],
            world_effects=[{"type": "unlock"}],
            metadata={"m": 1},
        )
        data = d.to_dict()
        assert data["id"] == "test"
        assert data["category"] == "challenge"
        assert data["difficulty"] == "nightmare"
        assert data["min_level"] == 60
        assert len(data["rewards"]) == 1
        assert len(data["world_effects"]) == 1

    def test_roundtrip(self):
        original = EndgameContentDefinition(
            id="rt",
            name="Roundtrip",
            description="desc",
            category="special_quest",
            min_level=25,
            rewards=[{"type": "gold", "amount": 100}],
            world_effects=[{"type": "buff", "stat": "hp", "value": 50}],
        )
        restored = EndgameContentDefinition.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.category == original.category
        assert restored.min_level == original.min_level
        assert restored.rewards == original.rewards
        assert restored.world_effects == original.world_effects


# ---------------------------------------------------------------------------
# EndgameContentState tests
# ---------------------------------------------------------------------------

class TestEndgameContentState(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "character_id": "c1",
            "content_id": "void_raid",
            "status": "completed",
            "best_score": 1500,
            "attempts": 5,
            "completed_at": "2024-01-01T00:00:00+00:00",
            "metadata": {"difficulty": "hard"},
        }
        s = EndgameContentState.from_dict(data)
        assert s.character_id == "c1"
        assert s.content_id == "void_raid"
        assert s.status == "completed"
        assert s.best_score == 1500
        assert s.attempts == 5

    def test_to_dict(self):
        s = EndgameContentState(
            character_id="c1",
            content_id="shadow_challenge",
            status="in_progress",
            best_score=800,
            attempts=3,
            metadata={"mod": "ng+2"},
        )
        data = s.to_dict()
        assert data["character_id"] == "c1"
        assert data["content_id"] == "shadow_challenge"
        assert data["status"] == "in_progress"
        assert data["best_score"] == 800
        assert data["attempts"] == 3

    def test_roundtrip(self):
        original = EndgameContentState(
            character_id="c1",
            content_id="void_raid",
            status="completed",
            best_score=2000,
            attempts=10,
            completed_at="2024-06-01T00:00:00+00:00",
            metadata={"ng_cycle": 3},
        )
        restored = EndgameContentState.from_dict(original.to_dict())
        assert restored.character_id == original.character_id
        assert restored.content_id == original.content_id
        assert restored.status == original.status
        assert restored.best_score == original.best_score
        assert restored.attempts == original.attempts


# ---------------------------------------------------------------------------
# EndgameManager tests
# ---------------------------------------------------------------------------

class TestEndgameManager(unittest.TestCase):
    def test_auto_load_from_data_directory(self):
        mgr = EndgameManager()
        # data/endgame_content.json may or may not exist; just verify no crash
        assert isinstance(mgr.list_definitions(), list)

    def test_register_and_list_definitions(self):
        mgr = _make_endgame_manager()
        defs = mgr.list_definitions()
        assert len(defs) == 3
        ids = [d["id"] for d in defs]
        assert "void_raid" in ids
        assert "shadow_challenge" in ids
        assert "eternal_bounties" in ids

    def test_start_content_creates_state(self):
        mgr = _make_endgame_manager()
        state = mgr.start_content("void_raid", character_id="hero")
        assert state is not None
        assert state.character_id == "hero"
        assert state.content_id == "void_raid"
        assert state.status == "available"
        assert state.attempts == 0

    def test_start_content_already_started(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        state = mgr.start_content("void_raid", character_id="hero")
        assert state is not None
        assert state.status == "available"

    def test_start_unknown_returns_none(self):
        mgr = _make_endgame_manager()
        assert mgr.start_content("nonexistent", character_id="hero") is None

    def test_begin_attempt(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        state = mgr.begin_attempt("void_raid", character_id="hero")
        assert state is not None
        assert state.status == "in_progress"
        assert state.attempts == 1

    def test_begin_attempt_unknown(self):
        mgr = _make_endgame_manager()
        assert mgr.begin_attempt("nonexistent", character_id="hero") is None

    def test_complete_content(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        mgr.begin_attempt("void_raid", character_id="hero")
        state = mgr.complete_content("void_raid", character_id="hero", score=1500)
        assert state is not None
        assert state.status == "completed"
        assert state.best_score == 1500
        assert state.completed_at is not None

    def test_complete_content_best_score(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        mgr.begin_attempt("void_raid", character_id="hero")
        mgr.complete_content("void_raid", character_id="hero", score=1000)
        mgr.begin_attempt("void_raid", character_id="hero")
        mgr.complete_content("void_raid", character_id="hero", score=1500)
        state = mgr.get_state("hero", "void_raid")
        assert state.best_score == 1500

    def test_fail_content(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        mgr.begin_attempt("void_raid", character_id="hero")
        state = mgr.fail_content("void_raid", character_id="hero")
        assert state is not None
        assert state.status == "available"

    def test_fail_content_not_in_progress(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        assert mgr.fail_content("void_raid", character_id="hero") is None

    def test_reset_progress(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        mgr.begin_attempt("void_raid", character_id="hero")
        mgr.complete_content("void_raid", character_id="hero", score=1500)
        state = mgr.reset_progress("void_raid", character_id="hero")
        assert state is not None
        assert state.status == "locked"
        assert state.best_score == 0
        assert state.attempts == 0
        assert state.completed_at is None

    def test_reset_missing_returns_none(self):
        mgr = _make_endgame_manager()
        assert mgr.reset_progress("void_raid", character_id="hero") is None

    def test_get_completed_content(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        mgr.begin_attempt("void_raid", character_id="hero")
        mgr.complete_content("void_raid", character_id="hero")
        mgr.start_content("eternal_bounties", character_id="hero")
        mgr.begin_attempt("eternal_bounties", character_id="hero")
        mgr.complete_content("eternal_bounties", character_id="hero")
        completed = mgr.get_completed_content("hero")
        assert len(completed) == 2
        assert "void_raid" in completed
        assert "eternal_bounties" in completed

    def test_get_content_stats(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        mgr.begin_attempt("void_raid", character_id="hero")
        mgr.start_content("eternal_bounties", character_id="hero")
        stats = mgr.get_content_stats("hero")
        assert stats["character_id"] == "hero"
        assert stats["total_attempts"] == 1
        assert stats["available_count"] == 2

    def test_get_world_effects(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        mgr.begin_attempt("void_raid", character_id="hero")
        mgr.complete_content("void_raid", character_id="hero")
        effects = mgr.get_world_effects("hero")
        assert len(effects) == 1
        assert effects[0]["type"] == "unlock_region"
        assert effects[0]["region"] == "void_temple"

    def test_export_import_roundtrip(self):
        mgr = _make_endgame_manager()
        mgr.start_content("void_raid", character_id="hero")
        mgr.begin_attempt("void_raid", character_id="hero")
        mgr.complete_content("void_raid", character_id="hero", score=1200)
        state = mgr.export_state()

        mgr2 = EndgameManager(data_directory="")
        mgr2.load_definitions(_sample_endgame_definitions())
        mgr2.import_state(state)
        assert len(mgr2.list_definitions()) == 3
        s = mgr2.get_state("hero", "void_raid")
        assert s is not None
        assert s.status == "completed"
        assert s.best_score == 1200

    def test_get_definition(self):
        mgr = _make_endgame_manager()
        d = mgr.get_definition("void_raid")
        assert d is not None
        assert d.name == "Void Raid"
        assert mgr.get_definition("nonexistent") is None


# ---------------------------------------------------------------------------
# New Game Plus tests
# ---------------------------------------------------------------------------

class TestNGPlusProfile(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "profile_id": "p1",
            "name": "NG+ Cycle 1",
            "difficulty_mult": 1.5,
            "carried_over_stats": ["strength", "intelligence"],
            "carried_over_items": ["legendary_sword"],
            "unlocked_features": ["ng_plus_shop"],
            "world_seed": 42,
            "metadata": {"note": "first cycle"},
        }
        p = NGPlusProfile.from_dict(data)
        assert p.profile_id == "p1"
        assert p.name == "NG+ Cycle 1"
        assert p.difficulty_mult == 1.5
        assert p.carried_over_stats == ["strength", "intelligence"]
        assert p.carried_over_items == ["legendary_sword"]
        assert p.unlocked_features == ["ng_plus_shop"]
        assert p.world_seed == 42

    def test_to_dict(self):
        p = NGPlusProfile(
            profile_id="p1",
            name="Test",
            difficulty_mult=2.0,
            carried_over_stats=["strength"],
            carried_over_items=["sword"],
            unlocked_features=["feature_a"],
            world_seed=123,
            metadata={"m": 1},
        )
        data = p.to_dict()
        assert data["profile_id"] == "p1"
        assert data["difficulty_mult"] == 2.0
        assert data["carried_over_stats"] == ["strength"]
        assert data["world_seed"] == 123

    def test_roundtrip(self):
        original = NGPlusProfile(
            profile_id="p1",
            name="Roundtrip",
            difficulty_mult=1.25,
            carried_over_stats=["str"],
            carried_over_items=["potion"],
            unlocked_features=["shop"],
            world_seed=7,
        )
        restored = NGPlusProfile.from_dict(original.to_dict())
        assert restored.profile_id == original.profile_id
        assert restored.difficulty_mult == original.difficulty_mult
        assert restored.carried_over_stats == original.carried_over_stats
        assert restored.carried_over_items == original.carried_over_items
        assert restored.unlocked_features == original.unlocked_features
        assert restored.world_seed == original.world_seed


# ---------------------------------------------------------------------------
# NGPlusRun tests
# ---------------------------------------------------------------------------

class TestNGPlusRun(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "run_id": "r1",
            "character_id": "hero",
            "base_world_id": "w1",
            "profile_id": "p1",
            "cycle": 2,
            "started_at": "2024-01-01T00:00:00+00:00",
            "status": "active",
            "bonus_points": 50,
            "completed_at": None,
            "metadata": {"note": "second run"},
        }
        r = NGPlusRun.from_dict(data)
        assert r.run_id == "r1"
        assert r.character_id == "hero"
        assert r.cycle == 2
        assert r.bonus_points == 50

    def test_to_dict(self):
        r = NGPlusRun(
            run_id="r1",
            character_id="hero",
            base_world_id="w1",
            profile_id="p1",
            cycle=3,
            status="completed",
            bonus_points=100,
            metadata={"m": 1},
        )
        data = r.to_dict()
        assert data["run_id"] == "r1"
        assert data["cycle"] == 3
        assert data["status"] == "completed"
        assert data["bonus_points"] == 100

    def test_roundtrip(self):
        original = NGPlusRun(
            run_id="r1",
            character_id="hero",
            base_world_id="w1",
            profile_id="p1",
            cycle=2,
            status="active",
            bonus_points=25,
        )
        restored = NGPlusRun.from_dict(original.to_dict())
        assert restored.run_id == original.run_id
        assert restored.character_id == original.character_id
        assert restored.cycle == original.cycle
        assert restored.bonus_points == original.bonus_points


# ---------------------------------------------------------------------------
# NGPlusManager tests
# ---------------------------------------------------------------------------

class TestNGPlusManager(unittest.TestCase):
    def test_create_profile(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile(
            name="NG+ Cycle 1",
            difficulty_mult=1.5,
            carried_over_stats=["strength"],
            carried_over_items=["sword"],
        )
        assert profile.profile_id is not None
        assert profile.name == "NG+ Cycle 1"
        assert profile.difficulty_mult == 1.5

    def test_list_profiles(self):
        mgr = NGPlusManager()
        mgr.create_profile("NG+ 1", difficulty_mult=1.0)
        mgr.create_profile("NG+ 2", difficulty_mult=1.5)
        profiles = mgr.list_profiles()
        assert len(profiles) == 2

    def test_get_profile(self):
        mgr = NGPlusManager()
        p = mgr.create_profile("NG+ 1")
        fetched = mgr.get_profile(p.profile_id)
        assert fetched is not None
        assert fetched.name == "NG+ 1"
        assert mgr.get_profile("nonexistent") is None

    def test_start_run(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1")
        run = mgr.start_run(
            character_id="hero",
            base_world_id="w1",
            profile_id=profile.profile_id,
        )
        assert run is not None
        assert run.character_id == "hero"
        assert run.base_world_id == "w1"
        assert run.profile_id == profile.profile_id
        assert run.cycle == 1

    def test_start_run_with_cycle(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1")
        run = mgr.start_run(
            character_id="hero",
            base_world_id="w1",
            profile_id=profile.profile_id,
            cycle=5,
        )
        assert run.cycle == 5

    def test_start_run_unknown_profile(self):
        mgr = NGPlusManager()
        assert mgr.start_run("hero", "w1", "nonexistent") is None

    def test_complete_run(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1")
        run = mgr.start_run("hero", "w1", profile.profile_id)
        completed = mgr.complete_run(run.run_id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.completed_at is not None

    def test_complete_missing_run(self):
        mgr = NGPlusManager()
        assert mgr.complete_run("missing") is None

    def test_abandon_run(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1")
        run = mgr.start_run("hero", "w1", profile.profile_id)
        abandoned = mgr.abandon_run(run.run_id)
        assert abandoned is not None
        assert abandoned.status == "abandoned"

    def test_award_bonus_points(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1")
        run = mgr.start_run("hero", "w1", profile.profile_id)
        mgr.award_bonus_points(run.run_id, 50)
        assert run.bonus_points == 50

    def test_award_bonus_points_completed_run_returns_none(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1")
        run = mgr.start_run("hero", "w1", profile.profile_id)
        mgr.complete_run(run.run_id)
        assert mgr.award_bonus_points(run.run_id, 50) is None

    def test_get_active_run(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1")
        run = mgr.start_run("hero", "w1", profile.profile_id)
        active = mgr.get_active_run("hero")
        assert active is not None
        assert active.run_id == run.run_id
        assert mgr.get_active_run("nonexistent") is None

    def test_get_highest_cycle(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1")
        run1 = mgr.start_run("hero", "w1", profile.profile_id, cycle=1)
        mgr.complete_run(run1.run_id)
        run2 = mgr.start_run("hero", "w1", profile.profile_id, cycle=2)
        mgr.complete_run(run2.run_id)
        assert mgr.get_highest_cycle("hero") == 2

    def test_get_carry_over_stats(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile(
            "NG+ 1",
            carried_over_stats=["strength", "dexterity"],
        )
        mgr.start_run("hero", "w1", profile.profile_id)
        carried = mgr.get_carry_over_stats("hero", {"strength": 20, "dexterity": 15, "hp": 100})
        assert carried == {"strength": 20, "dexterity": 15}

    def test_get_carry_over_stats_no_active_run(self):
        mgr = NGPlusManager()
        carried = mgr.get_carry_over_stats("hero", {"strength": 20})
        assert carried == {}

    def test_get_carry_over_items(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile(
            "NG+ 1",
            carried_over_items=["legendary_sword", "health_potion"],
        )
        mgr.start_run("hero", "w1", profile.profile_id)
        items = mgr.get_carry_over_items("hero", ["legendary_sword", "rusty_dagger", "health_potion"])
        assert "legendary_sword" in items
        assert "health_potion" in items
        assert "rusty_dagger" not in items

    def test_get_carry_over_items_no_active_run(self):
        mgr = NGPlusManager()
        items = mgr.get_carry_over_items("hero", ["sword"])
        assert items == []

    def test_get_ng_xp_multiplier(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1", difficulty_mult=2.0)
        mgr.start_run("hero", "w1", profile.profile_id)
        assert mgr.get_ng_xp_multiplier("hero") == 2.0

    def test_get_ng_xp_multiplier_no_active_run(self):
        mgr = NGPlusManager()
        assert mgr.get_ng_xp_multiplier("hero") == 1.0

    def test_list_runs(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1")
        run1 = mgr.start_run("hero", "w1", profile.profile_id)
        run2 = mgr.start_run("hero", "w1", profile.profile_id)
        runs = mgr.list_runs("hero")
        assert len(runs) == 2

    def test_list_runs_filter_by_character(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1")
        mgr.start_run("hero", "w1", profile.profile_id)
        mgr.start_run("sidekick", "w1", profile.profile_id)
        runs = mgr.list_runs("hero")
        assert len(runs) == 1
        assert runs[0]["character_id"] == "hero"

    def test_export_import_roundtrip(self):
        mgr = NGPlusManager()
        profile = mgr.create_profile("NG+ 1", difficulty_mult=1.5)
        run = mgr.start_run("hero", "w1", profile.profile_id, cycle=1)
        mgr.award_bonus_points(run.run_id, 30)
        mgr.complete_run(run.run_id)
        state = mgr.export_state()

        mgr2 = NGPlusManager()
        mgr2.import_state(state)
        assert len(mgr2.list_profiles()) == 1
        assert len(mgr2.list_runs("hero")) == 1
        assert mgr2.list_runs("hero")[0]["cycle"] == 1
        assert mgr2.list_runs("hero")[0]["bonus_points"] == 30


if __name__ == "__main__":
    suites = [
        TestEndgameContentDefinition,
        TestEndgameContentState,
        TestEndgameManager,
        TestNGPlusProfile,
        TestNGPlusRun,
        TestNGPlusManager,
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
