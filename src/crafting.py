"""
RPG-09-01: Crafting System
Core data model for materials, items, recipes, stations, and character crafting state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Rarity(Enum):
    """Item/material rarity tiers."""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class ItemType(Enum):
    """Broad buckets for crafted items."""

    WEAPON = "weapon"
    ARMOR = "armor"
    POTION = "potion"
    FOOD = "food"
    TOOL = "tool"
    MATERIAL = "material"
    ACCESSORY = "accessory"


class StationCategory(Enum):
    """Categories of crafting stations."""

    FORGE = "forge"
    ALCHEMY = "alchemy"
    COOKING = "cooking"
    TAILORING = "tailoring"
    WORKBENCH = "workbench"


@dataclass
class Material:
    """Base resource gathered in the world."""

    id: str
    name: str
    description: str = ""
    rarity: Rarity = Rarity.COMMON
    stackable: bool = True
    max_stack: int = 99

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rarity": self.rarity.value,
            "stackable": self.stackable,
            "max_stack": self.max_stack,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Material:
        return Material(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            rarity=Rarity(data.get("rarity", "common")),
            stackable=data.get("stackable", True),
            max_stack=data.get("max_stack", 99),
        )


@dataclass
class Item:
    """A finished craftable item."""

    id: str
    name: str
    description: str = ""
    item_type: ItemType = ItemType.MATERIAL
    rarity: Rarity = Rarity.COMMON
    stackable: bool = True
    max_stack: int = 99
    stats: dict[str, Any] = field(default_factory=dict)
    effects: dict[str, Any] = field(default_factory=dict)

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
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Item:
        return Item(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            item_type=ItemType(data.get("item_type", "material")),
            rarity=Rarity(data.get("rarity", "common")),
            stackable=data.get("stackable", True),
            max_stack=data.get("max_stack", 99),
            stats=data.get("stats", {}),
            effects=data.get("effects", {}),
        )


@dataclass
class CraftingStation:
    """A station required for certain recipe categories."""

    id: str
    name: str
    description: str = ""
    allowed_categories: list[StationCategory] = field(default_factory=list)
    level_required: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "allowed_categories": [c.value for c in self.allowed_categories],
            "level_required": self.level_required,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CraftingStation:
        return CraftingStation(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            allowed_categories=[
                StationCategory(c) for c in data.get("allowed_categories", [])
            ],
            level_required=data.get("level_required", 1),
        )


@dataclass
class Ingredient:
    """Single material + quantity required for a recipe."""

    material_id: str
    quantity: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"material_id": self.material_id, "quantity": self.quantity}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Ingredient:
        return Ingredient(
            material_id=data["material_id"],
            quantity=data.get("quantity", 1),
        )


@dataclass
class Recipe:
    """Defines how to craft an item."""

    id: str
    name: str
    description: str = ""
    station_id: str | None = None
    category: StationCategory = StationCategory.WORKBENCH
    result_item_id: str = ""
    result_quantity: int = 1
    ingredients: list[Ingredient] = field(default_factory=list)
    skill_requirements: dict[str, int] = field(default_factory=dict)
    level_required: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "station_id": self.station_id,
            "category": self.category.value,
            "result_item_id": self.result_item_id,
            "result_quantity": self.result_quantity,
            "ingredients": [i.to_dict() for i in self.ingredients],
            "skill_requirements": dict(self.skill_requirements),
            "level_required": self.level_required,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Recipe:
        return Recipe(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            station_id=data.get("station_id"),
            category=StationCategory(data.get("category", "workbench")),
            result_item_id=data["result_item_id"],
            result_quantity=data.get("result_quantity", 1),
            ingredients=[Ingredient.from_dict(i) for i in data.get("ingredients", [])],
            skill_requirements=data.get("skill_requirements", {}),
            level_required=data.get("level_required", 1),
        )


@dataclass
class CharacterCraftingState:
    """Tracks a character's crafting knowledge and unlocked stations."""

    character_id: str
    known_recipes: set[str] = field(default_factory=set)
    unlocked_stations: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "known_recipes": sorted(self.known_recipes),
            "unlocked_stations": sorted(self.unlocked_stations),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CharacterCraftingState:
        state = CharacterCraftingState(
            character_id=data["character_id"],
        )
        state.known_recipes = set(data.get("known_recipes", []))
        state.unlocked_stations = set(data.get("unlocked_stations", []))
        return state
