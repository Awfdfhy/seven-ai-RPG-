"""
Tests for RPG-XX Title System.
Run with: python -m pytest tests/ -v
or:       python tests/test_title_system.py
"""

from __future__ import annotations

import os
import sys

# Allow running from the repo root or the tests/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from character_sheet import CharacterSheet
from npc_reaction import NPCProfile, NPCReactionResolver
from title_system import (
    CharacterTitleState,
    TitleDefinition,
    TitleManager,
    TitleType,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _title_manager() -> TitleManager:
    mgr = TitleManager()
    return mgr


def _resolver() -> NPCReactionResolver:
    return NPCReactionResolver(title_manager=_title_manager())


# ---------------------------------------------------------------------------
# TitleDefinition tests
# ---------------------------------------------------------------------------

class TestTitleDefinition:
    def test_to_from_dict_roundtrip(self):
        data = {
            "id": "test.x",
            "name": "Test Title",
            "description": "A test title.",
            "title_type": "title",
            "requirements": {"quests_completed": 1},
            "effects": {"npc_reaction_modifier": 2},
            "display_format": "{name} the {title}",
        }
        title = TitleDefinition.from_dict(data)
        assert title.id == "test.x"
        assert title.title_type == TitleType.TITLE
        assert title.requirements == {"quests_completed": 1}
        assert title.effects == {"npc_reaction_modifier": 2}
        assert title.to_dict()["display_format"] == "{name} the {title}"

    def test_default_values(self):
        title = TitleDefinition(id="a", name="A")
        assert title.description == ""
        assert title.title_type == TitleType.TITLE
        assert title.requirements == {}
        assert title.effects == {}
        assert title.display_format == "{name} the {title}"


# ---------------------------------------------------------------------------
# CharacterTitleState tests
# ---------------------------------------------------------------------------

class TestCharacterTitleState:
    def test_initial_state(self):
        state = CharacterTitleState(character_id="c1")
        assert state.prestige_points == 0
        assert state.title_ranks == {}
        assert state.active_honorific is None

    def test_set_and_get_title_rank(self):
        state = CharacterTitleState(character_id="c1")
        state.set_title_rank("novice_adventurer", 1)
        assert state.get_title_rank("novice_adventurer") == 1
        assert state.has_title("novice_adventurer")
        state.set_title_rank("novice_adventurer", 0)
        assert not state.has_title("novice_adventurer")
        assert "novice_adventurer" not in state.title_ranks

    def test_prestige_points(self):
        state = CharacterTitleState(character_id="c1")
        state.increment_prestige(10)
        assert state.prestige_points == 10
        state.increment_prestige(5)
        assert state.prestige_points == 15

    def test_to_from_dict(self):
        state = CharacterTitleState(
            character_id="c1",
            prestige_points=50,
            title_ranks={"bronze": 1},
            active_honorific="sir",
            stats={"reputation": 120},
        )
        data = state.to_dict()
        restored = CharacterTitleState.from_dict(data)
        assert restored.character_id == "c1"
        assert restored.prestige_points == 50
        assert restored.title_ranks == {"bronze": 1}
        assert restored.active_honorific == "sir"
        assert restored.stats == {"reputation": 120}


# ---------------------------------------------------------------------------
# TitleManager tests
# ---------------------------------------------------------------------------

class TestTitleManager:
    def test_load_titles(self):
        mgr = _title_manager()
        assert "novice_adventurer" in mgr.titles
        assert "bronze" in mgr.prestige_ranks
        assert "sir" in mgr.honorifics

    def test_update_stat_triggers_title_unlock(self):
        mgr = _title_manager()
        mgr.update_stat("hero", "quests_completed", 1)
        state = mgr.get_character_state("hero")
        assert state.has_title("novice_adventurer")

    def test_prestige_unlock(self):
        mgr = _title_manager()
        mgr.add_prestige_points("hero", 10)
        state = mgr.get_character_state("hero")
        assert state.has_title("bronze")
        assert not state.has_title("silver")

        mgr.add_prestige_points("hero", 50)
        assert state.has_title("silver")

    def test_set_active_honorific_success(self):
        mgr = _title_manager()
        mgr.update_stats("hero", {"reputation": 100, "alignment": 5})  # lawful-ish
        result = mgr.set_active_honorific("hero", "sir")
        assert result["success"] is True
        state = mgr.get_character_state("hero")
        assert state.active_honorific == "sir"

    def test_set_active_honorific_failure(self):
        mgr = _title_manager()
        result = mgr.set_active_honorific("hero", "sir")
        assert result["success"] is False

    def test_get_npc_reaction_modifier(self):
        mgr = _title_manager()
        mgr.update_stat("hero", "quests_completed", 1)
        modifier = mgr.get_npc_reaction_modifier("hero")
        assert modifier == 0  # novice gives 0
        mgr.update_stat("hero", "enemies_defeated", 100)
        modifier = mgr.get_npc_reaction_modifier("hero")
        assert modifier == 2  # master combatant gives +2

    def test_format_character_name_honorific(self):
        mgr = _title_manager()
        mgr.update_stats("hero", {"reputation": 100, "alignment": 5})
        mgr.set_active_honorific("hero", "sir")
        formatted = mgr.format_character_name("hero", "Arthur")
        assert formatted == "Sir Arthur"

    def test_format_character_name_prestige(self):
        mgr = _title_manager()
        mgr.add_prestige_points("hero", 50)
        formatted = mgr.format_character_name("hero", "Lancelot")
        assert formatted == "Lancelot, Silver Rank"


# ---------------------------------------------------------------------------
# NPCReactionResolver tests
# ---------------------------------------------------------------------------

class TestNPCReactionResolver:
    def test_resolve_disposition_base(self):
        resolver = _resolver()
        npc = NPCProfile(id="villager", name="Villager", base_disposition=0)
        result = resolver.resolve_disposition("hero", npc)
        assert "disposition" in result
        assert "dialogue_tone" in result

    def test_fear_bonus(self):
        resolver = _resolver()
        mgr = _title_manager()
        mgr.update_stat("villain", "enemies_defeated", 100)
        resolver.title_manager = mgr

        npc = NPCProfile(
            id="guard",
            name="Guard",
            base_disposition=0,
            feared_titles=["master_combatant"],
        )
        result = resolver.resolve_disposition("villain", npc)
        assert result["disposition"] == 4  # +2 from title + 2*1 from feared

    def test_honorific_tone_override(self):
        resolver = _resolver()
        mgr = _title_manager()
        mgr.update_stats("knight", {"reputation": 100, "alignment": 5})
        mgr.set_active_honorific("knight", "sir")
        resolver.title_manager = mgr

        npc = NPCProfile(
            id="noble",
            name="Noble",
            base_disposition=0,
            preferred_honorifics=["sir"],
            dialogue_tone_bias="neutral",
        )
        result = resolver.resolve_disposition("knight", npc)
        assert result["dialogue_tone"] == "respectful"
        assert result["disposition"] == 4  # +2 from honorific effect + 2 from preferred

    def test_skill_check_modifier_social(self):
        resolver = _resolver()
        mgr = _title_manager()
        mgr.update_stat("hero", "quests_completed", 1)
        resolver.title_manager = mgr

        npc = NPCProfile(id="trader", name="Trader")
        mod = resolver.resolve_skill_check_modifier("hero", npc, skill_category="social")
        assert mod == 0  # novice gives 0 overall, 0//2 = 0


# ---------------------------------------------------------------------------
# CharacterSheet tests
# ---------------------------------------------------------------------------

class TestCharacterSheet:
    def test_render_sheet(self):
        sheet = CharacterSheet(
            skill_manager=self.skill_manager(),
            title_manager=_title_manager(),
        )
        result = sheet.render_sheet("hero", "Geralt")
        assert result["character_id"] == "hero"
        assert result["display_name"] == "Geralt"
        assert "skill_summaries" in result
        assert "title_summary" in result

    def test_render_sheet_with_title(self):
        sheet = CharacterSheet(
            skill_manager=self.skill_manager(),
            title_manager=_title_manager(),
        )
        # Unlock a title via the title manager directly
        sheet.title_manager.update_stat("hero", "quests_completed", 1)
        result = sheet.render_sheet("hero", "Geralt")
        assert result["display_name"] == "Geralt the Novice Adventurer"
        assert "Novice Adventurer" in result["formatted_titles"]

    def test_render_sheet_with_honorific(self):
        sheet = CharacterSheet(
            skill_manager=self.skill_manager(),
            title_manager=_title_manager(),
        )
        sheet.title_manager.update_stats("hero", {"reputation": 100, "alignment": 5})
        sheet.title_manager.set_active_honorific("hero", "sir")
        result = sheet.render_sheet("hero", "Arthur")
        assert result["display_name"] == "Sir Arthur"

    def skill_manager(self):
        from skill_tree_manager import SkillTreeManager
        return SkillTreeManager()


if __name__ == "__main__":
    import traceback

    suites = [
        TestTitleDefinition,
        TestCharacterTitleState,
        TestTitleManager,
        TestNPCReactionResolver,
        TestCharacterSheet,
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
