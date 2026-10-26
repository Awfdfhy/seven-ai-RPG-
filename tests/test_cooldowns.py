"""
Tests for RPG-08-07: Cooldowns.
Run with: python -m pytest tests/test_cooldowns.py -v
or:       python tests/test_cooldowns.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cooldowns import CooldownEntry, CooldownManager

# ---------------------------------------------------------------------------
# CooldownEntry tests
# ---------------------------------------------------------------------------

class TestCooldownEntry:
    def test_is_ready_before_ready_at(self):
        entry = CooldownEntry(ability_id="a.b", ready_at=10.0)
        assert entry.is_ready(9.0) is False

    def test_is_ready_after_ready_at(self):
        entry = CooldownEntry(ability_id="a.b", ready_at=10.0)
        assert entry.is_ready(10.0) is True

    def test_remaining(self):
        entry = CooldownEntry(ability_id="a.b", ready_at=10.0)
        assert entry.remaining(8.0) == 2.0
        assert entry.remaining(11.0) == 0.0

    def test_to_from_dict_roundtrip(self):
        entry = CooldownEntry(ability_id="a.b", ready_at=100.0, started_at=90.0)
        data = entry.to_dict()
        restored = CooldownEntry.from_dict(data)
        assert restored.ability_id == "a.b"
        assert restored.ready_at == 100.0
        assert restored.started_at == 90.0

    def test_default_values(self):
        entry = CooldownEntry(ability_id="a.b")
        assert entry.ready_at == 0.0
        assert entry.started_at == 0.0


# ---------------------------------------------------------------------------
# CooldownManager tests
# ---------------------------------------------------------------------------

class TestCooldownManager:
    def test_start_and_check_individual(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 8.0, now)
        assert mgr.is_on_cooldown("fire.fireball", now + 1.0) is True
        assert mgr.is_on_cooldown("fire.fireball", now + 9.0) is False

    def test_get_cooldown_remaining(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 8.0, now)
        remaining = mgr.get_cooldown_remaining("fire.fireball", now + 1.0)
        assert 6.9 <= remaining <= 7.9

    def test_can_use_and_use(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        ok, reason = mgr.use("fire.fireball", 8.0, now)
        assert ok is True
        ok, reason = mgr.use("fire.fireball", 8.0, now + 1.0)
        assert ok is False
        assert "cooldown" in reason.lower()

    def test_use_after_cooldown(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.use("fire.fireball", 8.0, now)
        ok, reason = mgr.use("fire.fireball", 8.0, now + 9.0)
        assert ok is True

    def test_global_cooldown(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_global_cooldown(1.5, now)
        assert mgr.is_on_cooldown("any.ability", now + 0.5) is True
        assert mgr.is_on_cooldown("any.ability", now + 2.0) is False

    def test_global_blocks_use(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_global_cooldown(2.0, now)
        ok, reason = mgr.use("fire.fireball", 0.0, now + 0.5)
        assert ok is False
        assert "cooldown" in reason.lower()

    def test_group_cooldown(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 8.0, now, group="fire")
        assert mgr.is_group_on_cooldown("fire", now + 1.0) is True
        assert mgr.is_group_on_cooldown("fire", now + 9.0) is False

    def test_group_blocks_use(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_cooldown("fire.inferno", 10.0, now, group="fire")
        ok, reason = mgr.use("fire.fireball", 0.0, now + 0.5, group="fire")
        assert ok is False
        assert "group" in reason.lower() and "cooldown" in reason.lower()

    def test_different_groups_independent(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 8.0, now, group="fire")
        mgr.start_cooldown("st.shadow_step", 12.0, now, group="stealth")
        # Fire on cooldown, stealth not
        assert mgr.is_group_on_cooldown("fire", now + 1.0) is True
        assert mgr.is_group_on_cooldown("stealth", now + 1.0) is True
        assert mgr.is_group_on_cooldown("fire", now + 9.0) is False
        assert mgr.is_group_on_cooldown("stealth", now + 9.0) is True

    def test_group_takes_longest_cooldown(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 5.0, now, group="fire")
        mgr.start_cooldown("fire.inferno", 10.0, now + 1.0, group="fire")
        # Inferno's cooldown should extend the group timer to now + 11.0
        remaining = mgr.get_group_cooldown_remaining("fire", now + 2.0)
        assert 8.9 <= remaining <= 9.9

    def test_clear_cooldown(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 8.0, now)
        mgr.clear_cooldown("fire.fireball")
        assert mgr.is_on_cooldown("fire.fireball", now + 1.0) is False

    def test_clear_group_cooldown(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 8.0, now, group="fire")
        mgr.clear_group_cooldown("fire")
        assert mgr.is_group_on_cooldown("fire", now + 1.0) is False

    def test_clear_all_cooldowns(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 8.0, now)
        mgr.start_global_cooldown(5.0, now)
        mgr.clear_all_cooldowns()
        assert mgr.is_on_cooldown("fire.fireball", now + 1.0) is False
        assert mgr.is_group_on_cooldown("fire", now + 1.0) is False
        assert mgr.global_cooldown_until == 0.0

    def test_tick_removes_expired(self):
        mgr = CooldownManager(character_id="hero")
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 5.0, now)
        mgr.start_cooldown("fire.inferno", 15.0, now)
        expired = mgr.tick(now + 6.0)
        assert "fire.fireball" in expired
        assert "fire.fireball" not in mgr.entries
        assert "fire.inferno" in mgr.entries

    def test_cooldown_reduction(self):
        mgr = CooldownManager(character_id="hero", reduction=0.5)
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 10.0, now)
        remaining = mgr.get_cooldown_remaining("fire.fireball", now + 2.0)
        assert 2.9 <= remaining <= 3.9  # 50% reduction -> 5s total, 3s remaining

    def test_global_cooldown_reduction(self):
        mgr = CooldownManager(character_id="hero", reduction=0.5)
        now = 1000.0
        mgr.start_global_cooldown(4.0, now)
        assert mgr.is_on_cooldown("any.ability", now + 1.5) is True  # reduced to 2s, 0.5s left
        assert mgr.is_on_cooldown("any.ability", now + 2.5) is False

    def test_to_from_dict_roundtrip(self):
        mgr = CooldownManager(character_id="hero", reduction=0.25)
        now = 1000.0
        mgr.start_cooldown("fire.fireball", 8.0, now)
        mgr.start_cooldown("fire.inferno", 10.0, now + 2.0, group="fire")
        mgr.start_global_cooldown(2.0, now)
        data = mgr.to_dict()
        restored = CooldownManager.from_dict(data)
        assert restored.character_id == "hero"
        assert restored.reduction == 0.25
        assert "fire.fireball" in restored.entries
        assert restored.global_cooldown_until == now + 1.5  # 2.0s reduced by 25%

    def test_default_values(self):
        mgr = CooldownManager(character_id="hero")
        assert mgr.entries == {}
        assert mgr.group_entries == {}
        assert mgr.global_cooldown_until == 0.0
        assert mgr.reduction == 0.0


if __name__ == "__main__":
    import traceback

    suites = [
        TestCooldownEntry,
        TestCooldownManager,
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
