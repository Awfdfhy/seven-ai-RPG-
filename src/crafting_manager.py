"""
RPG-09-01: Crafting System
Top-level manager: loads material, recipe, and station definitions and
exposes a simple API for character crafting interaction.
"""

from __future__ import annotations

import json
import os
from typing import Any

from crafting import (
    CharacterCraftingState,
    CraftingStation,
    Item,
    Material,
    Recipe,
)


class CraftingManager:
    """
    Singleton-style manager that loads all crafting data files
    and provides methods for character crafting interaction.
    """

    def __init__(self, data_directory: str | None = None) -> None:
        if data_directory is None:
            data_directory = os.path.join(
                os.path.dirname(__file__), "..", "data"
            )
        self.materials: dict[str, Material] = {}
        self.items: dict[str, Item] = {}
        self.recipes: dict[str, Recipe] = {}
        self.stations: dict[str, CraftingStation] = {}
        self.character_states: dict[str, CharacterCraftingState] = {}

        self._load_materials(data_directory)
        self._load_items(data_directory)
        self._load_stations(data_directory)
        self._load_recipes(data_directory)

    # ------------------------------------------------------------------ #
    # Loaders
    # ------------------------------------------------------------------ #

    def _load_materials(self, directory: str) -> None:
        path = os.path.join(directory, "crafting_materials.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for mat_data in data.get("materials", []):
            mat = Material.from_dict(mat_data)
            self.materials[mat.id] = mat

    def _load_items(self, directory: str) -> None:
        path = os.path.join(directory, "crafting_items.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for item_data in data.get("items", []):
            item = Item.from_dict(item_data)
            self.items[item.id] = item

    def _load_stations(self, directory: str) -> None:
        path = os.path.join(directory, "crafting_stations.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for st_data in data.get("stations", []):
            st = CraftingStation.from_dict(st_data)
            self.stations[st.id] = st

    def _load_recipes(self, directory: str) -> None:
        path = os.path.join(directory, "crafting_recipes.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for rec_data in data.get("recipes", []):
            rec = Recipe.from_dict(rec_data)
            self.recipes[rec.id] = rec

    # ------------------------------------------------------------------ #
    # Character state helpers
    # ------------------------------------------------------------------ #

    def get_character_state(self, character_id: str) -> CharacterCraftingState:
        if character_id not in self.character_states:
            self.character_states[character_id] = CharacterCraftingState(
                character_id=character_id
            )
        return self.character_states[character_id]

    def register_recipe(self, recipe: Recipe) -> None:
        """Register a recipe definition directly."""
        self.recipes[recipe.id] = recipe

    def grant_recipe(self, character_id: str, recipe_id: str) -> dict[str, Any]:
        state = self.get_character_state(character_id)
        state.known_recipes.add(recipe_id)
        return {"success": True, "recipe_id": recipe_id}

    def unlock_station(self, character_id: str, station_id: str) -> dict[str, Any]:
        state = self.get_character_state(character_id)
        state.unlocked_stations.add(station_id)
        return {"success": True, "station_id": station_id}

    # ------------------------------------------------------------------ #
    # Crafting logic
    # ------------------------------------------------------------------ #

    def get_available_recipes(self, character_id: str) -> list[dict[str, Any]]:
        state = self.get_character_state(character_id)
        available: list[dict[str, Any]] = []
        for recipe in self.recipes.values():
            if recipe.id not in state.known_recipes:
                continue
            available.append({
                "id": recipe.id,
                "name": recipe.name,
                "description": recipe.description,
                "result_item_id": recipe.result_item_id,
                "result_quantity": recipe.result_quantity,
                "station_id": recipe.station_id,
                "category": recipe.category.value,
                "ingredients": [i.to_dict() for i in recipe.ingredients],
            })
        return available

    def can_craft(
        self, character_id: str, recipe_id: str, quantity: int = 1
    ) -> tuple[bool, str]:
        recipe = self.recipes.get(recipe_id)
        if recipe is None:
            return False, "Recipe not found."

        state = self.get_character_state(character_id)
        if recipe_id not in state.known_recipes:
            return False, "Recipe not learned."

        if quantity < 1:
            return False, "Quantity must be >= 1."

        for ingredient in recipe.ingredients:
            total_needed = ingredient.quantity * quantity
            # In a full system we'd check inventory; here we validate structure.
            if total_needed < 0:
                return False, f"Invalid quantity for {ingredient.material_id}."

        return True, ""

    def craft(
        self, character_id: str, recipe_id: str, quantity: int = 1
    ) -> dict[str, Any]:
        ok, reason = self.can_craft(character_id, recipe_id, quantity)
        if not ok:
            return {"success": False, "reason": reason}

        recipe = self.recipes[recipe_id]
        return {
            "success": True,
            "recipe_id": recipe_id,
            "quantity": quantity,
            "result_item_id": recipe.result_item_id,
            "result_quantity": recipe.result_quantity * quantity,
            "ingredients_consumed": [
                {
                    "material_id": i.material_id,
                    "quantity": i.quantity * quantity,
                }
                for i in recipe.ingredients
            ],
        }

    def get_material(self, material_id: str) -> dict[str, Any] | None:
        mat = self.materials.get(material_id)
        if mat is None:
            return None
        return mat.to_dict()

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        item = self.items.get(item_id)
        if item is None:
            return None
        return item.to_dict()

    def get_station(self, station_id: str) -> dict[str, Any] | None:
        st = self.stations.get(station_id)
        if st is None:
            return None
        return st.to_dict()

    def list_recipes(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self.recipes.values()]

    def list_materials(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self.materials.values()]

    def list_stations(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.stations.values()]
