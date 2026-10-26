"""
Builder for constructing SkillTree instances from JSON data files.
"""

from __future__ import annotations

import json
import os
from typing import Any

from skill_tree import (
    NodeType,
    Prerequisite,
    SkillCategory,
    SkillNode,
    SkillTree,
)


def load_tree_from_json(path: str) -> SkillTree:
    """Load a single skill tree definition from a JSON file."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return build_tree(data)


def build_tree(data: dict[str, Any]) -> SkillTree:
    """
    Construct a SkillTree from a raw dict (loaded from JSON or similar).

    JSON format:
    {
      "id": "...",
      "name": "...",
      "description": "...",
      "nodes": [
        {
          "id": "...",
          "name": "...",
          "description": "...",
          "category": "combat",
          "node_type": "root|branch|leaf|capstone",
          "max_rank": 1,
          "point_cost": 1,
          "stat_costs": {},
          "prerequisites": [{"kind": "skill", "target": "...", "minimum": 1}],
          "effects": {},
          "parent_ids": []
        }
      ]
    }
    """
    tree = SkillTree(
        id=data["id"],
        name=data.get("name", data["id"]),
        description=data.get("description", ""),
    )

    for node_data in data.get("nodes", []):
        node = SkillNode(
            id=node_data["id"],
            name=node_data["name"],
            description=node_data.get("description", ""),
            category=SkillCategory(node_data.get("category", "combat")),
            node_type=NodeType(node_data.get("node_type", "leaf")),
            max_rank=node_data.get("max_rank", 1),
            point_cost=node_data.get("point_cost", 1),
            stat_costs=node_data.get("stat_costs", {}),
            prerequisites=[
                Prerequisite(kind=p["kind"], target=p["target"], minimum=p.get("minimum", 1))
                for p in node_data.get("prerequisites", [])
            ],
            effects=node_data.get("effects", {}),
            parent_ids=node_data.get("parent_ids", []),
        )
        tree.add_node(node)

    tree._link_children()
    return tree


def load_all_trees(directory: str) -> dict[str, SkillTree]:
    """Load every .json file in `directory` as a SkillTree, keyed by tree id.

    Skips files that are not skill-tree definitions (missing top-level "id").
    """
    trees: dict[str, SkillTree] = {}
    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(directory, filename)
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        if "id" not in data:
            continue
        try:
            tree = load_tree_from_json(path)
            trees[tree.id] = tree
        except Exception:
            continue
    return trees
