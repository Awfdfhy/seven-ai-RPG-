"""
Tests for RPG-08-13 Inventory UI
Run with: python tests/test_inventory.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from inventory import (
    EquipmentSlot,
    EquipmentSlotType,
    InventoryManager,
    InventoryState,
    Item,
    ItemCategory,
    ItemRarity,
    ItemSlot,
)
from inventory_ui import (
    InventoryUI,
    render_compact_tooltip,
    render_equipment_panel,
    render_equipment_summary,
    render_inventory_grid,
    render_inventory_list,
    render_tooltip,
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
        "rarity": "rare",
        "stackable": False,
        "max_stack": 1,
        "stats": {"attack_power": 10},
        "effects": {"bleed_chance": 0.05},
        "icon": "S",
    }
    data.update(overrides)
    return Item.from_dict(data)


# ---------------------------------------------------------------------------
# Item dataclass tests
# ---------------------------------------------------------------------------

class TestItem:
    def test_roundtrip(self):
        item = _item()
        restored = Item.from_dict(item.to_dict())
        assert restored.id == item.id
        assert restored.rarity == ItemRarity.RARE
        assert restored.stats["attack_power"] == 10

    def test_default_rarity(self):
        item = Item(id="x", name="X")
        assert item.rarity == ItemRarity.COMMON

    def test_item_category_enum(self):
        item = _item(item_type="weapon")
        assert item.item_type == ItemCategory.WEAPON
        assert item.item_type.value == "weapon"

    def test_durability_roundtrip(self):
        item = _item(durability=50, max_durability=100)
        assert item.durability == 50
        assert item.max_durability == 100
        restored = Item.from_dict(item.to_dict())
        assert restored.durability == 50
        assert restored.max_durability == 100

    def test_is_broken(self):
        item = _item(durability=0)
        assert item.is_broken()
        item2 = _item(durability=10)
        assert not item2.is_broken()

    def test_item_type_string_normalized(self):
        item = Item(id="y", name="Y", item_type="armor")
        assert item.item_type == ItemCategory.ARMOR


# ---------------------------------------------------------------------------
# ItemSlot tests
# ---------------------------------------------------------------------------

class TestItemSlot:
    def test_empty(self):
        slot = ItemSlot(slot_index=0)
        assert slot.is_empty()

    def test_with_item(self):
        slot = ItemSlot(slot_index=0, item=_item(), quantity=2)
        assert not slot.is_empty()
        assert slot.quantity == 2

    def test_roundtrip(self):
        slot = ItemSlot(slot_index=3, item=_item(), quantity=5)
        restored = ItemSlot.from_dict(slot.to_dict())
        assert restored.slot_index == 3
        assert restored.quantity == 5
        assert restored.item.id == "test_item"


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

    def test_roundtrip(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.CHEST, item=_item())
        restored = EquipmentSlot.from_dict(slot.to_dict())
        assert restored.slot_type == EquipmentSlotType.CHEST
        assert restored.item.name == "Test Item"


# ---------------------------------------------------------------------------
# InventoryState tests
# ---------------------------------------------------------------------------

class TestInventoryState:
    def test_initial_state(self):
        state = InventoryState(character_id="hero")
        assert state.capacity == 24
        assert len(state.slots) == 24
        assert state.gold == 0

    def test_get_empty_slot(self):
        state = InventoryState(character_id="hero")
        idx = state.get_empty_slot_index()
        assert idx == 0

    def test_total_quantity_empty(self):
        state = InventoryState(character_id="hero")
        assert state.total_quantity("potion") == 0
        assert not state.has_item("potion")

    def test_roundtrip(self):
        state = InventoryState(character_id="hero", capacity=10, gold=50)
        state.slots[0] = ItemSlot(slot_index=0, item=_item(), quantity=3)
        state.equipment["main_hand"] = EquipmentSlot(
            slot_type=EquipmentSlotType.MAIN_HAND, item=_item()
        )
        restored = InventoryState.from_dict(state.to_dict())
        assert restored.character_id == "hero"
        assert restored.capacity == 10
        assert restored.gold == 50
        assert restored.slots[0].quantity == 3
        assert restored.equipment["main_hand"].item.id == "test_item"


# ---------------------------------------------------------------------------
# InventoryManager tests
# ---------------------------------------------------------------------------

class TestInventoryManager:
    def test_get_inventory_creates(self):
        mgr = InventoryManager()
        inv = mgr.get_inventory("hero")
        assert inv.character_id == "hero"

    def test_add_stackable(self):
        mgr = InventoryManager()
        potion = _item(id="potion", name="Potion", stackable=True, max_stack=10)
        r = mgr.add_item("hero", potion, quantity=5)
        assert r["success"] is True
        assert r["added"] == 5
        inv = mgr.get_inventory("hero")
        assert inv.total_quantity("potion") == 5

    def test_add_non_stackable(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", stackable=False, max_stack=1)
        # Add 3 non-stackable items; should fill 3 slots
        r1 = mgr.add_item("hero", sword, quantity=1)
        r2 = mgr.add_item("hero", sword, quantity=1)
        r3 = mgr.add_item("hero", sword, quantity=1)
        assert r1["success"] is True
        assert r2["success"] is True
        assert r3["success"] is True
        inv = mgr.get_inventory("hero")
        assert inv.total_quantity("sword") == 3
        # Exceeding capacity should fail
        r4 = mgr.add_item("hero", sword, quantity=22)
        assert r4["success"] is False
        assert r4["reason"] == "Inventory full"

    def test_add_merges_stack(self):
        mgr = InventoryManager()
        potion = _item(id="potion", name="Potion", stackable=True, max_stack=10)
        mgr.add_item("hero", potion, quantity=3)
        mgr.add_item("hero", potion, quantity=4)
        inv = mgr.get_inventory("hero")
        assert inv.total_quantity("potion") == 7

    def test_remove_item(self):
        mgr = InventoryManager()
        potion = _item(id="potion", name="Potion", stackable=True, max_stack=99)
        mgr.add_item("hero", potion, quantity=5)
        r = mgr.remove_item("hero", "potion", quantity=2)
        assert r["success"] is True
        inv = mgr.get_inventory("hero")
        assert inv.total_quantity("potion") == 3

    def test_equip_weapon(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", item_type="weapon", stackable=False)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        slot_idx = inv.get_empty_slot_index()
        assert slot_idx == 1  # slot 0 now has the sword
        r = mgr.equip_item("hero", "sword", 0)
        assert r["success"] is True
        assert inv.equipment["main_hand"].item.id == "sword"
        assert inv.slots[0].is_empty()

    def test_equip_invalid_type(self):
        mgr = InventoryManager()
        ore = _item(id="ore", name="Ore", item_type="material", stackable=True)
        mgr.add_item("hero", ore, quantity=1)
        inv = mgr.get_inventory("hero")
        r = mgr.equip_item("hero", "ore", 0)
        assert r["success"] is False

    def test_unequip_item(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", item_type="weapon", stackable=False)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "sword", 0)
        r = mgr.unequip_item("hero", "main_hand")
        assert r["success"] is True
        assert inv.equipment["main_hand"].is_empty()
        assert not inv.slots[0].is_empty()

    def test_get_equipped_stats(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", item_type="weapon", stats={"attack": 10})
        shield = _item(id="shield", name="Shield", item_type="shield", stats={"defense": 5})
        mgr.add_item("hero", sword, quantity=1)
        mgr.add_item("hero", shield, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "sword", 0)
        mgr.equip_item("hero", "shield", 1)
        stats = mgr.get_equipped_stats("hero")
        assert stats["attack"] == 10
        assert stats["defense"] == 5


# ---------------------------------------------------------------------------
# UI rendering tests
# ---------------------------------------------------------------------------

class TestUIRendering:
    def test_tooltip_contains_name(self):
        item = _item()
        tip = render_tooltip(item)
        assert item.name in tip

    def test_tooltip_contains_stats(self):
        item = _item()
        tip = render_tooltip(item)
        assert "Attack Power" in tip
        assert "10" in tip

    def test_tooltip_contains_effects(self):
        item = _item()
        tip = render_tooltip(item)
        assert "Bleed Chance" in tip

    def test_compact_tooltip(self):
        item = _item()
        text = render_compact_tooltip(item)
        assert item.name in text

    def test_inventory_grid_empty(self):
        inv = InventoryState(character_id="hero")
        out = render_inventory_grid(inv)
        assert "Inventory" in out
        assert "hero" in out

    def test_inventory_list_empty(self):
        inv = InventoryState(character_id="hero")
        out = render_inventory_list(inv)
        assert "empty" in out.lower()

    def test_equipment_panel_empty(self):
        inv = InventoryState(character_id="hero")
        out = render_equipment_panel(inv)
        assert "Equipment" in out

    def test_equipment_summary_empty(self):
        inv = InventoryState(character_id="hero")
        out = render_equipment_summary(inv)
        assert "nothing equipped" in out.lower() or "empty" in out.lower()

    def test_full_screen_render(self):
        ui = InventoryUI()
        out = ui.show_full_screen("hero")
        assert "INVENTORY" in out
        assert "hero" in out

    def test_show_tooltip_empty_slot(self):
        ui = InventoryUI()
        out = ui.show_tooltip("hero", 0)
        assert "empty" in out.lower()

    def test_show_equipment_tooltip_empty(self):
        ui = InventoryUI()
        out = ui.show_equipment_tooltip("hero", "main_hand")
        assert "empty" in out.lower()


# ---------------------------------------------------------------------------
# ItemCategory / Rarity expansion tests
# ---------------------------------------------------------------------------

class TestItemCategory:
    def test_default_category(self):
        item = Item(id="x", name="X")
        assert item.item_type == ItemCategory.MISC

    def test_from_dict_string_category(self):
        item = Item.from_dict({"id": "sword", "name": "Sword", "item_type": "weapon"})
        assert item.item_type == ItemCategory.WEAPON

    def test_roundtrip_category(self):
        item = _item(item_type="weapon")
        restored = Item.from_dict(item.to_dict())
        assert restored.item_type == ItemCategory.WEAPON

    def test_equip_mapping_sword(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", item_type=ItemCategory.SWORD, stackable=False)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        r = mgr.equip_item("hero", "sword", 0)
        assert r["success"] is True
        assert inv.equipment["main_hand"].item.id == "sword"


# ---------------------------------------------------------------------------
# Durability tests
# ---------------------------------------------------------------------------

class TestDurability:
    def test_is_broken_false_when_no_durability(self):
        item = Item(id="potion", name="Potion", max_durability=0, durability=0)
        assert not item.is_broken()

    def test_is_broken_true_when_zero(self):
        item = Item(id="sword", name="Sword", max_durability=100, durability=0)
        assert item.is_broken()

    def test_is_broken_false_when_positive(self):
        item = Item(id="sword", name="Sword", max_durability=100, durability=50)
        assert not item.is_broken()

    def test_durability_percent(self):
        item = Item(id="sword", name="Sword", max_durability=100, durability=75)
        assert item.durability_percent() == 0.75

    def test_damage_item(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", item_type=ItemCategory.SWORD, max_durability=10, durability=10, stackable=False)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        r = mgr.damage_item("hero", 0, 3)
        assert r["success"] is True
        assert r["durability"] == 7
        assert not r["broken"]

    def test_damage_breaks_item(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", item_type=ItemCategory.SWORD, max_durability=5, durability=5, stackable=False)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        r = mgr.damage_item("hero", 0, 5)
        assert r["success"] is True
        assert r["broken"] is True
        assert inv.slots[0].is_empty()

    def test_repair_item(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", item_type=ItemCategory.SWORD, max_durability=10, durability=3, stackable=False)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "sword", 0)
        r = mgr.repair_item("hero", "main_hand", 4)
        assert r["success"] is True
        assert r["durability"] == 7

    def test_repair_caps_at_max(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", item_type=ItemCategory.SWORD, max_durability=10, durability=8, stackable=False)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "sword", 0)
        r = mgr.repair_item("hero", "main_hand", 10)
        assert r["success"] is True
        assert r["durability"] == 10

    def test_indestructible_item(self):
        mgr = InventoryManager()
        potion = _item(id="potion", name="Potion", max_durability=0, durability=0)
        mgr.add_item("hero", potion, quantity=1)
        r = mgr.damage_item("hero", 0, 5)
        assert r["success"] is True
        assert r["reason"] == "Item is indestructible"
        assert mgr.get_inventory("hero").slots[0].item is not None

    def test_equip_broken_item_fails(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", item_type=ItemCategory.SWORD, max_durability=5, durability=0, stackable=False)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        r = mgr.equip_item("hero", "sword", 0)
        assert r["success"] is False
        assert inv.equipment["main_hand"].is_empty()

    def test_consume_item(self):
        mgr = InventoryManager()
        potion = _item(id="potion", name="Potion", stackable=True, max_stack=99)
        mgr.add_item("hero", potion, quantity=5)
        r = mgr.consume_item("hero", "potion", 3)
        assert r["success"] is True
        assert r["consumed"] == 3
        inv = mgr.get_inventory("hero")
        assert inv.total_quantity("potion") == 2

    def test_consume_not_enough(self):
        mgr = InventoryManager()
        potion = _item(id="potion", name="Potion", stackable=True, max_stack=99)
        mgr.add_item("hero", potion, quantity=2)
        r = mgr.consume_item("hero", "potion", 5)
        assert r["success"] is False
        assert mgr.get_inventory("hero").total_quantity("potion") == 2


# ---------------------------------------------------------------------------
# Equipment set tests
# ---------------------------------------------------------------------------

class TestEquipmentSet:
    def test_roundtrip(self):
        from inventory import EquipmentSet
        eq_set = EquipmentSet(
            set_id="dragon",
            name="Dragon Set",
            pieces=["chest", "legs", "helm"],
            bonuses={2: {"defense": 10}, 3: {"fire_resist": 0.25}},
        )
        restored = EquipmentSet.from_dict(eq_set.to_dict())
        assert restored.set_id == "dragon"
        assert restored.bonuses[3]["fire_resist"] == 0.25


# ---------------------------------------------------------------------------
# UI durability rendering tests
# ---------------------------------------------------------------------------

class TestUIDurability:
    def test_tooltip_shows_durability(self):
        item = _item(max_durability=100, durability=75)
        tip = render_tooltip(item)
        assert "Durability" in tip
        assert "75/100" in tip

    def test_tooltip_no_durability_when_indestructible(self):
        item = _item(max_durability=0)
        tip = render_tooltip(item)
        assert "Durability" not in tip

    def test_compact_tooltip_shows_durability(self):
        item = _item(max_durability=50, durability=25)
        text = render_compact_tooltip(item)
        assert "25/50HP" in text

    def test_equipment_panel_shows_durability(self):
        mgr = InventoryManager()
        sword = _item(id="sword", name="Sword", item_type=ItemCategory.SWORD, max_durability=80, durability=60, stackable=False)
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "sword", 0)
        out = render_equipment_panel(inv)
        assert "Durability" in out
        assert "60/80" in out


if __name__ == "__main__":
    import traceback

    suites = [
        TestItem,
        TestItemSlot,
        TestEquipmentSlot,
        TestInventoryState,
        TestInventoryManager,
        TestUIRendering,
        TestItemCategory,
        TestDurability,
        TestEquipmentSet,
        TestUIDurability,
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
