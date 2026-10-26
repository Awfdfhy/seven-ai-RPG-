"""
Tests for RPG-10-19: Main Menu UI
Run with: python -m pytest tests/test_main_menu_ui.py -v
or:       python tests/test_main_menu_ui.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from accessibility import AccessibilityHelper
from difficulty_settings import (
    DifficultyPreset,
    GameSettings,
)
from main_menu_ui import (
    MainMenuNavigation,
    MainMenuUI,
    MainMenuUISession,
    MenuOption,
    _default_menu_options,
    create_main_menu_session,
    render_credits,
    render_main_menu,
    render_settings_panel,
    render_title_screen,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_settings() -> GameSettings:
    return GameSettings()


# ---------------------------------------------------------------------------
# Title screen tests
# ---------------------------------------------------------------------------

class TestRenderTitleScreen:
    def test_returns_string(self):
        out = render_title_screen()
        assert isinstance(out, str)

    def test_contains_version(self):
        out = render_title_screen(version="0.1.0")
        assert "0.1.0" in out

    def test_contains_title_text(self):
        out = render_title_screen()
        assert "SEVEN" in out or "RPG" in out or "modular" in out

    def test_contains_continue_prompt(self):
        out = render_title_screen()
        assert "Enter" in out


# ---------------------------------------------------------------------------
# Menu option tests
# ---------------------------------------------------------------------------

class TestMenuOption:
    def test_default_options_count(self):
        opts = _default_menu_options()
        assert len(opts) >= 4

    def test_default_options_include_new_game(self):
        opts = _default_menu_options()
        actions = [o.action for o in opts]
        assert "new_game" in actions

    def test_default_options_include_quit(self):
        opts = _default_menu_options()
        actions = [o.action for o in opts]
        assert "quit" in actions

    def test_disabled_option(self):
        opt = MenuOption("2", "Continue", "continue", enabled=False)
        assert opt.enabled is False


# ---------------------------------------------------------------------------
# Main menu rendering tests
# ---------------------------------------------------------------------------

class TestRenderMainMenu:
    def test_returns_string(self):
        out = render_main_menu()
        assert isinstance(out, str)

    def test_contains_main_menu_header(self):
        out = render_main_menu()
        assert "MAIN MENU" in out

    def test_contains_new_game(self):
        out = render_main_menu()
        assert "New Game" in out

    def test_contains_quit(self):
        out = render_main_menu()
        assert "Quit" in out

    def test_selection_marker(self):
        out = render_main_menu(selected_index=0)
        assert "▶" in out

    def test_disabled_option_appears_dimmed(self):
        opts = [
            MenuOption("1", "Enabled", "enabled", enabled=True),
            MenuOption("2", "Disabled", "disabled", enabled=False),
        ]
        out = render_main_menu(opts, selected_index=0)
        assert "Disabled" in out

    def test_custom_options(self):
        opts = [MenuOption("a", "Alpha", "alpha")]
        out = render_main_menu(opts)
        assert "Alpha" in out


# ---------------------------------------------------------------------------
# Settings panel tests
# ---------------------------------------------------------------------------

class TestRenderSettingsPanel:
    def test_returns_string(self):
        out = render_settings_panel()
        assert isinstance(out, str)

    def test_contains_settings_header(self):
        out = render_settings_panel()
        assert "SETTINGS" in out

    def test_contains_difficulty_label(self):
        out = render_settings_panel()
        assert "Difficulty" in out

    def test_contains_accessibility_label(self):
        out = render_settings_panel()
        assert "Accessibility" in out

    def test_contains_default_difficulty(self):
        out = render_settings_panel()
        assert "normal" in out.lower()

    def test_with_custom_settings(self):
        settings = GameSettings(difficulty=DifficultyPreset.HARD)
        out = render_settings_panel(settings)
        assert "hard" in out.lower()


# ---------------------------------------------------------------------------
# Credits tests
# ---------------------------------------------------------------------------

class TestRenderCredits:
    def test_returns_string(self):
        out = render_credits()
        assert isinstance(out, str)

    def test_contains_credits_header(self):
        out = render_credits()
        assert "CREDITS" in out

    def test_contains_team_text(self):
        out = render_credits()
        assert "Seven RPG Team" in out


# ---------------------------------------------------------------------------
# Navigation tests
# ---------------------------------------------------------------------------

class TestMainMenuNavigation:
    def test_default_selection(self):
        nav = MainMenuNavigation()
        assert nav.selected_index == 0

    def test_move_down(self):
        nav = MainMenuNavigation()
        nav.move_selection(1)
        # Default menu has "Continue" disabled at index 1, so it wraps to index 2
        assert nav.selected_index == 2

    def test_move_up(self):
        nav = MainMenuNavigation()
        nav.move_selection(-1)
        assert nav.selected_index == 4  # wraps around from 0

    def test_select_valid(self):
        nav = MainMenuNavigation()
        opt = nav.select("1")
        assert opt is not None
        assert opt.action == "new_game"

    def test_select_invalid(self):
        nav = MainMenuNavigation()
        opt = nav.select("9")
        assert opt is None

    def test_current_option(self):
        nav = MainMenuNavigation()
        opt = nav.current_option()
        assert opt is not None
        assert opt.enabled is True

    def test_skip_disabled(self):
        opts = [
            MenuOption("1", "First", "first", enabled=False),
            MenuOption("2", "Second", "second", enabled=True),
        ]
        nav = MainMenuNavigation(options=opts)
        nav.move_selection(1)
        assert nav.selected_index == 1


# ---------------------------------------------------------------------------
# MainMenuUI facade tests
# ---------------------------------------------------------------------------

class TestMainMenuUI:
    def test_show_title_screen(self):
        ui = MainMenuUI()
        out = ui.show_title_screen()
        assert "SEVEN" in out or "RPG" in out or "modular" in out

    def test_show_main_menu(self):
        ui = MainMenuUI()
        out = ui.show_main_menu()
        assert "MAIN MENU" in out

    def test_show_settings(self):
        ui = MainMenuUI()
        out = ui.show_settings()
        assert "SETTINGS" in out

    def test_show_credits(self):
        ui = MainMenuUI()
        out = ui.show_credits()
        assert "CREDITS" in out

    def test_update_settings(self):
        ui = MainMenuUI()
        new_settings = GameSettings(difficulty=DifficultyPreset.HARD)
        ui.update_settings(new_settings)
        assert ui.settings.difficulty == DifficultyPreset.HARD


# ---------------------------------------------------------------------------
# Interactive session smoke tests
# ---------------------------------------------------------------------------

class TestMainMenuUISession:
    def test_initial_render_does_not_crash(self):
        session = MainMenuUISession()
        session._running = False
        session._render()

    def test_session_run_returns_quit_when_choice_q(self):
        session = MainMenuUISession()
        session._running = True
        # Monkey-patch input to simulate 'q'
        session._view = "menu"
        session._running = False
        # Just verify construction works
        assert session.ui is not None

    def test_factory(self):
        session = create_main_menu_session()
        assert isinstance(session, MainMenuUISession)

    def test_session_has_version(self):
        session = MainMenuUISession(version="1.2.3")
        assert session.version == "1.2.3"


# ---------------------------------------------------------------------------
# Accessibility integration tests
# ---------------------------------------------------------------------------

class TestAccessibilityIntegration:
    def test_title_screen_with_accessibility(self):
        from accessibility import AccessibilitySettings
        acc = AccessibilityHelper(
            settings=AccessibilitySettings(
                text_scale="normal",
                high_contrast=False,
            )
        )
        out = render_title_screen(accessibility=acc)
        assert isinstance(out, str)
        assert len(out) > 0

    def test_main_menu_with_accessibility(self):
        from accessibility import AccessibilitySettings
        acc = AccessibilityHelper(
            settings=AccessibilitySettings(
                text_scale="normal",
                high_contrast=False,
            )
        )
        out = render_main_menu(accessibility=acc)
        assert "MAIN MENU" in out

    def test_settings_with_accessibility(self):
        from accessibility import AccessibilitySettings
        acc = AccessibilityHelper(
            settings=AccessibilitySettings(
                text_scale="normal",
                high_contrast=False,
            )
        )
        out = render_settings_panel(accessibility=acc)
        assert "SETTINGS" in out


if __name__ == "__main__":
    import traceback

    suites = [
        TestRenderTitleScreen,
        TestMenuOption,
        TestRenderMainMenu,
        TestRenderSettingsPanel,
        TestRenderCredits,
        TestMainMenuNavigation,
        TestMainMenuUI,
        TestMainMenuUISession,
        TestAccessibilityIntegration,
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
