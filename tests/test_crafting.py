"""
Tests for RPG-09-01 Crafting System.
Run with: python tests/test_crafting.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from crafting import (
    CharacterCraftingState,
    CraftingStation,
    Ingredient,
    Item,
    ItemType,
    Material,
    Rarity,
    Recipe,
    StationCategory,
)
from crafting_manager import CraftingManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _manager() -> CraftingManager:
    return CraftingManager(
        data_directory=os.path.join(os.path.dirname(__file__), "..", "data")
    )


# ---------------------------------------------------------------------------
# Dataclass round-trip tests
# ---------------------------------------------------------------------------

class TestMaterial:
    def test_to_from_dict_roundtrip(self):
        mat = Material(
            id="test_ore",
            name="Test Ore",
            description="A test material.",
            rarity=Rarity.UNCOMMON,
            stackable=True,
            max_stack=50,
        )
        data = mat.to_dict()
        restored = Material.from_dict(data)
        assert restored.id == "test_ore"
        assert restored.rarity == Rarity.UNCOMMON
        assert restored.max_stack == 50

    def test_default_values(self):
        mat = Material(id="m", name="M")
        assert mat.rarity == Rarity.COMMON
        assert mat.stackable is True
        assert mat.max_stack == 99


class TestItem:
    def test_to_from_dict_roundtrip(self):
        item = Item(
            id="test_sword",
            name="Test Sword",
            item_type=ItemType.WEAPON,
            rarity=Rarity.RARE,
            stackable=False,
            max_stack=1,
            stats={"attack_power": 15},
            effects={"on_hit": {"bleed_chance": 0.1}},
        )
        data = item.to_dict()
        restored = Item.from_dict(data)
        assert restored.id == "test_sword"
        assert restored.item_type == ItemType.WEAPON
        assert restored.rarity == Rarity.RARE
        assert restored.stats == {"attack_power": 15}


class TestIngredient:
    def test_to_from_dict_roundtrip(self):
        ing = Ingredient(material_id="iron_ingot", quantity=3)
        data = ing.to_dict()
        restored = Ingredient.from_dict(data)
        assert restored.material_id == "iron_ingot"
        assert restored.quantity == 3

    def test_default_quantity(self):
        ing = Ingredient(material_id="x")
        assert ing.quantity == 1


class TestRecipe:
    def test_to_from_dict_roundtrip(self):
        rec = Recipe(
            id="test.recipe",
            name="Test Recipe",
            station_id="forge",
            category=StationCategory.FORGE,
            result_item_id="sword",
            result_quantity=1,
            ingredients=[Ingredient(material_id="iron", quantity=2)],
            skill_requirements={"mining": 2},
            level_required=3,
        )
        data = rec.to_dict()
        restored = Recipe.from_dict(data)
        assert restored.id == "test.recipe"
        assert restored.category == StationCategory.FORGE
        assert restored.result_quantity == 1
        assert len(restored.ingredients) == 1
        assert restored.ingredients[0].material_id == "iron"


class TestCraftingStation:
    def test_to_from_dict_roundtrip(self):
        st = CraftingStation(
            id="test.forge",
            name="Test Forge",
            description="A test station.",
            allowed_categories=[StationCategory.FORGE],
            level_required=2,
        )
        data = st.to_dict()
        restored = CraftingStation.from_dict(data)
        assert restored.id == "test.forge"
        assert StationCategory.FORGE in restored.allowed_categories
        assert restored.level_required == 2


# ---------------------------------------------------------------------------
# CharacterCraftingState tests
# ---------------------------------------------------------------------------

class TestCharacterCraftingState:
    def test_initial_state(self):
        state = CharacterCraftingState(character_id="hero")
        assert state.known_recipes == set()
        assert state.unlocked_stations == set()

    def test_learn_recipe(self):
        state = CharacterCraftingState(character_id="hero")
        state.known_recipes.add("smelt_iron_ingot")
        assert "smelt_iron_ingot" in state.known_recipes

    def test_unlock_station(self):
        state = CharacterCraftingState(character_id="hero")
        state.unlocked_stations.add("stone_forge")
        assert "stone_forge" in state.unlocked_stations

    def test_to_from_dict(self):
        state = CharacterCraftingState(character_id="hero")
        state.known_recipes = {"r1", "r2"}
        state.unlocked_stations = {"s1"}
        data = state.to_dict()
        restored = CharacterCraftingState.from_dict(data)
        assert restored.character_id == "hero"
        assert restored.known_recipes == {"r1", "r2"}
        assert restored.unlocked_stations == {"s1"}


# ---------------------------------------------------------------------------
# CraftingManager integration tests
# ---------------------------------------------------------------------------

class TestCraftingManager:
    def test_load_data(self):
        mgr = _manager()
        assert len(mgr.materials) > 0
        assert len(mgr.items) > 0
        assert len(mgr.recipes) > 0
        assert len(mgr.stations) > 0

    def test_get_material(self):
        mgr = _manager()
        mat = mgr.get_material("iron_ore")
        assert mat is not None
        assert mat["name"] == "Iron Ore"

    def test_get_item(self):
        mgr = _manager()
        item = mgr.get_item("iron_sword")
        assert item is not None
        assert item["item_type"] == "weapon"

    def test_get_station(self):
        mgr = _manager()
        st = mgr.get_station("stone_forge")
        assert st is not None
        assert st["name"] == "Stone Forge"

    def test_get_available_recipes_empty(self):
        mgr = _manager()
        avail = mgr.get_available_recipes("new_hero")
        assert avail == []

    def test_learn_and_list_recipes(self):
        mgr = _manager()
        mgr.grant_recipe("hero", "smelt_iron_ingot")
        avail = mgr.get_available_recipes("hero")
        ids = [r["id"] for r in avail]
        assert "smelt_iron_ingot" in ids

    def test_can_craft_not_learned(self):
        mgr = _manager()
        ok, reason = mgr.can_craft("hero", "smelt_iron_ingot")
        assert ok is False
        assert "not learned" in reason.lower()

    def test_craft_success(self):
        mgr = _manager()
        mgr.grant_recipe("hero", "smelt_iron_ingot")
        result = mgr.craft("hero", "smelt_iron_ingot", quantity=1)
        assert result["success"] is True
        assert result["result_item_id"] == "iron_ingot"
        assert result["result_quantity"] == 1

    def test_craft_invalid_quantity(self):
        mgr = _manager()
        mgr.grant_recipe("hero", "smelt_iron_ingot")
        ok, reason = mgr.can_craft("hero", "smelt_iron_ingot", quantity=0)
        assert ok is False
        assert "quantity" in reason.lower()

    def test_unlock_station(self):
        mgr = _manager()
        r = mgr.unlock_station("hero", "stone_forge")
        assert r["success"] is True
        state = mgr.get_character_state("hero")
        assert "stone_forge" in state.unlocked_stations

    def test_recipe_ingredients_consumed(self):
        mgr = _manager()
        mgr.grant_recipe("hero", "smelt_iron_ingot")
        result = mgr.craft("hero", "smelt_iron_ingot", quantity=2)
        assert result["success"] is True
        consumed = {c["material_id"]: c["quantity"] for c in result["ingredients_consumed"]}
        assert consumed["iron_ore"] == 4
        assert consumed["coal"] == 2


if __name__ == "__main__":
    import traceback

    suites = [
        TestMaterial,
        TestItem,
        TestIngredient,
        TestRecipe,
        TestCraftingStation,
        TestCharacterCraftingState,
        TestCraftingManager,
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
