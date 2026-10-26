"""
Tests for RPG-08-06: Skill Check System.
Run with: python -m pytest tests/ -v
or:       python tests/test_skill_check.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import skill_check as sc
from skill_tree import (
    CharacterSkillState,
    SkillTree,
)
from skill_tree_builder import build_tree

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolver_with_thc() -> tuple[sc.SkillCheckResolver, SkillTree]:
    tree = build_tree({
        "id": "two_handed_combat",
        "name": "Two-Handed Combat",
        "nodes": [
            {
                "id": "thc.root",
                "name": "Heavy Weapons Training",
                "category": "combat",
                "node_type": "root",
                "max_rank": 1,
                "point_cost": 1,
                "stat_costs": {"strength": 8},
                "prerequisites": [],
                "effects": {"damage_bonus": 5},
                "parent_ids": [],
            },
            {
                "id": "thc.cleave",
                "name": "Cleave",
                "category": "combat",
                "node_type": "branch",
                "max_rank": 3,
                "point_cost": 2,
                "stat_costs": {"strength": 12},
                "prerequisites": [{"kind": "skill", "target": "thc.root", "minimum": 1}],
                "effects": {"check_bonus": 2, "damage_bonus": 3},
                "parent_ids": ["thc.root"],
            },
        ],
    })
    resolver = sc.SkillCheckResolver(trees={"two_handed_combat": tree})
    return resolver, tree


# ---------------------------------------------------------------------------
# Dice tests
# ---------------------------------------------------------------------------

class TestDice:
    def test_roll_d20_range(self):
        for _ in range(200):
            v = sc.roll_d20()
            assert 1 <= v <= 20

    def test_roll_dice_custom(self):
        rolls = sc.roll_dice(count=3, sides=6)
        assert len(rolls) == 3
        for r in rolls:
            assert 1 <= r <= 6


# ---------------------------------------------------------------------------
# Modifier resolution
# ---------------------------------------------------------------------------

class TestModifierResolution:
    def test_attribute_modifier(self):
        resolver, _ = _resolver_with_thc()
        ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength")
        result = resolver.resolve(ctx, {"strength": 10})
        # (10 - 10) // 2 = 0
        assert result.modifier_total == 0

    def test_attribute_modifier_high(self):
        resolver, _ = _resolver_with_thc()
        ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength")
        result = resolver.resolve(ctx, {"strength": 16})
        # (16 - 10) // 2 = 3
        assert result.modifier_total == 3

    def test_proficiency_bonus_applied(self):
        resolver, tree = _resolver_with_thc()
        state = CharacterSkillState(
            character_id="c1",
            available_points=1,
            attributes={"strength": 10},
            level=1,
        )
        state.unlock("thc.root", tree)
        ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength", skill_id="thc.root")
        ranks = {"thc.root": 1}
        result = resolver.resolve(ctx, {"strength": 10}, skill_ranks=ranks)
        # attr 0 + skill bonus 0 (damage_bonus not checked) + prof 2 + misc 0
        assert result.modifier_total == 2

    def test_skill_bonus_from_effects(self):
        resolver, tree = _resolver_with_thc()
        ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength", skill_id="thc.cleave")
        ranks = {"thc.cleave": 1}
        result = resolver.resolve(ctx, {"strength": 12}, skill_ranks=ranks)
        # attr 1 + check_bonus 2*1 + prof 2 = 5
        assert result.modifier_total == 5


# ---------------------------------------------------------------------------
# DC and success
# ---------------------------------------------------------------------------

class TestDCAndSuccess:
    def test_success_against_low_dc(self):
        resolver, _ = _resolver_with_thc()
        ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength", misc_bonus=10)
        result = resolver.resolve(ctx, {"strength": 10}, dc=5)
        assert result.success is True

    def test_failure_against_high_dc(self):
        import random as rmod
        original = rmod.randint
        rmod.randint = lambda a, b: 10
        try:
            resolver, _ = _resolver_with_thc()
            ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength", misc_bonus=-10)
            result = resolver.resolve(ctx, {"strength": 10}, dc=15)
            assert result.success is False
        finally:
            rmod.randint = original

    def test_natural_20_crit_success(self):
        import random as rmod
        original_randint = rmod.randint
        rmod.randint = lambda a, b: 20
        try:
            resolver, _ = _resolver_with_thc()
            ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength")
            result = resolver.resolve(ctx, {"strength": 10}, dc=sc.DifficultyClass.NEARLY_IMPOSSIBLE)
            assert result.critical_success is True
            assert result.success is True
        finally:
            rmod.randint = original_randint

    def test_natural_1_crit_failure(self):
        import random as rmod
        original_randint = rmod.randint
        rmod.randint = lambda a, b: 1
        try:
            resolver, _ = _resolver_with_thc()
            ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength", misc_bonus=100)
            result = resolver.resolve(ctx, {"strength": 10}, dc=sc.DifficultyClass.VERY_EASY)
            assert result.critical_failure is True
            assert result.success is False
        finally:
            rmod.randint = original_randint

    def test_advantage_picks_higher(self):
        import random as rmod
        original_randint = rmod.randint
        call_count = [0]
        def fake_randint(a, b):
            call_count[0] += 1
            return 5 if call_count[0] == 1 else 15
        rmod.randint = fake_randint
        try:
            resolver, _ = _resolver_with_thc()
            ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength", advantage=1)
            result = resolver.resolve(ctx, {"strength": 10}, dc=10)
            assert 15 in result.dice
            assert result.success is True
        finally:
            rmod.randint = original_randint

    def test_disadvantage_picks_lower(self):
        import random as rmod
        original_randint = rmod.randint
        rmod.randint = lambda a, b: 5 if a == 1 and b == 20 else 15
        try:
            resolver, _ = _resolver_with_thc()
            ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength", disadvantage=1)
            result = resolver.resolve(ctx, {"strength": 10}, dc=10)
            assert 5 in result.dice
            assert result.success is False
        finally:
            rmod.randint = original_randint


# ---------------------------------------------------------------------------
# Combat integration
# ---------------------------------------------------------------------------

class TestCombatResolver:
    def test_attack_hit(self):
        resolver, _ = _resolver_with_thc()
        combat = sc.CombatResolver(resolver=resolver)
        ctx = sc.AttackRollContext(
            character_id="c1",
            base_attribute="strength",
            target_ac=5,
            weapon_die=8,
            damage_bonus=2,
        )
        # Force max roll for reliability
        import random as rmod
        original = rmod.randint
        rmod.randint = lambda a, b: 20
        try:
            result = combat.attack(ctx, {"strength": 16}, skill_ranks={})
        finally:
            rmod.randint = original
        assert result.hit is True
        assert result.damage > 0
        assert result.crit is True

    def test_attack_miss(self):
        resolver, _ = _resolver_with_thc()
        combat = sc.CombatResolver(resolver=resolver)
        ctx = sc.AttackRollContext(
            character_id="c1",
            base_attribute="strength",
            target_ac=100,
            weapon_die=8,
        )
        import random as rmod
        original = rmod.randint
        rmod.randint = lambda a, b: 1
        try:
            result = combat.attack(ctx, {"strength": 16}, skill_ranks={})
        finally:
            rmod.randint = original
        assert result.hit is False
        assert result.crit is False

    def test_damage_includes_modifier(self):
        resolver, _ = _resolver_with_thc()
        combat = sc.CombatResolver(resolver=resolver)
        ctx = sc.AttackRollContext(
            character_id="c1",
            base_attribute="strength",
            target_ac=5,
            weapon_die=8,
        )
        import random as rmod
        original = rmod.randint
        rmod.randint = lambda a, b: 10
        try:
            result = combat.attack(ctx, {"strength": 16}, skill_ranks={})
        finally:
            rmod.randint = original
        # d8 roll 10 impossible, but with monkeypatch it's 10; attr mod +3
        assert result.modifier_total == 3
        assert result.damage >= 10 + 3


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_result_to_dict(self):
        resolver, _ = _resolver_with_thc()
        ctx = sc.SkillCheckContext(character_id="c1", base_attribute="strength")
        result = resolver.resolve(ctx, {"strength": 10}, dc=10)
        d = result.to_dict()
        assert "success" in d
        assert "total" in d
        assert "dice" in d
        assert "modifier_total" in d
        assert "dc" in d

    def test_attack_result_to_dict(self):
        resolver, _ = _resolver_with_thc()
        combat = sc.CombatResolver(resolver=resolver)
        ctx = sc.AttackRollContext(
            character_id="c1",
            base_attribute="strength",
            target_ac=10,
            weapon_die=6,
        )
        import random as rmod
        original = rmod.randint
        rmod.randint = lambda a, b: 10
        try:
            result = combat.attack(ctx, {"strength": 10}, skill_ranks={})
        finally:
            rmod.randint = original
        d = result.to_dict()
        assert d["hit"] is True
        assert d["ac"] == 10


if __name__ == "__main__":
    suites = [
        TestDice,
        TestModifierResolution,
        TestDCAndSuccess,
        TestCombatResolver,
        TestSerialization,
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
