"""
RPG-10-01: Ability System
Top-level orchestrator: loads ability tree definitions and exposes a simple
API for character ability management, integrating with skill trees and combat.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from ability import (
    Ability,
    AbilityTree,
    CharacterAbilityState,
)


class AbilityManager:
    """
    Singleton-style manager that loads all ability tree data files
    and provides methods for character ability interaction.
    """

    def __init__(self, data_directory: str | None = None) -> None:
        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self.ability_trees: dict[str, AbilityTree] = self._load_ability_trees(data_directory)
        self.abilities: dict[str, Ability] = {}
        self.character_states: dict[str, CharacterAbilityState] = {}
        self._load_abilities_from_data(data_directory)

    @staticmethod
    def _load_ability_trees(directory: str) -> dict[str, AbilityTree]:
        trees: dict[str, AbilityTree] = {}
        if not os.path.isdir(directory):
            return trees
        for filename in os.listdir(directory):
            if filename == "abilities.json":
                path = os.path.join(directory, filename)
                try:
                    with open(path, encoding="utf-8") as fh:
                        data = json.load(fh)
                    for tree_data in data.get("trees", []):
                        tree = AbilityTree.from_dict(tree_data)
                        trees[tree.id] = tree
                except Exception:
                    pass
        return trees

    def _load_abilities_from_data(self, directory: str) -> None:
        """Auto-load abilities from abilities.json if present."""
        if not os.path.isdir(directory):
            return
        path = os.path.join(directory, "abilities.json")
        if not os.path.isfile(path):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            for ability_data in data.get("abilities", []):
                ability = Ability.from_dict(ability_data)
                self.abilities[ability.id] = ability
        except Exception:
            pass

    def register(self, ability: Ability) -> None:
        """Register an ability definition into the manager."""
        self.abilities[ability.id] = ability

    def load_abilities_from_json(self, path: str) -> None:
        """Load a standalone abilities definition file (ability id -> ability)."""
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for ability_data in data.get("abilities", []):
            ability = Ability.from_dict(ability_data)
            self.abilities[ability.id] = ability

    def get_ability(self, ability_id: str) -> Ability | None:
        return self.abilities.get(ability_id)

    def get_tree(self, tree_id: str) -> AbilityTree | None:
        return self.ability_trees.get(tree_id)

    def list_trees(self) -> list[dict[str, Any]]:
        return [
            {"id": t.id, "name": t.name, "description": t.description}
            for t in self.ability_trees.values()
        ]

    def get_character_state(self, character_id: str) -> CharacterAbilityState:
        if character_id not in self.character_states:
            self.character_states[character_id] = CharacterAbilityState(character_id=character_id)
        return self.character_states[character_id]

    def grant_ability_points(self, character_id: str, points: int) -> None:
        state = self.get_character_state(character_id)
        state.available_points += points

    def grant_ability(self, character_id: str, ability_id: str) -> dict[str, Any]:
        """Grant an ability to a character if it is registered."""
        if ability_id not in self.abilities:
            return {"success": False, "reason": f"Ability '{ability_id}' not found."}
        state = self.get_character_state(character_id)
        state.unlocked_ability_nodes[ability_id] = 1
        state.ability_ranks[ability_id] = 1
        return {"success": True, "ability_id": ability_id}

    def set_mana(self, character_id: str, mana: int, max_mana: int) -> None:
        state = self.get_character_state(character_id)
        state.mana = mana
        state.max_mana = max_mana

    def set_attributes(self, character_id: str, attributes: dict[str, int]) -> None:
        state = self.get_character_state(character_id)
        state.attributes.update(attributes)

    def set_level(self, character_id: str, level: int) -> None:
        state = self.get_character_state(character_id)
        state.level = level

    def set_skill_ranks(self, character_id: str, skill_ranks: dict[str, int]) -> None:
        """Sync skill ranks from the skill tree system."""
        state = self.get_character_state(character_id)
        state.skill_ranks.update(skill_ranks)

    def get_available_ability_nodes(self, character_id: str, tree_id: str) -> list[dict[str, Any]]:
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
                "node_type": n.node_type,
                "max_rank": n.max_rank,
                "point_cost": n.point_cost,
                "ability_id": n.ability_id,
                "current_rank": state.unlocked_ability_nodes.get(n.id, 0),
            }
            for n in nodes
        ]

    def unlock_ability_node(self, character_id: str, tree_id: str, node_id: str) -> dict[str, Any]:
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
                "ability_id": node.ability_id if node else "",
                "new_rank": state.unlocked_ability_nodes.get(node_id, 0),
                "remaining_points": state.remaining_points(tree),
            }
        return {"success": False, "reason": reason}

    def refund_ability_node(self, character_id: str, tree_id: str, node_id: str) -> dict[str, Any]:
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

    def get_character_ability_summary(self, character_id: str, tree_id: str) -> dict[str, Any]:
        tree = self.get_tree(tree_id)
        if tree is None:
            return {"error": f"Tree '{tree_id}' not found."}
        state = self.get_character_state(character_id)
        unlocked = []
        for nid, rank in state.unlocked_ability_nodes.items():
            node = tree.get_node(nid)
            if node:
                ability = self.abilities.get(node.ability_id)
                unlocked.append({
                    "node_id": nid,
                    "name": node.name,
                    "rank": rank,
                    "max_rank": node.max_rank,
                    "ability_id": node.ability_id,
                    "ability_name": ability.name if ability else node.ability_id,
                })
        return {
            "character_id": character_id,
            "tree_id": tree_id,
            "tree_name": tree.name,
            "level": state.level,
            "available_points": state.available_points,
            "spent_points": state.spent_points(tree),
            "remaining_points": state.remaining_points(tree),
            "mana": state.mana,
            "max_mana": state.max_mana,
            "unlocked_abilities": unlocked,
        }

    # --- combat integration -------------------------------------------------

    def can_use(self, character_id: str, ability_id: str, current_time: float | None = None) -> tuple[bool, str]:
        if current_time is None:
            current_time = time.time()
        ability = self.abilities.get(ability_id)
        if ability is None:
            return False, f"Ability '{ability_id}' not found."
        state = self.get_character_state(character_id)
        return state.can_use_ability(ability, current_time)

    def use_ability(self, character_id: str, ability_id: str, current_time: float | None = None) -> dict[str, Any]:
        if current_time is None:
            current_time = time.time()
        ability = self.abilities.get(ability_id)
        if ability is None:
            return {"success": False, "reason": f"Ability '{ability_id}' not found."}
        state = self.get_character_state(character_id)
        ok, reason = state.use_ability(ability, current_time)
        if ok:
            return {
                "success": True,
                "ability_id": ability_id,
                "mana_remaining": state.mana,
                "cooldown_until": state.cooldown_manager.get_cooldown_ready_at(ability_id),
                "effects": [e.to_dict() for e in ability.effects],
            }
        return {"success": False, "reason": reason}
