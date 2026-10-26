"""
RPG-08-13: Inventory UI
Terminal-based UI renderer for inventory display, item tooltips,
and equipment management.
"""

from __future__ import annotations

from accessibility import AccessibilityHelper
from inventory import (
    EquipmentSlot,
    InventoryManager,
    InventoryState,
    Item,
)

# ---------------------------------------------------------------------------
# Color helpers (ANSI 256-color / 24-bit)
# ---------------------------------------------------------------------------

_RARITY_COLORS: dict[str, str] = {
    "common": "\033[37m",       # white
    "uncommon": "\033[32m",     # green
    "rare": "\033[34m",         # blue
    "epic": "\033[35m",         # magenta
    "legendary": "\033[33m",    # yellow
}
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

_SLOT_TYPE_NAMES: dict[str, str] = {
    "head": "Head",
    "chest": "Chest",
    "legs": "Legs",
    "hands": "Hands",
    "feet": "Feet",
    "main_hand": "Main Hand",
    "off_hand": "Off Hand",
    "ring": "Ring",
    "necklace": "Necklace",
    "accessory": "Accessory",
}


def _colorize(text: str, rarity: str, accessibility: AccessibilityHelper | None = None) -> str:
    if accessibility is not None:
        colors = accessibility.accessible_rarity_colors()
        code = colors.get(rarity, "")
        reset = accessibility.get_color("reset")
        return f"{code}{text}{reset}"
    return f"{_RARITY_COLORS.get(rarity, '')}{text}{_RESET}"


# ---------------------------------------------------------------------------
# Tooltip rendering
# ---------------------------------------------------------------------------

def render_tooltip(item: Item, equipped: bool = False, accessibility: AccessibilityHelper | None = None) -> str:
    """
    Return a multi-line tooltip string for an item.

    Includes:
      - Name (rarity-colored)
      - Type line
      - Description
      - Stats block
      - Effects block
    """
    lines: list[str] = []
    name = _colorize(item.name, item.rarity.value, accessibility)
    type_line = f"{item.item_type.value.title()} {'(Equipped)' if equipped else ''}"
    lines.append(f"{_BOLD}{name}{_RESET}  {_DIM}{type_line}{_RESET}")
    lines.append("─" * max(len(name) - len(_RARITY_COLORS.get(item.rarity.value, "")) - len(_RESET)*2, 20))

    if item.description:
        lines.append(item.description)

    if item.stats:
        lines.append("")
        lines.append(f"{_BOLD}Stats:{_RESET}")
        for stat, value in item.stats.items():
            lines.append(f"  {stat.replace('_', ' ').title()}: {value}")

    if item.effects:
        lines.append("")
        lines.append(f"{_BOLD}Effects:{_RESET}")
        for key, value in item.effects.items():
            if isinstance(value, dict):
                sub_parts = []
                for sk, sv in value.items():
                    sub_parts.append(f"{sk.replace('_', ' ').title()}: {sv}")
                lines.append(f"  {key.replace('_', ' ').title()}:")
                for sp in sub_parts:
                    lines.append(f"    {sp}")
            else:
                lines.append(f"  {key.replace('_', ' ').title()}: {value}")

    if item.stackable:
        lines.append("")
        lines.append(f"{_DIM}Stackable (max {item.max_stack}){_RESET}")

    if item.max_durability > 0:
        lines.append("")
        pct = int(item.durability_percent() * 100)
        lines.append(f"{_BOLD}Durability:{_RESET} {item.durability}/{item.max_durability} ({pct}%)")

    return "\n".join(lines)


def render_compact_tooltip(item: Item, width: int = 40, accessibility: AccessibilityHelper | None = None) -> str:
    """Single-line compact tooltip for list views."""
    name = _colorize(item.name[: width - 10], item.rarity.value, accessibility)
    stats_preview = ""
    if item.stats:
        first_stat = next(iter(item.stats.items()))
        stats_preview = f" [{first_stat[0]}={first_stat[1]}]"
    qty = f" x{item.quantity}" if item.stackable else ""
    dur = ""
    if item.max_durability > 0:
        dur = f" [{item.durability}/{item.max_durability}HP]"
    return f"{name}{stats_preview}{qty}{dur}"


# ---------------------------------------------------------------------------
# Inventory grid rendering
# ---------------------------------------------------------------------------

def render_inventory_grid(
    inventory: InventoryState,
    *,
    columns: int = 6,
    selected_slot: int | None = None,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render the inventory bag as a grid.

    Returns a string ready for terminal output.
    """
    slots = inventory.slots
    rows: list[list[str]] = []
    for i in range(0, len(slots), columns):
        rows.append(slots[i : i + columns])

    header = f"Inventory  ({inventory.character_id})  Gold: {inventory.gold}"
    lines: list[str] = [header, ""]
    lines.append(f"{_BOLD}Bag ({inventory.capacity} slots){_RESET}")
    lines.append("")

    for row in rows:
        cells: list[str] = []
        for slot in row:
            if slot.is_empty():
                cell = f"{_DIM}[    ]{_RESET}"
            else:
                rarity = slot.item.rarity.value
                icon = slot.item.icon
                qty = f"x{slot.quantity}" if slot.item.stackable and slot.quantity > 1 else ""
                label = f"[{icon}{qty}]"
                color = _RARITY_COLORS.get(rarity, "")
                if accessibility is not None:
                    acc_colors = accessibility.accessible_rarity_colors()
                    color = acc_colors.get(rarity, color)
                if slot.slot_index == selected_slot:
                    cell = f"{_BOLD}{color}> {label[:4]} <{_RESET}"
                else:
                    cell = f" {color} {label[:4]}  {_RESET}"
            cells.append(cell)
        lines.append("".join(cells))

    lines.append("")
    return "\n".join(lines)


def render_inventory_list(
    inventory: InventoryState,
    *,
    selected_index: int | None = None,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render the inventory as a numbered list with tooltip-style detail.

    Each non-empty slot shows a compact tooltip line.
    """
    lines: list[str] = [
        f"{_BOLD}Inventory{_RESET} ({inventory.character_id})  Gold: {inventory.gold}",
        "",
    ]
    idx = 0
    for slot in inventory.slots:
        if slot.is_empty():
            idx += 1
            continue
        marker = "> " if idx == selected_index else "  "
        lines.append(f"{marker}{idx}: {render_compact_tooltip(slot.item, accessibility=accessibility)}")
        idx += 1

    if all(s.is_empty() for s in inventory.slots):
        lines.append(f"{_DIM}Your bag is empty.{_RESET}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Equipment rendering
# ---------------------------------------------------------------------------

def render_equipment_panel(inventory: InventoryState, accessibility: AccessibilityHelper | None = None) -> str:
    """
    Render a human-readable equipment panel showing equipped items
    and their stats/effects.
    """
    lines: list[str] = [f"{_BOLD}Equipment{_RESET} ({inventory.character_id})", ""]

    grouped: dict[str, list[EquipmentSlot]] = {
        "body": [],
        "hands": [],
        "accessories": [],
    }
    slot_order: list[str] = []

    for key in ["head", "chest", "legs", "hands", "feet", "main_hand", "off_hand", "ring", "necklace", "accessory"]:
        slot_order.append(key)

    for key in slot_order:
        slot = inventory.equipment.get(key)
        if slot is None:
            continue
        display = _SLOT_TYPE_NAMES.get(key, key)
        if slot.is_empty():
            lines.append(f"  {display}: {_DIM}(empty){_RESET}")
        else:
            name = _colorize(slot.item.name, slot.item.rarity.value, accessibility)
            lines.append(f"  {display}: {name}")
            if slot.item.stats:
                for stat, value in slot.item.stats.items():
                    lines.append(f"      {stat.replace('_', ' ').title()}: {value}")
            if slot.item.effects:
                for effect, value in slot.item.effects.items():
                    lines.append(f"      {effect.replace('_', ' ').title()}: {value}")
            if slot.item.max_durability > 0:
                pct = int(slot.item.durability_percent() * 100)
                lines.append(f"      {_DIM}Durability: {slot.item.durability}/{slot.item.max_durability} ({pct}%){_RESET}")

    lines.append("")
    return "\n".join(lines)


def render_equipment_summary(inventory: InventoryState, accessibility: AccessibilityHelper | None = None) -> str:
    """One-line summary of each equipped slot."""
    parts: list[str] = []
    for key in ["head", "chest", "legs", "hands", "feet", "main_hand", "off_hand", "ring", "necklace", "accessory"]:
        slot = inventory.equipment.get(key)
        if slot and not slot.is_empty():
            parts.append(_colorize(slot.item.name, slot.item.rarity.value, accessibility))
    return ", ".join(parts) if parts else f"{_DIM}(nothing equipped){_RESET}"


# ---------------------------------------------------------------------------
# Full UI renderer
# ---------------------------------------------------------------------------

class InventoryUI:
    """
    High-level UI facade that composes grid, list, tooltip, and equipment
    views around an InventoryState and InventoryManager.
    """

    def __init__(self, manager: InventoryManager | None = None, accessibility: AccessibilityHelper | None = None) -> None:
        self.manager = manager or InventoryManager()
        self.accessibility = accessibility

    def show_full_screen(self, character_id: str) -> str:
        """Render a full inventory + equipment + stats view."""
        inv = self.manager.get_inventory(character_id)
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append(f"{_BOLD}{_colorize('INVENTORY', 'legendary', self.accessibility)}{_RESET}".center(60))
        lines.append("=" * 60)
        lines.append("")
        lines.append(render_equipment_panel(inv, accessibility=self.accessibility))
        lines.append(render_inventory_grid(inv, accessibility=self.accessibility))
        lines.append(f"Equipped stats: {self.manager.get_equipped_stats(character_id)}")
        lines.append(f"Equipped effects: {self.manager.get_equipped_effects(character_id)}")
        lines.append("")
        return "\n".join(lines)

    def show_tooltip(self, character_id: str, slot_index: int) -> str:
        """Show tooltip for the item at the given inventory slot."""
        inv = self.manager.get_inventory(character_id)
        slot = inv.slots[slot_index]
        if slot.is_empty():
            return f"{_DIM}Slot {slot_index} is empty.{_RESET}"
        return render_tooltip(slot.item, accessibility=self.accessibility)

    def show_equipment_tooltip(self, character_id: str, slot_type: str) -> str:
        """Show tooltip for the item in a specific equipment slot."""
        inv = self.manager.get_inventory(character_id)
        slot = inv.equipment.get(slot_type)
        if not slot or slot.is_empty():
            return f"{_DIM}{_SLOT_TYPE_NAMES.get(slot_type, slot_type)} is empty.{_RESET}"
        return render_tooltip(slot.item, equipped=True, accessibility=self.accessibility)
