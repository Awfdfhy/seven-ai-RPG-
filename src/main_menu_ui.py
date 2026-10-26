"""
RPG-10-19: Main Menu UI
Terminal-based main menu and navigation interface with title screen,
menu options, settings panels, and accessibility support.
"""

from __future__ import annotations

import os

from accessibility import AccessibilityHelper
from difficulty_settings import (
    DifficultyPreset,
    GameSettings,
)

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_UNDERLINE = "\033[4m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"
_WHITE = "\033[37m"

_MENU_COLORS: dict[str, str] = {
    "title": _CYAN,
    "option": _WHITE,
    "selected": _YELLOW,
    "disabled": _DIM,
    "header": _BLUE,
    "accent": _MAGENTA,
    "success": _GREEN,
    "error": _RED,
}


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def _bold(text: str) -> str:
    return f"{_BOLD}{text}{_RESET}"


def _dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}"


def _apply_menu_color(text: str, role: str, accessibility: AccessibilityHelper | None = None) -> str:
    if accessibility is not None:
        color_map = {
            "title": "cyan",
            "option": "white",
            "selected": "yellow",
            "disabled": "dim",
            "header": "blue",
            "accent": "magenta",
            "success": "green",
            "error": "red",
        }
        color_name = color_map.get(role, "white")
        return accessibility.color_text(text, color_name)
    code = _MENU_COLORS.get(role, _WHITE)
    return f"{code}{text}{_RESET}"


# ---------------------------------------------------------------------------
# Title screen
# ---------------------------------------------------------------------------

def render_title_screen(
    version: str = "0.1.0",
    *,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render the game title screen.

    Layout:
      - ASCII-style title art
      - Tagline
      - Version line
      - Press any key prompt
    """
    title_art = [
        " _   _                 ____ _     ___    ____                     ",
        "| \\ | | ___  ___      / ___| |   |_ _|  / ___| __ _ _ __ ___   __| |",
        "|  \\| |/ _ \\/ _ \\_____| |   | |    | |  | |  _ / _` | '_ ` _ \\ / _` |",
        "| |\\  |  __/ (_) |_____| |___| |___ | |  | |_| | (_| | | | | | | (_| |",
        "|_| \\_|\\___|\\___/       \\____|_____|___|  \\____|\\__,_|_| |_| |_|\\__,_|",
    ]

    lines: list[str] = []
    lines.append("")
    for row in title_art:
        lines.append(_apply_menu_color(row, "title", accessibility))
    lines.append("")
    lines.append(
        _apply_menu_color("A modular text/mechanical RPG framework", "dim", accessibility)
    )
    lines.append(
        _apply_menu_color(f"Version {version}", "disabled", accessibility)
    )
    lines.append("")
    lines.append(
        _dim("Press Enter to continue...") if accessibility is None
        else _apply_menu_color("Press Enter to continue...", "option", accessibility)
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Menu options
# ---------------------------------------------------------------------------

class MenuOption:
    """Represents a single main menu option."""

    def __init__(
        self,
        key: str,
        label: str,
        action: str,
        enabled: bool = True,
        description: str = "",
    ) -> None:
        self.key = key
        self.label = label
        self.action = action
        self.enabled = enabled
        self.description = description

    def __repr__(self) -> str:
        return f"MenuOption({self.key!r}, {self.label!r}, enabled={self.enabled})"


def _default_menu_options() -> list[MenuOption]:
    return [
        MenuOption("1", "New Game", "new_game", description="Start a fresh adventure"),
        MenuOption("2", "Continue", "continue", description="Resume last session", enabled=False),
        MenuOption("3", "Settings", "settings", description="Adjust difficulty and accessibility"),
        MenuOption("4", "Credits", "credits", description="View contributors"),
        MenuOption("5", "Quit", "quit", description="Exit to operating system"),
    ]


def render_main_menu(
    options: list[MenuOption] | None = None,
    *,
    selected_index: int = 0,
    accessibility: AccessibilityHelper | None = None,
    show_hints: bool = True,
) -> str:
    """
    Render the main menu with selectable options.

    Parameters:
        options: list of MenuOption instances (defaults to standard menu)
        selected_index: currently highlighted option index
        accessibility: optional AccessibilityHelper for colorblind-safe output
        show_hints: whether to show description hints under options
    """
    if options is None:
        options = _default_menu_options()

    lines: list[str] = []
    lines.append("")
    lines.append(
        _apply_menu_color("╔" + "═" * 46 + "╗", "header", accessibility)
    )
    lines.append(
        _apply_menu_color(
            "║" + "MAIN MENU".center(46) + "║",
            "header",
            accessibility,
        )
    )
    lines.append(
        _apply_menu_color("╚" + "═" * 46 + "╝", "header", accessibility)
    )
    lines.append("")

    for idx, opt in enumerate(options):
        marker = "▶" if idx == selected_index else " "
        if opt.enabled:
            if idx == selected_index:
                label = _apply_menu_color(
                    f"{marker} {opt.key}. {opt.label}", "selected", accessibility
                )
            else:
                label = _apply_menu_color(
                    f"  {opt.key}. {opt.label}", "option", accessibility
                )
        else:
            label = _apply_menu_color(
                f"  {opt.key}. {opt.label}", "disabled", accessibility
            )
        lines.append(label)

        if show_hints and opt.description and idx == selected_index:
            hint = _apply_menu_color(f"     {opt.description}", "dim", accessibility)
            lines.append(hint)

    lines.append("")
    if accessibility is not None:
        prompt = accessibility.simplify_command_prompt("Select an option: ")
    else:
        prompt = "Select an option: "
    lines.append(_bold(prompt))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Settings panels
# ---------------------------------------------------------------------------

def render_settings_panel(
    settings: GameSettings | None = None,
    *,
    selected_index: int = 0,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render the settings panel showing current game settings.

    Panels:
      - Difficulty preset
      - Accessibility options
    """
    if settings is None:
        settings = GameSettings()

    lines: list[str] = []
    lines.append("")
    lines.append(
        _apply_menu_color("╔" + "═" * 46 + "╗", "header", accessibility)
    )
    lines.append(
        _apply_menu_color(
            "║" + "SETTINGS".center(46) + "║",
            "header",
            accessibility,
        )
    )
    lines.append(
        _apply_menu_color("╚" + "═" * 46 + "╝", "header", accessibility)
    )
    lines.append("")

    # Difficulty
    difficulty_options = [
        DifficultyPreset.NARRATIVE,
        DifficultyPreset.EASY,
        DifficultyPreset.NORMAL,
        DifficultyPreset.HARD,
        DifficultyPreset.NIGHTMARE,
    ]
    lines.append(_bold("Difficulty:"))
    for idx, preset in enumerate(difficulty_options):
        marker = "▶" if idx == selected_index else " "
        if settings.difficulty == preset:
            label = _apply_menu_color(
                f"  {marker} {preset}", "selected", accessibility
            )
        else:
            label = _apply_menu_color(
                f"  {marker} {preset}", "option", accessibility
            )
        lines.append(label)
    lines.append("")

    # Accessibility
    acc = settings.accessibility
    lines.append(_bold("Accessibility:"))
    lines.append(
        _apply_menu_color(
            f"  Text Size: {acc.text_size}",
            "option",
            accessibility,
        )
    )
    lines.append(
        _apply_menu_color(
            f"  High Contrast: {acc.high_contrast_mode}",
            "option",
            accessibility,
        )
    )
    lines.append(
        _apply_menu_color(
            f"  Simplified Combat: {acc.simplified_combat}",
            "option",
            accessibility,
        )
    )
    lines.append(
        _apply_menu_color(
            f"  Auto-Advance Dialogue: {acc.auto_advance_dialogue}",
            "option",
            accessibility,
        )
    )
    lines.append(
        _apply_menu_color(
            f"  Screen Reader: {acc.screen_reader_mode}",
            "option",
            accessibility,
        )
    )
    lines.append(
        _apply_menu_color(
            f"  Reduce Flashes: {acc.reduce_flashes}",
            "option",
            accessibility,
        )
    )
    lines.append(
        _apply_menu_color(
            f"  Colorblind Support: {acc.colorblind_support}",
            "option",
            accessibility,
        )
    )
    lines.append("")
    lines.append(_dim("Press Enter to return to main menu."))
    lines.append("")
    return "\n".join(lines)


def render_credits(
    *,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render the credits screen.
    """
    lines: list[str] = []
    lines.append("")
    lines.append(
        _apply_menu_color("╔" + "═" * 46 + "╗", "header", accessibility)
    )
    lines.append(
        _apply_menu_color(
            "║" + "CREDITS".center(46) + "║",
            "header",
            accessibility,
        )
    )
    lines.append(
        _apply_menu_color("╚" + "═" * 46 + "╝", "header", accessibility)
    )
    lines.append("")
    lines.append(
        _apply_menu_color("  Seven RPG Team", "title", accessibility)
    )
    lines.append(
        _apply_menu_color("  Design, Engineering, and World-Building", "dim", accessibility)
    )
    lines.append("")
    lines.append(
        _apply_menu_color("  Built with Python and a love for RPGs.", "option", accessibility)
    )
    lines.append("")
    lines.append(_dim("  Press Enter to return to main menu."))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

class MainMenuNavigation:
    """
    Encapsulates main menu state and navigation helpers.
    """

    def __init__(
        self,
        options: list[MenuOption] | None = None,
        settings: GameSettings | None = None,
    ) -> None:
        self.options = options if options is not None else _default_menu_options()
        self.settings = settings or GameSettings()
        self.selected_index = 0
        self._enabled_indices = [
            idx for idx, opt in enumerate(self.options) if opt.enabled
        ]

    def move_selection(self, delta: int) -> None:
        if not self._enabled_indices:
            return
        if self.selected_index not in self._enabled_indices:
            self.selected_index = self._enabled_indices[0]
            return
        current_pos = self._enabled_indices.index(self.selected_index)
        new_pos = (current_pos + delta) % len(self._enabled_indices)
        self.selected_index = self._enabled_indices[new_pos]

    def select(self, key: str) -> MenuOption | None:
        for opt in self.options:
            if opt.key == key and opt.enabled:
                return opt
        return None

    def current_option(self) -> MenuOption:
        return self.options[self.selected_index]


# ---------------------------------------------------------------------------
# Full UI facade
# ---------------------------------------------------------------------------

class MainMenuUI:
    """
    High-level main menu UI facade.
    Composes title, menu, settings, and credits views.
    """

    def __init__(
        self,
        settings: GameSettings | None = None,
        accessibility: AccessibilityHelper | None = None,
    ) -> None:
        self.settings = settings or GameSettings()
        self.accessibility = accessibility
        self.navigation = MainMenuNavigation(settings=self.settings)

    def show_title_screen(self, version: str = "0.1.0") -> str:
        """Render the title screen."""
        return render_title_screen(version, accessibility=self.accessibility)

    def show_main_menu(self) -> str:
        """Render the main menu with current selection."""
        return render_main_menu(
            self.navigation.options,
            selected_index=self.navigation.selected_index,
            accessibility=self.accessibility,
        )

    def show_settings(self) -> str:
        """Render the settings panel."""
        return render_settings_panel(
            self.settings,
            accessibility=self.accessibility,
        )

    def show_credits(self) -> str:
        """Render the credits screen."""
        return render_credits(accessibility=self.accessibility)

    def update_settings(self, new_settings: GameSettings) -> None:
        """Update the stored settings reference."""
        self.settings = new_settings
        self.navigation.settings = new_settings


# ---------------------------------------------------------------------------
# Interactive session
# ---------------------------------------------------------------------------

class MainMenuUISession:
    """
    Interactive main menu loop in the terminal.

    Usage:
        session = MainMenuUISession()
        session.run()
    """

    def __init__(
        self,
        settings: GameSettings | None = None,
        accessibility: AccessibilityHelper | None = None,
        version: str = "0.1.0",
    ) -> None:
        self.ui = MainMenuUI(settings=settings, accessibility=accessibility)
        self.accessibility = accessibility
        self.version = version
        self._running = True
        self._view: str = "title"  # title | menu | settings | credits
        self._last_action: str = ""

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _render(self, message: str = "") -> None:
        output: list[str] = []
        if self._view == "title":
            output.append(self.ui.show_title_screen(self.version))
        elif self._view == "menu":
            output.append(self.ui.show_main_menu())
        elif self._view == "settings":
            output.append(self.ui.show_settings())
        elif self._view == "credits":
            output.append(self.ui.show_credits())

        if message:
            output.append(message)

        self._clear_screen()
        print("\n".join(output))

    def run(self) -> str:
        """
        Run the interactive main menu loop.

        Returns:
            The selected action string (e.g. "new_game", "quit").
        """
        self._view = "title"
        self._render()

        # Wait for Enter from title screen
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            return "quit"

        while self._running:
            self._view = "menu"
            self._render()

            try:
                prompt = "Select an option: "
                if self.accessibility:
                    prompt = self.accessibility.simplify_command_prompt(prompt)
                choice = input(_bold(prompt)).strip().lower()
            except (EOFError, KeyboardInterrupt):
                self._last_action = "quit"
                break

            if choice == "q":
                self._last_action = "quit"
                break

            option = self.ui.navigation.select(choice)
            if option is None:
                # Try numeric index from current selection
                current = self.ui.navigation.current_option()
                if current.enabled and current.key == choice:
                    option = current

            if option is None:
                self._render(_red("Invalid selection.") + _RESET)
                continue

            self._last_action = option.action

            if option.action == "new_game":
                self._render(_green("Starting new game...") + _RESET)
                break
            elif option.action == "continue":
                self._render(_red("No saved session found.") + _RESET)
                self._last_action = ""
                input(_dim("Press Enter to continue..."))
                continue
            elif option.action == "settings":
                self._view = "settings"
                self._render()
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    self._last_action = "quit"
                    break
                self._last_action = ""
                continue
            elif option.action == "credits":
                self._view = "credits"
                self._render()
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    self._last_action = "quit"
                    break
                self._last_action = ""
                continue
            elif option.action == "quit":
                self._render(_dim("Goodbye!") + _RESET)
                break

        return self._last_action or "quit"


def create_main_menu_session(
    settings: GameSettings | None = None,
    accessibility: AccessibilityHelper | None = None,
    version: str = "0.1.0",
) -> MainMenuUISession:
    """Convenience factory for a main menu session."""
    return MainMenuUISession(settings=settings, accessibility=accessibility, version=version)
