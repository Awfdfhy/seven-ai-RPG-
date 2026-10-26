"""
Tests for RPG-10-20: Settings UI and Options Menu
Run with: python -m pytest tests/test_settings_ui.py -v
or:       python tests/test_settings_ui.py
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from difficulty_settings import (
    AccessibilityOption,
    AccessibilitySettings,
    DifficultyPreset,
    DifficultySettings,
    GameSettings,
)
from settings_ui import (
    SettingsUI,
    render_main_menu_preview,
    render_settings_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_settings() -> GameSettings:
    return GameSettings()


def _custom_settings() -> GameSettings:
    ds = DifficultySettings(
        preset=DifficultyPreset.HARD,
        dc_modifier=3,
        damage_dealt_multiplier=0.85,
        damage_taken_multiplier=1.4,
        xp_multiplier=1.2,
        loot_rarity_boost=0.0,
        status_duration_multiplier=1.3,
        healing_effectiveness_multiplier=0.8,
    )
    acc = AccessibilitySettings(
        high_contrast_mode=True,
        simplified_combat=False,
        auto_advance_dialogue=True,
        text_size="large",
        screen_reader_mode=False,
        reduce_flashes=True,
        colorblind_support="deuteranopia",
    )
    return GameSettings(difficulty=ds, accessibility=acc)


# ---------------------------------------------------------------------------
# SettingsUI initialization and state
# ---------------------------------------------------------------------------


class TestSettingsUIInit(unittest.TestCase):
    def test_defaults(self):
        ui = SettingsUI()
        assert ui.settings is not None
        assert ui.settings.difficulty.preset == DifficultyPreset.NORMAL
        assert ui.settings.accessibility.text_size == AccessibilityOption.DEFAULTS[AccessibilityOption.TEXT_SIZE]

    def test_custom_settings(self):
        s = _custom_settings()
        ui = SettingsUI(settings=s)
        assert ui.settings.difficulty.preset == DifficultyPreset.HARD
        assert ui.settings.accessibility.high_contrast_mode is True
        assert ui.settings.accessibility.text_size == "large"

    def test_save_callback(self):
        saved = []

        def on_save(settings):
            saved.append(settings)

        ui = SettingsUI(settings=_default_settings(), on_save=on_save)
        ui.save()
        assert len(saved) == 1
        assert saved[0] is ui.settings


# ---------------------------------------------------------------------------
# Change tracking
# ---------------------------------------------------------------------------


class TestSettingsUIChanges(unittest.TestCase):
    def test_no_changes_initially(self):
        ui = SettingsUI(settings=_default_settings())
        assert ui.has_changes() is False

    def test_detects_difficulty_change(self):
        ui = SettingsUI(settings=_default_settings())
        ui.settings.difficulty.preset = DifficultyPreset.HARD
        assert ui.has_changes() is True

    def test_detects_accessibility_change(self):
        ui = SettingsUI(settings=_default_settings())
        ui.settings.accessibility.high_contrast_mode = True
        assert ui.has_changes() is True

    def test_reset_clears_changes(self):
        ui = SettingsUI(settings=_default_settings())
        ui.settings.difficulty.preset = DifficultyPreset.HARD
        ui.reset_to_defaults()
        assert ui.has_changes() is False
        assert ui.settings.difficulty.preset == DifficultyPreset.NORMAL

    def test_save_clears_changes(self):
        ui = SettingsUI(settings=_default_settings())
        ui.settings.difficulty.preset = DifficultyPreset.EASY
        ui.save()
        assert ui.has_changes() is False

    def test_clone_independence(self):
        ui = SettingsUI(settings=_default_settings())
        ui.settings.difficulty.dc_modifier = 5
        assert ui._original.difficulty.dc_modifier == 0


# ---------------------------------------------------------------------------
# Difficulty preset routing
# ---------------------------------------------------------------------------


class TestSettingsUIDifficultyPreset(unittest.TestCase):
    def test_preset_narrative(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_difficulty_preset_choice("1")
        assert ui.settings.difficulty.preset == DifficultyPreset.NARRATIVE

    def test_preset_easy(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_difficulty_preset_choice("2")
        assert ui.settings.difficulty.preset == DifficultyPreset.EASY

    def test_preset_normal(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_difficulty_preset_choice("3")
        assert ui.settings.difficulty.preset == DifficultyPreset.NORMAL

    def test_preset_hard(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_difficulty_preset_choice("4")
        assert ui.settings.difficulty.preset == DifficultyPreset.HARD

    def test_preset_nightmare(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_difficulty_preset_choice("5")
        assert ui.settings.difficulty.preset == DifficultyPreset.NIGHTMARE

    def test_preset_back(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_difficulty_preset_choice("0")
        assert ui.settings.difficulty.preset == DifficultyPreset.NORMAL

    def test_preset_invalid(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_difficulty_preset_choice("99")
        assert ui.settings.difficulty.preset == DifficultyPreset.NORMAL
        assert "Invalid selection" in ui._message


# ---------------------------------------------------------------------------
# Difficulty customization routing
# ---------------------------------------------------------------------------


class TestSettingsUIDifficultyCustom(unittest.TestCase):
    def test_dc_modifier_adjust(self):
        ui = SettingsUI(settings=_default_settings())
        with patch.object(ui, "_prompt", side_effect=["3"]):
            ui._apply_difficulty_custom_choice("1")
        assert ui.settings.difficulty.dc_modifier == 3

    def test_damage_dealt_adjust(self):
        ui = SettingsUI(settings=_default_settings())
        with patch.object(ui, "_prompt", side_effect=["150"]):
            ui._apply_difficulty_custom_choice("2")
        # After choosing field 2 (damage_dealt_multiplier), value 150 -> 1.5
        assert ui.settings.difficulty.damage_dealt_multiplier == 1.5

    def test_cancel_edit(self):
        ui = SettingsUI(settings=_default_settings())
        with patch.object(ui, "_prompt", side_effect=[""]):
            ui._apply_difficulty_custom_choice("1")
        assert ui.settings.difficulty.dc_modifier == 0

    def test_clamp_high(self):
        ui = SettingsUI(settings=_default_settings())
        with patch.object(ui, "_prompt", side_effect=["999"]):
            ui._apply_difficulty_custom_choice("1")
        assert ui.settings.difficulty.dc_modifier == 10

    def test_clamp_low(self):
        ui = SettingsUI(settings=_default_settings())
        with patch.object(ui, "_prompt", side_effect=["-999"]):
            ui._apply_difficulty_custom_choice("1")
        assert ui.settings.difficulty.dc_modifier == -10


# ---------------------------------------------------------------------------
# Accessibility routing
# ---------------------------------------------------------------------------


class TestSettingsUIAccessibility(unittest.TestCase):
    def test_toggle_high_contrast(self):
        ui = SettingsUI(settings=_default_settings())
        assert ui.settings.accessibility.high_contrast_mode is False
        ui._apply_accessibility_choice("1")
        assert ui.settings.accessibility.high_contrast_mode is True

    def test_toggle_screen_reader(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_accessibility_choice("5")
        assert ui.settings.accessibility.screen_reader_mode is True

    def test_cycle_text_size(self):
        ui = SettingsUI(settings=_default_settings())
        assert ui.settings.accessibility.text_size == "normal"
        ui._apply_accessibility_choice("4")
        assert ui.settings.accessibility.text_size == "large"
        ui._apply_accessibility_choice("4")
        assert ui.settings.accessibility.text_size == "extra_large"
        ui._apply_accessibility_choice("4")
        assert ui.settings.accessibility.text_size == "normal"

    def test_cycle_colorblind(self):
        ui = SettingsUI(settings=_default_settings())
        assert ui.settings.accessibility.colorblind_support == "none"
        ui._apply_accessibility_choice("7")
        assert ui.settings.accessibility.colorblind_support == "protanopia"
        ui._apply_accessibility_choice("7")
        assert ui.settings.accessibility.colorblind_support == "deuteranopia"

    def test_invalid_accessibility_choice(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_accessibility_choice("99")
        assert "Invalid selection" in ui._message


# ---------------------------------------------------------------------------
# Gameplay toggles
# ---------------------------------------------------------------------------


class TestSettingsUIGameplay(unittest.TestCase):
    def test_toggle_auto_save(self):
        ui = SettingsUI(settings=_default_settings())
        assert ui.settings.metadata.get("auto_save", True) is True
        ui._apply_gameplay_choice("1")
        assert ui.settings.metadata.get("auto_save") is False

    def test_toggle_subtitles(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_gameplay_choice("2")
        assert ui.settings.metadata.get("show_subtitles") is False

    def test_invalid_gameplay_choice(self):
        ui = SettingsUI(settings=_default_settings())
        ui._apply_gameplay_choice("99")
        assert "Invalid selection" in ui._message


# ---------------------------------------------------------------------------
# Audio / Video
# ---------------------------------------------------------------------------


class TestSettingsUIAudioVideo(unittest.TestCase):
    def test_adjust_master_volume(self):
        ui = SettingsUI(settings=_default_settings())
        with patch.object(ui, "_prompt", side_effect=["50"]):
            ui._apply_audio_video_choice("1")
        assert ui.settings.metadata.get("master_volume") == 50

    def test_clamp_volume(self):
        ui = SettingsUI(settings=_default_settings())
        with patch.object(ui, "_prompt", side_effect=["150"]):
            ui._apply_audio_video_choice("1")
        assert ui.settings.metadata.get("master_volume") == 100

    def test_cancel_volume(self):
        ui = SettingsUI(settings=_default_settings())
        with patch.object(ui, "_prompt", side_effect=[""]):
            ui._apply_audio_video_choice("1")
        assert "master_volume" not in ui.settings.metadata


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


class TestRenderSettingsSummary(unittest.TestCase):
    def test_defaults(self):
        out = render_settings_summary(_default_settings())
        assert "Normal" in out
        assert "DC Modifier: 0" in out
        assert "Damage Dealt: 100%" in out
        assert "Text Size: normal" in out

    def test_custom(self):
        out = render_settings_summary(_custom_settings())
        assert "Hard" in out
        assert "High Contrast: True" in out
        assert "Text Size: large" in out
        assert "Colorblind Support: deuteranopia" in out


class TestRenderMainMenuPreview(unittest.TestCase):
    def test_preview_defaults(self):
        out = render_main_menu_preview(_default_settings())
        assert "Normal" in out
        assert "100%" in out

    def test_preview_custom(self):
        out = render_main_menu_preview(_custom_settings())
        assert "Hard" in out
        assert "HC=True" in out


# ---------------------------------------------------------------------------
# SettingsUI integration (mocked input)
# ---------------------------------------------------------------------------


class TestSettingsUIIntegration(unittest.TestCase):
    def test_save_preserves_settings(self):
        ui = SettingsUI(settings=_custom_settings())
        ui.save()
        assert ui.has_changes() is False
        assert ui.settings.difficulty.preset == DifficultyPreset.HARD

    def test_reset_restores_defaults(self):
        ui = SettingsUI(settings=_custom_settings())
        ui.reset_to_defaults()
        assert ui.settings.difficulty.preset == DifficultyPreset.NORMAL
        assert ui.settings.accessibility.high_contrast_mode is False

    def test_metadata_roundtrip(self):
        s = _default_settings()
        s.metadata["master_volume"] = 60
        s.metadata["show_subtitles"] = False
        ui = SettingsUI(settings=s)
        assert ui.settings.metadata["master_volume"] == 60
        assert ui.settings.metadata["show_subtitles"] is False


if __name__ == "__main__":
    unittest.main()
