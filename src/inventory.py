"""
RPG-08-13: Inventory UI
Core data model for character inventory, equipment slots, and item stacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EquipmentSlotType(Enum):
    """Where an item can be equipped."""

    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    HANDS = "hands"
    FEET = "feet"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    RING = "ring"
    NECKLACE = "necklace"
    ACCESSORY = "accessory"


class ItemRarity(Enum):
    """Visual rarity tier."""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class ItemCategory(Enum):
    """Broad item classification for inventory and equipment rules."""

    MISC = "misc"
    WEAPON = "weapon"
    ARMOR = "armor"
    HELMET = "helmet"
    HAT = "hat"
    CHEST = "chest"
    LEGS = "legs"
    PANTS = "pants"
    LEGGINGS = "leggings"
    HANDS = "hands"
    GLOVES = "gloves"
    GAUNTLETS = "gauntlets"
    FEET = "feet"
    BOOTS = "boots"
    SHOES = "shoes"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    SWORD = "sword"
    AXE = "axe"
    MACE = "mace"
    STAFF = "staff"
    SHIELD = "shield"
    DAGGER = "dagger"
    RING = "ring"
    NECKLACE = "necklace"
    AMULET = "amulet"
    ACCESSORY = "accessory"
    CLOAK = "cloak"
    BELT = "belt"
    LEGGING = "leggings"
    POTION = "potion"
    FOOD = "food"
    TOOL = "tool"
    MATERIAL = "material"


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

@dataclass
class Item:
    """A single item instance with type, stats, effects, durability, and set info."""

    id: str
    name: str
    description: str = ""
    item_type: ItemCategory = ItemCategory.MISC
    rarity: ItemRarity = ItemRarity.COMMON
    stackable: bool = True
    max_stack: int = 99
    stats: dict[str, Any] = field(default_factory=dict)
    effects: dict[str, Any] = field(default_factory=dict)
    icon: str = "?"
    metadata: dict[str, Any] = field(default_factory=dict)
    set_id: str | None = None
    set_piece: str | None = None
    durability: int = 100
    max_durability: int = 100

    def __post_init__(self) -> None:
        if isinstance(self.item_type, str):
            self.item_type = ItemCategory(self.item_type)
        if isinstance(self.rarity, str):
            self.rarity = ItemRarity(self.rarity)

    def is_broken(self) -> bool:
        return self.max_durability > 0 and self.durability <= 0

    def durability_percent(self) -> float:
        if self.max_durability <= 0:
            return 0.0
        return max(0.0, min(1.0, self.durability / self.max_durability))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "item_type": self.item_type.value,
            "rarity": self.rarity.value,
            "stackable": self.stackable,
            "max_stack": self.max_stack,
            "stats": dict(self.stats),
            "effects": dict(self.effects),
            "icon": self.icon,
            "metadata": dict(self.metadata),
            "set_id": self.set_id,
            "set_piece": self.set_piece,
            "durability": self.durability,
            "max_durability": self.max_durability,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Item:
        raw_type = data.get("item_type", "misc")
        item_type = ItemCategory(raw_type) if not isinstance(raw_type, ItemCategory) else raw_type
        raw_rarity = data.get("rarity", "common")
        rarity = ItemRarity(raw_rarity) if not isinstance(raw_rarity, ItemRarity) else raw_rarity
        return Item(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            item_type=item_type,
            rarity=rarity,
            stackable=data.get("stackable", True),
            max_stack=data.get("max_stack", 99),
            stats=dict(data.get("stats", {})),
            effects=dict(data.get("effects", {})),
            icon=data.get("icon", "?"),
            metadata=dict(data.get("metadata", {})),
            set_id=data.get("set_id"),
            set_piece=data.get("set_piece"),
            durability=data.get("durability", 100),
            max_durability=data.get("max_durability", 100),
        )


# ---------------------------------------------------------------------------
# Inventory slots
# ---------------------------------------------------------------------------

@dataclass
class ItemSlot:
    """One slot in the inventory bag holding an item + quantity."""

    slot_index: int
    item: Item | None = None
    quantity: int = 0

    def is_empty(self) -> bool:
        return self.item is None or self.quantity <= 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_index": self.slot_index,
            "item": self.item.to_dict() if self.item else None,
            "quantity": self.quantity,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ItemSlot:
        item = Item.from_dict(data["item"]) if data.get("item") else None
        return ItemSlot(
            slot_index=data["slot_index"],
            item=item,
            quantity=data.get("quantity", 0),
        )


@dataclass
class EquipmentSlot:
    """One equipment slot holding an equipped item with durability."""

    slot_type: EquipmentSlotType
    item: Item | None = None
    durability: int = 100
    max_durability: int = 100

    def is_empty(self) -> bool:
        return self.item is None

    def is_broken(self) -> bool:
        return self.durability <= 0

    def durability_percent(self) -> float:
        if self.max_durability <= 0:
            return 1.0
        return max(0.0, self.durability / self.max_durability)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_type": self.slot_type.value,
            "item": self.item.to_dict() if self.item else None,
            "durability": self.durability,
            "max_durability": self.max_durability,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> EquipmentSlot:
        item = Item.from_dict(data["item"]) if data.get("item") else None
        return EquipmentSlot(
            slot_type=EquipmentSlotType(data["slot_type"]),
            item=item,
            durability=data.get("durability", 100),
            max_durability=data.get("max_durability", 100),
        )


# ---------------------------------------------------------------------------
# Equipment set definition
# ---------------------------------------------------------------------------

@dataclass
class EquipmentSet:
    """
    Defines a named equipment set with piece bonuses.
    Bonuses are keyed by minimum number of pieces required.
    """

    set_id: str
    name: str
    description: str = ""
    pieces: list[str] = field(default_factory=list)  # set_piece names
    bonuses: dict[int, dict[str, Any]] = field(default_factory=dict)  # pieces -> stats

    def to_dict(self) -> dict[str, Any]:
        return {
            "set_id": self.set_id,
            "name": self.name,
            "description": self.description,
            "pieces": list(self.pieces),
            "bonuses": {k: dict(v) for k, v in self.bonuses.items()},
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> EquipmentSet:
        return EquipmentSet(
            set_id=data["set_id"],
            name=data["name"],
            description=data.get("description", ""),
            pieces=list(data.get("pieces", [])),
            bonuses={int(k): dict(v) for k, v in data.get("bonuses", {}).items()},
        )


# ---------------------------------------------------------------------------
# Character inventory state
# ---------------------------------------------------------------------------

@dataclass
class InventoryState:
    """Full inventory state for a character."""

    character_id: str
    capacity: int = 24
    slots: list[ItemSlot] = field(default_factory=list)
    equipment: dict[str, EquipmentSlot] = field(default_factory=dict)
    gold: int = 0

    def __post_init__(self) -> None:
        if not self.slots:
            self.slots = [ItemSlot(slot_index=i) for i in range(self.capacity)]
        if not self.equipment:
            for slot_type in EquipmentSlotType:
                self.equipment[slot_type.value] = EquipmentSlot(slot_type=slot_type)

    def get_empty_slot_index(self) -> int | None:
        for slot in self.slots:
            if slot.is_empty():
                return slot.slot_index
        return None

    def get_item_slots(self, item_id: str) -> list[ItemSlot]:
        return [s for s in self.slots if s.item and s.item.id == item_id]

    def total_quantity(self, item_id: str) -> int:
        return sum(s.quantity for s in self.get_item_slots(item_id))

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        return self.total_quantity(item_id) >= quantity

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "capacity": self.capacity,
            "slots": [s.to_dict() for s in self.slots],
            "equipment": {k: v.to_dict() for k, v in self.equipment.items()},
            "gold": self.gold,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> InventoryState:
        state = InventoryState(
            character_id=data["character_id"],
            capacity=data.get("capacity", 24),
            gold=data.get("gold", 0),
        )
        state.slots = [ItemSlot.from_dict(s) for s in data.get("slots", [])]
        state.equipment = {
            k: EquipmentSlot.from_dict(v)
            for k, v in data.get("equipment", {}).items()
        }
        return state


# ---------------------------------------------------------------------------
# Inventory Manager
# ---------------------------------------------------------------------------

class InventoryManager:
    """
    Manages inventory operations: add/remove items, equip/unequip,
    stack merging, and persistence for a character.
    """

    def __init__(self, character_id: str | None = None, max_slots: int = 24) -> None:
        self._inventories: dict[str, InventoryState] = {}
        self._equipment_sets: dict[str, EquipmentSet] = {}
        self._character_id = character_id
        if character_id is not None:
            self._inventories[character_id] = InventoryState(character_id=character_id, capacity=max_slots)

    def register_equipment_set(self, eq_set: EquipmentSet) -> None:
        """Register an equipment set definition."""
        self._equipment_sets[eq_set.set_id] = eq_set

    def get_equipment_set(self, set_id: str) -> EquipmentSet | None:
        return self._equipment_sets.get(set_id)

    def list_equipment_sets(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._equipment_sets.values()]

    def get_inventory(self, character_id: str) -> InventoryState:
        if character_id not in self._inventories:
            self._inventories[character_id] = InventoryState(character_id=character_id)
        return self._inventories[character_id]

    def add_item(self, character_id: str | None = None, item: Item | None = None, quantity: int = 1) -> dict[str, Any]:
        """Add an item to the character's inventory, stacking where possible."""
        cid = character_id or self._character_id
        if cid is None:
            return {"success": False, "reason": "character_id is required"}
        inv = self.get_inventory(cid)

        if item.stackable:
            for slot in inv.slots:
                if not slot.is_empty() and slot.item.id == item.id:
                    space = slot.item.max_stack - slot.quantity
                    to_add = min(space, quantity)
                    slot.quantity += to_add
                    quantity -= to_add
                    if quantity <= 0:
                        return {"success": True, "added": to_add, "remaining": 0}

        # Place remaining in empty slots
        added_total = 0
        while quantity > 0:
            idx = inv.get_empty_slot_index()
            if idx is None:
                break
            to_add = min(quantity, item.max_stack)
            inv.slots[idx] = ItemSlot(slot_index=idx, item=item, quantity=to_add)
            quantity -= to_add
            added_total += to_add

        if quantity > 0:
            return {"success": False, "reason": "Inventory full", "added": added_total, "remaining": quantity}
        return {"success": True, "added": added_total, "remaining": 0}

    def remove_item(self, character_id: str, item_id: str, quantity: int = 1) -> dict[str, Any]:
        """Remove quantity of an item from inventory, splitting stacks as needed."""
        inv = self.get_inventory(character_id)
        if not inv.has_item(item_id, quantity):
            return {"success": False, "reason": "Not enough items", "removed": 0, "remaining": quantity}

        to_remove = quantity
        for slot in inv.get_item_slots(item_id):
            if to_remove <= 0:
                break
            if slot.quantity <= to_remove:
                to_remove -= slot.quantity
                slot.item = None
                slot.quantity = 0
            else:
                slot.quantity -= to_remove
                to_remove = 0

        return {"success": True, "removed": quantity, "remaining": 0}

    def equip_item(self, character_id: str | None = None, item_id: str = "", slot_index: int = -1) -> dict[str, Any]:
        """Move an item from bag to an equipment slot."""
        cid = character_id or self._character_id
        if cid is None:
            return {"success": False, "reason": "character_id is required"}
        inv = self.get_inventory(cid)
        slot = inv.slots[slot_index]
        if slot.is_empty() or slot.item.id != item_id:
            for s in inv.slots:
                if not s.is_empty() and s.item.id == item_id:
                    slot = s
                    break
            else:
                return {"success": False, "reason": "Item not found in inventory"}

        item = slot.item
        if item.is_broken():
            return {"success": False, "reason": "Cannot equip broken item"}

        equip_type = self._equip_type_for_item(item)
        if equip_type is None:
            return {"success": False, "reason": f"Item type '{item.item_type.value}' cannot be equipped"}

        equip_slot = inv.equipment[equip_type.value]
        if equip_slot.item:
            # Unequip current item back to bag
            self.unequip_item(character_id, equip_type.value)

        slot.item = None
        slot.quantity = 0
        inv.equipment[equip_type.value] = EquipmentSlot(
            slot_type=equip_type,
            item=item,
            durability=item.durability,
            max_durability=item.max_durability,
        )
        return {"success": True, "slot": equip_type.value, "item_id": item.id}

    def unequip_item(self, character_id: str | None = None, slot_type: str = "") -> dict[str, Any]:
        """Move an equipped item back to the bag."""
        cid = character_id or self._character_id
        if cid is None:
            return {"success": False, "reason": "character_id is required"}
        inv = self.get_inventory(cid)
        try:
            equip_slot = inv.equipment[slot_type]
        except KeyError:
            return {"success": False, "reason": "Invalid equipment slot"}

        if equip_slot.is_empty():
            return {"success": False, "reason": "Slot is empty"}

        item = equip_slot.item
        result = self.add_item(character_id, item, quantity=1)
        if result.get("success"):
            equip_slot.item = None
            equip_slot.durability = 100
            equip_slot.max_durability = 100
            return {"success": True, "slot": slot_type, "item_id": item.id}
        return result

    def damage_item(self, character_id: str, slot_index: int, amount: int = 1) -> dict[str, Any]:
        """Reduce the durability of the item in the given inventory slot."""
        inv = self.get_inventory(character_id)
        if slot_index < 0 or slot_index >= len(inv.slots):
            return {"success": False, "reason": "Invalid slot index"}

        slot = inv.slots[slot_index]
        if slot.is_empty():
            return {"success": False, "reason": "Slot is empty"}

        item = slot.item
        if item.max_durability <= 0:
            return {"success": True, "reason": "Item is indestructible", "durability": item.durability}

        item.durability = max(0, item.durability - amount)
        if item.is_broken():
            slot.item = None
            slot.quantity = 0
            return {"success": True, "broken": True, "durability": 0}

        return {"success": True, "broken": False, "durability": item.durability}

    def repair_item(self, character_id: str, slot_index: int, amount: int) -> dict[str, Any]:
        """Restore durability of the item in the given inventory slot."""
        inv = self.get_inventory(character_id)
        if slot_index < 0 or slot_index >= len(inv.slots):
            return {"success": False, "reason": "Invalid slot index"}

        slot = inv.slots[slot_index]
        if slot.is_empty():
            return {"success": False, "reason": "Slot is empty"}

        item = slot.item
        if item.max_durability <= 0:
            return {"success": True, "reason": "Item is indestructible", "durability": item.durability}

        item.durability = min(item.max_durability, item.durability + amount)
        return {"success": True, "durability": item.durability}

    def consume_item(self, character_id: str, item_id: str, quantity: int = 1) -> dict[str, Any]:
        """Consume a stackable item (e.g., potions, food), reducing stack size."""
        inv = self.get_inventory(character_id)
        if not inv.has_item(item_id, quantity):
            return {"success": False, "reason": "Not enough items to consume"}

        to_consume = quantity
        for slot in inv.get_item_slots(item_id):
            if to_consume <= 0:
                break
            if slot.quantity <= to_consume:
                to_consume -= slot.quantity
                slot.item = None
                slot.quantity = 0
            else:
                slot.quantity -= to_consume
                to_consume = 0

        return {"success": True, "consumed": quantity}

    def get_equipped_stats(self, character_id: str) -> dict[str, Any]:
        """Aggregate stats from all equipped items that are not broken."""
        inv = self.get_inventory(character_id)
        aggregated: dict[str, Any] = {}
        for slot in inv.equipment.values():
            if slot.item and not slot.is_broken():
                for stat, value in slot.item.stats.items():
                    aggregated[stat] = aggregated.get(stat, 0) + value
        return aggregated

    def get_equipped_effects(self, character_id: str) -> dict[str, Any]:
        """Aggregate effects from all equipped items that are not broken."""
        inv = self.get_inventory(character_id)
        aggregated: dict[str, Any] = {}
        for slot in inv.equipment.values():
            if slot.item and not slot.is_broken():
                for key, value in slot.item.effects.items():
                    if isinstance(value, dict):
                        merged = aggregated.setdefault(key, {})
                        for sub_key, sub_val in value.items():
                            merged[sub_key] = merged.get(sub_key, 0) + sub_val
                    else:
                        aggregated[key] = aggregated.get(key, 0) + value
        return aggregated

    def _equip_type_for_item(self, item: Item) -> EquipmentSlotType | None:
        mapping = {
            ItemCategory.HELMET: EquipmentSlotType.HEAD,
            ItemCategory.HAT: EquipmentSlotType.HEAD,
            ItemCategory.ARMOR: EquipmentSlotType.CHEST,
            ItemCategory.CHEST: EquipmentSlotType.CHEST,
            ItemCategory.LEGS: EquipmentSlotType.LEGS,
            ItemCategory.LEGGING: EquipmentSlotType.LEGS,
            ItemCategory.PANTS: EquipmentSlotType.LEGS,
            ItemCategory.HANDS: EquipmentSlotType.HANDS,
            ItemCategory.GLOVES: EquipmentSlotType.HANDS,
            ItemCategory.GAUNTLETS: EquipmentSlotType.HANDS,
            ItemCategory.FEET: EquipmentSlotType.FEET,
            ItemCategory.BOOTS: EquipmentSlotType.FEET,
            ItemCategory.SHOES: EquipmentSlotType.FEET,
            ItemCategory.WEAPON: EquipmentSlotType.MAIN_HAND,
            ItemCategory.OFF_HAND: EquipmentSlotType.OFF_HAND,
            ItemCategory.SHIELD: EquipmentSlotType.OFF_HAND,
            ItemCategory.DAGGER: EquipmentSlotType.OFF_HAND,
            ItemCategory.RING: EquipmentSlotType.RING,
            ItemCategory.NECKLACE: EquipmentSlotType.NECKLACE,
            ItemCategory.AMULET: EquipmentSlotType.NECKLACE,
            ItemCategory.ACCESSORY: EquipmentSlotType.ACCESSORY,
            ItemCategory.CLOAK: EquipmentSlotType.ACCESSORY,
            ItemCategory.BELT: EquipmentSlotType.ACCESSORY,
        }
        return mapping.get(item.item_type)

    # --- durability -----------------------------------------------------------

    def damage_equipment(self, character_id: str, slot_type: str, amount: int) -> dict[str, Any]:
        """Reduce durability on an equipped item."""
        inv = self.get_inventory(character_id)
        try:
            equip_slot = inv.equipment[slot_type]
        except KeyError:
            return {"success": False, "reason": "Invalid equipment slot"}

        if equip_slot.is_empty():
            return {"success": False, "reason": "Slot is empty"}

        equip_slot.durability = max(0, equip_slot.durability - amount)
        if equip_slot.item:
            equip_slot.item.durability = equip_slot.durability

        return {
            "success": True,
            "slot": slot_type,
            "durability": equip_slot.durability,
            "max_durability": equip_slot.max_durability,
            "broken": equip_slot.is_broken(),
        }

    def repair_item(self, character_id: str, slot_type: str, amount: int | None = None) -> dict[str, Any]:
        """Restore durability on an equipped item."""
        inv = self.get_inventory(character_id)
        try:
            equip_slot = inv.equipment[slot_type]
        except KeyError:
            return {"success": False, "reason": "Invalid equipment slot"}

        if equip_slot.is_empty():
            return {"success": False, "reason": "Slot is empty"}

        if amount is None:
            equip_slot.durability = equip_slot.max_durability
        else:
            equip_slot.durability = min(equip_slot.max_durability, equip_slot.durability + amount)

        if equip_slot.item:
            equip_slot.item.durability = equip_slot.durability

        return {
            "success": True,
            "slot": slot_type,
            "durability": equip_slot.durability,
            "max_durability": equip_slot.max_durability,
        }

    def repair_all(self, character_id: str) -> dict[str, Any]:
        """Fully repair all equipped items."""
        inv = self.get_inventory(character_id)
        repaired = []
        for slot_name, slot in inv.equipment.items():
            if not slot.is_empty():
                slot.durability = slot.max_durability
                if slot.item:
                    slot.item.durability = slot.max_durability
                repaired.append(slot_name)
        return {"success": True, "repaired": repaired}

    # --- set bonuses ----------------------------------------------------------

    def get_equipped_set_pieces(self, character_id: str) -> dict[str, dict[str, int]]:
        """
        Return a mapping of set_id -> {set_piece -> count}.
        Only counts items that are not broken.
        """
        inv = self.get_inventory(character_id)
        sets: dict[str, dict[str, int]] = {}
        for slot in inv.equipment.values():
            if slot.item and not slot.is_broken() and slot.item.set_id:
                sid = slot.item.set_id
                piece = slot.item.set_piece or "unknown"
                sets.setdefault(sid, {})
                sets[sid][piece] = sets[sid].get(piece, 0) + 1
        return sets

    def get_active_set_bonuses(self, character_id: str) -> dict[str, dict[str, Any]]:
        """
        Return set_id -> bonus_stats for all sets where the piece count
        meets at least one threshold.
        """
        inv = self.get_inventory(character_id)
        piece_counts: dict[str, int] = {}
        for slot in inv.equipment.values():
            if slot.item and not slot.is_broken() and slot.item.set_id:
                piece_counts[slot.item.set_id] = piece_counts.get(slot.item.set_id, 0) + 1

        active: dict[str, dict[str, Any]] = {}
        for sid, count in piece_counts.items():
            eq_set = self._equipment_sets.get(sid)
            if not eq_set:
                continue
            best_bonus: dict[str, Any] = {}
            best_threshold = 0
            for threshold, bonus in eq_set.bonuses.items():
                if count >= threshold and threshold > best_threshold:
                    best_bonus = dict(bonus)
                    best_threshold = threshold
            if best_bonus:
                active[sid] = best_bonus
        return active

    def get_total_stats(self, character_id: str) -> dict[str, Any]:
        """
        Aggregate stats from equipped items plus active set bonuses.
        Broken items contribute no stats.
        """
        stats = self.get_equipped_stats(character_id)
        set_bonuses = self.get_active_set_bonuses(character_id)
        for bonus in set_bonuses.values():
            for stat, value in bonus.items():
                stats[stat] = stats.get(stat, 0) + value
        return stats

    # --- helpers --------------------------------------------------------------

    def _equip_type_for_item(self, item: Item) -> EquipmentSlotType | None:
        mapping = {
            ItemCategory.HELMET: EquipmentSlotType.HEAD,
            ItemCategory.HAT: EquipmentSlotType.HEAD,
            ItemCategory.ARMOR: EquipmentSlotType.CHEST,
            ItemCategory.CHEST: EquipmentSlotType.CHEST,
            ItemCategory.LEGS: EquipmentSlotType.LEGS,
            ItemCategory.LEGGING: EquipmentSlotType.LEGS,
            ItemCategory.PANTS: EquipmentSlotType.LEGS,
            ItemCategory.HANDS: EquipmentSlotType.HANDS,
            ItemCategory.GLOVES: EquipmentSlotType.HANDS,
            ItemCategory.GAUNTLETS: EquipmentSlotType.HANDS,
            ItemCategory.FEET: EquipmentSlotType.FEET,
            ItemCategory.BOOTS: EquipmentSlotType.FEET,
            ItemCategory.SHOES: EquipmentSlotType.FEET,
            ItemCategory.MAIN_HAND: EquipmentSlotType.MAIN_HAND,
            ItemCategory.WEAPON: EquipmentSlotType.MAIN_HAND,
            ItemCategory.SWORD: EquipmentSlotType.MAIN_HAND,
            ItemCategory.AXE: EquipmentSlotType.MAIN_HAND,
            ItemCategory.MACE: EquipmentSlotType.MAIN_HAND,
            ItemCategory.STAFF: EquipmentSlotType.MAIN_HAND,
            ItemCategory.OFF_HAND: EquipmentSlotType.OFF_HAND,
            ItemCategory.SHIELD: EquipmentSlotType.OFF_HAND,
            ItemCategory.DAGGER: EquipmentSlotType.OFF_HAND,
            ItemCategory.RING: EquipmentSlotType.RING,
            ItemCategory.NECKLACE: EquipmentSlotType.NECKLACE,
            ItemCategory.AMULET: EquipmentSlotType.NECKLACE,
            ItemCategory.CLOAK: EquipmentSlotType.ACCESSORY,
            ItemCategory.ACCESSORY: EquipmentSlotType.ACCESSORY,
            ItemCategory.BELT: EquipmentSlotType.ACCESSORY,
        }
        return mapping.get(item.item_type)

    def list_items(self, character_id: str | None = None) -> list[ItemSlot]:
        """Return all non-empty inventory slots for a character."""
        cid = character_id or self._character_id
        if cid is None:
            return []
        inv = self.get_inventory(cid)
        return [slot for slot in inv.slots if not slot.is_empty()]

    def get_equipped_item(self, character_id: str | None = None, slot_type: str | None = None) -> EquipmentSlot | None:
        """Return the equipped item in a given slot for a character."""
        cid = character_id or self._character_id
        if cid is None:
            return None
        inv = self.get_inventory(cid)
        if slot_type is not None:
            return inv.equipment.get(slot_type)
        # return first non-empty equipment slot
        for slot in inv.equipment.values():
            if not slot.is_empty():
                return slot
        return None

    def to_dict(self) -> dict[str, Any]:
        return {cid: inv.to_dict() for cid, inv in self._inventories.items()}
