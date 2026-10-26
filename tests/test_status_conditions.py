"""
Tests for RPG-08-08 Status Conditions System.
Run with: python -m pytest tests/test_status_conditions.py -v
or:       python tests/test_status_conditions.py
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from status_conditions import (
    ActiveStatusCondition,
    StatOperator,
    StatusCondition,
    StatusConditionEffect,
    StatusConditionType,
)
from status_manager import StatusManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _poison_def() -> StatusCondition:
    return StatusCondition(
        id="poison",
        name="Poison",
        condition_type=StatusConditionType.POISON,
        description="Takes damage over time.",
        duration_seconds=10.0,
        max_stacks=5,
        effects=[
            StatusConditionEffect(stat="health", value=-3.0, operator=StatOperator.ADD),
        ],
        tick_interval_seconds=1.0,
        can_be_cleansed=True,
        prevents_actions=False,
    )


def _stun_def() -> StatusCondition:
    return StatusCondition(
        id="stun",
        name="Stun",
        condition_type=StatusConditionType.STUN,
        description="Cannot act.",
        duration_seconds=3.0,
        max_stacks=1,
        effects=[],
        tick_interval_seconds=0.0,
        can_be_cleansed=False,
        prevents_actions=True,
    )


def _regen_def() -> StatusCondition:
    return StatusCondition(
        id="regen",
        name="Regeneration",
        condition_type=StatusConditionType.HEAL_OVER_TIME,
        description="Heals over time.",
        duration_seconds=8.0,
        max_stacks=3,
        effects=[
            StatusConditionEffect(stat="health", value=2.0, operator=StatOperator.ADD),
        ],
        tick_interval_seconds=2.0,
        can_be_cleansed=True,
        prevents_actions=False,
    )


# ---------------------------------------------------------------------------
# StatusCondition tests
# ---------------------------------------------------------------------------

class TestStatusCondition:
    def test_to_from_dict_roundtrip(self):
        condition = _poison_def()
        data = condition.to_dict()
        restored = StatusCondition.from_dict(data)
        assert restored.id == "poison"
        assert restored.condition_type == StatusConditionType.POISON
        assert restored.duration_seconds == 10.0
        assert restored.max_stacks == 5
        assert len(restored.effects) == 1
        assert restored.effects[0].stat == "health"
        assert restored.effects[0].value == -3.0
        assert restored.tick_interval_seconds == 1.0
        assert restored.can_be_cleansed is True

    def test_default_values(self):
        condition = StatusCondition(id="x", name="X")
        assert condition.description == ""
        assert condition.duration_seconds == 0.0
        assert condition.max_stacks == 1
        assert condition.effects == []
        assert condition.tick_interval_seconds == 0.0
        assert condition.can_be_cleansed is True
        assert condition.prevents_actions is False


# ---------------------------------------------------------------------------
# ActiveStatusCondition tests
# ---------------------------------------------------------------------------

class TestActiveStatusCondition:
    def test_is_expired(self):
        now = time.time()
        active = ActiveStatusCondition(
            condition_id="poison",
            character_id="c1",
            remaining_duration=0.0,
            applied_at=now,
        )
        assert active.is_expired(now) is True

    def test_not_expired(self):
        now = time.time()
        active = ActiveStatusCondition(
            condition_id="poison",
            character_id="c1",
            remaining_duration=5.0,
            applied_at=now,
        )
        assert active.is_expired(now) is False

    def test_to_from_dict_roundtrip(self):
        now = 1000.0
        active = ActiveStatusCondition(
            condition_id="stun",
            character_id="hero",
            stacks=1,
            remaining_duration=3.0,
            applied_at=now,
            last_tick_at=now,
            source_ability_id="bash",
            source_character_id="orc",
        )
        data = active.to_dict()
        restored = ActiveStatusCondition.from_dict(data)
        assert restored.condition_id == "stun"
        assert restored.character_id == "hero"
        assert restored.stacks == 1
        assert restored.remaining_duration == 3.0
        assert restored.source_ability_id == "bash"


# ---------------------------------------------------------------------------
# StatusManager tests
# ---------------------------------------------------------------------------

class TestStatusManager:
    def test_register_and_get_definition(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        assert mgr.get_definition("poison") is not None
        assert mgr.get_definition("nonexistent") is None

    def test_apply_and_has_condition(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        now = 1000.0
        active = mgr.apply_condition("hero", "poison", current_time=now)
        assert active is not None
        assert mgr.has_condition("hero", "poison") is True
        assert mgr.count_stacks("hero", "poison") == 1

    def test_stack_limit(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        now = 1000.0
        mgr.apply_condition("hero", "poison", current_time=now, stacks=3)
        mgr.apply_condition("hero", "poison", current_time=now + 1.0, stacks=3)
        assert mgr.count_stacks("hero", "poison") == 5  # max_stacks=5

    def test_remove_condition(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        now = 1000.0
        mgr.apply_condition("hero", "poison", current_time=now)
        assert mgr.has_condition("hero", "poison") is True
        assert mgr.remove_condition("hero", "poison") is True
        assert mgr.has_condition("hero", "poison") is False
        assert mgr.remove_condition("hero", "poison") is False

    def test_cleanse(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        mgr.register_definition(_stun_def())
        now = 1000.0
        mgr.apply_condition("hero", "poison", current_time=now)
        mgr.apply_condition("hero", "stun", current_time=now)
        cleansed = mgr.cleanse("hero")
        assert "poison" in cleansed
        assert "stun" not in cleansed
        assert mgr.has_condition("hero", "poison") is False
        assert mgr.has_condition("hero", "stun") is True

    def test_remove_conditions_by_type(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        mgr.register_definition(_regen_def())
        now = 1000.0
        mgr.apply_condition("hero", "poison", current_time=now)
        mgr.apply_condition("hero", "regen", current_time=now)
        removed = mgr.remove_conditions_by_type("hero", StatusConditionType.DEBUFF)
        # poison is POISON type, not DEBUFF
        assert "poison" not in removed
        assert "regen" not in removed

    def test_is_action_prevented(self):
        mgr = StatusManager()
        mgr.register_definition(_stun_def())
        now = 1000.0
        assert mgr.is_action_prevented("hero") is False
        mgr.apply_condition("hero", "stun", current_time=now)
        assert mgr.is_action_prevented("hero") is True

    def test_is_stunned(self):
        mgr = StatusManager()
        mgr.register_definition(_stun_def())
        mgr.register_definition(_poison_def())
        now = 1000.0
        assert mgr.is_stunned("hero") is False
        mgr.apply_condition("hero", "stun", current_time=now)
        assert mgr.is_stunned("hero") is True
        mgr.apply_condition("hero", "poison", current_time=now)
        assert mgr.is_stunned("hero") is True

    def test_tick_expiry(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        now = 1000.0
        mgr.apply_condition("hero", "poison", current_time=now)
        assert mgr.has_condition("hero", "poison") is True
        results = mgr.tick("hero", current_time=now + 10.5)
        assert mgr.has_condition("hero", "poison") is False
        assert len(results) == 1
        assert results[0].expired is True

    def test_tick_damage(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        now = 1000.0
        mgr.apply_condition("hero", "poison", current_time=now, stacks=2)
        # fast-forward 2 seconds, crossing tick intervals
        results = mgr.tick("hero", current_time=now + 2.0)
        # remaining duration after 2s: 8.0 -> still active
        # tick_value=-3, stacks=2 -> damage = -6 per tick. Since duration > 0, no expired tick yet
        assert len(results) == 0

    def test_clear_all(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        mgr.register_definition(_stun_def())
        now = 1000.0
        mgr.apply_condition("hero", "poison", current_time=now)
        mgr.apply_condition("hero", "stun", current_time=now)
        mgr.clear_all("hero")
        assert mgr.get_active_conditions("hero") == []

    def test_get_active_conditions(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        mgr.register_definition(_stun_def())
        now = 1000.0
        mgr.apply_condition("hero", "poison", current_time=now)
        mgr.apply_condition("hero", "stun", current_time=now)
        active_list = mgr.get_active_conditions("hero")
        ids = {a.condition_id for a in active_list}
        assert ids == {"poison", "stun"}

    def test_tick_all(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        now = 1000.0
        mgr.apply_condition("hero", "poison", current_time=now)
        mgr.apply_condition("villain", "poison", current_time=now)
        results = mgr.tick_all(current_time=now + 10.5)
        assert "hero" in results
        assert "villain" in results

    def test_to_from_dict_roundtrip(self):
        mgr = StatusManager()
        mgr.register_definition(_poison_def())
        now = 1000.0
        mgr.apply_condition("hero", "poison", current_time=now, stacks=2)
        data = mgr.to_dict()
        restored = StatusManager.from_dict(data)
        assert restored.get_definition("poison") is not None
        assert restored.has_condition("hero", "poison") is True
        assert restored.count_stacks("hero", "poison") == 2

    def test_load_definitions_from_dicts(self):
        mgr = StatusManager()
        mgr.load_definitions_from_dicts(
            [
                {
                    "id": "burn",
                    "name": "Burn",
                    "condition_type": "burn",
                    "duration_seconds": 5.0,
                    "max_stacks": 3,
                    "effects": [],
                    "tick_interval_seconds": 1.0,
                    "can_be_cleansed": True,
                    "prevents_actions": False,
                }
            ]
        )
        assert mgr.get_definition("burn") is not None
        assert mgr.get_definition("burn").condition_type == StatusConditionType.BURN


if __name__ == "__main__":
    import traceback

    suites = [
        TestStatusCondition,
        TestActiveStatusCondition,
        TestStatusManager,
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
                    traceback.print_exc()
                    failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
