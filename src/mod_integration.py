"""
RPG-11-01: Mod Integration
Applies enabled mod data into existing game managers.
"""

from __future__ import annotations

import json
import os
from typing import Any


def _load_json_list(path: str, key: str) -> list[dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        entries = data if isinstance(data, list) else data.get(key, [])
        return [dict(e) for e in entries]
    except Exception:
        return []


def integrate_skill_tree_manager(manager, data_directory: str) -> None:
    from skill_tree_builder import load_tree_from_json
    for filename in os.listdir(data_directory):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(data_directory, filename)
        try:
            tree = load_tree_from_json(path)
            manager.trees[tree.id] = tree
        except Exception:
            continue


def integrate_ability_manager(manager, data_directory: str) -> None:
    from ability import Ability, AbilityTree
    tree_path = os.path.join(data_directory, "abilities.json")
    if os.path.isfile(tree_path):
        try:
            with open(tree_path, encoding="utf-8") as fh:
                data = json.load(fh)
            for tree_data in data.get("trees", []):
                tree = AbilityTree.from_dict(tree_data)
                manager.ability_trees[tree.id] = tree
            for ability_data in data.get("abilities", []):
                ability = Ability.from_dict(ability_data)
                manager.abilities[ability.id] = ability
        except Exception:
            pass


def integrate_milestone_manager(manager, data_directory: str) -> None:
    from milestone import MilestoneDefinition
    entries = _load_json_list(
        os.path.join(data_directory, "milestones.json"), "milestones"
    )
    for entry in entries:
        try:
            d = MilestoneDefinition.from_dict(entry)
            manager.register_definition(d)
        except Exception:
            continue


def integrate_crafting_manager(manager, data_directory: str) -> None:
    from crafting import CraftingStation, Item, Material, Recipe
    loaders = [
        ("crafting_materials.json", "materials", Material.from_dict, "materials"),
        ("crafting_items.json", "items", Item.from_dict, "items"),
        ("crafting_stations.json", "stations", CraftingStation.from_dict, "stations"),
        ("crafting_recipes.json", "recipes", Recipe.from_dict, "recipes"),
    ]
    for filename, key, from_dict_fn, attr in loaders:
        entries = _load_json_list(os.path.join(data_directory, filename), key)
        for entry in entries:
            try:
                obj = from_dict_fn(entry)
                getattr(manager, attr)[obj.id] = obj
            except Exception:
                continue


def integrate_status_manager(manager, data_directory: str) -> None:
    from status_conditions import StatusCondition
    entries = _load_json_list(
        os.path.join(data_directory, "status_conditions.json"), "conditions"
    )
    for entry in entries:
        try:
            cond = StatusCondition.from_dict(entry)
            manager.register_definition(cond)
        except Exception:
            continue


def integrate_character_customization_manager(manager, data_directory: str) -> None:
    from character_customization import (
        AppearanceOption,
        BackgroundDefinition,
        ClassDefinition,
    )
    path = os.path.join(data_directory, "character_customization.json")
    if not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for entry in data.get("classes", []):
            cls = ClassDefinition.from_dict(entry)
            manager._classes[cls.id] = cls
        for entry in data.get("backgrounds", []):
            bg = BackgroundDefinition.from_dict(entry)
            manager._backgrounds[bg.id] = bg
        for entry in data.get("appearances", []):
            opt = AppearanceOption.from_dict(entry)
            manager._appearances[opt.id] = opt
    except Exception:
        pass


def integrate_economy_manager(manager, data_directory: str) -> None:
    from economy import MerchantDefinition, PriceRule
    path = os.path.join(data_directory, "economy.json")
    if not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for entry in data.get("merchants", []):
            try:
                md = MerchantDefinition.from_dict(entry)
                manager._definitions[md.id] = md
            except Exception:
                continue
        for merchant_id, rules in data.get("price_rules", {}).items():
            for entry in rules:
                try:
                    pr = PriceRule.from_dict(entry)
                    manager._price_rules.setdefault(merchant_id, {})[pr.item_id] = pr
                except Exception:
                    continue
    except Exception:
        pass


def integrate_party_manager(manager, data_directory: str) -> None:
    from party import CompanionArchetype, PartyFormation
    path = os.path.join(data_directory, "companions.json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            for entry in data.get("companions", []):
                arch = CompanionArchetype.from_dict(entry)
                manager._archetypes[arch.id] = arch
        except Exception:
            pass
    path = os.path.join(data_directory, "formations.json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            for entry in data.get("formations", []):
                f = PartyFormation.from_dict(entry)
                manager._formations[f.formation_id] = f
        except Exception:
            pass


def integrate_title_system_manager(manager, data_directory: str) -> None:
    from title_system import TitleDefinition
    entries = _load_json_list(
        os.path.join(data_directory, "titles.json"), "titles"
    )
    for entry in entries:
        try:
            td = TitleDefinition.from_dict(entry)
            manager._definitions[td.id] = td
        except Exception:
            continue


def integrate_ai_narration_manager(manager, data_directory: str) -> None:
    from ai_narration import NarrationTemplate
    entries = _load_json_list(
        os.path.join(data_directory, "narration_templates.json"), "templates"
    )
    for entry in entries:
        try:
            tmpl = NarrationTemplate.from_dict(entry)
            manager._templates[tmpl.template_id] = tmpl
        except Exception:
            continue


# Registry of manager class name -> integrator function
INTEGRATORS: dict[str, Any] = {
    "SkillTreeManager": integrate_skill_tree_manager,
    "AbilityManager": integrate_ability_manager,
    "MilestoneManager": integrate_milestone_manager,
    "CraftingManager": integrate_crafting_manager,
    "StatusManager": integrate_status_manager,
    "CharacterCustomizationManager": integrate_character_customization_manager,
    "EconomyManager": integrate_economy_manager,
    "PartyManager": integrate_party_manager,
    "TitleManager": integrate_title_system_manager,
    "NarrationManager": integrate_ai_narration_manager,
}


def apply_mods_to_manager(manager: Any, mod_manager: Any) -> None:
    """
    Apply all enabled mod data into the given manager instance.

    The function looks up the manager class name in the INTEGRATORS
    registry and calls the corresponding integration function for each
    enabled mod's data directory.

    Args:
        manager: An instantiated game manager (e.g. SkillTreeManager)
        mod_manager: An instantiated ModManager with discovered mods
    """
    class_name = type(manager).__name__
    integrator = INTEGRATORS.get(class_name)
    if integrator is None:
        return
    for data_directory in mod_manager.get_enabled_mod_data_directories():
        try:
            integrator(manager, data_directory)
        except Exception:
            continue
