"""
RPG-10-20: Settings UI and Options Menu
Terminal-based interactive settings menu for difficulty, accessibility,
gameplay, audio, and controls. Uses ANSI escape codes and numbered
selection for terminal compatibility.

Sections:
  - Difficulty Preset (Narrative, Easy, Normal, Hard, Nightmare)
  - Difficulty Customization (sliders/values for multipliers)
  - Accessibility (toggles for high contrast, simplified combat, etc.)
  - Gameplay (auto-save hints, subtitle toggles)
  - Audio / Video (volume placeholders, brightness)
  - Controls (key bindings display)
  - Save / Reset / Back
"""

from __future__ import annotations

from typing import Any

from difficulty_settings import (
    AccessibilityOption,
    AccessibilitySettings,
    DifficultyPreset,
    DifficultySettings,
    GameSettings,
)

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


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def _bold(text: str) -> str:
    return f"{_BOLD}{text}{_RESET}"


def _dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}"


def _inverse(text: str) -> str:
    return f"{_INVERSE}{text}{_RESET}"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DIFFICULTY_SECTIONS = [
    "Difficulty Preset",
    "Difficulty Customization",
    "Accessibility",
    "Gameplay",
    "Audio / Video",
    "Controls",
    "Save Settings",
    "Reset to Defaults",
    "Back",
]

_NUMERIC_FIELDS: list[tuple[str, str, float, float, float, str]] = [
    (
        "dc_modifier",
        "DC Modifier",
        -10,
        10,
        0,
        "Adjusts skill-check difficulty. Negative = easier checks.",
    ),
    (
        "damage_dealt_multiplier",
        "Damage Dealt %",
        10,
        300,
        100,
        "Percentage multiplier for outgoing damage.",
    ),
    (
        "damage_taken_multiplier",
        "Damage Taken %",
        10,
        300,
        100,
        "Percentage multiplier for incoming damage.",
    ),
    (
        "xp_multiplier",
        "XP Gain %",
        10,
        500,
        100,
        "Percentage multiplier for experience earned.",
    ),
    (
        "loot_rarity_boost",
        "Loot Rarity Boost %",
        -50,
        50,
        0,
        "Percentage boost to rare drop chance.",
    ),
    (
        "status_duration_multiplier",
        "Status Duration %",
        10,
        300,
        100,
        "Percentage multiplier for status effect duration.",
    ),
    (
        "healing_effectiveness_multiplier",
        "Healing Effectiveness %",
        10,
        300,
        100,
        "Percentage multiplier for healing received.",
    ),
]

_ACCESSIBILITY_FIELDS: list[tuple[str, str, Any, str]] = [
    (
        "high_contrast_mode",
        "High Contrast Mode",
        False,
        "Increases contrast for readability.",
    ),
    (
        "simplified_combat",
        "Simplified Combat",
        False,
        "Reduces combat UI complexity.",
    ),
    (
        "auto_advance_dialogue",
        "Auto-Advance Dialogue",
        False,
        "Automatically advances dialogue text.",
    ),
    (
        "text_size",
        "Text Size",
        "normal",
        "Font size: normal, large, or extra_large.",
    ),
    (
        "screen_reader_mode",
        "Screen Reader Mode",
        False,
        "Optimizes output for screen readers.",
    ),
    (
        "reduce_flashes",
        "Reduce Flashes",
        False,
        "Disables flashing animations.",
    ),
    (
        "colorblind_support",
        "Colorblind Support",
        "none",
        "Palette: none, protanopia, deuteranopia, tritanopia.",
    ),
]

_TEXT_SIZE_OPTIONS = AccessibilityOption.TEXT_SIZE_OPTIONS
_COLORBLIND_OPTIONS = AccessibilityOption.COLORBLIND_OPTIONS

_GAMEPLAY_TOGGLES: list[tuple[str, str, bool, str]] = [
    ("auto_save", "Auto-Save", True, "Automatically saves progress periodically."),
    ("show_subtitles", "Show Subtitles", True, "Displays text for voiced lines."),
    ("show_tutorial_hints", "Show Tutorial Hints", True, "Displays contextual tutorial tips."),
]

_AUDIO_VIDEO_FIELDS: list[tuple[str, str, int, int, int, str]] = [
    ("master_volume", "Master Volume", 0, 100, 80, "Overall game volume."),
    ("music_volume", "Music Volume", 0, 100, 70, "Music track volume."),
    (
        "sfx_volume",
        "Sound Effects Volume",
        0,
        100,
        85,
        "Sound effects and voice volume.",
    ),
    (
        "brightness",
        "Brightness",
        0,
        100,
        80,
        "Screen brightness (where supported).",
    ),
]

# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_box(title: str, body_lines: list[str], width: int = 60) -> str:
    border_top = "┌" + "─" * (width - 2) + "┐"
    border_bottom = "└" + "─" * (width - 2) + "┘"
    header = f"│ {_bold(title)}".ljust(width - 1) + "│"
    lines = [border_top, header, border_bottom]
    for line in body_lines:
        lines.append(f"│ {line}".ljust(width - 1) + "│")
    return "\n".join(lines)


def _render_section_header(text: str, width: int = 60) -> str:
    return _color("═" * width, _CYAN) + "\n" + _bold(_color(text.center(width), _CYAN)) + "\n" + _color("═" * width, _CYAN)


def _render_option(index: int, label: str, value: str, active: bool = False) -> str:
    marker = f"{_bold('[>]')}" if active else f"{_dim(f'[{index}]')}"
    value_str = _color(value, _YELLOW) if active else _dim(value)
    return f"  {marker}  {label}: {value_str}"


def _render_toggle(index: int, label: str, enabled: bool, hint: str = "") -> str:
    status = _color("ON", _GREEN) if enabled else _color("OFF", _RED)
    marker = f"{_bold('[>]')}"
    return f"  {marker}  {label}: {status}" + (f"  {_dim(hint)}" if hint else "")


# ---------------------------------------------------------------------------
# Settings UI class
# ---------------------------------------------------------------------------


class SettingsUI:
    """
    Interactive terminal-based settings menu.

    Usage:
        ui = SettingsUI(settings=GameSettings())
        ui.run()
    """

    def __init__(
        self,
        settings: GameSettings | None = None,
        on_save: Any = None,
    ) -> None:
        self.settings = settings or GameSettings()
        self._original = self._clone(self.settings)
        self._on_save = on_save
        self._running = False
        self._message: str = ""

    # ------------------------------------------------------------------
        # Public API
        # ------------------------------------------------------------------

    def run(self) -> GameSettings:
        """Launch the settings menu loop. Returns the final settings."""
        self._running = True
        while self._running:
            self._clear()
            self._render_main_menu()
            choice = self._prompt("Select an option")
            self._handle_main_choice(choice)
        return self.settings

    def get_current_settings(self) -> GameSettings:
        return self.settings

    def reset_to_defaults(self) -> None:
        self.settings = GameSettings()
        self._message = "Settings reset to defaults."

    def save(self) -> None:
        self._original = self._clone(self.settings)
        self._message = "Settings saved."
        if self._on_save is not None:
            self._on_save(self.settings)

    def has_changes(self) -> bool:
        return self.settings.to_dict() != self._original.to_dict()

    # ------------------------------------------------------------------
        # Rendering
        # ------------------------------------------------------------------

    def _clear(self) -> None:
        print("\033[H\033[J", end="")

    def _render_main_menu(self) -> None:
        width = 60
        title = "SETTINGS"
        print(_color("═" * width, _MAGENTA))
        print(_bold(_color(title.center(width), _MAGENTA)))
        print(_color("═" * width, _MAGENTA))
        print()

        ds = self.settings.difficulty
        acc = self.settings.accessibility

        # Difficulty summary
        preset_name = DifficultyPreset.preset(ds.preset).get("display_name", ds.preset)
        print(f"  {_bold('Difficulty:')}   {_color(preset_name, _YELLOW)}")
        print(f"  {_dim('Damage Dealt:')} {int(ds.damage_dealt_multiplier * 100)}%  "
              f"{_dim('Damage Taken:')} {int(ds.damage_taken_multiplier * 100)}%  "
              f"{_dim('XP:')} {int(ds.xp_multiplier * 100)}%")
        print(f"  {_dim('Accessibility:')} HC={_color(str(acc.high_contrast_mode), _GREEN if acc.high_contrast_mode else _RED)}  "
              f"SR={_color(str(acc.screen_reader_mode), _GREEN if acc.screen_reader_mode else _RED)}  "
              f"TS={_color(acc.text_size, _CYAN)}")
        print()

        # Menu options
        for i, section in enumerate(_DIFFICULTY_SECTIONS, start=1):
            marker = _bold(f"[{i}]") if i <= len(_DIFFICULTY_SECTIONS) else _dim(f"[{i}]")
            if section == "Save Settings" and not self.has_changes() or section == "Reset to Defaults" and not self.has_changes():
                section_display = _dim(section)
            else:
                section_display = section
            print(f"  {marker}  {section_display}")

        if self._message:
            print()
            print(f"  {_color(self._message, _GREEN)}")
            self._message = ""

    def _render_difficulty_preset(self) -> None:
        self._clear()
        width = 60
        print(_render_section_header("DIFFICULTY PRESET", width))
        print()
        current = self.settings.difficulty.preset
        for i, key in enumerate(DifficultyPreset.available_presets(), start=1):
            preset = DifficultyPreset.preset(key)
            active = key == current
            line = _render_option(
                i,
                preset["display_name"],
                preset["description"],
                active=active,
            )
            print(line)

        print()
        print(f"  {_dim('[0] Back')}")
        print()
        choice = self._prompt("Select preset")
        self._apply_difficulty_preset_choice(choice)

    def _apply_difficulty_preset_choice(self, choice: str) -> None:
        presets = DifficultyPreset.available_presets()
        if choice == "0":
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(presets):
                key = presets[idx]
                self.settings.difficulty = DifficultySettings.from_preset(key)
                self._message = f"Difficulty set to {DifficultyPreset.preset(key)['display_name']}."
            else:
                self._message = "Invalid selection."
        except ValueError:
            self._message = "Invalid selection."

    def _render_difficulty_customization(self) -> None:
        self._clear()
        width = 60
        print(_render_section_header("DIFFICULTY CUSTOMIZATION", width))
        print()
        ds = self.settings.difficulty
        for i, (field, label, lo, hi, default, hint) in enumerate(_NUMERIC_FIELDS, start=1):
            value = getattr(ds, field)
            display = f"{int(value * 100)}%"
            if value != default / 100:
                display = _color(display, _YELLOW)
            else:
                display = _dim(display)
            marker = _bold(f"[{i}]")
            print(f"  {marker}  {label}: {display}  {_dim(hint)}")

        print()
        print(f"  {_dim('[0] Back')}")
        print()
        choice = self._prompt("Select field to adjust")
        self._apply_difficulty_custom_choice(choice)

    def _apply_difficulty_custom_choice(self, choice: str) -> None:
        if choice == "0":
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(_NUMERIC_FIELDS):
                field, label, lo, hi, default, hint = _NUMERIC_FIELDS[idx]
                current = getattr(self.settings.difficulty, field)
                print(f"  Current {label}: {int(current * 100)}%")
                raw = self._prompt(f"Enter new value ({lo}–{hi}) or press Enter to cancel")
                if raw == "":
                    return
                try:
                    val = float(raw)
                    val = max(lo, min(hi, val))
                    if field != "dc_modifier":
                        val = val / 100.0
                    setattr(self.settings.difficulty, field, val)
                    self._message = f"{label} set to {int(val * 100)}%."
                except ValueError:
                    self._message = "Invalid number."
        except ValueError:
            self._message = "Invalid selection."

    def _render_accessibility(self) -> None:
        self._clear()
        width = 60
        print(_render_section_header("ACCESSIBILITY", width))
        print()
        acc = self.settings.accessibility
        for i, (field, label, default, hint) in enumerate(_ACCESSIBILITY_FIELDS, start=1):
            value = getattr(acc, field)
            if isinstance(value, bool):
                line = _render_toggle(i, label, value, hint)
            else:
                active = value != default
                display = _color(value, _YELLOW) if active else _dim(value)
                line = f"  {_bold(f'[{i}]')}  {label}: {display}  {_dim(hint)}"
            print(line)

        print()
        print(f"  {_dim('[0] Back')}")
        print()
        choice = self._prompt("Select option to toggle/adjust")
        self._apply_accessibility_choice(choice)

    def _apply_accessibility_choice(self, choice: str) -> None:
        if choice == "0":
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(_ACCESSIBILITY_FIELDS):
                field, label, default, hint = _ACCESSIBILITY_FIELDS[idx]
                value = getattr(self.settings.accessibility, field)
                if isinstance(value, bool):
                    setattr(self.settings.accessibility, field, not value)
                    state = "ON" if not value else "OFF"
                    self._message = f"{label} turned {state}."
                elif field == "text_size":
                    current_idx = _TEXT_SIZE_OPTIONS.index(value) if value in _TEXT_SIZE_OPTIONS else 0
                    next_idx = (current_idx + 1) % len(_TEXT_SIZE_OPTIONS)
                    new_val = _TEXT_SIZE_OPTIONS[next_idx]
                    setattr(self.settings.accessibility, field, new_val)
                    self._message = f"Text size set to {new_val}."
                elif field == "colorblind_support":
                    current_idx = _COLORBLIND_OPTIONS.index(value) if value in _COLORBLIND_OPTIONS else 0
                    next_idx = (current_idx + 1) % len(_COLORBLIND_OPTIONS)
                    new_val = _COLORBLIND_OPTIONS[next_idx]
                    setattr(self.settings.accessibility, field, new_val)
                    self._message = f"Colorblind support set to {new_val}."
            else:
                self._message = "Invalid selection."
        except ValueError:
            self._message = "Invalid selection."

    def _render_gameplay(self) -> None:
        self._clear()
        width = 60
        print(_render_section_header("GAMEPLAY", width))
        print()
        for i, (key, label, default, hint) in enumerate(_GAMEPLAY_TOGGLES, start=1):
            # Store these temporarily on the settings object's metadata
            current = self.settings.metadata.get(key, default)
            line = _render_toggle(i, label, current, hint)
            print(line)
        print()
        print(f"  {_dim('[0] Back')}")
        print()
        choice = self._prompt("Select option to toggle")
        self._apply_gameplay_choice(choice)

    def _apply_gameplay_choice(self, choice: str) -> None:
        if choice == "0":
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(_GAMEPLAY_TOGGLES):
                key, label, default, hint = _GAMEPLAY_TOGGLES[idx]
                current = self.settings.metadata.get(key, default)
                new_val = not current
                self.settings.metadata[key] = new_val
                state = "ON" if new_val else "OFF"
                self._message = f"{label} turned {state}."
            else:
                self._message = "Invalid selection."
        except ValueError:
            self._message = "Invalid selection."

    def _render_audio_video(self) -> None:
        self._clear()
        width = 60
        print(_render_section_header("AUDIO / VIDEO", width))
        print()
        for i, (key, label, lo, hi, default, hint) in enumerate(_AUDIO_VIDEO_FIELDS, start=1):
            value = self.settings.metadata.get(key, default)
            display = f"{value}"
            if value != default:
                display = _color(display, _YELLOW)
            else:
                display = _dim(display)
            marker = _bold(f"[{i}]")
            print(f"  {marker}  {label}: {display}  {_dim(hint)}")
        print()
        print(f"  {_dim('[0] Back')}")
        print()
        choice = self._prompt("Select field to adjust")
        self._apply_audio_video_choice(choice)

    def _apply_audio_video_choice(self, choice: str) -> None:
        if choice == "0":
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(_AUDIO_VIDEO_FIELDS):
                key, label, lo, hi, default, hint = _AUDIO_VIDEO_FIELDS[idx]
                current = self.settings.metadata.get(key, default)
                print(f"  Current {label}: {current}")
                raw = self._prompt(f"Enter new value ({lo}–{hi}) or press Enter to cancel")
                if raw == "":
                    return
                try:
                    val = int(raw)
                    val = max(lo, min(hi, val))
                    self.settings.metadata[key] = val
                    self._message = f"{label} set to {val}."
                except ValueError:
                    self._message = "Invalid number."
        except ValueError:
            self._message = "Invalid selection."

    def _render_controls(self) -> None:
        self._clear()
        width = 60
        print(_render_section_header("CONTROLS", width))
        print()
        controls = [
            ("W / ↑", "Move up"),
            ("S / ↓", "Move down"),
            ("A / ←", "Move left / previous"),
            ("D / →", "Move right / next"),
            ("Enter", "Confirm / select"),
            ("Esc", "Back / cancel"),
            ("M", "Open map"),
            ("I", "Open inventory"),
            ("C", "Open character sheet"),
            ("P", "Pause game"),
        ]
        for key, desc in controls:
            print(f"  {_color(key.ljust(10), _CYAN)} {desc}")
        print()
        print(f"  {_dim('[0] Back')}")
        input("  Press Enter to continue...")

    def _render_save(self) -> None:
        self.save()

    def _render_reset(self) -> None:
        if self.has_changes():
            confirm = self._prompt("Reset all settings to defaults? (y/N)")
            if confirm.lower() == "y":
                self.reset_to_defaults()
        else:
            self._message = "No changes to reset."

    # ------------------------------------------------------------------
        # Input routing
        # ------------------------------------------------------------------

    def _handle_main_choice(self, choice: str) -> None:
        handlers = {
            "1": self._render_difficulty_preset,
            "2": self._render_difficulty_customization,
            "3": self._render_accessibility,
            "4": self._render_gameplay,
            "5": self._render_audio_video,
            "6": self._render_controls,
            "7": self._render_save,
            "8": self._render_reset,
            "9": lambda: setattr(self, "_running", False),
        }
        handler = handlers.get(choice)
        if handler:
            handler()
        else:
            self._message = "Invalid selection."

    def _prompt(self, text: str) -> str:
        try:
            return input(f"  {_color(text + ': ', _CYAN)}").strip()
        except (EOFError, KeyboardInterrupt):
            return "0"

    # ------------------------------------------------------------------
        # Internal helpers
        # ------------------------------------------------------------------

    @staticmethod
    def _clone(settings: GameSettings) -> GameSettings:
        return GameSettings(
            difficulty=DifficultySettings.from_dict(settings.difficulty.to_dict()),
            accessibility=AccessibilitySettings.from_dict(settings.accessibility.to_dict()),
            metadata=dict(settings.metadata),
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def launch_settings_menu(
    settings: GameSettings | None = None,
    on_save: Any = None,
) -> GameSettings:
    """
    Launch the interactive settings menu and return the final settings.

    Args:
        settings: Initial GameSettings (uses defaults if None).
        on_save: Optional callback invoked with GameSettings on save.

    Returns:
        The (possibly modified) GameSettings.
    """
    ui = SettingsUI(settings=settings, on_save=on_save)
    return ui.run()


# ---------------------------------------------------------------------------
# Non-interactive renderers (for testing / embedding)
# ---------------------------------------------------------------------------


def render_settings_summary(settings: GameSettings) -> str:
    """Return a plain-text summary of current settings."""
    ds = settings.difficulty
    acc = settings.accessibility
    preset = DifficultyPreset.preset(ds.preset)
    lines = [
        f"Difficulty Preset: {preset['display_name']} ({ds.preset})",
        f"  DC Modifier: {ds.dc_modifier}",
        f"  Damage Dealt: {int(ds.damage_dealt_multiplier * 100)}%",
        f"  Damage Taken: {int(ds.damage_taken_multiplier * 100)}%",
        f"  XP Multiplier: {int(ds.xp_multiplier * 100)}%",
        f"  Loot Rarity Boost: {int(ds.loot_rarity_boost * 100)}%",
        f"  Status Duration: {int(ds.status_duration_multiplier * 100)}%",
        f"  Healing Effectiveness: {int(ds.healing_effectiveness_multiplier * 100)}%",
        "Accessibility:",
        f"  High Contrast: {acc.high_contrast_mode}",
        f"  Simplified Combat: {acc.simplified_combat}",
        f"  Auto Advance Dialogue: {acc.auto_advance_dialogue}",
        f"  Text Size: {acc.text_size}",
        f"  Screen Reader Mode: {acc.screen_reader_mode}",
        f"  Reduce Flashes: {acc.reduce_flashes}",
        f"  Colorblind Support: {acc.colorblind_support}",
    ]
    return "\n".join(lines)


def render_main_menu_preview(settings: GameSettings) -> str:
    """Return a plain-text preview of the main settings menu."""
    ds = settings.difficulty
    acc = settings.accessibility
    preset_name = DifficultyPreset.preset(ds.preset).get("display_name", ds.preset)
    lines = [
        f"Difficulty: {preset_name}",
        f"  Damage Dealt: {int(ds.damage_dealt_multiplier * 100)}%  "
        f"Damage Taken: {int(ds.damage_taken_multiplier * 100)}%  "
        f"XP: {int(ds.xp_multiplier * 100)}%",
        f"Accessibility: HC={acc.high_contrast_mode}  "
        f"SR={acc.screen_reader_mode}  "
        f"TS={acc.text_size}",
    ]
    return "\n".join(lines)
