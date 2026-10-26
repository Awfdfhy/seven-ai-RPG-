"""
RPG-10-01: Ability System
Core data model for abilities, ability trees, mana costs, and
character ability state. Cooldowns are delegated to RPG-08-07.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cooldowns import CooldownManager


class AbilityCategory(Enum):
    """Broad category buckets for abilities."""

    COMBAT = "combat"
    MAGIC = "magic"
    STEALTH = "stealth"
    SURVIVAL = "survival"
    SOCIAL = "social"


class TargetType(Enum):
    """Who/what an ability can affect."""

    SELF = "self"
    SINGLE_TARGET = "single_target"
    AOE = "aoe"
    CONE = "cone"
    GROUND_TARGETED = "ground_targeted"


class EffectType(Enum):
    """What kind of effect an ability produces."""

    DAMAGE = "damage"
    HEALING = "healing"
    BUFF = "buff"
    DEBUFF = "debuff"
    STUN = "stun"
    DOT = "dot"
    HOT = "hot"


@dataclass
class AbilityEffect:
    """
    One effect produced by an ability.

    Supports layered effects (e.g., a fireball that damages and burns).
    """

    effect_type: str  # EffectType.value
    value: int = 0
    duration_seconds: float = 0.0
    chance: float = 1.0  # 0.0 – 1.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "effect_type": self.effect_type,
            "value": self.value,
            "duration_seconds": self.duration_seconds,
            "chance": self.chance,
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AbilityEffect:
        return AbilityEffect(
            effect_type=data["effect_type"],
            value=data.get("value", 0),
            duration_seconds=data.get("duration_seconds", 0.0),
            chance=data.get("chance", 1.0),
            extra=data.get("extra", {}),
        )


@dataclass
class Ability:
    """
    A playable ability a character can use in combat or exploration.

    Attributes:
        id              : unique identifier (e.g. "fire.fireball")
        name            : human-readable display name
        description     : flavor / mechanical text
        category        : top-level category bucket
        target_type     : who/what the ability can target
        mana_cost       : mana consumed on use
        cooldown_seconds: seconds before this ability can be used again
        effects         : list of AbilityEffect objects
        skill_tree_ids  : optional skill tree node ids that gate this ability
    """

    id: str
    name: str
    description: str = ""
    category: AbilityCategory = AbilityCategory.COMBAT
    target_type: TargetType = TargetType.SINGLE_TARGET
    mana_cost: int = 0
    cooldown_seconds: float = 0.0
    cooldown_group: str | None = None
    global_cooldown_seconds: float = 0.0
    effects: list[AbilityEffect] = field(default_factory=list)
    skill_tree_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "target_type": self.target_type.value,
            "mana_cost": self.mana_cost,
            "cooldown_seconds": self.cooldown_seconds,
            "cooldown_group": self.cooldown_group,
            "global_cooldown_seconds": self.global_cooldown_seconds,
            "effects": [e.to_dict() for e in self.effects],
            "skill_tree_ids": list(self.skill_tree_ids),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Ability:
        return Ability(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            category=AbilityCategory(data.get("category", "combat")),
            target_type=TargetType(data.get("target_type", "single_target")),
            mana_cost=data.get("mana_cost", 0),
            cooldown_seconds=data.get("cooldown_seconds", 0.0),
            cooldown_group=data.get("cooldown_group"),
            global_cooldown_seconds=data.get("global_cooldown_seconds", 0.0),
            effects=[AbilityEffect.from_dict(e) for e in data.get("effects", [])],
            skill_tree_ids=data.get("skill_tree_ids", []),
        )


@dataclass
class AbilityNode:
    """
    One node in an ability tree. Unlocking a node grants the associated
    Ability to the character.

    Attributes:
        id            : unique identifier (e.g. "fire.fireball_rank_1")
        name          : display name for the tree node
        description   : flavor text
        category      : top-level category bucket
        node_type     : structural role (root/branch/leaf/capstone)
        max_rank      : how many times this ability node can be leveled
        point_cost    : ability points required per rank
        stat_costs    : minimum attribute investments
        prerequisites : list of prerequisite conditions
        ability_id    : the Ability granted by this node
        parent_ids    : upstream node ids
    """

    id: str
    name: str
    ability_id: str
    description: str = ""
    category: AbilityCategory = AbilityCategory.COMBAT
    node_type: str = "leaf"
    max_rank: int = 1
    point_cost: int = 1
    stat_costs: dict[str, int] = field(default_factory=dict)
    prerequisites: list[dict[str, Any]] = field(default_factory=list)
    parent_ids: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "ability_id": self.ability_id,
            "category": self.category.value,
            "node_type": self.node_type,
            "max_rank": self.max_rank,
            "point_cost": self.point_cost,
            "stat_costs": dict(self.stat_costs),
            "prerequisites": [dict(p) for p in self.prerequisites],
            "parent_ids": list(self.parent_ids),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AbilityNode:
        return AbilityNode(
            id=data["id"],
            name=data["name"],
            ability_id=data["ability_id"],
            description=data.get("description", ""),
            category=AbilityCategory(data.get("category", "combat")),
            node_type=data.get("node_type", "leaf"),
            max_rank=data.get("max_rank", 1),
            point_cost=data.get("point_cost", 1),
            stat_costs=data.get("stat_costs", {}),
            prerequisites=data.get("prerequisites", []),
            parent_ids=data.get("parent_ids", []),
        )


@dataclass
class AbilityTree:
    """
    A named collection of AbilityNodes forming one branching ability path tree.

    Example trees: "fire_magic", "shadow_stealth".
    """

    id: str
    name: str
    description: str = ""
    root_id: str | None = None
    nodes: dict[str, AbilityNode] = field(default_factory=dict, repr=False, compare=False)

    def add_node(self, node: AbilityNode) -> None:
        self.nodes[node.id] = node
        if node.node_type == "root":
            self.root_id = node.id

    def get_node(self, node_id: str) -> AbilityNode | None:
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> list[AbilityNode]:
        node = self.nodes.get(node_id)
        return [self.nodes[cid] for cid in (node.children if node else []) if cid in self.nodes]

    def get_parents(self, node_id: str) -> list[AbilityNode]:
        node = self.nodes.get(node_id)
        return [self.nodes[pid] for pid in (node.parent_ids if node else []) if pid in self.nodes]

    def _check_stat_costs(self, node: AbilityNode, state: CharacterAbilityState) -> tuple[bool, str]:
        for attr, minimum in node.stat_costs.items():
            value = state.attributes.get(attr, 0)
            if value < minimum:
                return False, f"Requires {attr} >= {minimum} (have {value})."
        return True, ""

    def get_available_nodes(self, state: CharacterAbilityState) -> list[AbilityNode]:
        available = []
        for node in self.nodes.values():
            if node.id in state.unlocked_ability_nodes:
                current = state.unlocked_ability_nodes[node.id]
                if current >= node.max_rank:
                    continue
                if state.remaining_points(self) < node.point_cost:
                    continue
                available.append(node)
                continue
            if self._is_satisfied(node, state):
                if state.remaining_points(self) >= node.point_cost:
                    available.append(node)
        return available

    def _is_satisfied(self, node: AbilityNode, state: CharacterAbilityState) -> bool:
        for prereq in node.prerequisites:
            kind = prereq.get("kind", "")
            if kind == "skill":
                target = prereq.get("target", "")
                minimum = prereq.get("minimum", 1)
                rank = state.skill_ranks.get(target, 0)
                if rank < minimum:
                    return False
            elif kind == "attribute":
                target = prereq.get("target", "")
                minimum = prereq.get("minimum", 1)
                value = state.attributes.get(target, 0)
                if value < minimum:
                    return False
            elif kind == "level":
                minimum = prereq.get("minimum", 1)
                if state.level < minimum:
                    return False
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
    def from_dict(data: dict[str, Any]) -> AbilityTree:
        tree = AbilityTree(
            id=data["id"],
            name=data.get("name", data["id"]),
            description=data.get("description", ""),
        )
        nodes_data = data.get("nodes", {})
        if isinstance(nodes_data, list):
            for node_data in nodes_data:
                tree.add_node(AbilityNode.from_dict(node_data))
        else:
            for nid, ndata in nodes_data.items():
                tree.add_node(AbilityNode.from_dict(ndata))
        tree._link_children()
        return tree

    def _link_children(self) -> None:
        for node in self.nodes.values():
            node.children = []
        for node in self.nodes.values():
            for pid in node.parent_ids:
                parent = self.nodes.get(pid)
                if parent and node.id not in parent.children:
                    parent.children.append(node.id)


@dataclass
class CharacterAbilityState:
    """
    Tracks a character's unlocked abilities, cooldowns, mana, and
    related attributes for ability-use checks.
    """

    character_id: str
    available_points: int = 0
    level: int = 1
    attributes: dict[str, int] = field(default_factory=dict)
    mana: int = 0
    max_mana: int = 0
    # skill node_id -> current rank (synced from skill tree system)
    skill_ranks: dict[str, int] = field(default_factory=dict)
    # ability_id (or ability_node_id) -> current rank
    ability_ranks: dict[str, int] = field(default_factory=dict)
    # node_id -> rank (expanded view including all nodes)
    unlocked_ability_nodes: dict[str, int] = field(default_factory=dict)
    # RPG-08-07: delegated to CooldownManager
    cooldown_manager: CooldownManager = field(default=None)

    def __post_init__(self) -> None:
        if self.cooldown_manager is None:
            self.cooldown_manager = CooldownManager(character_id=self.character_id)

    def spent_points(self, tree: AbilityTree) -> int:
        total = 0
        for nid, rank in self.unlocked_ability_nodes.items():
            node = tree.get_node(nid)
            if node:
                total += node.point_cost * rank
        return total

    def remaining_points(self, tree: AbilityTree) -> int:
        return self.available_points - self.spent_points(tree)

    def can_unlock(self, node: AbilityNode, tree: AbilityTree) -> tuple[bool, str]:
        if node.id in self.unlocked_ability_nodes:
            current = self.unlocked_ability_nodes[node.id]
            if current >= node.max_rank:
                return False, "Already at max rank."
            if self.remaining_points(tree) < node.point_cost:
                return False, "Not enough ability points."
            return True, ""

        if not tree._is_satisfied(node, self):
            missing = []
            for prereq in node.prerequisites:
                kind = prereq.get("kind", "")
                if kind == "skill":
                    target = prereq.get("target", "")
                    minimum = prereq.get("minimum", 1)
                    rank = self.skill_ranks.get(target, 0)
                    if rank < minimum:
                        missing.append(f"{target} rank {minimum} (have {rank})")
                elif kind == "attribute":
                    target = prereq.get("target", "")
                    minimum = prereq.get("minimum", 1)
                    value = self.attributes.get(target, 0)
                    if value < minimum:
                        missing.append(f"{target} >= {minimum} (have {value})")
                elif kind == "level":
                    minimum = prereq.get("minimum", 1)
                    if self.level < minimum:
                        missing.append(f"level >= {minimum} (have {self.level})")
            return False, "Prerequisites not met: " + "; ".join(missing)

        if self.remaining_points(tree) < node.point_cost:
            return False, "Not enough ability points."
        return True, ""

    def unlock(self, node_id: str, tree: AbilityTree) -> tuple[bool, str]:
        node = tree.get_node(node_id)
        if node is None:
            return False, "Node not found in tree."

        ok, reason = self.can_unlock(node, tree)
        if not ok:
            return False, reason

        current = self.unlocked_ability_nodes.get(node_id, 0)
        self.unlocked_ability_nodes[node_id] = current + 1
        self.ability_ranks[node_id] = self.unlocked_ability_nodes[node_id]
        return True, ""

    def refund(self, node_id: str, tree: AbilityTree) -> tuple[bool, str]:
        """Remove one rank from a node; refunds the point cost."""
        current = self.unlocked_ability_nodes.get(node_id, 0)
        if current <= 0:
            return False, "No ranks to refund."

        node = tree.get_node(node_id)
        if node is None:
            return False, "Node not found in tree."

        for nid, rank in self.unlocked_ability_nodes.items():
            if rank > 0 and nid != node_id:
                other = tree.get_node(nid)
                if other and node_id in other.parent_ids:
                    return False, f"Cannot refund: required by {nid}."

        self.unlocked_ability_nodes[node_id] = current - 1
        self.ability_ranks[node_id] = self.unlocked_ability_nodes[node_id]
        if self.unlocked_ability_nodes[node_id] == 0:
            del self.unlocked_ability_nodes[node_id]
            del self.ability_ranks[node_id]
        return True, ""

    # --- cooldown / mana helpers -------------------------------------------------

    def is_on_cooldown(self, ability_id: str, current_time: float) -> bool:
        return self.cooldown_manager.is_on_cooldown(ability_id, current_time)

    def get_cooldown_remaining(self, ability_id: str, current_time: float) -> float:
        return self.cooldown_manager.get_cooldown_remaining(ability_id, current_time)

    def start_cooldown(self, ability_id: str, cooldown_seconds: float, current_time: float) -> None:
        self.cooldown_manager.start_cooldown(ability_id, cooldown_seconds, current_time)

    def can_use_ability(self, ability: Ability, current_time: float) -> tuple[bool, str]:
        if self.mana < ability.mana_cost:
            return False, f"Not enough mana (have {self.mana}, need {ability.mana_cost})."
        if self.is_on_cooldown(ability.id, current_time):
            remaining = self.get_cooldown_remaining(ability.id, current_time)
            return False, f"On cooldown ({remaining:.1f}s remaining)."
        if ability.cooldown_group and self.cooldown_manager.is_group_on_cooldown(ability.cooldown_group, current_time):
            remaining = self.cooldown_manager.get_group_cooldown_remaining(ability.cooldown_group, current_time)
            return False, f"Group on cooldown ({remaining:.1f}s remaining)."
        return True, ""

    def use_ability(self, ability: Ability, current_time: float) -> tuple[bool, str]:
        ok, reason = self.can_use_ability(ability, current_time)
        if not ok:
            return False, reason

        self.mana -= ability.mana_cost
        if ability.cooldown_seconds > 0:
            self.start_cooldown(ability.id, ability.cooldown_seconds, current_time)
            if ability.cooldown_group:
                self.cooldown_manager.start_cooldown(
                    ability.id,
                    ability.cooldown_seconds,
                    current_time,
                    group=ability.cooldown_group,
                )
        if ability.global_cooldown_seconds > 0:
            self.cooldown_manager.start_global_cooldown(ability.global_cooldown_seconds, current_time)
        return True, ""

    def restore_mana(self, amount: int) -> None:
        self.mana = min(self.max_mana, self.mana + amount)
