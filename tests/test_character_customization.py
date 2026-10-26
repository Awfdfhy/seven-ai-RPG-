"""
RPG-10-04: Character Customization System Tests
Run with: python -m pytest tests/test_character_customization.py -v
or:       python tests/test_character_customization.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from character_customization import (
    AppearanceOption,
    BackgroundDefinition,
    CharacterAppearance,
    CharacterCustomizationManager,
    CharacterCustomizationState,
    ClassDefinition,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _manager() -> CharacterCustomizationManager:
    mgr = CharacterCustomizationManager(
        data_directory=os.path.join(os.path.dirname(__file__), "..", "data")
    )
    return mgr


# ---------------------------------------------------------------------------
# Data definition tests
# ---------------------------------------------------------------------------

class TestClassDefinition:
    def test_to_from_dict_roundtrip(self):
        data = {
            "id": "warrior",
            "name": "Warrior",
            "description": "A melee fighter.",
            "base_stats": {"strength": 15, "vitality": 14},
            "skill_tree_ids": ["two_handed_combat"],
            "ability_ids": [],
            "starting_equipment": ["iron_sword"],
            "stat_bonuses": {"strength": 3},
        }
        cls = ClassDefinition.from_dict(data)
        assert cls.id == "warrior"
        assert cls.base_stats["strength"] == 15
        assert cls.stat_bonuses["strength"] == 3
        assert cls.to_dict()["skill_tree_ids"] == ["two_handed_combat"]

    def test_defaults(self):
        cls = ClassDefinition(id="test", name="Test")
        assert cls.description == ""
        assert cls.base_stats == {}
        assert cls.skill_tree_ids == []
        assert cls.ability_ids == []
        assert cls.starting_equipment == []
        assert cls.stat_bonuses == {}


class TestBackgroundDefinition:
    def test_to_from_dict_roundtrip(self):
        data = {
            "id": "noble",
            "name": "Noble",
            "description": "Born to wealth.",
            "stat_bonuses": {"charisma": 2, "intelligence": 1},
            "skill_bonuses": ["diplomacy"],
            "starting_item_ids": ["signet_ring"],
            "dialogue_tags": ["noble"],
        }
        bg = BackgroundDefinition.from_dict(data)
        assert bg.id == "noble"
        assert bg.stat_bonuses["charisma"] == 2
        assert bg.skill_bonuses == ["diplomacy"]
        assert bg.to_dict()["dialogue_tags"] == ["noble"]


class TestAppearanceOption:
    def test_from_dict(self):
        data = {"id": "black", "name": "Black", "category": "hair_colors", "hex": "#1a1a1a"}
        opt = AppearanceOption.from_dict(data)
        assert opt.id == "black"
        assert opt.category == "hair_colors"
        assert opt.hex == "#1a1a1a"
        assert opt.to_dict()["name"] == "Black"


# ---------------------------------------------------------------------------
# State tests
# ---------------------------------------------------------------------------

class TestCharacterAppearance:
    def test_defaults(self):
        app = CharacterAppearance()
        assert app.body_type == "average"
        assert app.hair_style == "short"
        assert app.hair_color == "brown"
        assert app.height_cm == 170

    def test_roundtrip(self):
        app = CharacterAppearance(
            body_type="muscular",
            hair_style="ponytail",
            hair_color="red",
            skin_tone="tan",
            eye_color="amber",
            voice="deep",
            height_cm=185,
            additional_notes="scar on cheek",
        )
        restored = CharacterAppearance.from_dict(app.to_dict())
        assert restored.body_type == "muscular"
        assert restored.hair_color == "red"
        assert restored.eye_color == "amber"
        assert restored.height_cm == 185
        assert restored.additional_notes == "scar on cheek"


class TestCharacterCustomizationState:
    def test_defaults(self):
        state = CharacterCustomizationState(character_id="c1")
        assert state.class_id == ""
        assert state.background_id == ""
        assert state.is_customized is False
        assert state.stats == {}

    def test_roundtrip(self):
        state = CharacterCustomizationState(
            character_id="c1",
            name="Aldric",
            class_id="warrior",
            background_id="soldier",
            appearance=CharacterAppearance(body_type="muscular", hair_color="black"),
            stats={"strength": 16, "vitality": 15},
            unspent_customization_points=2,
            is_customized=True,
        )
        restored = CharacterCustomizationState.from_dict(state.to_dict())
        assert restored.name == "Aldric"
        assert restored.class_id == "warrior"
        assert restored.background_id == "soldier"
        assert restored.appearance.body_type == "muscular"
        assert restored.stats["strength"] == 16
        assert restored.unspent_customization_points == 2
        assert restored.is_customized is True


# ---------------------------------------------------------------------------
# Manager tests
# ---------------------------------------------------------------------------

class TestCharacterCustomizationManager:
    def test_loads_classes(self):
        mgr = _manager()
        assert len(mgr.classes) > 0
        assert "warrior" in mgr.classes
        assert "mage" in mgr.classes

    def test_loads_backgrounds(self):
        mgr = _manager()
        assert len(mgr.backgrounds) > 0
        assert "noble" in mgr.backgrounds
        assert "soldier" in mgr.backgrounds

    def test_loads_appearance_options(self):
        mgr = _manager()
        assert "hair_styles" in mgr.appearance_options
        assert "hair_colors" in mgr.appearance_options
        assert "skin_tones" in mgr.appearance_options
        assert len(mgr.appearance_options["hair_styles"]) > 0

    def test_get_state_creates_default(self):
        mgr = _manager()
        state = mgr.get_state("new_char")
        assert state.character_id == "new_char"
        assert state.class_id == ""
        assert state.is_customized is False

    def test_select_class(self):
        mgr = _manager()
        result = mgr.select_class("c1", "warrior")
        assert result["success"] is True
        assert result["class_id"] == "warrior"
        assert result["stats"]["strength"] == 18  # 15 base + 3 bonus

        state = mgr.get_state("c1")
        assert state.class_id == "warrior"
        assert state.stats["strength"] == 18

    def test_select_class_invalid(self):
        mgr = _manager()
        result = mgr.select_class("c1", "nonexistent")
        assert result["success"] is False
        assert "not found" in result["reason"]

    def test_select_background(self):
        mgr = _manager()
        mgr.select_class("c1", "warrior")
        result = mgr.select_background("c1", "noble")
        assert result["success"] is True
        assert result["background_id"] == "noble"
        assert result["stats"]["charisma"] == 8  # 6 base + 2 noble bonus

    def test_select_background_invalid(self):
        mgr = _manager()
        result = mgr.select_background("c1", "nonexistent")
        assert result["success"] is False
        assert "not found" in result["reason"]

    def test_background_bonuses_stacked(self):
        mgr = _manager()
        mgr.select_class("c1", "mage")
        mgr.select_background("c1", "scholar")
        state = mgr.get_state("c1")
        assert state.stats["intelligence"] == 21  # 16 base + 3 class bonus + 2 scholar bonus

    def test_set_appearance(self):
        mgr = _manager()
        result = mgr.set_appearance("c1", hair_color="red", skin_tone="dark", height_cm=180)
        assert result["success"] is True
        state = mgr.get_state("c1")
        assert state.appearance.hair_color == "red"
        assert state.appearance.skin_tone == "dark"
        assert state.appearance.height_cm == 180

    def test_set_appearance_invalid_field(self):
        mgr = _manager()
        result = mgr.set_appearance("c1", invalid_field="test")
        assert result["success"] is False
        assert "Unknown appearance field" in result["reason"]

    def test_set_stats(self):
        mgr = _manager()
        mgr.select_class("c1", "warrior")
        result = mgr.set_stats("c1", {"luck": 10})
        assert result["success"] is True
        assert result["stats"]["luck"] == 10

    def test_set_stats_invalid(self):
        mgr = _manager()
        result = mgr.set_stats("c1", {"invalid_stat": 5})
        assert result["success"] is False
        assert "Invalid stat" in result["reason"]

    def test_allocate_customization_point(self):
        mgr = _manager()
        state = mgr.get_state("c1")
        state.unspent_customization_points = 1
        ok, reason = mgr.allocate_customization_point("c1", "strength")
        assert ok is True
        assert state.stats["strength"] == 1
        assert state.unspent_customization_points == 0

    def test_allocate_customization_point_no_points(self):
        mgr = _manager()
        ok, reason = mgr.allocate_customization_point("c1", "strength")
        assert ok is False
        assert "No unspent customization points" in reason

    def test_allocate_customization_point_invalid_stat(self):
        mgr = _manager()
        state = mgr.get_state("c1")
        state.unspent_customization_points = 1
        ok, reason = mgr.allocate_customization_point("c1", "invalid_stat")
        assert ok is False
        assert "Invalid stat" in reason

    def test_mark_customized_success(self):
        mgr = _manager()
        mgr.select_class("c1", "warrior")
        mgr.select_background("c1", "soldier")
        result = mgr.mark_customized("c1")
        assert result["success"] is True
        state = mgr.get_state("c1")
        assert state.is_customized is True

    def test_mark_customized_missing_class(self):
        mgr = _manager()
        result = mgr.mark_customized("c1")
        assert result["success"] is False
        assert "class" in result["reason"]

    def test_mark_customized_missing_background(self):
        mgr = _manager()
        mgr.select_class("c1", "warrior")
        result = mgr.mark_customized("c1")
        assert result["success"] is False
        assert "background" in result["reason"]

    def test_reset_customization(self):
        mgr = _manager()
        mgr.select_class("c1", "warrior")
        mgr.select_background("c1", "soldier")
        mgr.set_appearance("c1", hair_color="black")
        mgr.mark_customized("c1")
        result = mgr.reset_customization("c1")
        assert result["success"] is True
        state = mgr.get_state("c1")
        assert state.class_id == ""
        assert state.background_id == ""
        assert state.appearance.hair_color == "brown"  # default
        assert state.is_customized is False

    def test_get_character_summary(self):
        mgr = _manager()
        mgr.select_class("c1", "mage")
        mgr.select_background("c1", "scholar")
        mgr.set_appearance("c1", hair_color="white")
        mgr.mark_customized("c1")
        summary = mgr.get_character_summary("c1")
        assert summary["is_customized"] is True
        assert summary["class"]["id"] == "mage"
        assert summary["background"]["id"] == "scholar"
        assert summary["appearance"]["hair_color"] == "white"
        assert "fire_magic" in summary["skill_tree_ids"]
        assert "fire.fireball" in summary["ability_ids"]

    def test_apply_to_progression_manager(self):
        mgr = _manager()
        mgr.select_class("c1", "warrior")
        mgr.select_background("c1", "soldier")
        mgr.mark_customized("c1")

        class FakeProgressionManager:
            def __init__(self):
                self.level = None
                self.attrs = {}

            def set_level(self, cid, level):
                self.level = level

            def set_attributes(self, cid, attrs):
                self.attrs = attrs

        fake_pm = FakeProgressionManager()
        result = mgr.apply_to_progression_manager("c1", fake_pm)
        assert result["success"] is True
        assert fake_pm.level == 1
        assert fake_pm.attrs["strength"] >= 15

    def test_apply_to_progression_manager_not_customized(self):
        mgr = _manager()

        class FakePM:
            def set_level(self, cid, level):
                pass

            def set_attributes(self, cid, attrs):
                pass

        result = mgr.apply_to_progression_manager("c1", FakePM())
        assert result["success"] is False
        assert "not been customized" in result["reason"]

    def test_list_classes(self):
        mgr = _manager()
        classes = mgr.list_classes()
        assert len(classes) >= 4
        ids = [c["id"] for c in classes]
        assert "warrior" in ids
        assert "mage" in ids
        assert "rogue" in ids
        assert "cleric" in ids

    def test_list_backgrounds(self):
        mgr = _manager()
        bgs = mgr.list_backgrounds()
        assert len(bgs) >= 4
        ids = [b["id"] for b in bgs]
        assert "noble" in ids
        assert "soldier" in ids
        assert "outlaw" in ids
        assert "scholar" in ids

    def test_get_appearance_options(self):
        mgr = _manager()
        hair_styles = mgr.get_appearance_options("hair_styles")
        assert len(hair_styles) >= 6
        assert hair_styles[0]["category"] == "hair_styles"

    def test_serialization_roundtrip(self):
        mgr = _manager()
        mgr.select_class("c1", "rogue")
        mgr.select_background("c1", "outlaw")
        mgr.set_appearance("c1", hair_color="black", eye_color="amber")
        mgr.get_state("c1").unspent_customization_points = 3
        mgr.mark_customized("c1")

        data = mgr.to_dict()
        restored = CharacterCustomizationManager.from_dict(data)
        assert restored.get_state("c1").class_id == "rogue"
        assert restored.get_state("c1").background_id == "outlaw"
        assert restored.get_state("c1").appearance.hair_color == "black"
        assert restored.get_state("c1").appearance.eye_color == "amber"
        assert restored.get_state("c1").unspent_customization_points == 3


if __name__ == "__main__":
    suites = [
        TestClassDefinition,
        TestBackgroundDefinition,
        TestAppearanceOption,
        TestCharacterAppearance,
        TestCharacterCustomizationState,
        TestCharacterCustomizationManager,
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
