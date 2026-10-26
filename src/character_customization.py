"""
RPG-10-04: Character Customization System

Manages character appearance, base stats, background selection, and class choice.
Integrates with ProgressionManager and SkillTreeManager.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Enumerations and definitions
# ---------------------------------------------------------------------------

# Stat names are fixed by the progression system; we import from there.
_BASE_STATS = ("strength", "dexterity", "intelligence", "vitality", "charisma", "luck")


# ---------------------------------------------------------------------------
# Data definitions (loaded from character_customization.json)
# ---------------------------------------------------------------------------

@dataclass
class ClassDefinition:
    """A playable class with base stats, skill tree access, and starting gear."""

    id: str
    name: str
    description: str = ""
    base_stats: dict[str, int] = field(default_factory=dict)
    skill_tree_ids: list[str] = field(default_factory=list)
    ability_ids: list[str] = field(default_factory=list)
    starting_equipment: list[str] = field(default_factory=list)
    stat_bonuses: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "base_stats": dict(self.base_stats),
            "skill_tree_ids": list(self.skill_tree_ids),
            "ability_ids": list(self.ability_ids),
            "starting_equipment": list(self.starting_equipment),
            "stat_bonuses": dict(self.stat_bonuses),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ClassDefinition:
        return ClassDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            base_stats=data.get("base_stats", {}),
            skill_tree_ids=data.get("skill_tree_ids", []),
            ability_ids=data.get("ability_ids", []),
            starting_equipment=data.get("starting_equipment", []),
            stat_bonuses=data.get("stat_bonuses", {}),
        )


@dataclass
class BackgroundDefinition:
    """A character background providing lore, bonuses, and flavor items."""

    id: str
    name: str
    description: str = ""
    stat_bonuses: dict[str, int] = field(default_factory=dict)
    skill_bonuses: list[str] = field(default_factory=list)
    starting_item_ids: list[str] = field(default_factory=list)
    dialogue_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "stat_bonuses": dict(self.stat_bonuses),
            "skill_bonuses": list(self.skill_bonuses),
            "starting_item_ids": list(self.starting_item_ids),
            "dialogue_tags": list(self.dialogue_tags),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> BackgroundDefinition:
        return BackgroundDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            stat_bonuses=data.get("stat_bonuses", {}),
            skill_bonuses=data.get("skill_bonuses", []),
            starting_item_ids=data.get("starting_item_ids", []),
            dialogue_tags=data.get("dialogue_tags", []),
        )


@dataclass
class AppearanceOption:
    """A single appearance variant within a category."""

    id: str
    name: str
    category: str
    description: str = ""
    hex: str = ""
    pitch: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = {"id": self.id, "name": self.name, "category": self.category}
        if self.description:
            data["description"] = self.description
        if self.hex:
            data["hex"] = self.hex
        if self.pitch:
            data["pitch"] = self.pitch
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AppearanceOption:
        return AppearanceOption(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            description=data.get("description", ""),
            hex=data.get("hex", ""),
            pitch=data.get("pitch", ""),
        )


# ---------------------------------------------------------------------------
# Character customization state
# ---------------------------------------------------------------------------

@dataclass
class CharacterAppearance:
    """Describes how a character looks."""

    body_type: str = "average"
    hair_style: str = "short"
    hair_color: str = "brown"
    skin_tone: str = "medium"
    eye_color: str = "brown"
    voice: str = "neutral"
    height_cm: int = 170
    additional_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "body_type": self.body_type,
            "hair_style": self.hair_style,
            "hair_color": self.hair_color,
            "skin_tone": self.skin_tone,
            "eye_color": self.eye_color,
            "voice": self.voice,
            "height_cm": self.height_cm,
            "additional_notes": self.additional_notes,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CharacterAppearance:
        return CharacterAppearance(
            body_type=data.get("body_type", "average"),
            hair_style=data.get("hair_style", "short"),
            hair_color=data.get("hair_color", "brown"),
            skin_tone=data.get("skin_tone", "medium"),
            eye_color=data.get("eye_color", "brown"),
            voice=data.get("voice", "neutral"),
            height_cm=data.get("height_cm", 170),
            additional_notes=data.get("additional_notes", ""),
        )


@dataclass
class CharacterCustomizationState:
    """
    Full customization record for a character.

    Holds the selected class, background, appearance, and point-spent
    stats. Stat overrides are applied on top of class/base stats.
    """

    character_id: str
    name: str = ""
    class_id: str = ""
    background_id: str = ""
    appearance: CharacterAppearance = field(default_factory=CharacterAppearance)
    stats: dict[str, int] = field(default_factory=dict)
    unspent_customization_points: int = 0
    is_customized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "name": self.name,
            "class_id": self.class_id,
            "background_id": self.background_id,
            "appearance": self.appearance.to_dict(),
            "stats": dict(self.stats),
            "unspent_customization_points": self.unspent_customization_points,
            "is_customized": self.is_customized,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CharacterCustomizationState:
        return CharacterCustomizationState(
            character_id=data["character_id"],
            name=data.get("name", ""),
            class_id=data.get("class_id", ""),
            background_id=data.get("background_id", ""),
            appearance=CharacterAppearance.from_dict(data.get("appearance", {})),
            stats=data.get("stats", {}),
            unspent_customization_points=data.get("unspent_customization_points", 0),
            is_customized=data.get("is_customized", False),
        )


# ---------------------------------------------------------------------------
# Character Customization Manager
# ---------------------------------------------------------------------------

class CharacterCustomizationManager:
    """
    Loads class, background, and appearance definitions and manages
    per-character customization state.
    """

    def __init__(self, data_directory: str | None = None) -> None:
        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_directory = data_directory
        self.classes: dict[str, ClassDefinition] = {}
        self.backgrounds: dict[str, BackgroundDefinition] = {}
        self.appearance_options: dict[str, list[AppearanceOption]] = {}
        self.character_states: dict[str, CharacterCustomizationState] = {}

        self._load_data()

    # --- Data loading -------------------------------------------------------

    def _load_data(self) -> None:
        path = os.path.join(self.data_directory, "character_customization.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        for entry in data.get("classes", []):
            cls = ClassDefinition.from_dict(entry)
            self.classes[cls.id] = cls

        for entry in data.get("backgrounds", []):
            bg = BackgroundDefinition.from_dict(entry)
            self.backgrounds[bg.id] = bg

        opts_raw = data.get("appearance_options", {})
        for category, entries in opts_raw.items():
            opts: list[AppearanceOption] = []
            for entry in entries:
                entry["category"] = category
                opts.append(AppearanceOption.from_dict(entry))
            self.appearance_options[category] = opts

    # --- State management ---------------------------------------------------

    def get_state(self, character_id: str) -> CharacterCustomizationState:
        if character_id not in self.character_states:
            self.character_states[character_id] = CharacterCustomizationState(
                character_id=character_id
            )
        return self.character_states[character_id]

    # --- Class selection ----------------------------------------------------

    def get_class(self, class_id: str) -> ClassDefinition | None:
        return self.classes.get(class_id)

    def list_classes(self) -> list[dict[str, Any]]:
        return [cls.to_dict() for cls in self.classes.values()]

    def select_class(
        self, character_id: str, class_id: str
    ) -> dict[str, Any]:
        """
        Apply a class to a character, setting base stats and class bonuses.
        """
        cls = self.get_class(class_id)
        if cls is None:
            return {"success": False, "reason": f"Class '{class_id}' not found."}

        state = self.get_state(character_id)
        state.class_id = class_id

        # Start with class base stats, then apply class bonuses
        combined: dict[str, int] = {}
        for stat, val in cls.base_stats.items():
            combined[stat] = val
        for stat, bonus in cls.stat_bonuses.items():
            combined[stat] = combined.get(stat, 0) + bonus

        state.stats = combined
        state.is_customized = state.is_customized and bool(state.background_id)

        return {
            "success": True,
            "class_id": class_id,
            "stats": dict(state.stats),
        }

    # --- Background selection -----------------------------------------------

    def get_background(self, background_id: str) -> BackgroundDefinition | None:
        return self.backgrounds.get(background_id)

    def list_backgrounds(self) -> list[dict[str, Any]]:
        return [bg.to_dict() for bg in self.backgrounds.values()]

    def select_background(
        self, character_id: str, background_id: str
    ) -> dict[str, Any]:
        """
        Apply a background to a character, stacking bonuses on top of class stats.
        """
        bg = self.get_background(background_id)
        if bg is None:
            return {"success": False, "reason": f"Background '{background_id}' not found."}

        state = self.get_state(character_id)
        state.background_id = background_id

        for stat, bonus in bg.stat_bonuses.items():
            state.stats[stat] = state.stats.get(stat, 0) + bonus

        state.is_customized = state.is_customized and bool(state.class_id)

        return {
            "success": True,
            "background_id": background_id,
            "stats": dict(state.stats),
        }

    # --- Appearance ---------------------------------------------------------

    def get_appearance_options(self, category: str) -> list[dict[str, Any]]:
        opts = self.appearance_options.get(category, [])
        return [o.to_dict() for o in opts]

    def set_appearance(
        self, character_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Update one or more appearance fields. Valid fields are those
        on CharacterAppearance plus 'height_cm'.
        """
        state = self.get_state(character_id)
        allowed = {
            "body_type",
            "hair_style",
            "hair_color",
            "skin_tone",
            "eye_color",
            "voice",
            "height_cm",
            "additional_notes",
        }
        for key, value in kwargs.items():
            if key not in allowed:
                return {"success": False, "reason": f"Unknown appearance field '{key}'."}
            setattr(state.appearance, key, value)

        return {"success": True, "appearance": state.appearance.to_dict()}

    # --- Stat customization ------------------------------------------------

    def set_stats(
        self, character_id: str, stats: dict[str, int]
    ) -> dict[str, Any]:
        """
        Directly replace the character's stat dict after class + background.
        """
        for stat in stats:
            if stat not in _BASE_STATS:
                return {
                    "success": False,
                    "reason": f"Invalid stat '{stat}'. Valid stats: {', '.join(_BASE_STATS)}",
                }

        state = self.get_state(character_id)
        state.stats.update(stats)
        return {"success": True, "stats": dict(state.stats)}

    def allocate_customization_point(
        self, character_id: str, attribute: str
    ) -> tuple[bool, str]:
        """
        Spend one customization point to increase an attribute.
        """
        if attribute not in _BASE_STATS:
            return False, f"Invalid stat '{attribute}'."
        state = self.get_state(character_id)
        if state.unspent_customization_points <= 0:
            return False, "No unspent customization points."
        state.unspent_customization_points -= 1
        state.stats[attribute] = state.stats.get(attribute, 0) + 1
        return True, ""

    # --- Full customization flow -------------------------------------------

    def mark_customized(self, character_id: str) -> dict[str, Any]:
        """
        Mark a character as fully customized once all choices are made.
        """
        state = self.get_state(character_id)
        missing: list[str] = []
        if not state.class_id:
            missing.append("class")
        if not state.background_id:
            missing.append("background")
        if missing:
            return {
                "success": False,
                "reason": f"Missing customization: {', '.join(missing)}",
            }
        state.is_customized = True
        return {"success": True, "state": state.to_dict()}

    def reset_customization(self, character_id: str) -> dict[str, Any]:
        """
        Clear all customization choices for a character.
        """
        state = self.get_state(character_id)
        state.class_id = ""
        state.background_id = ""
        state.appearance = CharacterAppearance()
        state.stats = {}
        state.unspent_customization_points = 0
        state.is_customized = False
        return {"success": True, "state": state.to_dict()}

    # --- Integration helpers -----------------------------------------------

    def get_character_summary(self, character_id: str) -> dict[str, Any]:
        """
        Return a full customization summary including class, background,
        appearance, stats, and starting gear.
        """
        state = self.get_state(character_id)
        cls = self.get_class(state.class_id) if state.class_id else None
        bg = self.get_background(state.background_id) if state.background_id else None

        return {
            "character_id": character_id,
            "name": state.name,
            "is_customized": state.is_customized,
            "class": cls.to_dict() if cls else None,
            "background": bg.to_dict() if bg else None,
            "appearance": state.appearance.to_dict(),
            "stats": dict(state.stats),
            "unspent_customization_points": state.unspent_customization_points,
            "starting_equipment": cls.starting_equipment if cls else [],
            "skill_tree_ids": cls.skill_tree_ids if cls else [],
            "ability_ids": cls.ability_ids if cls else [],
        }

    def apply_to_progression_manager(
        self, character_id: str, progression_manager: Any
    ) -> dict[str, Any]:
        """
        Sync the customization stats into the progression manager.
        """
        if not progression_manager:
            return {"success": False, "reason": "Progression manager is required."}

        state = self.get_state(character_id)
        if not state.is_customized:
            return {"success": False, "reason": "Character has not been customized yet."}

        # Apply starting level bonus if any; here we simply hand over stats.
        # The progression manager tracks level/XP separately.
        progression_manager.set_level(character_id, 1)
        progression_manager.set_attributes(character_id, dict(state.stats))

        return {
            "success": True,
            "character_id": character_id,
            "stats_applied": dict(state.stats),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "classes": [c.to_dict() for c in self.classes.values()],
            "backgrounds": [b.to_dict() for b in self.backgrounds.values()],
            "appearance_options": {
                cat: [o.to_dict() for o in opts]
                for cat, opts in self.appearance_options.items()
            },
            "character_states": {
                cid: s.to_dict() for cid, s in self.character_states.items()
            },
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CharacterCustomizationManager:
        mgr = CharacterCustomizationManager.__new__(CharacterCustomizationManager)
        mgr.data_directory = ""
        mgr.classes = {}
        mgr.backgrounds = {}
        mgr.appearance_options = {}
        mgr.character_states = {}

        for entry in data.get("classes", []):
            cls = ClassDefinition.from_dict(entry)
            mgr.classes[cls.id] = cls

        for entry in data.get("backgrounds", []):
            bg = BackgroundDefinition.from_dict(entry)
            mgr.backgrounds[bg.id] = bg

        raw_opts = data.get("appearance_options", {})
        for cat, entries in raw_opts.items():
            mgr.appearance_options[cat] = [
                AppearanceOption.from_dict(e) for e in entries
            ]

        for cid, entry in data.get("character_states", {}).items():
            mgr.character_states[cid] = CharacterCustomizationState.from_dict(entry)

        return mgr
