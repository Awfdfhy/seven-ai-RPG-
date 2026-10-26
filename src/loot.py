"""
RPG-08-15: Loot and rewards system.
Provides random loot tables, rarity tiers, loot rolling, and instance
tracking scoped to worlds and sessions.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Rarity tiers
# ---------------------------------------------------------------------------

RARITY_TIERS: dict[str, dict[str, Any]] = {
    "common": {
        "order": 0,
        "display_name": "Common",
        "color": "#9d9d9d",
        "weight_multiplier": 50,
        "min_quantity": 1,
        "max_quantity": 3,
    },
    "uncommon": {
        "order": 1,
        "display_name": "Uncommon",
        "color": "#1eff00",
        "weight_multiplier": 30,
        "min_quantity": 1,
        "max_quantity": 2,
    },
    "rare": {
        "order": 2,
        "display_name": "Rare",
        "color": "#0070dd",
        "weight_multiplier": 15,
        "min_quantity": 1,
        "max_quantity": 2,
    },
    "epic": {
        "order": 3,
        "display_name": "Epic",
        "color": "#a335ee",
        "weight_multiplier": 4,
        "min_quantity": 1,
        "max_quantity": 1,
    },
    "legendary": {
        "order": 4,
        "display_name": "Legendary",
        "color": "#ff8000",
        "weight_multiplier": 1,
        "min_quantity": 1,
        "max_quantity": 1,
    },
}


def get_rarity_info(rarity: str) -> dict[str, Any]:
    """Return metadata for a rarity tier; defaults to common if unknown."""
    return RARITY_TIERS.get(rarity, RARITY_TIERS["common"])


def roll_rarity() -> str:
    """
    Roll a rarity tier using the configured weight multipliers.
    Higher-weight rarities are more common.
    """
    weights = [(tier, info["weight_multiplier"]) for tier, info in RARITY_TIERS.items()]
    tiers, tier_weights = zip(*weights)
    return random.choices(tiers, weights=tier_weights, k=1)[0]


def roll_quantity(rarity: str) -> int:
    """Roll a quantity for a given rarity tier."""
    info = get_rarity_info(rarity)
    return random.randint(info["min_quantity"], info["max_quantity"])


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

@dataclass
class LootEntry:
    """
    A possible drop in a loot table.

    Attributes:
        item_id       : reference to the item definition
        rarity        : rarity tier name
        weight        : relative drop chance within this table
        min_quantity  : minimum stack size when dropped
        max_quantity  : maximum stack size when dropped
        metadata      : opaque extra data (e.g. condition, enchantment)
    """

    item_id: str
    rarity: str = "common"
    weight: int = 1
    min_quantity: int = 1
    max_quantity: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "rarity": self.rarity,
            "weight": self.weight,
            "min_quantity": self.min_quantity,
            "max_quantity": self.max_quantity,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LootEntry:
        return LootEntry(
            item_id=data["item_id"],
            rarity=data.get("rarity", "common"),
            weight=data.get("weight", 1),
            min_quantity=data.get("min_quantity", 1),
            max_quantity=data.get("max_quantity", 1),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class LootTable:
    """
    Static definition of a loot table.

    Attributes:
        id              : unique identifier
        name            : human-readable display name
        description     : flavor text
        entries         : list of possible drops with weights
        min_drops       : minimum number of distinct items to roll
        max_drops       : maximum number of distinct items to roll
        allow_duplicates: whether the same item can appear multiple times
        metadata        : opaque extra data
    """

    id: str
    name: str
    description: str = ""
    entries: list[dict[str, Any]] = field(default_factory=list)
    min_drops: int = 1
    max_drops: int = 3
    allow_duplicates: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "entries": [e.to_dict() for e in self._entry_objects()],
            "min_drops": self.min_drops,
            "max_drops": self.max_drops,
            "allow_duplicates": self.allow_duplicates,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LootTable:
        return LootTable(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            entries=list(data.get("entries", [])),
            min_drops=data.get("min_drops", 1),
            max_drops=data.get("max_drops", 3),
            allow_duplicates=data.get("allow_duplicates", False),
            metadata=dict(data.get("metadata", {})),
        )

    def _entry_objects(self) -> list[LootEntry]:
        return [LootEntry.from_dict(e) if isinstance(e, dict) else e for e in self.entries]


# ---------------------------------------------------------------------------
# Runtime instances
# ---------------------------------------------------------------------------

@dataclass
class LootInstance:
    """
    Runtime record for one loot generation event.

    Attributes:
        instance_id   : unique identifier for this loot roll
        loot_table_id : reference to the LootTable used
        world_id      : the world this loot belongs to
        session_id    : optional session that generated it
        items         : list of granted items with quantities
        rolled_at     : ISO timestamp
        source        : what triggered the loot (e.g. "combat", "quest")
        metadata      : opaque extra data
    """

    instance_id: str
    loot_table_id: str
    world_id: str
    session_id: str | None = None
    items: list[dict[str, Any]] = field(default_factory=list)
    rolled_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    source: str = "random"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "loot_table_id": self.loot_table_id,
            "world_id": self.world_id,
            "session_id": self.session_id,
            "items": [dict(item) for item in self.items],
            "rolled_at": self.rolled_at,
            "source": self.source,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LootInstance:
        return LootInstance(
            instance_id=data["instance_id"],
            loot_table_id=data["loot_table_id"],
            world_id=data["world_id"],
            session_id=data.get("session_id"),
            items=[dict(item) for item in data.get("items", [])],
            rolled_at=data.get("rolled_at", ""),
            source=data.get("source", "random"),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Legacy alias
# ---------------------------------------------------------------------------

RolledLoot = LootInstance
LootTableEntry = LootEntry


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class LootManager:
    """
    Manages loot table definitions and runtime loot instances across
    worlds/sessions.

    Integrates with world state by scoping loot instances to a world_id
    and session_id, and exposing loot history for display or integration.
    """

    def __init__(self) -> None:
        self._instances: dict[str, LootInstance] = {}
        self._definitions: dict[str, LootTable] = {}
        self._session_loot: dict[str, set[str]] = {}
        self._world_loot: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Definition loading
    # ------------------------------------------------------------------

    def register_definition(self, definition: LootTable) -> None:
        self._definitions[definition.id] = definition

    def load_definitions(self, definitions: list[LootTable]) -> None:
        for d in definitions:
            self.register_definition(d)

    def get_definition(self, loot_table_id: str) -> LootTable | None:
        return self._definitions.get(loot_table_id)

    def list_definitions(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._definitions.values()]

    # ------------------------------------------------------------------
    # Rolling
    # ------------------------------------------------------------------

    def roll_loot(
        self,
        loot_table_id: str,
        world_id: str,
        session_id: str | None = None,
        source: str = "random",
        seed: int | None = None,
        metadata: dict[str, Any] | None = None,
        loot_rarity_boost: float = 0.0,
    ) -> LootInstance | None:
        """
        Roll loot from a loot table and record the result.

        Args:
            loot_table_id: ID of the LootTable definition
            world_id:     world this loot belongs to
            session_id:   optional session that triggered the roll
            source:       what triggered the loot ("combat", "quest", etc.)
            seed:         optional RNG seed for deterministic rolls
            metadata:     extra data to attach to the instance
            loot_rarity_boost: positive values shift weights toward higher
                               rarities; negative toward lower (from difficulty)

        Returns:
            LootInstance or None if the table does not exist
        """
        table = self._definitions.get(loot_table_id)
        if table is None:
            return None

        if seed is not None:
            rng = random.Random(seed)
        else:
            rng = random

        entries = table._entry_objects()
        if not entries:
            return None

        num_drops = rng.randint(table.min_drops, table.max_drops)
        dropped_items: list[dict[str, Any]] = []

        # Build rarity lookup for boost application
        rarity_order = {
            "common": 0,
            "uncommon": 1,
            "rare": 2,
            "epic": 3,
            "legendary": 4,
        }

        def _boost_weight(entry: LootEntry) -> int:
            base = max(1, entry.weight)
            if loot_rarity_boost == 0.0:
                return base
            tier = rarity_order.get(entry.rarity, 0)
            # Positive boost: higher tiers get a bonus; negative: lower tiers get bonus
            shift = loot_rarity_boost * tier
            return max(1, int(base + base * shift))

        if table.allow_duplicates:
            # Weighted sample with replacement
            weights = [_boost_weight(e) for e in entries]
            chosen = rng.choices(entries, weights=weights, k=num_drops)
            for entry in chosen:
                qty = rng.randint(entry.min_quantity, entry.max_quantity)
                dropped_items.append({
                    "item_id": entry.item_id,
                    "rarity": entry.rarity,
                    "quantity": qty,
                    "metadata": dict(entry.metadata),
                })
        else:
            # Weighted sample without replacement
            available = list(entries)
            for _ in range(min(num_drops, len(available))):
                weights = [_boost_weight(e) for e in available]
                entry = rng.choices(available, weights=weights, k=1)[0]
                qty = rng.randint(entry.min_quantity, entry.max_quantity)
                dropped_items.append({
                    "item_id": entry.item_id,
                    "rarity": entry.rarity,
                    "quantity": qty,
                    "metadata": dict(entry.metadata),
                })
                available.remove(entry)

        instance = LootInstance(
            instance_id=str(uuid.uuid4()),
            loot_table_id=loot_table_id,
            world_id=world_id,
            session_id=session_id,
            items=dropped_items,
            source=source,
            metadata=metadata or {},
        )
        self._instances[instance.instance_id] = instance
        self._world_loot.setdefault(world_id, set()).add(instance.instance_id)
        if session_id:
            self._session_loot.setdefault(session_id, set()).add(instance.instance_id)
        return instance

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_loot(self, instance_id: str) -> LootInstance | None:
        return self._instances.get(instance_id)

    def list_loot(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        instances = list(self._instances.values())
        if world_id is not None:
            instances = [i for i in instances if i.world_id == world_id]
        if session_id is not None:
            instances = [i for i in instances if i.session_id == session_id]
        if source is not None:
            instances = [i for i in instances if i.source == source]
        return [i.to_dict() for i in sorted(instances, key=lambda i: i.rolled_at)]

    def get_loot_history(self, world_id: str) -> list[dict[str, Any]]:
        """
        Return aggregated loot history for a world, grouped by item_id.
        """
        instances = [i for i in self._instances.values() if i.world_id == world_id]
        totals: dict[str, dict[str, Any]] = {}
        for inst in instances:
            for item in inst.items:
                key = item["item_id"]
                if key not in totals:
                    totals[key] = {
                        "item_id": key,
                        "rarity": item["rarity"],
                        "total_quantity": 0,
                        "rolls": 0,
                    }
                totals[key]["total_quantity"] += item["quantity"]
                totals[key]["rolls"] += 1
        return sorted(totals.values(), key=lambda x: x["item_id"])

    def get_loot_summary(self, world_id: str) -> dict[str, Any]:
        """
        Return a summary of loot for a world: total rolls, items received,
        and rarity breakdown.
        """
        instances = [i for i in self._instances.values() if i.world_id == world_id]
        rarity_counts: dict[str, int] = {}
        total_items = 0
        for inst in instances:
            for item in inst.items:
                total_items += item["quantity"]
                rarity_counts[item["rarity"]] = rarity_counts.get(item["rarity"], 0) + item["quantity"]
        return {
            "world_id": world_id,
            "total_rolls": len(instances),
            "total_items": total_items,
            "rarity_breakdown": rarity_counts,
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "instances": {iid: i.to_dict() for iid, i in self._instances.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._instances.clear()
        self._session_loot.clear()
        self._world_loot.clear()
        for iid, idata in state.get("instances", {}).items():
            instance = LootInstance.from_dict(idata)
            self._instances[iid] = instance
            self._world_loot.setdefault(instance.world_id, set()).add(iid)
            if instance.session_id:
                self._session_loot.setdefault(instance.session_id, set()).add(iid)
