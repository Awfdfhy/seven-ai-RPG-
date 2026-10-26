"""
RPG-08-05: Skill Tree System
Core data model for skills, nodes, trees, and character skill state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SkillCategory(Enum):
    """Broad category buckets for grouping skills."""

    COMBAT = "combat"
    MAGIC = "magic"
    STEALTH = "stealth"
    SURVIVAL = "survival"
    SOCIAL = "social"


class NodeType(Enum):
    """Structural role of a node inside a skill tree."""

    ROOT = "root"           # Starting node; no prerequisites.
    BRANCH = "branch"       # Mid-tree gate/choice node.
    LEAF = "leaf"           # Terminal skill node.
    CAPSTONE = "capstone"   # High-tier endpoint requiring a full path.


@dataclass
class Prerequisite:
    """
    A single prerequisite condition for unlocking a skill.

    Supports three kinds of gates:
      - skill_id   : another skill must be unlocked to a minimum rank
      - attribute  : a character attribute must meet a minimum value
      - level      : character level must be at least N
    """

    kind: str          # "skill" | "attribute" | "level"
    target: str        # skill id, attribute name, or literal "level"
    minimum: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "target": self.target, "minimum": self.minimum}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Prerequisite:
        return Prerequisite(
            kind=data["kind"],
            target=data["target"],
            minimum=data.get("minimum", 1),
        )


@dataclass
class SkillNode:
    """
    One node in a skill tree. Each node represents one rank of a skill.

    Attributes:
        id            : unique identifier (e.g. "combat.two_handed.rank_1")
        name          : human-readable display name
        description   : flavor / mechanical text
        category      : top-level category bucket
        node_type     : structural role in the tree
        max_rank      : how many times this skill can be leveled (1 = single purchase)
        point_cost    : skill points required per rank
        stat_costs    : e.g. {"strength": 5} – minimum attribute investment
        prerequisites : list of Prerequisite objects that must be satisfied
        effects       : opaque effect dict (resolved by the game engine)
        parent_ids    : upstream node ids (direct parents in the DAG)
    """

    id: str
    name: str
    description: str = ""
    category: SkillCategory = SkillCategory.COMBAT
    node_type: NodeType = NodeType.LEAF
    max_rank: int = 1
    point_cost: int = 1
    stat_costs: dict[str, int] = field(default_factory=dict)
    prerequisites: list[Prerequisite] = field(default_factory=list)
    effects: dict[str, Any] = field(default_factory=dict)
    parent_ids: list[str] = field(default_factory=list)

    # --- derived (populated by SkillTree after all nodes are registered) ---
    children: list[str] = field(default_factory=list, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "node_type": self.node_type.value,
            "max_rank": self.max_rank,
            "point_cost": self.point_cost,
            "stat_costs": dict(self.stat_costs),
            "prerequisites": [p.to_dict() for p in self.prerequisites],
            "effects": dict(self.effects),
            "parent_ids": list(self.parent_ids),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SkillNode:
        return SkillNode(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            category=SkillCategory(data.get("category", "combat")),
            node_type=NodeType(data.get("node_type", "leaf")),
            max_rank=data.get("max_rank", 1),
            point_cost=data.get("point_cost", 1),
            stat_costs=data.get("stat_costs", {}),
            prerequisites=[Prerequisite.from_dict(p) for p in data.get("prerequisites", [])],
            effects=data.get("effects", {}),
            parent_ids=data.get("parent_ids", []),
        )


@dataclass
class SkillTree:
    """
    A named collection of SkillNodes forming one branching skill path tree.

    Example trees: "two_handed_combat", "fire_magic", "shadow_stealth".
    """

    id: str
    name: str
    description: str = ""
    root_id: str | None = None
    nodes: dict[str, SkillNode] = field(default_factory=dict, repr=False, compare=False)

    def add_node(self, node: SkillNode) -> None:
        self.nodes[node.id] = node
        if node.node_type == NodeType.ROOT:
            self.root_id = node.id

    def get_node(self, node_id: str) -> SkillNode | None:
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> list[SkillNode]:
        node = self.nodes.get(node_id)
        return [self.nodes[cid] for cid in (node.children if node else []) if cid in self.nodes]

    def get_parents(self, node_id: str) -> list[SkillNode]:
        node = self.nodes.get(node_id)
        return [self.nodes[pid] for pid in (node.parent_ids if node else []) if pid in self.nodes]

    def _check_stat_costs(self, node: SkillNode, state: CharacterSkillState) -> tuple[bool, str]:
        """Verify the character meets all minimum attribute investments for `node`."""
        for attr, minimum in node.stat_costs.items():
            value = state.attributes.get(attr, 0)
            if value < minimum:
                return False, f"Requires {attr} >= {minimum} (have {value})."
        return True, ""

    def get_available_nodes(self, character_state: CharacterSkillState) -> list[SkillNode]:
        """Return nodes eligible for unlocking given the character's current state."""
        available = []
        for node in self.nodes.values():
            if node.id in character_state.unlocked_nodes:
                current = character_state.unlocked_nodes[node.id]
                if current >= node.max_rank:
                    continue
                if character_state.remaining_points(self) < node.point_cost:
                    continue
                available.append(node)
                continue
            if self._is_satisfied(node, character_state):
                if character_state.remaining_points(self) >= node.point_cost:
                    available.append(node)
        return available

    def _is_satisfied(self, node: SkillNode, state: CharacterSkillState) -> bool:
        """Check whether all prerequisites and stat costs for `node` are met by `state`."""
        for prereq in node.prerequisites:
            if prereq.kind == "skill":
                rank = state.skill_ranks.get(prereq.target, 0)
                if rank < prereq.minimum:
                    return False
            elif prereq.kind == "attribute":
                value = state.attributes.get(prereq.target, 0)
                if value < prereq.minimum:
                    return False
            elif prereq.kind == "level":
                if state.level < prereq.minimum:
                    return False
        # Also enforce minimum attribute investments defined on the node itself.
        for attr, minimum in node.stat_costs.items():
            value = state.attributes.get(attr, 0)
            if value < minimum:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "root_id": self.root_id,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SkillTree:
        tree = SkillTree(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            root_id=data.get("root_id"),
        )
        for nid, ndata in data.get("nodes", {}).items():
            tree.add_node(SkillNode.from_dict(ndata))
        tree._link_children()
        return tree

    def _link_children(self) -> None:
        """Populate the `children` field on each node from parent_ids."""
        for node in self.nodes.values():
            node.children = []
        for node in self.nodes.values():
            for pid in node.parent_ids:
                parent = self.nodes.get(pid)
                if parent and node.id not in parent.children:
                    parent.children.append(node.id)


@dataclass
class CharacterSkillState:
    """
    Tracks which nodes a character has unlocked, at what rank,
    plus character-level stats used for prerequisite checks.
    """

    character_id: str
    available_points: int = 0
    level: int = 1
    attributes: dict[str, int] = field(default_factory=dict)
    # skill_id (parent node id) -> current rank achieved
    skill_ranks: dict[str, int] = field(default_factory=dict)
    # node_id -> rank (expanded view including all nodes)
    unlocked_nodes: dict[str, int] = field(default_factory=dict)

    def spent_points(self, tree: SkillTree) -> int:
        total = 0
        for nid, rank in self.unlocked_nodes.items():
            node = tree.get_node(nid)
            if node:
                total += node.point_cost * rank
        return total

    def remaining_points(self, tree: SkillTree) -> int:
        return self.available_points - self.spent_points(tree)

    def can_unlock(self, node: SkillNode, tree: SkillTree) -> tuple[bool, str]:
        """Return (ok, reason)."""
        if node.id in self.unlocked_nodes:
            current = self.unlocked_nodes[node.id]
            if current >= node.max_rank:
                return False, "Already at max rank."
            # cost for next rank
            if self.remaining_points(tree) < node.point_cost:
                return False, "Not enough skill points."
            return True, ""

        if not tree._is_satisfied(node, self):
            missing = []
            for prereq in node.prerequisites:
                if prereq.kind == "skill":
                    rank = self.skill_ranks.get(prereq.target, 0)
                    if rank < prereq.minimum:
                        missing.append(f"{prereq.target} rank {prereq.minimum} (have {rank})")
                elif prereq.kind == "attribute":
                    value = self.attributes.get(prereq.target, 0)
                    if value < prereq.minimum:
                        missing.append(f"{prereq.target} >= {prereq.minimum} (have {value})")
                elif prereq.kind == "level":
                    if self.level < prereq.minimum:
                        missing.append(f"level >= {prereq.minimum} (have {self.level})")
            for attr, minimum in node.stat_costs.items():
                value = self.attributes.get(attr, 0)
                if value < minimum:
                    missing.append(f"{attr} >= {minimum} (have {value})")
            return False, "Prerequisites not met: " + "; ".join(missing)

        if self.remaining_points(tree) < node.point_cost:
            return False, "Not enough skill points."

        return True, ""

    def unlock(self, node_id: str, tree: SkillTree) -> tuple[bool, str]:
        node = tree.get_node(node_id)
        if node is None:
            return False, "Node not found in tree."

        ok, reason = self.can_unlock(node, tree)
        if not ok:
            return False, reason

        current = self.unlocked_nodes.get(node_id, 0)
        self.unlocked_nodes[node_id] = current + 1
        self.skill_ranks[node_id] = self.unlocked_nodes[node_id]
        return True, ""

    def refund(self, node_id: str, tree: SkillTree) -> tuple[bool, str]:
        """Remove one rank from a node; refunds the point cost."""
        current = self.unlocked_nodes.get(node_id, 0)
        if current <= 0:
            return False, "No ranks to refund."

        node = tree.get_node(node_id)
        if node is None:
            return False, "Node not found in tree."

        # Check downstream dependencies – we cannot refund a node that
        # is a prerequisite for currently-unlocked nodes.
        for nid, rank in self.unlocked_nodes.items():
            if rank > 0 and nid != node_id:
                other = tree.get_node(nid)
                if other and node_id in other.parent_ids:
                    return False, f"Cannot refund: required by {nid}."

        self.unlocked_nodes[node_id] = current - 1
        self.skill_ranks[node_id] = self.unlocked_nodes[node_id]
        if self.unlocked_nodes[node_id] == 0:
            del self.unlocked_nodes[node_id]
            del self.skill_ranks[node_id]
        return True, ""
