"""
Tests for RPG-10-12 Tutorial System.
Run with: python -m pytest tests/test_tutorial.py -v
or:       python tests/test_tutorial.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tutorial import (
    TutorialDefinition,
    TutorialInstance,
    TutorialManager,
    TutorialStepDefinition,
)

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
                actions=[
                    {"action_type": "open_inventory", "target": "inventory"}
                ],
                prerequisites=[],
            ),
            TutorialStepDefinition(
                id="step_02",
                name="Travel",
                description="Travel to the village.",
                hint="Use the map.",
                actions=[
                    {"action_type": "travel", "target": "village"}
                ],
                prerequisites=["step_01"],
            ),
            TutorialStepDefinition(
                id="step_03",
                name="Use Ability",
                description="Use a basic ability.",
                hint="Select an ability.",
                actions=[
                    {"action_type": "use_ability", "target": "strike"}
                ],
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
                actions=[
                    {"action_type": "craft_item", "target": "potion"}
                ],
                prerequisites=[],
            ),
        ],
        metadata={"difficulty": "medium"},
    )


def _make_manager() -> TutorialManager:
    mgr = TutorialManager()
    mgr.load_definitions([_sample_onboarding(), _sample_advanced()])
    return mgr


# ---------------------------------------------------------------------------
# TutorialDefinition / TutorialStepDefinition tests
# ---------------------------------------------------------------------------

class TestTutorialStepDefinition(unittest.TestCase):
    def test_get_expected_actions(self):
        step = TutorialStepDefinition(
            id="s1",
            name="Step One",
            description="desc",
            hint="hint",
            actions=[
                {"action_type": "travel", "target": "home"},
                {"action_type": "open_inventory", "target": "inventory"},
            ],
        )
        actions = step.get_expected_actions()
        assert len(actions) == 2
        assert actions[0].action_type == "travel"
        assert actions[0].target == "home"
        assert actions[1].action_type == "open_inventory"

    def test_to_from_dict_roundtrip(self):
        original = TutorialStepDefinition(
            id="s1",
            name="Step One",
            description="desc",
            hint="hint",
            actions=[{"action_type": "travel", "target": "home"}],
            prerequisites=["pre1"],
            metadata={"key": "val"},
        )
        restored = TutorialStepDefinition.from_dict(original.to_dict())
        assert restored.id == "s1"
        assert restored.name == "Step One"
        assert restored.hint == "hint"
        assert len(restored.actions) == 1
        assert restored.prerequisites == ["pre1"]
        assert restored.metadata == {"key": "val"}


class TestTutorialDefinition(unittest.TestCase):
    def test_get_step(self):
        tut = _sample_onboarding()
        step = tut.get_step("step_02")
        assert step is not None
        assert step.name == "Travel"

    def test_get_step_missing(self):
        tut = _sample_onboarding()
        assert tut.get_step("nonexistent") is None

    def test_to_from_dict_roundtrip(self):
        original = _sample_onboarding()
        restored = TutorialDefinition.from_dict(original.to_dict())
        assert restored.id == "onboarding_basics"
        assert len(restored.steps) == 3
        assert restored.prerequisites == []


# ---------------------------------------------------------------------------
# TutorialInstance tests
# ---------------------------------------------------------------------------

class TestTutorialInstance(unittest.TestCase):
    def test_to_from_dict_roundtrip(self):
        original = TutorialInstance(
            instance_id="inst-1",
            tutorial_id="tut-1",
            world_id="w1",
            session_id="s1",
            status="active",
            current_step_index=1,
            completed_steps=["step_01"],
            skipped_steps=[],
            metadata={"source": "new_player"},
        )
        restored = TutorialInstance.from_dict(original.to_dict())
        assert restored.instance_id == "inst-1"
        assert restored.tutorial_id == "tut-1"
        assert restored.status == "active"
        assert restored.current_step_index == 1
        assert restored.completed_steps == ["step_01"]

    def test_default_status_is_active(self):
        inst = TutorialInstance(
            instance_id="i1", tutorial_id="t1", world_id="w1"
        )
        assert inst.status == "active"
        assert inst.current_step_index == 0


# ---------------------------------------------------------------------------
# TutorialManager tests
# ---------------------------------------------------------------------------

class TestTutorialManager(unittest.TestCase):
    def test_start_tutorial_success(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        assert inst is not None
        assert inst.status == "active"
        assert inst.current_step_index == 0

    def test_start_tutorial_unknown(self):
        mgr = _make_manager()
        assert mgr.start_tutorial("nonexistent", world_id="w1") is None

    def test_start_tutorial_prerequisites_not_met(self):
        mgr = _make_manager()
        # onboarding_advanced requires onboarding_basics to be completed
        assert mgr.start_tutorial("onboarding_advanced", world_id="w1") is None

    def test_start_tutorial_prerequisites_met(self):
        mgr = _make_manager()
        inst1 = mgr.start_tutorial("onboarding_basics", world_id="w1")
        assert inst1 is not None
        # Complete the first tutorial
        mgr.complete_tutorial(inst1.instance_id)
        inst2 = mgr.start_tutorial("onboarding_advanced", world_id="w1")
        assert inst2 is not None

    def test_start_tutorial_already_completed(self):
        mgr = _make_manager()
        inst1 = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_tutorial(inst1.instance_id)
        # Starting again after completion should still create a new instance
        # (the system doesn't block re-starting, it just tracks state)
        inst2 = mgr.start_tutorial("onboarding_basics", world_id="w1")
        assert inst2 is not None

    def test_complete_step_advances(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_step(inst.instance_id)
        assert inst.current_step_index == 1
        assert "step_01" in inst.completed_steps

    def test_complete_step_last_completes_tutorial(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        # Advance to last step
        inst.current_step_index = 2
        mgr.complete_step(inst.instance_id)
        assert inst.status == "completed"
        assert inst.completed_at is not None

    def test_complete_step_inactive_returns_none(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_tutorial(inst.instance_id)
        result = mgr.complete_step(inst.instance_id)
        assert result is None

    def test_skip_step(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.skip_step(inst.instance_id)
        assert inst.current_step_index == 1
        assert "step_01" in inst.skipped_steps

    def test_skip_step_last_skips_tutorial(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        inst.current_step_index = 2
        mgr.skip_step(inst.instance_id)
        assert inst.status == "skipped"
        assert inst.skipped_at is not None

    def test_skip_tutorial(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.skip_tutorial(inst.instance_id)
        assert inst.status == "skipped"
        assert inst.skipped_at is not None

    def test_complete_tutorial(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_tutorial(inst.instance_id)
        assert inst.status == "completed"
        assert inst.current_step_index == 2
        assert len(inst.completed_steps) == 3

    def test_get_current_step(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        _, step = mgr.get_current_step(inst.instance_id)
        assert step is not None
        assert step.id == "step_01"
        assert step.name == "Open Inventory"

    def test_get_current_step_after_advance(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_step(inst.instance_id)
        _, step = mgr.get_current_step(inst.instance_id)
        assert step.id == "step_02"

    def test_get_current_step_inactive(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_tutorial(inst.instance_id)
        _, step = mgr.get_current_step(inst.instance_id)
        assert step is None

    def test_get_hint(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        hint = mgr.get_hint(inst.instance_id)
        assert hint == "Press I."

    def test_get_hint_inactive(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_tutorial(inst.instance_id)
        assert mgr.get_hint(inst.instance_id) is None

    def test_match_action(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        assert mgr.match_action(inst.instance_id, "open_inventory", "inventory") is True
        assert mgr.match_action(inst.instance_id, "travel", "village") is False

    def test_match_action_after_advance(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_step(inst.instance_id)
        assert mgr.match_action(inst.instance_id, "travel", "village") is True
        assert mgr.match_action(inst.instance_id, "open_inventory", "inventory") is False

    def test_list_instances_scoped(self):
        mgr = _make_manager()
        inst1 = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.start_tutorial("onboarding_basics", world_id="w2")
        assert len(mgr.list_instances(world_id="w1")) == 1
        assert len(mgr.list_instances()) == 2

    def test_list_instances_status_filter(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_tutorial(inst.instance_id)
        assert len(mgr.list_instances(status="completed")) == 1
        assert len(mgr.list_instances(status="active")) == 0

    def test_list_definitions(self):
        mgr = _make_manager()
        defs = mgr.list_definitions()
        assert len(defs) == 2
        ids = [d["id"] for d in defs]
        assert "onboarding_basics" in ids
        assert "onboarding_advanced" in ids

    def test_get_definition(self):
        mgr = _make_manager()
        d = mgr.get_definition("onboarding_basics")
        assert d is not None
        assert d.name == "First Steps"
        assert mgr.get_definition("nonexistent") is None

    def test_get_available_tutorials(self):
        mgr = _make_manager()
        available = mgr.get_available_tutorials("w1")
        ids = [t["id"] for t in available]
        assert "onboarding_basics" in ids
        assert "onboarding_advanced" not in ids  # prerequisites not met

        # Complete basics
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_tutorial(inst.instance_id)
        available = mgr.get_available_tutorials("w1")
        ids = [t["id"] for t in available]
        assert "onboarding_advanced" in ids

    def test_get_completed_tutorials(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.complete_tutorial(inst.instance_id)
        completed = mgr.get_completed_tutorials("w1")
        assert "onboarding_basics" in completed

    def test_get_skipped_tutorials(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial("onboarding_basics", world_id="w1")
        mgr.skip_tutorial(inst.instance_id)
        skipped = mgr.get_skipped_tutorials("w1")
        assert "onboarding_basics" in skipped

    def test_session_scoping(self):
        mgr = _make_manager()
        inst1 = mgr.start_tutorial("onboarding_basics", world_id="w1", session_id="s1")
        mgr.start_tutorial("onboarding_basics", world_id="w1", session_id="s2")
        assert len(mgr.list_instances(session_id="s1")) == 1
        assert len(mgr.list_instances(session_id="s2")) == 1

    def test_export_import_roundtrip(self):
        mgr = _make_manager()
        inst1 = mgr.start_tutorial(
            "onboarding_basics", world_id="w1", session_id="s1"
        )
        mgr.complete_step(inst1.instance_id)

        state = mgr.export_state()

        mgr2 = TutorialManager()
        mgr2.load_definitions([_sample_onboarding(), _sample_advanced()])
        mgr2.import_state(state)

        assert len(mgr2.list_instances()) == 1
        inst = mgr2.get_instance(inst1.instance_id)
        assert inst is not None
        assert inst.current_step_index == 1
        assert "step_01" in inst.completed_steps

    def test_start_with_metadata(self):
        mgr = _make_manager()
        inst = mgr.start_tutorial(
            "onboarding_basics",
            world_id="w1",
            metadata={"source": "new_player_flow", "flow_id": "flow-1"},
        )
        assert inst is not None
        assert inst.metadata["source"] == "new_player_flow"
        assert inst.metadata["flow_id"] == "flow-1"


if __name__ == "__main__":
    suites = [TestTutorialStepDefinition, TestTutorialDefinition, TestTutorialInstance, TestTutorialManager]
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
