"""
RPG-08-14: Equipment UI
Terminal-based equipment panel renderer with visual slot layout,
item display, and stat bonuses aggregation.
"""

from __future__ import annotations

import os

from accessibility import AccessibilityHelper
from inventory import (
    EquipmentSlot,
    InventoryManager,
    InventoryState,
)

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"
_WHITE = "\033[37m"

_RARITY_COLORS: dict[str, str] = {
    "common": _WHITE,
    "uncommon": _GREEN,
    "rare": _BLUE,
    "epic": _MAGENTA,
    "legendary": _YELLOW,
}

_SLOT_DISPLAY_NAMES: dict[str, str] = {
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

_SLOT_ICONS: dict[str, str] = {
    "head": "◎",
    "chest": "◉",
    "legs": "⬡",
    "hands": "⬢",
    "feet": "▽",
    "main_hand": "⚔",
    "off_hand": "🛡",
    "ring": "◈",
    "necklace": "♢",
    "accessory": "◇",
}


def _colorize(text: str, rarity: str, accessibility: AccessibilityHelper | None = None) -> str:
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


def _bold(text: str) -> str:
    return f"{_BOLD}{text}{_RESET}"


def _dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}"


def _red(text: str) -> str:
    return f"{_RED}{text}{_RESET}"


def _green(text: str) -> str:
    return f"{_GREEN}{text}{_RESET}"


def _durability_bar(pct: int, width: int = 10) -> str:
    filled = max(0, min(width, int(width * pct / 100)))
    empty = width - filled
    if pct > 60:
        color = _GREEN
    elif pct > 30:
        color = _YELLOW
    else:
        color = _RED
    return f"{color}{'█' * filled}{_DIM}{'░' * empty}{_RESET}"


# ---------------------------------------------------------------------------
# Slot rendering
# ---------------------------------------------------------------------------

def render_equipment_slot(
    slot: EquipmentSlot,
    slot_key: str,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render a single equipment slot as a human-readable line block.
    """
    display = _SLOT_DISPLAY_NAMES.get(slot_key, slot_key)
    icon = _SLOT_ICONS.get(slot_key, "?")

    if slot.is_empty():
        return f"  {icon} {_dim(display + ': (empty)') + _RESET}"

    item = slot.item
    name = _colorize(item.name, item.rarity.value, accessibility)
    lines: list[str] = [f"  {icon} {display}: {name}"]

    if item.stats:
        for stat, value in item.stats.items():
            lines.append(f"      {stat.replace('_', ' ').title()}: {value}")

    if item.effects:
        for effect, value in item.effects.items():
            lines.append(f"      {effect.replace('_', ' ').title()}: {value}")

    if item.max_durability > 0:
        pct = int(slot.durability_percent() * 100)
        bar = _durability_bar(pct)
        lines.append(
            f"      Durability: {bar} {slot.durability}/{slot.max_durability} ({pct}%)"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Equipment panel rendering
# ---------------------------------------------------------------------------

def render_equipment_panel(
    inventory: InventoryState,
    manager: InventoryManager | None = None,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render the full character equipment panel.

    Shows a visual ASCII layout of equipment slots, equipped items,
    and aggregated stat bonuses (including set bonuses).
    """
    lines: list[str] = [
        _bold("╔" + "═" * 58 + "╗"),
        _bold("║" + f"EQUIPMENT — {inventory.character_id}".center(58) + "║"),
        _bold("╚" + "═" * 58 + "╝"),
        "",
    ]

    # --- visual slot map ---
    lines.append("         " + _bold("[ Head ]") + "           ")
    lines.append("             │                 ")

    # chest, hands, legs row
    chest_slot = inventory.equipment.get("chest")
    hands_slot = inventory.equipment.get("hands")
    legs_slot = inventory.equipment.get("legs")

    def _slot_preview(key: str) -> str:
        slot = inventory.equipment.get(key)
        if slot is None or slot.is_empty():
            return _dim(f"[{_SLOT_ICONS.get(key, '?')} {_SLOT_DISPLAY_NAMES.get(key, key)}]")
        return _colorize(slot.item.name, slot.item.rarity.value, accessibility)

    lines.append(
        f"  {_slot_preview('chest'):20s} │ {_slot_preview('hands'):20s} │ {_slot_preview('legs')}"
    )
    lines.append("             │       │         │                 ")

    # main hand / off hand row
    lines.append(
        f"  {_slot_preview('main_hand'):20s} │ {_slot_preview('off_hand'):20s}"
    )
    lines.append("                                           ")

    # feet / accessory row
    lines.append(
        f"  {_slot_preview('feet'):20s} │ {_slot_preview('accessory'):20s}"
    )
    lines.append("                                           ")

    # ring / necklace row
    lines.append(
        f"  {_slot_preview('ring'):20s} │ {_slot_preview('necklace'):20s}"
    )
    lines.append("                                           ")
    lines.append("")

    # --- detailed slot list ---
    lines.append(_bold("── Equipped Items ──") + _RESET)
    lines.append("")

    slot_order = [
        "head",
        "chest",
        "legs",
        "hands",
        "feet",
        "main_hand",
        "off_hand",
        "ring",
        "necklace",
        "accessory",
    ]
    for key in slot_order:
        slot = inventory.equipment.get(key)
        if slot is None:
            continue
        lines.append(render_equipment_slot(slot, key, accessibility))

    lines.append("")

    # --- stat bonuses ---
    if manager is not None:
        lines.append(render_stat_bonuses(inventory, manager, accessibility))

    return "\n".join(lines)


def render_stat_bonuses(
    inventory: InventoryState,
    manager: InventoryManager,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render total stats, equipped item stats, and active set bonuses.
    """
    lines: list[str] = [_bold("── Stat Bonuses ──") + _RESET, ""]

    equipped_stats = manager.get_equipped_stats(inventory.character_id)
    set_bonuses = manager.get_active_set_bonuses(inventory.character_id)
    total_stats = manager.get_total_stats(inventory.character_id)

    if equipped_stats:
        lines.append(_bold("Equipped Item Stats:") + _RESET)
        for stat, value in equipped_stats.items():
            lines.append(f"  {stat.replace('_', ' ').title()}: {value}")
        lines.append("")

    if set_bonuses:
        lines.append(_bold("Active Set Bonuses:") + _RESET)
        for set_id, bonuses in set_bonuses.items():
            eq_set = manager.get_equipment_set(set_id)
            set_name = eq_set.name if eq_set else set_id
            lines.append(f"  {_bold(set_name)}:")
            for stat, value in bonuses.items():
                lines.append(f"    {stat.replace('_', ' ').title()}: {value}")
        lines.append("")

    lines.append(_bold("Total Stats:") + _RESET)
    if total_stats:
        for stat, value in total_stats.items():
            lines.append(f"  {stat.replace('_', ' ').title()}: {value}")
    else:
        lines.append(f"  {_dim('(no bonuses active)') + _RESET}")

    lines.append("")
    return "\n".join(lines)


def render_equipment_summary(
    inventory: InventoryState,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """One-line summary of equipped items."""
    parts: list[str] = []
    for key in [
        "head",
        "chest",
        "legs",
        "hands",
        "feet",
        "main_hand",
        "off_hand",
        "ring",
        "necklace",
        "accessory",
    ]:
        slot = inventory.equipment.get(key)
        if slot and not slot.is_empty():
            parts.append(_colorize(slot.item.name, slot.item.rarity.value, accessibility))
    return ", ".join(parts) if parts else f"{_dim('(nothing equipped)') + _RESET}"


# ---------------------------------------------------------------------------
# Full UI facade
# ---------------------------------------------------------------------------

class EquipmentUI:
    """
    High-level equipment UI facade.
    Composes panel, summary, and stat views around an InventoryManager.
    """

    def __init__(
        self,
        manager: InventoryManager | None = None,
        accessibility: AccessibilityHelper | None = None,
    ) -> None:
        self.manager = manager or InventoryManager()
        self.accessibility = accessibility

    def show_full_screen(self, character_id: str) -> str:
        """Render a full equipment panel with stats."""
        inv = self.manager.get_inventory(character_id)
        return render_equipment_panel(inv, manager=self.manager, accessibility=self.accessibility)

    def show_summary(self, character_id: str) -> str:
        """Show a one-line equipment summary."""
        inv = self.manager.get_inventory(character_id)
        return render_equipment_summary(inv, accessibility=self.accessibility)

    def show_stat_bonuses(self, character_id: str) -> str:
        """Show detailed stat bonuses panel."""
        inv = self.manager.get_inventory(character_id)
        return render_stat_bonuses(inv, self.manager, accessibility=self.accessibility)

    def show_slot_tooltip(self, character_id: str, slot_key: str) -> str:
        """Show tooltip for a specific equipment slot."""
        inv = self.manager.get_inventory(character_id)
        slot = inv.equipment.get(slot_key)
        if not slot or slot.is_empty():
            return (
                _dim(_SLOT_DISPLAY_NAMES.get(slot_key, slot_key) + " is empty.")
                + _RESET
            )
        return render_equipment_slot(slot, slot_key, accessibility=self.accessibility)


# ---------------------------------------------------------------------------
# Interactive session
# ---------------------------------------------------------------------------


class EquipmentUISession:
    """
    Interactive equipment management loop in the terminal.

    Usage:
        session = EquipmentUISession(manager, "hero")
        session.run()
    """

    def __init__(
        self,
        manager: InventoryManager,
        character_id: str,
        accessibility: AccessibilityHelper | None = None,
    ) -> None:
        self.manager = manager
        self.character_id = character_id
        self.accessibility = accessibility
        self._running = True

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _render_frame(self, message: str = "") -> None:
        inv = self.manager.get_inventory(self.character_id)
        panel = render_equipment_panel(inv, manager=self.manager, accessibility=self.accessibility)

        output: list[str] = []
        output.append(_bold("╔" + "═" * 58 + "╗"))
        output.append(_bold("║" + "EQUIPMENT".center(58) + "║"))
        output.append(_bold("╚" + "═" * 58 + "╝"))
        output.append("")
        output.append(panel)

        if message:
            output.append(message)

        self._clear_screen()
        print("\n".join(output))

    def run(self) -> InventoryState:
        """
        Run the interactive loop. Returns the final inventory state.
        """
        self._render_frame()

        while self._running:
            try:
                prompt = "Command [s=stats, q=quit]: "
                if self.accessibility:
                    prompt = self.accessibility.simplify_command_prompt(prompt)
                choice = input(_bold(prompt) + _RESET).strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "q":
                self._running = False
                break

            if choice == "s":
                inv = self.manager.get_inventory(self.character_id)
                stats = self.manager.get_total_stats(self.character_id)
                self._render_frame()
                print(_bold("Total Stats:") + _RESET)
                for stat, value in stats.items():
                    print(f"  {stat.replace('_', ' ').title()}: {value}")
                if not stats:
                    print(_dim("  (no bonuses active)") + _RESET)
                cont_prompt = "Press Enter to continue..."
                if self.accessibility:
                    cont_prompt = self.accessibility.simplify_command_prompt(cont_prompt)
                input(_dim(cont_prompt) + _RESET)
                self._render_frame()
                continue

            self._render_frame()
            print(_red(f"Unknown command: {choice}") + _RESET)

        return self.manager.get_inventory(self.character_id)


def create_equipment_session(
    manager: InventoryManager,
    character_id: str,
    accessibility: AccessibilityHelper | None = None,
) -> EquipmentUISession:
    """Convenience factory for an equipment session."""
    return EquipmentUISession(manager, character_id, accessibility)
