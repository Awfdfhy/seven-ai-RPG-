"""
RPG-10-11: Accessibility Features
Provides colorblind mode, text scaling, and simplified controls
for the Seven RPG terminal-based UI.

Features
--------
ColorblindMode : enum of supported colorblind types
TextScale      : enum of supported text size presets
SimplifiedControls : flag that toggles simpler command prompts
AccessibilitySettings : aggregate settings dataclass
AccessibilityHelper   : applies settings to rendered UI strings
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ColorblindMode(str, Enum):
    """Supported colorblind accessibility modes."""
    OFF = "off"
    PROTANOPIA = "protanopia"        # red-blind
    DEUTERANOPIA = "deuteranopia"    # green-blind
    TRITANOPIA = "tritanopia"        # blue-blind
    MONOCHROME = "monochrome"        # grayscale


class TextScale(str, Enum):
    """Supported text scaling presets."""
    SMALL = "small"        # 0.75x
    NORMAL = "normal"      # 1.0x
    LARGE = "large"        # 1.5x
    EXTRA_LARGE = "xlarge" # 2.0x


# ---------------------------------------------------------------------------
# ANSI color palettes
# ---------------------------------------------------------------------------

# Default palette (standard 8-color ANSI)
_DEFAULT_COLORS: dict[str, str] = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
    "inverse": "\033[7m",
}

# Colorblind-safe palettes
_COLORBLIND_PALETTES: dict[str, dict[str, str]] = {
    ColorblindMode.PROTANOPIA: {
        "black": "\033[30m",
        "red": "\033[34m",      # use blue instead of red
        "green": "\033[36m",    # use cyan instead of green
        "yellow": "\033[37m",   # use white instead of yellow
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
        "inverse": "\033[7m",
    },
    ColorblindMode.DEUTERANOPIA: {
        "black": "\033[30m",
        "red": "\033[31m",      # keep red, but it may look brownish
        "green": "\033[34m",    # use blue instead of green
        "yellow": "\033[37m",   # use white instead of yellow
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
        "inverse": "\033[7m",
    },
    ColorblindMode.TRITANOPIA: {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",   # keep yellow (still visible to tritanopia)
        "blue": "\033[34m",     # use dark blue instead of light blue
        "magenta": "\033[35m",
        "cyan": "\033[36m",     # use cyan instead of light blue
        "white": "\033[37m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
        "inverse": "\033[7m",
    },
    ColorblindMode.MONOCHROME: {
        "black": "\033[30m",
        "red": "\033[37m",      # white instead of red
        "green": "\033[37m",    # white instead of green
        "yellow": "\033[37m",   # white instead of yellow
        "blue": "\033[37m",     # white instead of blue
        "magenta": "\033[37m",  # white instead of magenta
        "cyan": "\033[37m",     # white instead of cyan
        "white": "\033[37m",    # bright white
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
        "inverse": "\033[7m",
    },
}

# Text scaling multipliers
_TEXT_SCALE_MULTIPLIERS: dict[TextScale, float] = {
    TextScale.SMALL: 0.75,
    TextScale.NORMAL: 1.0,
    TextScale.LARGE: 1.5,
    TextScale.EXTRA_LARGE: 2.0,
}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@dataclass
class AccessibilitySettings:
    """
    Aggregate accessibility settings for the game UI.

    Attributes:
        colorblind_mode   : colorblind accessibility mode (default: off)
        text_scale        : text size preset (default: normal)
        simplified_controls : if True, use shorter/simpler command prompts
        high_contrast     : if True, emphasize borders and labels
    """
    colorblind_mode: ColorblindMode = ColorblindMode.OFF
    text_scale: TextScale = TextScale.NORMAL
    simplified_controls: bool = False
    high_contrast: bool = False

    @classmethod
    def from_game_settings(cls, game_accessibility: Any) -> AccessibilitySettings:
        """
        Convert a difficulty_settings.AccessibilitySettings instance
        into this module's AccessibilitySettings.

        Unknown/missing fields fall back to defaults.
        """
        cb_map = {
            "none": ColorblindMode.OFF,
            "protanopia": ColorblindMode.PROTANOPIA,
            "deuteranopia": ColorblindMode.DEUTERANOPIA,
            "tritanopia": ColorblindMode.TRITANOPIA,
        }
        ts_map = {
            "normal": TextScale.NORMAL,
            "large": TextScale.LARGE,
            "extra_large": TextScale.EXTRA_LARGE,
        }
        colorblind_raw = getattr(game_accessibility, "colorblind_support", "none")
        text_size_raw = getattr(game_accessibility, "text_size", "normal")
        return cls(
            colorblind_mode=cb_map.get(colorblind_raw, ColorblindMode.OFF),
            text_scale=ts_map.get(text_size_raw, TextScale.NORMAL),
            simplified_controls=bool(getattr(game_accessibility, "simplified_combat", False)),
            high_contrast=bool(getattr(game_accessibility, "high_contrast_mode", False)),
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

class AccessibilityHelper:
    """
    Applies accessibility settings to rendered UI strings.

    Usage:
        helper = AccessibilityHelper(settings)
        safe_text = helper.color_text("Hello", "green")
        scaled = helper.scale_text("Line 1\\nLine 2")
    """

    def __init__(self, settings: AccessibilitySettings | None = None) -> None:
        self.settings = settings or AccessibilitySettings()

    @classmethod
    def from_game_settings(cls, game_settings: Any) -> AccessibilityHelper:
        """
        Construct an AccessibilityHelper from a GameSettings or
        difficulty_settings.AccessibilitySettings instance.
        """
        if hasattr(game_settings, "accessibility"):
            acc = game_settings.accessibility
        else:
            acc = game_settings
        return cls(AccessibilitySettings.from_game_settings(acc))

    # --- palette ----------------------------------------------------------

    def get_color(self, name: str) -> str:
        """Return the ANSI escape code for `name` under current settings."""
        mode = self.settings.colorblind_mode
        if mode != ColorblindMode.OFF:
            palette = _COLORBLIND_PALETTES.get(mode, {})
            if name in palette:
                return palette[name]
        return _DEFAULT_COLORS.get(name, "")

    def color_text(self, text: str, color_name: str) -> str:
        """Wrap text in the appropriate ANSI color code + reset."""
        code = self.get_color(color_name)
        reset = self.get_color("reset")
        return f"{code}{text}{reset}"

    # --- scaling ----------------------------------------------------------

    def scale_text(self, text: str) -> str:
        """
        Scale text vertically by repeating each line `multiplier` times.

        For text_scale > 1.0, lines are widened by repeating characters.
        For text_scale < 1.0, lines are narrowed by dropping characters.
        """
        multiplier = _TEXT_SCALE_MULTIPLIERS.get(self.settings.text_scale, 1.0)
        lines = text.split("\n")
        result: list[str] = []
        for line in lines:
            target_len = max(1, round(len(line) * multiplier))
            if multiplier >= 1.0:
                # Stretch: repeat characters to fill target length
                stretched = ""
                for i, ch in enumerate(line):
                    repeats = max(1, round(multiplier))
                    stretched += ch * repeats
                result.append(stretched[:target_len])
            else:
                # Shrink: sample characters
                if len(line) <= target_len:
                    result.append(line)
                else:
                    indices = [int(i * len(line) / target_len) for i in range(target_len)]
                    result.append("".join(line[i] for i in indices))
        return "\n".join(result)

    # --- simplified controls ----------------------------------------------

    def simplify_command_prompt(self, prompt: str) -> str:
        """
        Simplify a command prompt for easier reading.

        If simplified_controls is enabled, replace verbose instructions
        with shorter alternatives.
        """
        if not self.settings.simplified_controls:
            return prompt

        replacements = {
            "Enter a number/letter to travel, or 'l' for location info.": "Choose: number = travel, l = info, q = quit",
            "number=travel, l=info, q=quit": "number/l/q",
            "Press Enter to continue...": "Press Enter...",
            "Press Enter to return to map...": "Press Enter...",
        }
        result = prompt
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    # --- high contrast ----------------------------------------------------

    def emphasize(self, text: str) -> str:
        """
        Wrap text in bold + inverse if high_contrast is enabled.
        """
        if not self.settings.high_contrast:
            return text
        bold = self.get_color("bold")
        inverse = self.get_color("inverse")
        reset = self.get_color("reset")
        return f"{bold}{inverse}{text}{reset}"

    # --- bulk helpers -----------------------------------------------------

    def apply_to_ui(self, ui_output: str) -> str:
        """
        Apply all active accessibility transformations to a UI output string.
        """
        result = self.simplify_command_prompt(ui_output)
        if self.settings.text_scale != TextScale.NORMAL:
            result = self.scale_text(result)
        return result

    def accessible_rarity_colors(self) -> dict[str, str]:
        """
        Return rarity -> ANSI code mapping adjusted for colorblind mode.
        Falls back to adding text markers when color alone is insufficient.
        """
        mode = self.settings.colorblind_mode
        if mode == ColorblindMode.OFF:
            return {
                "common": "\033[37m",
                "uncommon": "\033[32m",
                "rare": "\033[34m",
                "epic": "\033[35m",
                "legendary": "\033[33m",
            }

        # In colorblind mode, prepend a text marker for distinction
        base = _COLORBLIND_PALETTES.get(mode, {})
        return {
            "common": base.get("white", "") + "[C]",
            "uncommon": base.get("green", "") + "[U]",
            "rare": base.get("blue", "") + "[R]",
            "epic": base.get("magenta", "") + "[E]",
            "legendary": base.get("yellow", "") + "[L]",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "colorblind_mode": self.settings.colorblind_mode.value,
            "text_scale": self.settings.text_scale.value,
            "simplified_controls": self.settings.simplified_controls,
            "high_contrast": self.settings.high_contrast,
        }
