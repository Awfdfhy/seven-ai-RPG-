"""
Data integrity tests for Seven RPG JSON data files.

Validates:
- Files are valid JSON
- Top-level keys are present where expected
- Required fields exist on entries
- IDs are unique within each file
- Enums / categorical fields contain known-safe values
"""

from __future__ import annotations

import json
import os

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

KNOWN_ABILITY_CATEGORIES = {"magic", "physical", "stealth", "support", "passive", "combat"}
KNOWN_TARGET_TYPES = {"self", "ally", "enemy", "aoe", "cone", "line", "party", "ground_targeted"}
KNOWN_EFFECT_TYPES = {"damage", "heal", "dot", "hot", "buff", "debuff", "knockback", "stun"}
KNOWN_ITEM_RARITIES = {"common", "uncommon", "rare", "epic", "legendary", "mythic"}
KNOWN_CRAFTING_STATIONS = {"forge", "alchemy", "workbench", "anvil", "cauldron", "loom"}
KNOWN_DIFFICULTIES = {"easy", "normal", "hard", "nightmare"}


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Generic JSON validity
# ---------------------------------------------------------------------------

class TestDataJsonValidity:
    @pytest.mark.data
    def test_all_data_files_are_valid_json(self, data_files):
        for path in data_files:
            with open(path, encoding="utf-8") as f:
                json.load(f)  # will raise if invalid

    @pytest.mark.data
    def test_data_files_are_dicts(self, data_files):
        for path in data_files:
            data = _load_json(path)
            assert isinstance(data, (dict, list)), f"{path} top-level is not a dict or list"


# ---------------------------------------------------------------------------
# Abilities data
# ---------------------------------------------------------------------------

class TestAbilitiesData:
    def _data_file(self):
        return "abilities.json"

    def load_data(self, data_path: str):
        filename = self._data_file()
        self.data = _load_json(os.path.join(data_path, filename))

    @pytest.fixture(autouse=True)
    def setup(self, data_path: str):
        self.load_data(data_path)

    def test_top_level_key(self):
        assert "abilities" in self.data

    def test_unique_ids(self):
        ids = [a["id"] for a in self.data.get("abilities", [])]
        assert len(ids) == len(set(ids)), "Duplicate ability IDs found"

    def test_required_fields(self):
        required = {"id", "name", "description", "category", "target_type"}
        for ability in self.data.get("abilities", []):
            missing = required - ability.keys()
            assert not missing, f"Ability {ability.get('id')} missing: {missing}"

    def test_valid_categories(self):
        for ability in self.data.get("abilities", []):
            assert ability.get("category") in KNOWN_ABILITY_CATEGORIES, \
                f"Unknown category '{ability.get('category')}' in {ability.get('id')}"

    def test_valid_target_types(self):
        for ability in self.data.get("abilities", []):
            assert ability.get("target_type") in KNOWN_TARGET_TYPES, \
                f"Unknown target_type '{ability.get('target_type')}' in {ability.get('id')}"

    def test_effects_have_required_fields(self):
        required = {"effect_type", "value", "chance"}
        for ability in self.data.get("abilities", []):
            for effect in ability.get("effects", []):
                missing = required - effect.keys()
                assert not missing, \
                    f"Effect in {ability.get('id')} missing: {missing}"


# ---------------------------------------------------------------------------
# Crafting data
# ---------------------------------------------------------------------------

class TestCraftingData:
    @pytest.fixture(autouse=True)
    def load_data(self, data_path: str):
        self.data = _load_json(os.path.join(data_path, "crafting_recipes.json"))

    def test_top_level_key(self):
        assert "recipes" in self.data

    def test_unique_recipe_ids(self):
        ids = [r["id"] for r in self.data.get("recipes", [])]
        assert len(ids) == len(set(ids)), "Duplicate recipe IDs found"

    def test_recipe_has_ingredients(self):
        for recipe in self.data.get("recipes", []):
            assert "ingredients" in recipe, f"Recipe {recipe.get('id')} missing ingredients"
            assert isinstance(recipe["ingredients"], list)
            assert len(recipe["ingredients"]) > 0


# ---------------------------------------------------------------------------
# Loot tables data
# ---------------------------------------------------------------------------

class TestLootTablesData:
    @pytest.fixture(autouse=True)
    def load_data(self, data_path: str):
        self.data = _load_json(os.path.join(data_path, "loot_tables.json"))

    def test_top_level_key(self):
        # loot_tables.json is a top-level list of loot tables
        assert isinstance(self.data, list)

    def test_unique_ids(self):
        ids = [lt["id"] for lt in self.data]
        assert len(ids) == len(set(ids)), "Duplicate loot table IDs found"

    def test_entries_have_required_fields(self):
        required = {"item_id", "weight", "min_quantity", "max_quantity"}
        for table in self.data:
            for entry in table.get("entries", []):
                missing = required - entry.keys()
                assert not missing, \
                    f"Loot entry in {table.get('id')} missing: {missing}"


# ---------------------------------------------------------------------------
# World map data
# ---------------------------------------------------------------------------

class TestWorldMapData:
    @pytest.fixture(autouse=True)
    def load_data(self, data_path: str):
        self.data = _load_json(os.path.join(data_path, "world_map.json"))

    def test_top_level_key(self):
        # world_map.json is a top-level list of locations
        assert isinstance(self.data, list)

    def test_unique_location_ids(self):
        ids = [loc["id"] for loc in self.data]
        assert len(ids) == len(set(ids)), "Duplicate location IDs found"

    def test_location_has_coordinates(self):
        for loc in self.data:
            assert "x" in loc and "y" in loc, f"Location {loc.get('id')} missing x/y"


# ---------------------------------------------------------------------------
# Quests data
# ---------------------------------------------------------------------------

class TestQuestsData:
    @pytest.fixture(autouse=True)
    def load_data(self, data_path: str):
        self.data = _load_json(os.path.join(data_path, "quests.json"))

    def test_top_level_key(self):
        # quests.json is a top-level list of quests
        assert isinstance(self.data, list)

    def test_unique_quest_ids(self):
        ids = [q["id"] for q in self.data]
        assert len(ids) == len(set(ids)), "Duplicate quest IDs found"

    def test_quest_has_title_and_description(self):
        for quest in self.data:
            assert "title" in quest or "name" in quest, f"Quest {quest.get('id')} missing title/name"
            assert "description" in quest, f"Quest {quest.get('id')} missing description"
