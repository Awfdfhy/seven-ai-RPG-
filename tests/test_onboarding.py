"""
Tests for RPG-10-12 Onboarding System.
Run with: python -m pytest tests/test_onboarding.py -v
or:       python tests/test_onboarding.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from onboarding import OnboardingManager, OnboardingState
from tutorial import TutorialDefinition, TutorialManager, TutorialStepDefinition
from world_persistence import WorldPersistence

# ---------------------------------------------------------------------------
# Sample definitions
# ---------------------------------------------------------------------------

def _sample_onboarding() -> TutorialDefinition:
    return TutorialDefinition(
        id="onboarding_basics",
        name="First Steps",
        description="Learn the basics.",
        prerequisites=[],
        steps=[
            TutorialStepDefinition(
                id="step_01",
                name="Open Inventory",
                description="Open your inventory.",
                hint="Press I.",
                actions=[{"action_type": "open_inventory", "target": "inventory"}],
                prerequisites=[],
            ),
            TutorialStepDefinition(
                id="step_02",
                name="Travel",
                description="Travel to the village.",
                hint="Use the map.",
                actions=[{"action_type": "travel", "target": "village"}],
                prerequisites=["step_01"],
            ),
            TutorialStepDefinition(
                id="step_03",
                name="Use Ability",
                description="Use a basic ability.",
                hint="Select an ability.",
                actions=[{"action_type": "use_ability", "target": "strike"}],
                prerequisites=["step_02"],
            ),
        ],
        metadata={"difficulty": "easy"},
    )


def _sample_advanced() -> TutorialDefinition:
    return TutorialDefinition(
        id="onboarding_advanced",
        name="Advanced Skills",
        description="For experienced players.",
        prerequisites=["onboarding_basics"],
        steps=[
            TutorialStepDefinition(
                id="adv_01",
                name="Craft",
                description="Craft an item.",
                hint="Open the crafting menu.",
                actions=[{"action_type": "craft_item", "target": "potion"}],
                prerequisites=[],
            ),
        ],
        metadata={"difficulty": "medium"},
    )


def _make_tutorial_manager() -> TutorialManager:
    mgr = TutorialManager()
    mgr.load_definitions([_sample_onboarding(), _sample_advanced()])
    return mgr


def _make_onboarding_manager() -> OnboardingManager:
    return OnboardingManager(tutorial_manager=_make_tutorial_manager())


# ---------------------------------------------------------------------------
# OnboardingState tests
# ---------------------------------------------------------------------------

class TestOnboardingState(unittest.TestCase):
    def test_to_from_dict_roundtrip(self):
        original = OnboardingState(
            world_id="w1",
            session_id="s1",
            started=True,
            completed=False,
            skipped=False,
            active_instance_id="inst-1",
            metadata={"source": "new_player"},
        )
        restored = OnboardingState.from_dict(original.to_dict())
        assert restored.world_id == "w1"
        assert restored.session_id == "s1"
        assert restored.started is True
        assert restored.completed is False
        assert restored.active_instance_id == "inst-1"
        assert restored.metadata == {"source": "new_player"}

    def test_defaults(self):
        state = OnboardingState(world_id="w1")
        assert state.session_id is None
        assert state.started is False
        assert state.completed is False
        assert state.skipped is False
        assert state.active_instance_id is None


# ---------------------------------------------------------------------------
# OnboardingManager tests
# ---------------------------------------------------------------------------

class TestOnboardingManager(unittest.TestCase):
    def test_start_onboarding_success(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        assert state is not None
        assert state.started is True
        assert state.active_instance_id is not None

    def test_start_onboarding_already_onboarded_returns_none(self):
        mgr = _make_onboarding_manager()
        state1 = mgr.start_onboarding("w1", session_id="s1")
        mgr.complete_onboarding("w1")
        state2 = mgr.start_onboarding("w1", session_id="s2")
        assert state2 is None

    def test_is_onboarded_false_before_start(self):
        mgr = _make_onboarding_manager()
        assert mgr.is_onboarded("w1") is False

    def test_is_onboarded_true_after_complete(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        mgr.complete_onboarding("w1")
        assert mgr.is_onboarded("w1") is True

    def test_is_onboarded_true_after_skip(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        mgr.skip_onboarding("w1")
        assert mgr.is_onboarded("w1") is True

    def test_complete_current_step_advances(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        inst, step = mgr.get_current_tutorial_instance("w1")
        assert step.id == "basics_01"
        mgr.complete_current_step(state.active_instance_id)
        inst, step = mgr.get_current_tutorial_instance("w1")
        assert step.id == "basics_02"

    def test_complete_current_step_marks_completed_when_done(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        # Complete all steps manually
        inst = mgr.tutorial_manager.get_instance(state.active_instance_id)
        for _ in range(len(mgr.tutorial_manager.get_definition("onboarding_basics").steps)):
            mgr.complete_current_step(state.active_instance_id)
        assert mgr.is_onboarded("w1") is True

    def test_skip_current_step(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        mgr.skip_current_step(state.active_instance_id)
        inst, step = mgr.get_current_tutorial_instance("w1")
        assert step.id == "basics_02"

    def test_skip_onboarding(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        result = mgr.skip_onboarding("w1")
        assert result is not None
        assert result.skipped is True
        assert mgr.is_onboarded("w1") is True

    def test_complete_onboarding(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        result = mgr.complete_onboarding("w1")
        assert result is not None
        assert result.completed is True
        assert mgr.is_onboarded("w1") is True

    def test_get_hint(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        hint = mgr.get_hint("w1")
        assert hint == "Press the inventory key or click the inventory button on the HUD."

    def test_get_hint_none_when_not_started(self):
        mgr = _make_onboarding_manager()
        assert mgr.get_hint("w1") is None

    def test_match_action(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        assert mgr.match_action("w1", "open_inventory", "inventory") is True
        assert mgr.match_action("w1", "travel", "village") is False

    def test_match_action_after_advance(self):
        mgr = _make_onboarding_manager()
        state = mgr.start_onboarding("w1", session_id="s1")
        mgr.complete_current_step(state.active_instance_id)
        assert mgr.match_action("w1", "travel", "village_square") is True
        assert mgr.match_action("w1", "open_inventory", "inventory") is False

    def test_get_state_returns_none_for_unknown_world(self):
        mgr = _make_onboarding_manager()
        assert mgr.get_state("unknown") is None

    def test_list_worlds_pending_onboarding(self):
        mgr = _make_onboarding_manager()
        state1 = mgr.start_onboarding("w1", session_id="s1")
        state2 = mgr.start_onboarding("w2", session_id="s2")
        mgr.complete_onboarding("w1")
        pending = mgr.list_worlds_pending_onboarding()
        assert "w2" in pending
        assert "w1" not in pending

    def test_export_import_roundtrip(self):
        mgr = _make_onboarding_manager()
        mgr.start_onboarding("w1", session_id="s1")
        mgr.complete_current_step(mgr.get_state("w1").active_instance_id)

        state = mgr.export_state()
        mgr2 = OnboardingManager(tutorial_manager=_make_tutorial_manager())
        mgr2.import_state(state)

        assert mgr2.is_onboarded("w1") is False  # not completed/skipped
        assert mgr2.get_state("w1") is not None
        assert mgr2.get_state("w1").started is True

    def test_set_onboarding_tutorial(self):
        mgr = _make_onboarding_manager()
        mgr.set_onboarding_tutorial("onboarding_advanced")
        # Advanced requires basics to be completed, so starting for fresh world returns None
        state = mgr.start_onboarding("w1", session_id="s1")
        assert state is None
        # Complete basics first
        basics = mgr.tutorial_manager.start_tutorial("onboarding_basics", world_id="w1", session_id="s1")
        mgr.tutorial_manager.complete_tutorial(basics.instance_id)
        state = mgr.start_onboarding("w1", session_id="s1")
        assert state is not None


# ---------------------------------------------------------------------------
# WorldPersistence integration tests
# ---------------------------------------------------------------------------

class TestWorldPersistenceOnboarding(unittest.TestCase):
    def test_save_load_includes_tutorials(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "save.json")

            mgr = _make_tutorial_manager()
            persistence = WorldPersistence(tutorials=mgr)
            inst = mgr.start_tutorial("onboarding_basics", world_id="w1", session_id="s1")
            mgr.complete_step(inst.instance_id)

            save_result = persistence.save(path)
            assert save_result["tutorial_instances"] == 1

            mgr2 = _make_tutorial_manager()
            persistence2 = WorldPersistence(tutorials=mgr2)
            load_result = persistence2.load(path)
            assert load_result["tutorial_instances"] == 1
            assert len(mgr2.list_instances()) == 1
            loaded_inst = mgr2.get_instance(inst.instance_id)
            assert loaded_inst is not None
            assert loaded_inst.current_step_index == 1
            assert "step_01" in loaded_inst.completed_steps

    def test_load_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "nonexistent.json")
            mgr = _make_tutorial_manager()
            persistence = WorldPersistence(tutorials=mgr)
            try:
                persistence.load(path)
            except FileNotFoundError:
                pass
            else:
                raise AssertionError("Expected FileNotFoundError")

    def test_save_without_tutorials_backward_compat(self):
        """Saves that predate tutorial support should still load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "legacy.json")
            payload = {
                "version": 1,
                "worlds": {},
                "sessions": [],
                "milestones": {},
            }
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)

            mgr = _make_tutorial_manager()
            persistence = WorldPersistence(tutorials=mgr)
            result = persistence.load(path)
            assert result["success"] is True
            assert result["tutorial_instances"] == 0


if __name__ == "__main__":
    suites = [
        TestOnboardingState,
        TestOnboardingManager,
        TestWorldPersistenceOnboarding,
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
