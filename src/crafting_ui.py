"""
RPG-10-17: Crafting UI
Terminal-based crafting interface with recipe list, ingredient checklist,
station info, and interactive crafting session.
"""

from __future__ import annotations

import os
from typing import Any

from accessibility import AccessibilityHelper
from crafting_manager import CraftingManager

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_INVERSE = "\033[7m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"
_WHITE = "\033[37m"

def _red(text: str) -> str:
    return f"{_RED}{text}{_RESET}"

def _green(text: str) -> str:
    return f"{_GREEN}{text}{_RESET}"

def _yellow(text: str) -> str:
    return f"{_YELLOW}{text}{_RESET}"

def _blue(text: str) -> str:
    return f"{_BLUE}{text}{_RESET}"

def _magenta(text: str) -> str:
    return f"{_MAGENTA}{text}{_RESET}"

def _cyan(text: str) -> str:
    return f"{_CYAN}{text}{_RESET}"

def _white(text: str) -> str:
    return f"{_WHITE}{text}{_RESET}"

_RARITY_COLORS: dict[str, str] = {
    "common": _WHITE,
    "uncommon": _GREEN,
    "rare": _BLUE,
    "epic": _MAGENTA,
    "legendary": _YELLOW,
}

_CATEGORY_ICONS: dict[str, str] = {
    "forge": "⚒",
    "alchemy": "⚗",
    "cooking": "🍲",
    "tailoring": "🧵",
    "workbench": "🔨",
}

_ITEM_TYPE_ICONS: dict[str, str] = {
    "weapon": "⚔",
    "armor": "🛡",
    "potion": "🧪",
    "food": "🍖",
    "tool": "🔧",
    "material": "💎",
    "accessory": "💍",
}


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def _bold(text: str) -> str:
    return f"{_BOLD}{text}{_RESET}"


def _dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}"


def _colorize_rarity(
    text: str,
    rarity: str,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    if accessibility is not None:
        colors = accessibility.accessible_rarity_colors()
        code = colors.get(rarity, "")
        reset = accessibility.get_color("reset")
        if not code:
            return text
        return f"{code}{text}{reset}"
    code = _RARITY_COLORS.get(rarity, "")
    if not code:
        return text
    return f"{code}{text}{_RESET}"


# ---------------------------------------------------------------------------
# Recipe rendering
# ---------------------------------------------------------------------------


def render_recipe_card(
    recipe: dict[str, Any],
    *,
    manager: CraftingManager | None = None,
    accessibility: AccessibilityHelper | None = None,
    selected: bool = False,
    can_craft: bool = True,
) -> str:
    """
    Render a single recipe as a compact card block.
    """
    name = recipe.get("name", "Unknown Recipe")
    description = recipe.get("description", "")
    result_item_id = recipe.get("result_item_id", "")
    result_quantity = recipe.get("result_quantity", 1)
    category = recipe.get("category", "workbench")
    station_id = recipe.get("station_id")
    ingredients = recipe.get("ingredients", [])

    icon = _CATEGORY_ICONS.get(category, "?")

    result_name = result_item_id
    result_rarity = "common"
    if manager is not None:
        item_data = manager.get_item(result_item_id)
        if item_data:
            result_name = item_data.get("name", result_item_id)
            result_rarity = item_data.get("rarity", "common")
        else:
            mat_data = manager.get_material(result_item_id)
            if mat_data:
                result_name = mat_data.get("name", result_item_id)
                result_rarity = mat_data.get("rarity", "common")

    result_display = _colorize_rarity(
        f"{icon} {result_name} x{result_quantity}", result_rarity, accessibility
    )

    if selected:
        if accessibility is not None:
            result_display = accessibility.emphasize(result_display)
        else:
            result_display = f"{_BOLD}{_INVERSE}{result_display}{_RESET}"

    marker = "▶ " if selected else "  "

    lines: list[str] = [f"{marker}{_bold(name)} — {result_display}"]

    if description:
        lines.append(f"     {_dim(description) + _RESET}")

    lines.append(
        f"     Category: {category} | Station: {station_id or 'any'}"
    )

    if ingredients:
        ing_parts: list[str] = []
        for ing in ingredients:
            mat_id = ing.get("material_id", "?")
            qty = ing.get("quantity", 1)
            mat_name = mat_id
            if manager is not None:
                mat_data = manager.get_material(mat_id)
                if mat_data:
                    mat_name = mat_data.get("name", mat_id)
            ing_parts.append(f"{mat_name} x{qty}")
        lines.append(f"     Ingredients: {', '.join(ing_parts)}")

    if not can_craft:
        lines.append(f"     {_dim('(missing requirements)') + _RESET}")

    return "\n".join(lines)


def render_recipe_detail(
    recipe: dict[str, Any],
    *,
    manager: CraftingManager | None = None,
    accessibility: AccessibilityHelper | None = None,
    character_id: str = "",
) -> str:
    """
    Render a detailed view of a single recipe.
    """
    lines = [_bold("╔" + "═" * 58 + "╗")]

    name = recipe.get("name", "Unknown")
    description = recipe.get("description", "")
    result_item_id = recipe.get("result_item_id", "")
    result_quantity = recipe.get("result_quantity", 1)
    station_id = recipe.get("station_id")
    ingredients = recipe.get("ingredients", [])

    result_name = result_item_id
    result_rarity = "common"
    item_type = ""
    if manager is not None:
        item_data = manager.get_item(result_item_id)
        if item_data:
            result_name = item_data.get("name", result_item_id)
            result_rarity = item_data.get("rarity", "common")
            item_type = item_data.get("item_type", "")
        else:
            mat_data = manager.get_material(result_item_id)
            if mat_data:
                result_name = mat_data.get("name", result_item_id)
                result_rarity = mat_data.get("rarity", "common")

    type_icon = _ITEM_TYPE_ICONS.get(item_type, "?")
    header = (
        f"RECIPE: {_bold(name)} — "
        + _colorize_rarity(f"{result_name} x{result_quantity}", result_rarity, accessibility)
    )
    lines.append(_bold("║" + header.center(58) + "║"))
    lines.append(_bold("╚" + "═" * 58 + "╝"))
    lines.append("")

    if description:
        lines.append(f"  {description}")
        lines.append("")

    lines.append(f"  Station: {station_id or 'Any'}")
    lines.append("")

    lines.append(_bold("Ingredients:") + _RESET)
    for ing in ingredients:
        mat_id = ing.get("material_id", "?")
        qty = ing.get("quantity", 1)
        mat_name = mat_id
        mat_rarity = "common"
        if manager is not None:
            mat_data = manager.get_material(mat_id)
            if mat_data:
                mat_name = mat_data.get("name", mat_id)
                mat_rarity = mat_data.get("rarity", "common")
        lines.append(
            f"  {_colorize_rarity(mat_name, mat_rarity, accessibility)}: {qty}"
        )

    lines.append("")
    lines.append(_bold("Instructions:") + _RESET)
    lines.append("  Use the appropriate station and gather the ingredients above.")
    lines.append("  Press 'c' to craft this recipe.")

    return "\n".join(lines)


def render_crafting_panel(
    character_id: str,
    manager: CraftingManager,
    *,
    selected_recipe_id: str | None = None,
    inventory: Any = None,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render the full crafting panel for a character.
    """
    lines: list[str] = [
        _bold("╔" + "═" * 58 + "╗"),
        _bold("║" + f"CRAFTING — {character_id}".center(58) + "║"),
        _bold("╚" + "═" * 58 + "╝"),
        "",
    ]

    recipes = manager.get_available_recipes(character_id)
    if not recipes:
        lines.append(_dim("No recipes learned yet.") + _RESET)
        return "\n".join(lines)

    # Group by category
    categories: dict[str, list[dict[str, Any]]] = {}
    for rec in recipes:
        cat = rec.get("category", "workbench")
        categories.setdefault(cat, []).append(rec)

    def _can_craft(recipe: dict[str, Any]) -> bool:
        if inventory is None:
            return True
        for ing in recipe.get("ingredients", []):
            if not inventory.has_item(ing.get("material_id", ""), ing.get("quantity", 1)):
                return False
        return True

    for cat, cat_recipes in categories.items():
        icon = _CATEGORY_ICONS.get(cat, "?")
        lines.append(_bold(f"── {icon} {cat.title()} ──") + _RESET)
        for rec in cat_recipes:
            cc = _can_craft(rec)
            lines.append(
                render_recipe_card(
                    rec,
                    manager=manager,
                    accessibility=accessibility,
                    selected=(rec["id"] == selected_recipe_id),
                    can_craft=cc,
                )
            )
            lines.append("")

    return "\n".join(lines)


def render_station_info(
    station: dict[str, Any] | None,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render details for a crafting station.
    """
    if station is None:
        return _dim("Station information unavailable.") + _RESET

    lines = [
        _bold("Station:") + _RESET,
        f"  {station.get('name', 'Unknown')}",
        f"  {station.get('description', '')}",
        f"  Categories: {', '.join(station.get('allowed_categories', []))}",
        f"  Level Required: {station.get('level_required', 1)}",
    ]
    return "\n".join(lines)


def render_craft_log(
    log: list[str],
    *,
    max_lines: int = 5,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render a short craft log.
    """
    if not log:
        return "Craft log: —"
    lines = ["Craft log:"]
    for entry in log[-max_lines:]:
        lines.append(f"  - {entry}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------


class CraftingUI:
    """
    High-level crafting UI facade.
    Composes panel, detail, and station views around a CraftingManager.
    """

    def __init__(
        self,
        manager: CraftingManager,
        accessibility: AccessibilityHelper | None = None,
    ) -> None:
        self.manager = manager
        self.accessibility = accessibility

    def show_full_screen(
        self, character_id: str, *, selected_recipe_id: str | None = None
    ) -> str:
        recipes = self.manager.get_available_recipes(character_id)
        recipe_map = {r["id"]: r for r in recipes}
        selected = recipe_map.get(selected_recipe_id) if selected_recipe_id else None

        output = render_crafting_panel(
            character_id,
            self.manager,
            selected_recipe_id=selected_recipe_id,
            accessibility=self.accessibility,
        )
        if selected:
            output += "\n\n" + render_recipe_detail(
                selected,
                manager=self.manager,
                accessibility=self.accessibility,
                character_id=character_id,
            )
        return output

    def show_recipe_detail(self, character_id: str, recipe_id: str) -> str:
        recipes = self.manager.get_available_recipes(character_id)
        recipe_map = {r["id"]: r for r in recipes}
        recipe = recipe_map.get(recipe_id)
        if not recipe:
            return (
                _dim(f"Recipe '{recipe_id}' not found or not learned.")
                + _RESET
            )
        return render_recipe_detail(
            recipe,
            manager=self.manager,
            accessibility=self.accessibility,
            character_id=character_id,
        )

    def show_summary(self, character_id: str) -> str:
        recipes = self.manager.get_available_recipes(character_id)
        parts = [r["name"] for r in recipes]
        return ", ".join(parts) if parts else _dim("(no recipes learned)") + _RESET

    def show_station_info(self, station_id: str) -> str:
        station = self.manager.get_station(station_id)
        return render_station_info(station, accessibility=self.accessibility)

    def show_craft_log(self, log: list[str]) -> str:
        return render_craft_log(log, accessibility=self.accessibility)


# ---------------------------------------------------------------------------
# Interactive session
# ---------------------------------------------------------------------------


class CraftingUISession:
    """
    Interactive crafting management loop in the terminal.

    Usage:
        session = CraftingUISession(manager, "hero")
        session.run()
    """

    def __init__(
        self,
        manager: CraftingManager,
        character_id: str,
        accessibility: AccessibilityHelper | None = None,
    ) -> None:
        self.manager = manager
        self.character_id = character_id
        self.accessibility = accessibility
        self._running = True
        self._selected_recipe_id: str | None = None
        self._craft_log: list[str] = []

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _render_frame(self, message: str = "") -> None:
        panel = render_crafting_panel(
            self.character_id,
            self.manager,
            selected_recipe_id=self._selected_recipe_id,
            accessibility=self.accessibility,
        )
        output: list[str] = []
        output.append(_bold("╔" + "═" * 58 + "╗"))
        output.append(_bold("║" + "CRAFTING".center(58) + "║"))
        output.append(_bold("╚" + "═" * 58 + "╝"))
        output.append("")
        output.append(panel)

        if self._selected_recipe_id:
            recipes = self.manager.get_available_recipes(self.character_id)
            recipe_map = {r["id"]: r for r in recipes}
            selected = recipe_map.get(self._selected_recipe_id)
            if selected:
                output.append("")
                output.append(
                    render_recipe_detail(
                        selected,
                        manager=self.manager,
                        accessibility=self.accessibility,
                    )
                )

        output.append("")
        output.append(
            render_craft_log(
                self._craft_log, accessibility=self.accessibility
            )
        )

        if message:
            output.append(message)

        self._clear_screen()
        print("\n".join(output))

    def run(self) -> list[str]:
        """
        Run the interactive loop. Returns the craft log.
        """
        self._render_frame()

        while self._running:
            try:
                prompt = "Command [n=next, p=prev, c=craft, q=quit]: "
                if self.accessibility:
                    prompt = self.accessibility.simplify_command_prompt(prompt)
                choice = input(_bold(prompt) + _RESET).strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "q":
                self._running = False
                break

            if choice == "c" and self._selected_recipe_id:
                result = self.manager.craft(
                    self.character_id, self._selected_recipe_id, quantity=1
                )
                if result.get("success"):
                    item_id = result.get("result_item_id", "?")
                    qty = result.get("result_quantity", 1)
                    name = item_id
                    if self.manager:
                        item_data = self.manager.get_item(item_id)
                        if item_data:
                            name = item_data.get("name", item_id)
                    msg = (
                        _green(f"Crafted: {name} x{qty}")
                        + _RESET
                    )
                    self._craft_log.append(f"Crafted {name} x{qty}")
                else:
                    reason = result.get("reason", "unknown")
                    msg = _red(f"Failed: {reason}") + _RESET
                    self._craft_log.append(f"Failed to craft: {reason}")
                self._render_frame(msg)
                continue

            if choice in ("n", "p"):
                recipes = self.manager.get_available_recipes(self.character_id)
                if not recipes:
                    self._render_frame(
                        _yellow("No recipes available.") + _RESET
                    )
                    continue
                current_idx = 0
                if self._selected_recipe_id:
                    for i, r in enumerate(recipes):
                        if r["id"] == self._selected_recipe_id:
                            current_idx = i
                            break
                if choice == "n":
                    current_idx = (current_idx + 1) % len(recipes)
                else:
                    current_idx = (current_idx - 1) % len(recipes)
                self._selected_recipe_id = recipes[current_idx]["id"]
                self._render_frame()
                continue

            self._render_frame()
            print(_red(f"Unknown command: {choice}") + _RESET)

        return self._craft_log


def create_crafting_session(
    manager: CraftingManager,
    character_id: str,
    accessibility: AccessibilityHelper | None = None,
) -> CraftingUISession:
    """Convenience factory for a crafting session."""
    return CraftingUISession(manager, character_id, accessibility)
