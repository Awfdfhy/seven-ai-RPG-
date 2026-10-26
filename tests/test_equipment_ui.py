"""
Tests for RPG-08-14 Equipment UI
Run with: python tests/test_equipment_ui.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from equipment_ui import (
    EquipmentUI,
    EquipmentUISession,
    _colorize,
    _durability_bar,
    render_equipment_panel,
    render_equipment_slot,
    render_equipment_summary,
    render_stat_bonuses,
)
from inventory import (
    EquipmentSlot,
    EquipmentSlotType,
    InventoryManager,
    InventoryState,
    Item,
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
        "durability": 100,
        "max_durability": 100,
    }
    data.update(overrides)
    return Item.from_dict(data)


def _make_manager() -> InventoryManager:
    mgr = InventoryManager()
    from inventory import EquipmentSet
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
# Durability bar tests
# ---------------------------------------------------------------------------

class TestDurabilityBar:
    def test_full_bar(self):
        bar = _durability_bar(100)
        assert "█" in bar
        assert "░" not in bar

    def test_empty_bar(self):
        bar = _durability_bar(0)
        assert "░" in bar
        assert "█" not in bar

    def test_half_bar(self):
        bar = _durability_bar(50)
        assert "█" in bar
        assert "░" in bar


# ---------------------------------------------------------------------------
# Slot rendering tests
# ---------------------------------------------------------------------------

class TestRenderEquipmentSlot:
    def test_empty_slot(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.HEAD)
        out = render_equipment_slot(slot, "head")
        assert "Head" in out
        assert "(empty)" in out

    def test_equipped_slot_shows_name(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.MAIN_HAND, item=_item())
        out = render_equipment_slot(slot, "main_hand")
        assert "Test Item" in out
        assert "Main Hand" in out

    def test_equipped_slot_shows_stats(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.CHEST, item=_item())
        out = render_equipment_slot(slot, "chest")
        assert "Attack Power" in out
        assert "10" in out

    def test_equipped_slot_shows_effects(self):
        slot = EquipmentSlot(slot_type=EquipmentSlotType.RING, item=_item())
        out = render_equipment_slot(slot, "ring")
        assert "Bleed Chance" in out

    def test_equipped_slot_shows_durability(self):
        slot = EquipmentSlot(
            slot_type=EquipmentSlotType.FEET,
            item=_item(durability=75, max_durability=100),
            durability=75,
            max_durability=100,
        )
        out = render_equipment_slot(slot, "feet")
        assert "Durability" in out
        assert "75" in out


# ---------------------------------------------------------------------------
# Stat bonuses rendering tests
# ---------------------------------------------------------------------------

class TestRenderStatBonuses:
    def test_empty_stats(self):
        mgr = _make_manager()
        inv = InventoryState(character_id="hero")
        out = render_stat_bonuses(inv, mgr)
        assert "no bonuses active" in out.lower()

    def test_equipped_stats_displayed(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword", stats={"attack": 10})
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "sword", 0)
        out = render_stat_bonuses(inv, mgr)
        assert "attack" in out.lower()
        assert "10" in out

    def test_set_bonuses_displayed(self):
        mgr = _make_manager()
        chest = _item(
            id="dragon_chest",
            name="Dragon Chest",
            item_type="chest",
            set_id="dragon_armor",
            set_piece="chest",
        )
        legs = _item(
            id="dragon_legs",
            name="Dragon Legs",
            item_type="leggings",
            set_id="dragon_armor",
            set_piece="legs",
        )
        mgr.add_item("hero", chest, quantity=1)
        mgr.add_item("hero", legs, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "dragon_chest", 0)
        mgr.equip_item("hero", "dragon_legs", 1)
        out = render_stat_bonuses(inv, mgr)
        assert "Dragon Armor" in out
        assert "defense" in out.lower()
        assert "15" in out


# ---------------------------------------------------------------------------
# Equipment panel rendering tests
# ---------------------------------------------------------------------------

class TestRenderEquipmentPanel:
    def test_empty_panel(self):
        inv = InventoryState(character_id="hero")
        out = render_equipment_panel(inv)
        assert "EQUIPMENT" in out
        assert "hero" in out

    def test_panel_with_equipped_items(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword", stats={"attack": 10})
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "sword", 0)
        out = render_equipment_panel(inv, manager=mgr)
        assert "Sword" in out
        assert "Attack" in out
        assert "Total Stats" in out

    def test_panel_shows_set_bonuses(self):
        mgr = _make_manager()
        chest = _item(
            id="dragon_chest",
            name="Dragon Chest",
            item_type="chest",
            set_id="dragon_armor",
            set_piece="chest",
            stats={"defense": 10},
        )
        legs = _item(
            id="dragon_legs",
            name="Dragon Legs",
            item_type="leggings",
            set_id="dragon_armor",
            set_piece="legs",
        )
        mgr.add_item("hero", chest, quantity=1)
        mgr.add_item("hero", legs, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "dragon_chest", 0)
        mgr.equip_item("hero", "dragon_legs", 1)
        out = render_equipment_panel(inv, manager=mgr)
        assert "Dragon Armor" in out
        assert "defense" in out.lower()

    def test_panel_shows_durability_bar(self):
        mgr = _make_manager()
        sword = _item(
            id="sword",
            name="Sword",
            item_type="sword",
            durability=50,
            max_durability=100,
            stackable=False,
        )
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "sword", 0)
        out = render_equipment_panel(inv, manager=mgr)
        assert "Durability" in out


# ---------------------------------------------------------------------------
# Summary rendering tests
# ---------------------------------------------------------------------------

class TestRenderEquipmentSummary:
    def test_empty_summary(self):
        inv = InventoryState(character_id="hero")
        out = render_equipment_summary(inv)
        assert "nothing equipped" in out.lower() or "(nothing equipped)" in out.lower()

    def test_summary_with_items(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword")
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "sword", 0)
        out = render_equipment_summary(inv)
        assert "Sword" in out


# ---------------------------------------------------------------------------
# EquipmentUI facade tests
# ---------------------------------------------------------------------------

class TestEquipmentUI:
    def test_show_full_screen(self):
        mgr = _make_manager()
        ui = EquipmentUI(manager=mgr)
        out = ui.show_full_screen("hero")
        assert "EQUIPMENT" in out
        assert "hero" in out

    def test_show_summary(self):
        mgr = _make_manager()
        ui = EquipmentUI(manager=mgr)
        out = ui.show_summary("hero")
        assert isinstance(out, str)

    def test_show_stat_bonuses(self):
        mgr = _make_manager()
        ui = EquipmentUI(manager=mgr)
        out = ui.show_stat_bonuses("hero")
        assert "Stat Bonuses" in out

    def test_show_slot_tooltip_empty(self):
        mgr = _make_manager()
        ui = EquipmentUI(manager=mgr)
        out = ui.show_slot_tooltip("hero", "main_hand")
        assert "empty" in out.lower()

    def test_show_slot_tooltip_equipped(self):
        mgr = _make_manager()
        sword = _item(id="sword", name="Sword", item_type="sword")
        mgr.add_item("hero", sword, quantity=1)
        inv = mgr.get_inventory("hero")
        mgr.equip_item("hero", "sword", 0)
        ui = EquipmentUI(manager=mgr)
        out = ui.show_slot_tooltip("hero", "main_hand")
        assert "Sword" in out


# ---------------------------------------------------------------------------
# Colorize helper tests
# ---------------------------------------------------------------------------

class TestColorize:
    def test_returns_colored_text(self):
        out = _colorize("hello", "rare")
        assert "\033" in out

    def test_unknown_rarity_no_color(self):
        out = _colorize("hello", "unknown")
        # Should not contain ANSI codes for unknown rarity
        assert out == "hello"


# ---------------------------------------------------------------------------
# Interactive session smoke tests
# ---------------------------------------------------------------------------

class TestEquipmentUISession:
    def test_initial_render_does_not_crash(self):
        mgr = _make_manager()
        session = EquipmentUISession(mgr, "hero")
        session._running = False
        session._render_frame()

    def test_session_run_returns_inventory(self):
        mgr = _make_manager()
        session = EquipmentUISession(mgr, "hero")
        session._running = False
        result = session.run()
        assert result.character_id == "hero"


if __name__ == "__main__":
    import traceback

    suites = [
        TestDurabilityBar,
        TestRenderEquipmentSlot,
        TestRenderStatBonuses,
        TestRenderEquipmentPanel,
        TestRenderEquipmentSummary,
        TestEquipmentUI,
        TestColorize,
        TestEquipmentUISession,
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
