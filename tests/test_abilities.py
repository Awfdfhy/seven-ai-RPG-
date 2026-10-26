"""
Tests for RPG-10-01 Ability System.
Run with: python -m pytest tests/test_abilities.py -v
or:       python tests/test_abilities.py
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ability import (
    Ability,
    AbilityCategory,
    AbilityEffect,
    AbilityNode,
    AbilityTree,
    CharacterAbilityState,
    TargetType,
)
from ability_manager import AbilityManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fire_tree() -> AbilityTree:
    tree = AbilityTree(
        id="fire_magic_abilities",
        name="Fire Magic Abilities",
        description="Test fire abilities.",
    )
    tree.add_node(AbilityNode(
        id="fire_ability.root",
        name="Spark",
        description="Ignite basics.",
        ability_id="fire.fireball",
        category=AbilityCategory.MAGIC,
        node_type="root",
        max_rank=1,
        point_cost=1,
        stat_costs={"intelligence": 10},
        prerequisites=[],
        parent_ids=[],
    ))
    tree.add_node(AbilityNode(
        id="fire_ability.inferno",
        name="Inferno Channel",
        description="Channel flame.",
        ability_id="fire.inferno",
        category=AbilityCategory.MAGIC,
        node_type="branch",
        max_rank=1,
        point_cost=2,
        stat_costs={"intelligence": 16},
        prerequisites=[{"kind": "skill", "target": "fire.fireball", "minimum": 2}],
        parent_ids=["fire_ability.root"],
    ))
    tree._link_children()
    return tree


def _make_fireball_ability() -> Ability:
    return Ability(
        id="fire.fireball",
        name="Fireball",
        description="A searing explosion.",
        category=AbilityCategory.MAGIC,
        target_type=TargetType.AOE,
        mana_cost=25,
        cooldown_seconds=8.0,
        effects=[
            AbilityEffect(effect_type="damage", value=35, chance=1.0),
            AbilityEffect(effect_type="dot", value=8, duration_seconds=5.0, chance=0.75),
        ],
        skill_tree_ids=["fire.fireball"],
    )


# ---------------------------------------------------------------------------
# AbilityEffect tests
# ---------------------------------------------------------------------------

class TestAbilityEffect:
    def test_to_from_dict_roundtrip(self):
        effect = AbilityEffect(
            effect_type="damage",
            value=35,
            duration_seconds=5.0,
            chance=0.8,
            extra={"armor_penetration": 10},
        )
        data = effect.to_dict()
        restored = AbilityEffect.from_dict(data)
        assert restored.effect_type == "damage"
        assert restored.value == 35
        assert restored.duration_seconds == 5.0
        assert restored.chance == 0.8
        assert restored.extra == {"armor_penetration": 10}

    def test_default_values(self):
        effect = AbilityEffect(effect_type="heal")
        assert effect.value == 0
        assert effect.duration_seconds == 0.0
        assert effect.chance == 1.0
        assert effect.extra == {}


# ---------------------------------------------------------------------------
# Ability tests
# ---------------------------------------------------------------------------

class TestAbility:
    def test_to_from_dict_roundtrip(self):
        ability = _make_fireball_ability()
        data = ability.to_dict()
        restored = Ability.from_dict(data)
        assert restored.id == "fire.fireball"
        assert restored.mana_cost == 25
        assert restored.cooldown_seconds == 8.0
        assert len(restored.effects) == 2
        assert restored.effects[0].effect_type == "damage"

    def test_to_from_dict_with_cooldown_group(self):
        ability = Ability(
            id="fire.meteor", name="Meteor",
            cooldown_seconds=45.0, cooldown_group="fire",
            global_cooldown_seconds=1.0,
        )
        data = ability.to_dict()
        restored = Ability.from_dict(data)
        assert restored.cooldown_group == "fire"
        assert restored.global_cooldown_seconds == 1.0

    def test_default_values(self):
        ability = Ability(id="test", name="Test")
        assert ability.description == ""
        assert ability.mana_cost == 0
        assert ability.cooldown_seconds == 0.0
        assert ability.effects == []
        assert ability.skill_tree_ids == []


# ---------------------------------------------------------------------------
# AbilityNode tests
# ---------------------------------------------------------------------------

class TestAbilityNode:
    def test_to_from_dict_roundtrip(self):
        node = AbilityNode(
            id="test.node",
            name="Test Node",
            ability_id="test.ability",
            category=AbilityCategory.MAGIC,
            node_type="branch",
            max_rank=2,
            point_cost=3,
            stat_costs={"intelligence": 12},
            prerequisites=[{"kind": "skill", "target": "other.node", "minimum": 1}],
            parent_ids=["parent.node"],
        )
        data = node.to_dict()
        restored = AbilityNode.from_dict(data)
        assert restored.id == "test.node"
        assert restored.ability_id == "test.ability"
        assert restored.category == AbilityCategory.MAGIC
        assert restored.node_type == "branch"
        assert restored.max_rank == 2
        assert restored.point_cost == 3
        assert restored.stat_costs == {"intelligence": 12}
        assert len(restored.prerequisites) == 1
        assert restored.parent_ids == ["parent.node"]

    def test_default_values(self):
        node = AbilityNode(id="a", name="A", ability_id="b")
        assert node.description == ""
        assert node.max_rank == 1
        assert node.point_cost == 1
        assert node.prerequisites == []
        assert node.parent_ids == []


# ---------------------------------------------------------------------------
# AbilityTree tests
# ---------------------------------------------------------------------------

class TestAbilityTree:
    def test_add_and_get_node(self):
        tree = _fire_tree()
        assert tree.get_node("fire_ability.root") is not None
        assert tree.get_node("nonexistent") is None

    def test_root_id_set(self):
        tree = _fire_tree()
        assert tree.root_id == "fire_ability.root"

    def test_children_linked(self):
        tree = _fire_tree()
        root = tree.get_node("fire_ability.root")
        assert "fire_ability.inferno" in root.children

    def test_get_children(self):
        tree = _fire_tree()
        children = tree.get_children("fire_ability.root")
        assert len(children) == 1
        assert children[0].id == "fire_ability.inferno"

    def test_available_with_no_points(self):
        tree = _fire_tree()
        state = CharacterAbilityState(character_id="c1", available_points=0, attributes={"intelligence": 20})
        available = tree.get_available_nodes(state)
        ids = [n.id for n in available]
        assert "fire_ability.root" not in ids

    def test_available_after_points(self):
        tree = _fire_tree()
        state = CharacterAbilityState(
            character_id="c1",
            available_points=5,
            attributes={"intelligence": 20},
            level=1,
        )
        available = tree.get_available_nodes(state)
        ids = [n.id for n in available]
        assert "fire_ability.root" in ids
        assert "fire_ability.inferno" not in ids

    def test_prereq_not_met(self):
        tree = _fire_tree()
        state = CharacterAbilityState(
            character_id="c1",
            available_points=10,
            attributes={"intelligence": 10},  # below inferno's 16
            level=1,
        )
        state.unlock("fire_ability.root", tree)
        available = tree.get_available_nodes(state)
        ids = [n.id for n in available]
        assert "fire_ability.inferno" not in ids


# ---------------------------------------------------------------------------
# CharacterAbilityState tests
# ---------------------------------------------------------------------------

class TestCharacterAbilityState:
    def test_unlock_and_rank(self):
        tree = _fire_tree()
        state = CharacterAbilityState(
            character_id="c1",
            available_points=10,
            attributes={"intelligence": 20},
            level=1,
        )
        assert state.unlock("fire_ability.root", tree)[0] is True
        assert state.unlocked_ability_nodes["fire_ability.root"] == 1
        ok, reason = state.unlock("fire_ability.root", tree)
        assert ok is False
        assert "max rank" in reason.lower()

    def test_spent_and_remaining_points(self):
        tree = _fire_tree()
        state = CharacterAbilityState(
            character_id="c1",
            available_points=10,
            attributes={"intelligence": 20},
            level=1,
        )
        state.unlock("fire_ability.root", tree)  # cost 1, remaining 9
        assert state.spent_points(tree) == 1
        assert state.remaining_points(tree) == 9

    def test_refund(self):
        tree = _fire_tree()
        state = CharacterAbilityState(
            character_id="c1",
            available_points=10,
            attributes={"intelligence": 20},
            level=1,
        )
        state.unlock("fire_ability.root", tree)
        assert state.unlocked_ability_nodes["fire_ability.root"] == 1
        ok, reason = state.refund("fire_ability.root", tree)
        assert ok is True
        assert "fire_ability.root" not in state.unlocked_ability_nodes

    def test_refund_blocked_by_dependency(self):
        tree = _fire_tree()
        state = CharacterAbilityState(
            character_id="c1",
            available_points=10,
            attributes={"intelligence": 20},
            level=1,
            skill_ranks={"fire.fireball": 2},
        )
        state.unlock("fire_ability.root", tree)
        state.unlock("fire_ability.inferno", tree)
        # Cannot refund root because inferno depends on it
        ok, reason = state.refund("fire_ability.root", tree)
        assert ok is False
        assert "required by" in reason.lower()

    def test_mana_and_cooldown(self):
        ability = _make_fireball_ability()
        state = CharacterAbilityState(character_id="c1", mana=50, max_mana=100)
        now = 1000.0
        ok, reason = state.can_use_ability(ability, now)
        assert ok is True
        ok, reason = state.use_ability(ability, now)
        assert ok is True
        assert state.mana == 25
        assert state.is_on_cooldown("fire.fireball", now + 1.0)
        remaining = state.get_cooldown_remaining("fire.fireball", now + 1.0)
        assert 6.9 <= remaining <= 7.9  # roughly 8s cooldown

    def test_use_ability_not_enough_mana(self):
        ability = _make_fireball_ability()
        state = CharacterAbilityState(character_id="c1", mana=10, max_mana=100)
        now = 1000.0
        ok, reason = state.use_ability(ability, now)
        assert ok is False
        assert "mana" in reason.lower()

    def test_group_cooldown_blocks_use(self):
        fireball = Ability(
            id="fire.fireball", name="Fireball", mana_cost=25,
            cooldown_seconds=8.0, cooldown_group="fire",
        )
        inferno = Ability(
            id="fire.inferno", name="Inferno", mana_cost=45,
            cooldown_seconds=18.0, cooldown_group="fire",
        )
        state = CharacterAbilityState(character_id="c1", mana=100, max_mana=100)
        now = 1000.0
        ok, reason = state.use_ability(fireball, now)
        assert ok is True
        ok, reason = state.use_ability(inferno, now + 1.0)
        assert ok is False
        assert "group" in reason.lower() and "cooldown" in reason.lower()

    def test_different_groups_independent(self):
        fireball = Ability(
            id="fire.fireball", name="Fireball", mana_cost=25,
            cooldown_seconds=8.0, cooldown_group="fire",
        )
        shadow = Ability(
            id="st.shadow_step", name="Shadow Step", mana_cost=15,
            cooldown_seconds=12.0, cooldown_group="stealth",
        )
        state = CharacterAbilityState(character_id="c1", mana=100, max_mana=100)
        now = 1000.0
        state.use_ability(fireball, now)
        ok, reason = state.use_ability(shadow, now + 1.0)
        assert ok is True

    def test_global_cooldown_blocks_use(self):
        fireball = Ability(
            id="fire.fireball", name="Fireball", mana_cost=25,
            cooldown_seconds=0.0, global_cooldown_seconds=2.0,
        )
        state = CharacterAbilityState(character_id="c1", mana=100, max_mana=100)
        now = 1000.0
        ok, reason = state.use_ability(fireball, now)
        assert ok is True
        ok, reason = state.use_ability(fireball, now + 0.5)
        assert ok is False
        assert "cooldown" in reason.lower()
        ok, reason = state.use_ability(fireball, now + 2.5)
        assert ok is True


# ---------------------------------------------------------------------------
# AbilityManager integration tests
# ---------------------------------------------------------------------------

class TestAbilityManager:
    def test_list_trees(self):
        mgr = AbilityManager()
        ids = [t["id"] for t in mgr.list_trees()]
        assert "fire_magic_abilities" in ids
        assert "combat_abilities" in ids
        assert "stealth_abilities" in ids

    def test_full_unlock_flow(self):
        mgr = AbilityManager()
        mgr.set_attributes("hero", {"intelligence": 22, "strength": 16, "dexterity": 14})
        mgr.set_level("hero", 16)
        mgr.grant_ability_points("hero", 50)
        mgr.set_mana("hero", 200, 200)
        mgr.set_skill_ranks("hero", {
            "fire.root": 1,
            "fire.fireball": 3,
            "fire.inferno": 1,
            "thc.root": 1,
            "thc.cleave": 3,
            "st.root": 1,
        })

        # Unlock fire root ability
        r = mgr.unlock_ability_node("hero", "fire_magic_abilities", "fire_ability.root")
        assert r["success"] is True

        # Unlock inferno
        r = mgr.unlock_ability_node("hero", "fire_magic_abilities", "fire_ability.inferno")
        assert r["success"] is True

        # Unlock meteor (needs level 15, fireball 3, inferno 1)
        r = mgr.unlock_ability_node("hero", "fire_magic_abilities", "fire_ability.meteor")
        assert r["success"] is True

        # Summary
        summary = mgr.get_character_ability_summary("hero", "fire_magic_abilities")
        assert summary["spent_points"] == 1 + 2 + 4
        assert len(summary["unlocked_abilities"]) == 3

    def test_combat_integration(self):
        mgr = AbilityManager()
        mgr.set_mana("warrior", 50, 100)
        now = time.time()

        r = mgr.use_ability("warrior", "fire.fireball", now)
        assert r["success"] is True
        assert r["mana_remaining"] == 25
        assert r["cooldown_until"] > now

        # Can't use again immediately
        ok, reason = mgr.can_use("warrior", "fire.fireball", now + 1.0)
        assert ok is False
        assert "cooldown" in reason.lower()

        # Use after cooldown
        ok, reason = mgr.can_use("warrior", "fire.fireball", now + 10.0)
        assert ok is True

    def test_refund_flow(self):
        mgr = AbilityManager()
        mgr.set_attributes("rogue", {"dexterity": 16, "intelligence": 10})
        mgr.grant_ability_points("rogue", 10)
        mgr.set_skill_ranks("rogue", {"st.root": 1})

        r = mgr.unlock_ability_node("rogue", "stealth_abilities", "stealth_ability.shadow_step")
        assert r["success"] is True

        r = mgr.refund_ability_node("rogue", "stealth_abilities", "stealth_ability.shadow_step")
        assert r["success"] is True
        summary = mgr.get_character_ability_summary("rogue", "stealth_abilities")
        assert summary["spent_points"] == 0


if __name__ == "__main__":
    import traceback

    suites = [
        TestAbilityEffect,
        TestAbility,
        TestAbilityNode,
        TestAbilityTree,
        TestCharacterAbilityState,
        TestAbilityManager,
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
