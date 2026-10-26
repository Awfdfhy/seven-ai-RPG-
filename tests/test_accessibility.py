"""
Tests for RPG-10-11: Accessibility Features
Run with: python tests/test_accessibility.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from accessibility import (
    AccessibilityHelper,
    AccessibilitySettings,
    ColorblindMode,
    TextScale,
)
from difficulty_settings import AccessibilitySettings as GameAccessibilitySettings

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TestAccessibilitySettings:
    def test_defaults(self):
        s = AccessibilitySettings()
        assert s.colorblind_mode == ColorblindMode.OFF
        assert s.text_scale == TextScale.NORMAL
        assert s.simplified_controls is False
        assert s.high_contrast is False


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

class TestColorText:
    def test_default_color(self):
        helper = AccessibilityHelper()
        out = helper.color_text("hello", "green")
        assert "\033[32m" in out
        assert "hello" in out
        assert "\033[0m" in out

    def test_colorblind_overrides(self):
        for mode in (
            ColorblindMode.PROTANOPIA,
            ColorblindMode.DEUTERANOPIA,
            ColorblindMode.TRITANOPIA,
            ColorblindMode.MONOCHROME,
        ):
            settings = AccessibilitySettings(colorblind_mode=mode)
            helper = AccessibilityHelper(settings)
            out = helper.color_text("hi", "red")
            # Should contain an ANSI code
            assert "\033[" in out
            assert "hi" in out

    def test_unknown_color_falls_back(self):
        helper = AccessibilityHelper()
        out = helper.color_text("x", "not_a_color")
        assert "x" in out

    def test_high_contrast_emphasize(self):
        settings = AccessibilitySettings(high_contrast=True)
        helper = AccessibilityHelper(settings)
        out = helper.emphasize("text")
        assert "\033[1m" in out
        assert "\033[7m" in out


# ---------------------------------------------------------------------------
# Text scaling
# ---------------------------------------------------------------------------

class TestScaleText:
    def test_normal_no_change(self):
        helper = AccessibilityHelper()
        assert helper.scale_text("hello") == "hello"

    def test_large_centers(self):
        settings = AccessibilitySettings(text_scale=TextScale.LARGE)
        helper = AccessibilityHelper(settings)
        out = helper.scale_text("hi")
        # 2 chars * 1.5 = 3 chars
        assert len(out) == 3

    def test_xlarge_doubles(self):
        settings = AccessibilitySettings(text_scale=TextScale.EXTRA_LARGE)
        helper = AccessibilityHelper(settings)
        out = helper.scale_text("ab")
        # 2 chars * 2.0 = 4 chars
        assert len(out) == 4

    def test_small_compresses(self):
        settings = AccessibilitySettings(text_scale=TextScale.SMALL)
        helper = AccessibilityHelper(settings)
        out = helper.scale_text("hello")
        # 5 chars * 0.75 = 3.75 -> round to 4
        assert len(out) == 4


# ---------------------------------------------------------------------------
# Simplified controls
# ---------------------------------------------------------------------------

class TestSimplifiedControls:
    def test_no_change_when_off(self):
        helper = AccessibilityHelper()
        original = "Enter a number/letter to travel, or 'l' for location info."
        assert helper.simplify_command_prompt(original) == original

    def test_shortens_prompt(self):
        settings = AccessibilitySettings(simplified_controls=True)
        helper = AccessibilityHelper(settings)
        original = "Enter a number/letter to travel, or 'l' for location info."
        simplified = helper.simplify_command_prompt(original)
        assert simplified != original
        assert "number = travel" in simplified

    def test_press_enter(self):
        settings = AccessibilitySettings(simplified_controls=True)
        helper = AccessibilityHelper(settings)
        assert helper.simplify_command_prompt("Press Enter to continue...") == "Press Enter..."
        assert helper.simplify_command_prompt("Press Enter to return to map...") == "Press Enter..."


# ---------------------------------------------------------------------------
# Bulk apply
# ---------------------------------------------------------------------------

class TestApplyToUI:
    def test_passthrough_by_default(self):
        helper = AccessibilityHelper()
        out = helper.apply_to_ui("plain text")
        assert out == "plain text"

    def test_simplify_then_scale(self):
        settings = AccessibilitySettings(
            simplified_controls=True,
            text_scale=TextScale.LARGE,
        )
        helper = AccessibilityHelper(settings)
        prompt = "Enter a number/letter to travel, or 'l' for location info."
        out = helper.apply_to_ui(prompt)
        # Scaling repeats characters, so check the un-scaled simplified form
        # by applying simplification independently
        simplified = helper.simplify_command_prompt(prompt)
        assert "number = travel" in simplified
        assert out != prompt


# ---------------------------------------------------------------------------
# Accessibility-aware rarity colors
# ---------------------------------------------------------------------------

class TestAccessibleRarityColors:
    def test_default_has_codes(self):
        helper = AccessibilityHelper()
        colors = helper.accessible_rarity_colors()
        for key in ("common", "uncommon", "rare", "epic", "legendary"):
            assert key in colors
            assert "\033[" in colors[key]

    def test_monochrome_adds_markers(self):
        settings = AccessibilitySettings(colorblind_mode=ColorblindMode.MONOCHROME)
        helper = AccessibilityHelper(settings)
        colors = helper.accessible_rarity_colors()
        assert "[C]" in colors["common"]
        assert "[L]" in colors["legendary"]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestToDict:
    def test_roundtrip(self):
        settings = AccessibilitySettings(
            colorblind_mode=ColorblindMode.DEUTERANOPIA,
            text_scale=TextScale.LARGE,
            simplified_controls=True,
            high_contrast=True,
        )
        helper = AccessibilityHelper(settings)
        d = helper.to_dict()
        assert d["colorblind_mode"] == "deuteranopia"
        assert d["text_scale"] == "large"
        assert d["simplified_controls"] is True
        assert d["high_contrast"] is True


# ---------------------------------------------------------------------------
# Game settings bridge
# ---------------------------------------------------------------------------

class TestFromGameSettings:
    def test_defaults_from_game_settings(self):
        game_acc = GameAccessibilitySettings()
        settings = AccessibilitySettings.from_game_settings(game_acc)
        assert settings.colorblind_mode == ColorblindMode.OFF
        assert settings.text_scale == TextScale.NORMAL
        assert settings.simplified_controls is False
        assert settings.high_contrast is False

    def test_colorblind_mapping(self):
        for game_val, expected in (
            ("protanopia", ColorblindMode.PROTANOPIA),
            ("deuteranopia", ColorblindMode.DEUTERANOPIA),
            ("tritanopia", ColorblindMode.TRITANOPIA),
            ("none", ColorblindMode.OFF),
        ):
            game_acc = GameAccessibilitySettings(colorblind_support=game_val)
            settings = AccessibilitySettings.from_game_settings(game_acc)
            assert settings.colorblind_mode == expected

    def test_text_size_mapping(self):
        for game_val, expected in (
            ("normal", TextScale.NORMAL),
            ("large", TextScale.LARGE),
            ("extra_large", TextScale.EXTRA_LARGE),
        ):
            game_acc = GameAccessibilitySettings(text_size=game_val)
            settings = AccessibilitySettings.from_game_settings(game_acc)
            assert settings.text_scale == expected

    def test_simplified_combat_maps_to_simplified_controls(self):
        game_acc = GameAccessibilitySettings(simplified_combat=True)
        settings = AccessibilitySettings.from_game_settings(game_acc)
        assert settings.simplified_controls is True

    def test_high_contrast_mode_maps_to_high_contrast(self):
        game_acc = GameAccessibilitySettings(high_contrast_mode=True)
        settings = AccessibilitySettings.from_game_settings(game_acc)
        assert settings.high_contrast is True


class TestHelperFromGameSettings:
    def test_from_game_settings_creates_helper(self):
        game_acc = GameAccessibilitySettings(
            colorblind_support="deuteranopia",
            text_size="large",
            simplified_combat=True,
            high_contrast_mode=True,
        )
        helper = AccessibilityHelper.from_game_settings(game_acc)
        assert helper.settings.colorblind_mode == ColorblindMode.DEUTERANOPIA
        assert helper.settings.text_scale == TextScale.LARGE
        assert helper.settings.simplified_controls is True
        assert helper.settings.high_contrast is True

    def test_from_game_settings_with_game_settings_object(self):
        from difficulty_settings import GameSettings
        gs = GameSettings()
        gs.accessibility = GameAccessibilitySettings(
            colorblind_support="protanopia",
            text_size="extra_large",
        )
        helper = AccessibilityHelper.from_game_settings(gs)
        assert helper.settings.colorblind_mode == ColorblindMode.PROTANOPIA
        assert helper.settings.text_scale == TextScale.EXTRA_LARGE


if __name__ == "__main__":
    suites = [
        TestAccessibilitySettings,
        TestColorText,
        TestScaleText,
        TestSimplifiedControls,
        TestApplyToUI,
        TestAccessibleRarityColors,
        TestToDict,
        TestFromGameSettings,
        TestHelperFromGameSettings,
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
                    import traceback
                    traceback.print_exc()
                    failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
