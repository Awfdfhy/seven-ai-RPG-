"""
Tests for RPG-10-17 Crafting UI
Run with: python tests/test_crafting_ui.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from typing import Any

from crafting_manager import CraftingManager
from crafting_ui import (
    CraftingUI,
    CraftingUISession,
    _colorize_rarity,
    create_crafting_session,
    render_craft_log,
    render_crafting_panel,
    render_recipe_card,
    render_recipe_detail,
    render_station_info,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _manager() -> CraftingManager:
    return CraftingManager(
        data_directory=os.path.join(os.path.dirname(__file__), "..", "data")
    )


def _recipe(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "test_recipe",
        "name": "Test Recipe",
        "description": "A test recipe.",
        "station_id": "stone_forge",
        "category": "forge",
        "result_item_id": "iron_sword",
        "result_quantity": 1,
        "ingredients": [{"material_id": "iron_ore", "quantity": 2}],
        "skill_requirements": {"mining": 1},
        "level_required": 1,
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Colorize helper tests
# ---------------------------------------------------------------------------


class TestColorizeRarity:
    def test_common_returns_colored(self):
        out = _colorize_rarity("hello", "common")
        assert "\033" in out

    def test_unknown_rarity_no_color(self):
        out = _colorize_rarity("hello", "unknown")
        assert out == "hello"

    def test_rare_is_blue(self):
        out = _colorize_rarity("hello", "rare")
        assert "\033[34m" in out


# ---------------------------------------------------------------------------
# Recipe card tests
# ---------------------------------------------------------------------------


class TestRenderRecipeCard:
    def test_basic_card(self):
        out = render_recipe_card(_recipe())
        assert "Test Recipe" in out
        assert "Iron Sword" in out or "iron_sword" in out
        assert "forge" in out

    def test_shows_ingredients(self):
        out = render_recipe_card(_recipe())
        assert "Iron Ore" in out or "iron_ore" in out
        assert "x2" in out

    def test_selected_marker(self):
        out = render_recipe_card(_recipe(), selected=True)
        assert "▶" in out

    def test_unselected_marker(self):
        out = render_recipe_card(_recipe(), selected=False)
        assert "▶" not in out

    def test_missing_requirements_message(self):
        out = render_recipe_card(_recipe(), can_craft=False)
        assert "missing requirements" in out.lower()

    def test_resolves_item_name_with_manager(self):
        mgr = _manager()
        out = render_recipe_card(_recipe(), manager=mgr)
        assert "Iron Sword" in out


# ---------------------------------------------------------------------------
# Recipe detail tests
# ---------------------------------------------------------------------------


class TestRenderRecipeDetail:
    def test_basic_detail(self):
        out = render_recipe_detail(_recipe())
        assert "RECIPE" in out
        assert "Test Recipe" in out or "Iron Sword" in out

    def test_shows_ingredients(self):
        out = render_recipe_detail(_recipe())
        assert "Ingredients:" in out

    def test_shows_station(self):
        out = render_recipe_detail(_recipe())
        assert "stone_forge" in out or "Stone Forge" in out

    def test_resolves_item_name(self):
        mgr = _manager()
        out = render_recipe_detail(_recipe(), manager=mgr)
        assert "Iron Sword" in out

    def test_unknown_recipe_returns_detail_anyway(self):
        out = render_recipe_detail(_recipe(recipe_id="does_not_exist"))
        assert "RECIPE" in out


# ---------------------------------------------------------------------------
# Crafting panel tests
# ---------------------------------------------------------------------------


class TestRenderCraftingPanel:
    def test_empty_character(self):
        mgr = _manager()
        out = render_crafting_panel("no_recipes_hero", mgr)
        assert "CRAFTING" in out
        assert "no_recipes_hero" in out

    def test_lists_available_recipes(self):
        mgr = _manager()
        mgr.grant_recipe("hero", "smelt_iron_ingot")
        out = render_crafting_panel("hero", mgr)
        assert "Smelt Iron Ingot" in out

    def test_groups_by_category(self):
        mgr = _manager()
        mgr.grant_recipe("hero", "smelt_iron_ingot")
        out = render_crafting_panel("hero", mgr)
        assert "Forge" in out

    def test_shows_category_icon(self):
        mgr = _manager()
        mgr.grant_recipe("hero", "smelt_iron_ingot")
        out = render_crafting_panel("hero", mgr)
        assert "⚒" in out


# ---------------------------------------------------------------------------
# Station info tests
# ---------------------------------------------------------------------------


class TestRenderStationInfo:
    def test_none_station(self):
        out = render_station_info(None)
        assert "unavailable" in out.lower()

    def test_station_details(self):
        station = {
            "id": "stone_forge",
            "name": "Stone Forge",
            "description": "A basic forge.",
            "allowed_categories": ["forge"],
            "level_required": 1,
        }
        out = render_station_info(station)
        assert "Stone Forge" in out
        assert "forge" in out


# ---------------------------------------------------------------------------
# Craft log tests
# ---------------------------------------------------------------------------


class TestRenderCraftLog:
    def test_empty_log(self):
        out = render_craft_log([])
        assert "Craft log" in out

    def test_entries_displayed(self):
        out = render_craft_log(["Made a sword"])
        assert "Made a sword" in out


# ---------------------------------------------------------------------------
# CraftingUI facade tests
# ---------------------------------------------------------------------------


class TestCraftingUI:
    def test_show_full_screen(self):
        mgr = _manager()
        ui = CraftingUI(mgr)
        out = ui.show_full_screen("hero")
        assert "CRAFTING" in out
        assert "hero" in out

    def test_show_recipe_detail_unknown(self):
        mgr = _manager()
        ui = CraftingUI(mgr)
        out = ui.show_recipe_detail("hero", "does_not_exist")
        assert "not found" in out.lower()

    def test_show_recipe_detail_known(self):
        mgr = _manager()
        mgr.grant_recipe("hero", "smelt_iron_ingot")
        ui = CraftingUI(mgr)
        out = ui.show_recipe_detail("hero", "smelt_iron_ingot")
        assert "Iron Ingot" in out

    def test_show_summary_empty(self):
        mgr = _manager()
        ui = CraftingUI(mgr)
        out = ui.show_summary("hero")
        assert "no recipes" in out.lower()

    def test_show_summary_with_recipes(self):
        mgr = _manager()
        mgr.grant_recipe("hero", "smelt_iron_ingot")
        ui = CraftingUI(mgr)
        out = ui.show_summary("hero")
        assert "Smelt Iron Ingot" in out


# ---------------------------------------------------------------------------
# Session smoke tests
# ---------------------------------------------------------------------------


class TestCraftingUISession:
    def test_initial_render_does_not_crash(self):
        mgr = _manager()
        session = CraftingUISession(mgr, "hero")
        session._running = False
        session._render_frame()

    def test_create_factory(self):
        mgr = _manager()
        session = create_crafting_session(mgr, "hero")
        assert isinstance(session, CraftingUISession)


if __name__ == "__main__":
    import traceback

    suites = [
        TestColorizeRarity,
        TestRenderRecipeCard,
        TestRenderRecipeDetail,
        TestRenderCraftingPanel,
        TestRenderStationInfo,
        TestRenderCraftLog,
        TestCraftingUI,
        TestCraftingUISession,
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
