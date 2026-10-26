"""
Tests for RPG-08-05 Skill Tree System.
Run with: python -m pytest tests/ -v
or:       python tests/test_skill_tree.py
"""

from __future__ import annotations

import os
import sys

# Allow running from the repo root or the tests/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from skill_tree import (
    CharacterSkillState,
    NodeType,
    Prerequisite,
    SkillCategory,
    SkillNode,
    SkillTree,
)
from skill_tree_builder import build_tree, load_tree_from_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _thc_tree() -> SkillTree:
    return build_tree({
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
                "effects": {"weapon_damage_bonus": 5},
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
                "effects": {"extra_targets": 1},
                "parent_ids": ["thc.root"],
            },
            {
                "id": "thc.capstone",
                "name": "Mighty Blow",
                "category": "combat",
                "node_type": "capstone",
                "max_rank": 1,
                "point_cost": 4,
                "stat_costs": {"strength": 18},
                "prerequisites": [
                    {"kind": "skill", "target": "thc.cleave", "minimum": 3},
                    {"kind": "level", "target": "level", "minimum": 10},
                ],
                "effects": {"damage_multiplier": 2.0},
                "parent_ids": ["thc.cleave"],
            },
        ],
    })


def _stealth_tree() -> SkillTree:
    return build_tree({
        "id": "shadow_stealth",
        "name": "Shadow & Stealth",
        "nodes": [
            {
                "id": "stealth.root",
                "name": "Shadow Step",
                "category": "stealth",
                "node_type": "root",
                "max_rank": 1,
                "point_cost": 1,
                "stat_costs": {"dexterity": 12},
                "prerequisites": [],
                "effects": {"stealth_bonus": 10},
                "parent_ids": [],
            },
            {
                "id": "stealth.backstab",
                "name": "Backstab",
                "category": "stealth",
                "node_type": "branch",
                "max_rank": 3,
                "point_cost": 2,
                "stat_costs": {"dexterity": 14},
                "prerequisites": [{"kind": "skill", "target": "stealth.root", "minimum": 1}],
                "effects": {"critical_chance_bonus": 15},
                "parent_ids": ["st.root"],
            },
        ],
    })


# ---------------------------------------------------------------------------
# SkillNode tests
# ---------------------------------------------------------------------------

class TestSkillNode:
    def test_to_from_dict_roundtrip(self):
        node = SkillNode(
            id="test.x",
            name="Test",
            category=SkillCategory.MAGIC,
            node_type=NodeType.LEAF,
            max_rank=2,
            point_cost=3,
            stat_costs={"intelligence": 10},
            prerequisites=[Prerequisite(kind="skill", target="other.y", minimum=1)],
            effects={"damage": 50},
            parent_ids=["parent.z"],
        )
        data = node.to_dict()
        restored = SkillNode.from_dict(data)
        assert restored.id == "test.x"
        assert restored.category == SkillCategory.MAGIC
        assert restored.node_type == NodeType.LEAF
        assert restored.max_rank == 2
        assert restored.point_cost == 3
        assert restored.stat_costs == {"intelligence": 10}
        assert len(restored.prerequisites) == 1
        assert restored.prerequisites[0].target == "other.y"
        assert restored.effects == {"damage": 50}
        assert restored.parent_ids == ["parent.z"]

    def test_default_values(self):
        node = SkillNode(id="a", name="A")
        assert node.description == ""
        assert node.max_rank == 1
        assert node.point_cost == 1
        assert node.prerequisites == []
        assert node.effects == {}
        assert node.parent_ids == []


# ---------------------------------------------------------------------------
# SkillTree tests
# ---------------------------------------------------------------------------

class TestSkillTree:
    def test_add_and_get_node(self):
        tree = _thc_tree()
        assert tree.get_node("thc.root") is not None
        assert tree.get_node("nonexistent") is None

    def test_root_id_set(self):
        tree = _thc_tree()
        assert tree.root_id == "thc.root"

    def test_children_linked(self):
        tree = _thc_tree()
        root = tree.get_node("thc.root")
        assert "thc.cleave" in root.children

    def test_get_children(self):
        tree = _thc_tree()
        children = tree.get_children("thc.root")
        assert len(children) == 1
        assert children[0].id == "thc.cleave"

    def test_get_available_with_no_points(self):
        tree = _thc_tree()
        state = CharacterSkillState(character_id="c1", available_points=0, attributes={"strength": 20})
        # root costs 1 point, we have 0 → not available
        available = tree.get_available_nodes(state)
        ids = [n.id for n in available]
        assert "thc.root" not in ids

    def test_available_after_points(self):
        tree = _thc_tree()
        state = CharacterSkillState(
            character_id="c1",
            available_points=5,
            attributes={"strength": 20},
            level=1,
        )
        available = tree.get_available_nodes(state)
        ids = [n.id for n in available]
        assert "thc.root" in ids
        # cleave requires thc.root rank 1, so not available yet
        assert "thc.cleave" not in ids

    def test_available_after_unlock_root(self):
        tree = _thc_tree()
        state = CharacterSkillState(
            character_id="c1",
            available_points=5,
            attributes={"strength": 20},
            level=1,
        )
        state.unlock("thc.root", tree)
        available = tree.get_available_nodes(state)
        ids = [n.id for n in available]
        assert "thc.cleave" in ids

    def test_prereq_not_met(self):
        tree = _thc_tree()
        state = CharacterSkillState(
            character_id="c1",
            available_points=10,
            attributes={"strength": 10},  # below cleave's 12
            level=1,
        )
        state.unlock("thc.root", tree)
        available = tree.get_available_nodes(state)
        ids = [n.id for n in available]
        assert "thc.cleave" not in ids

    def test_level_gate(self):
        tree = _thc_tree()
        state = CharacterSkillState(
            character_id="c1",
            available_points=20,
            attributes={"strength": 20},
            level=9,  # below capstone requirement
        )
        state.unlock("thc.root", tree)
        # Simulate cleave at rank 3
        for _ in range(3):
            state.unlock("thc.cleave", tree)
        available = tree.get_available_nodes(state)
        ids = [n.id for n in available]
        assert "thc.capstone" not in ids

        state.level = 10
        available = tree.get_available_nodes(state)
        ids = [n.id for n in available]
        assert "thc.capstone" in ids


# ---------------------------------------------------------------------------
# CharacterSkillState tests
# ---------------------------------------------------------------------------

class TestCharacterSkillState:
    def test_unlock_and_rank(self):
        tree = _thc_tree()
        state = CharacterSkillState(
            character_id="c1",
            available_points=10,
            attributes={"strength": 20},
            level=1,
        )
        assert state.unlock("thc.root", tree)[0] is True
        assert state.unlocked_nodes["thc.root"] == 1
        # Root max_rank=1, second unlock should fail
        ok, reason = state.unlock("thc.root", tree)
        assert ok is False
        assert "max rank" in reason.lower()

    def test_spent_and_remaining_points(self):
        tree = _thc_tree()
        state = CharacterSkillState(
            character_id="c1",
            available_points=10,
            attributes={"strength": 20},
            level=1,
        )
        state.unlock("thc.root", tree)  # cost 1, remaining 9
        assert state.spent_points(tree) == 1
        assert state.remaining_points(tree) == 9

    def test_refund(self):
        tree = _thc_tree()
        state = CharacterSkillState(
            character_id="c1",
            available_points=10,
            attributes={"strength": 20},
            level=1,
        )
        state.unlock("thc.root", tree)
        assert state.unlocked_nodes["thc.root"] == 1
        ok, reason = state.refund("thc.root", tree)
        assert ok is True
        assert "thc.root" not in state.unlocked_nodes

    def test_refund_blocked_by_dependency(self):
        tree = _thc_tree()
        state = CharacterSkillState(
            character_id="c1",
            available_points=20,
            attributes={"strength": 20},
            level=1,
        )
        state.unlock("thc.root", tree)
        state.unlock("thc.cleave", tree)
        # Cannot refund root because cleave depends on it
        ok, reason = state.refund("thc.root", tree)
        assert ok is False
        assert "required by" in reason.lower()

    def test_can_unlock_details(self):
        tree = _thc_tree()
        state = CharacterSkillState(
            character_id="c1",
            available_points=0,
            attributes={"strength": 20},
            level=1,
        )
        # No points → detail should mention points
        ok, reason = state.can_unlock(tree.get_node("thc.root"), tree)
        assert ok is False
        assert "points" in reason.lower()


# ---------------------------------------------------------------------------
# Builder / JSON tests
# ---------------------------------------------------------------------------

class TestBuilder:
    def test_load_two_handed_combat_json(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "data", "two_handed_combat.json"
        )
        tree = load_tree_from_json(path)
        assert tree.id == "two_handed_combat"
        assert tree.root_id == "thc.root"
        assert len(tree.nodes) == 6
        # Verify children were linked
        root = tree.get_node("thc.root")
        child_ids = [c.id for c in tree.get_children("thc.root")]
        assert "thc.cleave" in child_ids
        assert "thc.execute" in child_ids

    def test_load_fire_magic_json(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "data", "fire_magic.json"
        )
        tree = load_tree_from_json(path)
        assert tree.id == "fire_magic"
        assert tree.root_id == "fire.root"
        assert len(tree.nodes) == 5

    def test_load_shadow_stealth_json(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "data", "shadow_stealth.json"
        )
        tree = load_tree_from_json(path)
        assert tree.id == "shadow_stealth"
        assert tree.root_id == "stealth.root"
        assert len(tree.nodes) == 5


# ---------------------------------------------------------------------------
# Manager integration tests
# ---------------------------------------------------------------------------

class TestManager:
    def test_list_trees(self):
        from skill_tree_manager import SkillTreeManager
        mgr = SkillTreeManager()
        ids = [t["id"] for t in mgr.list_trees()]
        assert "two_handed_combat" in ids
        assert "fire_magic" in ids
        assert "shadow_stealth" in ids

    def test_full_unlock_flow(self):
        from skill_tree_manager import SkillTreeManager
        mgr = SkillTreeManager()
        mgr.set_attributes("hero", {"strength": 20, "intelligence": 10, "dexterity": 10})
        mgr.set_level("hero", 11)
        mgr.grant_points("hero", 50)

        # Unlock root
        r = mgr.unlock_node("hero", "two_handed_combat", "thc.root")
        assert r["success"] is True

        # Unlock cleave x3
        for _ in range(3):
            r = mgr.unlock_node("hero", "two_handed_combat", "thc.cleave")
            assert r["success"] is True

        # Unlock capstone (needs level 10)
        r = mgr.unlock_node("hero", "two_handed_combat", "thc.mighty_blow")
        assert r["success"] is True

        # Check summary
        summary = mgr.get_character_summary("hero", "two_handed_combat")
        assert summary["spent_points"] == 1 + 3 * 2 + 4
        assert len(summary["unlocked_skills"]) == 3

    def test_refund_flow(self):
        from skill_tree_manager import SkillTreeManager
        mgr = SkillTreeManager()
        mgr.set_attributes("hero2", {"strength": 20, "dexterity": 14, "agility": 10})
        mgr.grant_points("hero2", 10)
        mgr.unlock_node("hero2", "shadow_stealth", "stealth.root")
        mgr.unlock_node("hero2", "shadow_stealth", "stealth.backstab")
        summary_before = mgr.get_character_summary("hero2", "shadow_stealth")
        assert summary_before["spent_points"] == 1 + 2

        r = mgr.refund_node("hero2", "shadow_stealth", "stealth.backstab")
        assert r["success"] is True
        summary_after = mgr.get_character_summary("hero2", "shadow_stealth")
        assert summary_after["spent_points"] == 1


if __name__ == "__main__":
    import traceback
    suites = [
        TestSkillNode,
        TestSkillTree,
        TestCharacterSkillState,
        TestBuilder,
        TestManager,
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
