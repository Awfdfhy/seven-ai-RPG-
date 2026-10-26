"""
RPG-08-05: Skill Tree System
Top-level orchestrator: loads all tree definitions and exposes a simple
API for character skill management.
"""

from __future__ import annotations

import os
from typing import Any

from skill_tree import CharacterSkillState, SkillTree
from skill_tree_builder import load_all_trees


class SkillTreeManager:
    """
    Singleton-style manager that loads all skill tree data files
    and provides methods for character skill interaction.
    """

    def __init__(self, data_directory: str | None = None) -> None:
        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self.trees: dict[str, SkillTree] = load_all_trees(data_directory)
        self.character_states: dict[str, CharacterSkillState] = {}

    def get_tree(self, tree_id: str) -> SkillTree | None:
        return self.trees.get(tree_id)

    def list_trees(self) -> list[dict[str, Any]]:
        return [
            {"id": t.id, "name": t.name, "description": t.description}
            for t in self.trees.values()
        ]

    def get_character_state(self, character_id: str) -> CharacterSkillState:
        if character_id not in self.character_states:
            self.character_states[character_id] = CharacterSkillState(character_id=character_id)
        return self.character_states[character_id]

    def grant_points(self, character_id: str, points: int) -> None:
        state = self.get_character_state(character_id)
        state.available_points += points

    def set_attributes(self, character_id: str, attributes: dict[str, int]) -> None:
        state = self.get_character_state(character_id)
        state.attributes.update(attributes)

    def set_level(self, character_id: str, level: int) -> None:
        state = self.get_character_state(character_id)
        state.level = level

    def get_available_nodes(self, character_id: str, tree_id: str) -> list[dict[str, Any]]:
        tree = self.get_tree(tree_id)
        if tree is None:
            return []
        state = self.get_character_state(character_id)
        nodes = tree.get_available_nodes(state)
        return [
            {
                "id": n.id,
                "name": n.name,
                "description": n.description,
                "node_type": n.node_type.value,
                "max_rank": n.max_rank,
                "point_cost": n.point_cost,
                "current_rank": state.unlocked_nodes.get(n.id, 0),
            }
            for n in nodes
        ]

    def unlock_node(self, character_id: str, tree_id: str, node_id: str) -> dict[str, Any]:
        tree = self.get_tree(tree_id)
        if tree is None:
            return {"success": False, "reason": f"Tree '{tree_id}' not found."}
        state = self.get_character_state(character_id)
        ok, reason = state.unlock(node_id, tree)
        if ok:
            node = tree.get_node(node_id)
            return {
                "success": True,
                "node_id": node_id,
                "new_rank": state.unlocked_nodes.get(node_id, 0),
                "remaining_points": state.remaining_points(tree),
                "effects": node.effects if node else {},
            }
        return {"success": False, "reason": reason}

    def refund_node(self, character_id: str, tree_id: str, node_id: str) -> dict[str, Any]:
        tree = self.get_tree(tree_id)
        if tree is None:
            return {"success": False, "reason": f"Tree '{tree_id}' not found."}
        state = self.get_character_state(character_id)
        ok, reason = state.refund(node_id, tree)
        if ok:
            return {
                "success": True,
                "node_id": node_id,
                "remaining_points": state.remaining_points(tree),
            }
        return {"success": False, "reason": reason}

    def get_character_summary(self, character_id: str, tree_id: str) -> dict[str, Any]:
        tree = self.get_tree(tree_id)
        if tree is None:
            return {"error": f"Tree '{tree_id}' not found."}
        state = self.get_character_state(character_id)
        unlocked = []
        for nid, rank in state.unlocked_nodes.items():
            node = tree.get_node(nid)
            if node:
                unlocked.append({
                    "node_id": nid,
                    "name": node.name,
                    "rank": rank,
                    "max_rank": node.max_rank,
                    "effects": node.effects,
                })
        return {
            "character_id": character_id,
            "tree_id": tree_id,
            "tree_name": tree.name,
            "level": state.level,
            "available_points": state.available_points,
            "spent_points": state.spent_points(tree),
            "remaining_points": state.remaining_points(tree),
            "unlocked_skills": unlocked,
        }
