"""
RPG-08-14: Equipment System
Tests for equipment slots, durability, set bonuses, and stat aggregation.
Run with: python -m pytest tests/test_equipment.py -v
or:       python tests/test_equipment.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from typing import Any

from inventory import (
    EquipmentSet,
    EquipmentSlot,
    EquipmentSlotType,
    InventoryManager,
    InventoryState,
    Item,
    ItemRarity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(**overrides: Any) -> Item:
    data: dict[str, Any] = {
        "id": "test_item",
        "name": "Test Item",
        "description": "A test item.",
        "item_type": "weapon",
        "rarity": ItemRarity.RARE,
        "stackable": False,
        "max_stack": 1,
        "stats": {"attack_power": 10},
        "effects": {"bleed_chance": 0.05},
        "icon": "S",
        "set_id": None,
        "set_piece": None,
        "durability": 100,
        "max_durability": 100,
    }
    data.update(overrides)
    return Item.from_dict(data)


def _make_manager() -> InventoryManager:
    mgr = InventoryManager()
    mgr.register_equipment_set(EquipmentSet(
        set_id="dragon_armor",
        name="Dragon Armor",
        description="Ancient dragon-scaled armor.",
        pieces=["chest", "legs", "helmet", "gloves", "boots"],
        bonuses={
            2: {"defense": 15, "magic_resistance": 5},
            3: {"defense": 30, "magic_resistance": 10, "fire_resistance": 10},
            5: {"defense": 50, "magic_resistance": 20, "fire_resistance": 20, "dragon_blood": 1},
        },
    ))
    return mgr


# ---------------------------------------------------------------------------
# Item dataclass tests
# ---------------------------------------------------------------------------

class TestItem:
    def test_durability_defaults(self):
        item = _item()
        assert item.durability == 100
        assert item.max_durability == 100

    def test_is_broken_true(self):
        item = _item(durability=0)
        assert item.is_broken() is True

    def test_is_broken_false(self):
        item = _item(durability=50)
        assert item.is_broken() is False

    def test_negative_durability_is_broken(self):
        item = _item(durability=-5)
        assert item.is_broken() is True

    def test_set_fields(self):
        item = _item(set_id="dragon_armor", set_piece="chest")
        assert item.set_id == "dragon_armor"
        assert item.set_piece == "chest"

    def test_to_from_dict_with_durability(self):
        item = _item(durability=75, max_durability=150, set_id="test_set", set_piece="boots")
        restored = Item.from_dict(item.to_dict())
        assert restored.durability == 75
        assert restored.max_durability == 150
        assert restored.set_id == "test_set"
        assert restored.set_piece == "boots"


# ---------------------------------------------------------------------------
# EquipmentSlot tests
# ---------------------------------------------------------------------------

class TestEquipmentSlot:
    def test_empty(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.MAIN_HAND)
        assert slot.is_empty()

    def test_with_item(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.MAIN_HAND, item=_item())
        assert not slot.is_empty()

    def test_is_broken_false_when_full(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.CHEST, item=_item(), durability=100)
        assert not slot.is_broken()

    def test_is_broken_true_when_zero(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.CHEST, item=_item(), durability=0)
        assert slot.is_broken()

    def test_is_broken_false_when_empty(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.HEAD)
        assert not slot.is_broken()

    def test_roundtrip(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.CHEST, item=_item(), durability=80, max_durability=120)
        restored = EquipmentSlot.from_dict(slot.to_dict())
        assert restored.slot_type == EquipmentSlotType.CHEST
        assert restored.item.name == "Test Item"
        assert restored.durability == 80
        assert restored.max_durability == 120


# ---------------------------------------------------------------------------
# EquipmentSet tests
# ---------------------------------------------------------------------------

class TestEquipmentSet:
    def test_roundtrip(self):
        eq_set = EquipmentSet(
            set_id="shadow_set",
            name="Shadow Set",
            pieces=["chest", "legs", "helmet"],
            bonuses={2: {"stealth": 10}, 3: {"stealth": 25, "attack": 5}},
        )
        restored = EquipmentSet.from_dict(eq_set.to_dict())
        assert restored.set_id == "shadow_set"
        assert restored.bonuses[2] == {"stealth": 10}
        assert restored.bonuses[3] == {"stealth": 25, "attack": 5}

    def test_empty_bonuses(self):
        eq_set = EquipmentSet(set_id="empty", name="Empty")
        assert eq_set.bonuses == {}


# ---------------------------------------------------------------------------
# Durability tests
# ---------------------------------------------------------------------------

class TestDurability:
    def test_damage_equipment(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword", durability=100, max_durability=100)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        slot_idx = inv.get_empty_slot_index()
        mgr.equip_item("hero", "sword", slot_idx)
        r = mgr.damage_equipment("hero", "main_hand", 30)
        assert r["success"] is True
        assert r["durability"] == 70
        assert r["broken"] is False

    def test_damage_to_break(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword", durability=10, max_durability=100)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        slot_idx = inv.get_empty_slot_index()
        mgr.equip_item("hero", "sword", slot_idx)
        r = mgr.damage_equipment("hero", "main_hand", 15)
        assert r["success"] is True
        assert r["durability"] == 0
        assert r["broken"] is True

    def test_damage_empty_slot(self):
        mgr = _make_manager()
        r = mgr.damage_equipment("hero", "main_hand", 10)
        assert r["success"] is False
        assert "empty" in r["reason"].lower()

    def test_repair_item(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword", durability=30, max_durability=100)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        slot_idx = inv.get_empty_slot_index()
        mgr.equip_item("hero", "sword", slot_idx)
        r = mgr.repair_item("hero", "main_hand", 40)
        assert r["success"] is True
        assert r["durability"] == 70

    def test_repair_full(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword", durability=30, max_durability=100)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        slot_idx = inv.get_empty_slot_index()
        mgr.equip_item("hero", "sword", slot_idx)
        r = mgr.repair_item("hero", "main_hand")
        assert r["success"] is True
        assert r["durability"] == 100

    def test_repair_all(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword", durability=50, max_durability=100)
        shield = _item(id="shield", name="Shield", item_type="shield", durability=20, max_durability=80)
        mgr.add_item("hero", sword, quantity=1)
        mgr.add_item("hero", shield, quantity=1)
        inv = mgr.get_inventory("hero")
        idx1 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "sword", idx1)
        idx2 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "shield", idx2)
        r = mgr.repair_all("hero")
        assert r["success"] is True
        assert "main_hand" in r["repaired"]
        assert "off_hand" in r["repaired"]
        assert mgr.get_inventory("hero").equipment["main_hand"].durability == 100
        assert mgr.get_inventory("hero").equipment["off_hand"].durability == 80


# ---------------------------------------------------------------------------
# Set bonus tests
# ---------------------------------------------------------------------------

class TestSetBonuses:
    def test_register_and_list_sets(self):
        mgr = _make_manager()
        sets = mgr.list_equipment_sets()
        ids = [s["set_id"] for s in sets]
        assert "dragon_armor" in ids

    def test_get_equipped_set_pieces(self):
        mgr = _make_manager()
        chest = _item(id="dragon_chest", name="Dragon Chest", item_type="chest",
                      set_id="dragon_armor", set_piece="chest")
        legs = _item(id="dragon_legs", name="Dragon Legs", item_type="leggings",
                     set_id="dragon_armor", set_piece="legs")
        mgr.add_item("hero", chest, quantity=1)
        mgr.add_item("hero", legs, quantity=1)
        inv = mgr.get_inventory("hero")
        idx1 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_chest", idx1)
        idx2 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_legs", idx2)
        pieces = mgr.get_equipped_set_pieces("hero")
        assert "dragon_armor" in pieces
        assert pieces["dragon_armor"]["chest"] == 1
        assert pieces["dragon_armor"]["legs"] == 1

    def test_active_set_bonuses_threshold_2(self):
        mgr = _make_manager()
        chest = _item(id="dragon_chest", name="Dragon Chest", item_type="chest",
                      set_id="dragon_armor", set_piece="chest")
        legs = _item(id="dragon_legs", name="Dragon Legs", item_type="leggings",
                     set_id="dragon_armor", set_piece="legs")
        mgr.add_item("hero", chest, quantity=1)
        mgr.add_item("hero", legs, quantity=1)
        inv = mgr.get_inventory("hero")
        idx1 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_chest", idx1)
        idx2 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_legs", idx2)
        bonuses = mgr.get_active_set_bonuses("hero")
        assert "dragon_armor" in bonuses
        assert bonuses["dragon_armor"]["defense"] == 15
        assert bonuses["dragon_armor"]["magic_resistance"] == 5

    def test_active_set_bonuses_threshold_3(self):
        mgr = _make_manager()
        chest = _item(id="dragon_chest", name="Dragon Chest", item_type="chest",
                      set_id="dragon_armor", set_piece="chest")
        legs = _item(id="dragon_legs", name="Dragon Legs", item_type="leggings",
                     set_id="dragon_armor", set_piece="legs")
        helmet = _item(id="dragon_helm", name="Dragon Helm", item_type="helmet",
                       set_id="dragon_armor", set_piece="helmet")
        mgr.add_item("hero", chest, quantity=1)
        mgr.add_item("hero", legs, quantity=1)
        mgr.add_item("hero", helmet, quantity=1)
        inv = mgr.get_inventory("hero")
        idx1 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_chest", idx1)
        idx2 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_legs", idx2)
        idx3 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_helm", idx3)
        bonuses = mgr.get_active_set_bonuses("hero")
        assert bonuses["dragon_armor"]["defense"] == 30
        assert bonuses["dragon_armor"]["fire_resistance"] == 10

    def test_broken_items_dont_count_for_set(self):
        mgr = _make_manager()
        chest = _item(id="dragon_chest", name="Dragon Chest", item_type="chest",
                      set_id="dragon_armor", set_piece="chest", durability=0)
        legs = _item(id="dragon_legs", name="Dragon Legs", item_type="leggings",
                     set_id="dragon_armor", set_piece="legs")
        mgr.add_item("hero", chest, quantity=1)
        mgr.add_item("hero", legs, quantity=1)
        inv = mgr.get_inventory("hero")
        idx1 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_chest", idx1)
        idx2 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_legs", idx2)
        bonuses = mgr.get_active_set_bonuses("hero")
        assert "dragon_armor" not in bonuses


# ---------------------------------------------------------------------------
# Stat aggregation tests
# ---------------------------------------------------------------------------

class TestStatAggregation:
    def test_total_stats_includes_set_bonuses(self):
        mgr = _make_manager()
        chest = _item(id="dragon_chest", name="Dragon Chest", item_type="chest",
                      set_id="dragon_armor", set_piece="chest", stats={"defense": 10})
        legs = _item(id="dragon_legs", name="Dragon Legs", item_type="leggings",
                     set_id="dragon_armor", set_piece="legs", stats={"defense": 8})
        mgr.add_item("hero", chest, quantity=1)
        mgr.add_item("hero", legs, quantity=1)
        inv = mgr.get_inventory("hero")
        idx1 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_chest", idx1)
        idx2 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_legs", idx2)
        total = mgr.get_total_stats("hero")
        # 10 + 8 from items + 15 from 2-piece bonus
        assert total["defense"] == 33
        assert total["magic_resistance"] == 5

    def test_broken_items_excluded_from_stats(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword",
                      stats={"attack": 20}, durability=0)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        idx = inv.get_empty_slot_index()
        mgr.equip_item("hero", "sword", idx)
        stats = mgr.get_equipped_stats("hero")
        assert "attack" not in stats

    def test_unequip_removes_set_piece(self):
        mgr = _make_manager()
        chest = _item(id="dragon_chest", name="Dragon Chest", item_type="chest",
                      set_id="dragon_armor", set_piece="chest")
        legs = _item(id="dragon_legs", name="Dragon Legs", item_type="leggings",
                     set_id="dragon_armor", set_piece="legs")
        mgr.add_item("hero", chest, quantity=1)
        mgr.add_item("hero", legs, quantity=1)
        inv = mgr.get_inventory("hero")
        idx1 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_chest", idx1)
        idx2 = inv.get_empty_slot_index()
        mgr.equip_item("hero", "dragon_legs", idx2)
        mgr.unequip_item("hero", "chest")
        pieces = mgr.get_equipped_set_pieces("hero")
        assert "chest" not in pieces.get("dragon_armor", {})


# ---------------------------------------------------------------------------
# Roundtrip / persistence tests
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_inventory_state_roundtrip_with_durability(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword", durability=60, max_durability=100)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        idx = inv.get_empty_slot_index()
        mgr.equip_item("hero", "sword", idx)
        mgr.damage_equipment("hero", "main_hand", 10)
        state = mgr.to_dict()
        mgr2 = InventoryManager()
        mgr2.register_equipment_set(EquipmentSet(
            set_id="dragon_armor", name="Dragon Armor", pieces=[], bonuses={}
        ))
        mgr2._inventories["hero"] = InventoryState.from_dict(state["hero"])
        inv2 = mgr2.get_inventory("hero")
        assert inv2.equipment["main_hand"].durability == 50
        assert inv2.equipment["main_hand"].item.durability == 50


if __name__ == "__main__":
    import traceback

    suites = [
        TestItem,
        TestEquipmentSlot,
        TestEquipmentSet,
        TestDurability,
        TestSetBonuses,
        TestStatAggregation,
        TestPersistence,
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
