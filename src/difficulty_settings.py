"""
RPG-10-10: Difficulty and Accessibility Settings
Core data models for difficulty presets, per-session customization,
and accessibility options. Integrates with combat, progression,
loot, and status systems via multipliers and modifiers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Enums and presets
# ---------------------------------------------------------------------------

class DifficultyPreset:
    """Named difficulty presets with canonical multiplier values."""

    NARRATIVE = "narrative"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    NIGHTMARE = "nightmare"

    PRESETS: dict[str, dict[str, Any]] = {
        NARRATIVE: {
            "display_name": "Narrative",
            "description": "Focus on story; minimal challenge.",
            "dc_modifier": -5,
            "damage_dealt_multiplier": 1.5,
            "damage_taken_multiplier": 0.5,
            "xp_multiplier": 1.0,
            "loot_rarity_boost": 0.15,
            "status_duration_multiplier": 0.5,
            "healing_effectiveness_multiplier": 2.0,
        },
        EASY: {
            "display_name": "Easy",
            "description": "Relaxed combat; mistakes are forgiving.",
            "dc_modifier": -2,
            "damage_dealt_multiplier": 1.2,
            "damage_taken_multiplier": 0.7,
            "xp_multiplier": 1.0,
            "loot_rarity_boost": 0.0,
            "status_duration_multiplier": 0.7,
            "healing_effectiveness_multiplier": 1.5,
        },
        NORMAL: {
            "display_name": "Normal",
            "description": "Balanced experience for standard play.",
            "dc_modifier": 0,
            "damage_dealt_multiplier": 1.0,
            "damage_taken_multiplier": 1.0,
            "xp_multiplier": 1.0,
            "loot_rarity_boost": 0.0,
            "status_duration_multiplier": 1.0,
            "healing_effectiveness_multiplier": 1.0,
        },
        HARD: {
            "display_name": "Hard",
            "description": "Tough fights; careful planning required.",
            "dc_modifier": 3,
            "damage_dealt_multiplier": 0.85,
            "damage_taken_multiplier": 1.4,
            "xp_multiplier": 1.2,
            "loot_rarity_boost": 0.0,
            "status_duration_multiplier": 1.3,
            "healing_effectiveness_multiplier": 0.8,
        },
        NIGHTMARE: {
            "display_name": "Nightmare",
            "description": "Brutal; every fight is a life-or-death struggle.",
            "dc_modifier": 6,
            "damage_dealt_multiplier": 0.6,
            "damage_taken_multiplier": 2.0,
            "xp_multiplier": 1.5,
            "loot_rarity_boost": -0.1,
            "status_duration_multiplier": 1.6,
            "healing_effectiveness_multiplier": 0.5,
        },
    }

    @classmethod
    def preset(cls, name: str) -> dict[str, Any]:
        return cls.PRESETS.get(name, cls.PRESETS[cls.NORMAL])

    @classmethod
    def available_presets(cls) -> list[str]:
        return list(cls.PRESETS.keys())


class AccessibilityOption:
    """Named accessibility toggles and their defaults."""

    HIGH_CONTRAST_MODE = "high_contrast_mode"
    SIMPLIFIED_COMBAT = "simplified_combat"
    AUTO_ADVANCE_DIALOGUE = "auto_advance_dialogue"
    TEXT_SIZE = "text_size"
    SCREEN_READER_MODE = "screen_reader_mode"
    REDUCE_FLASHES = "reduce_flashes"
    COLORBLIND_SUPPORT = "colorblind_support"

    DEFAULTS: dict[str, Any] = {
        HIGH_CONTRAST_MODE: False,
        SIMPLIFIED_COMBAT: False,
        AUTO_ADVANCE_DIALOGUE: False,
        TEXT_SIZE: "normal",
        SCREEN_READER_MODE: False,
        REDUCE_FLASHES: False,
        COLORBLIND_SUPPORT: "none",
    }

    TEXT_SIZE_OPTIONS = ["normal", "large", "extra_large"]
    COLORBLIND_OPTIONS = ["none", "protanopia", "deuteranopia", "tritanopia"]


# ---------------------------------------------------------------------------
# Settings dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DifficultySettings:
    """
    Tunable difficulty multipliers and modifiers.
    All numeric fields are clamped to safe ranges on assignment.
    """

    preset: str = DifficultyPreset.NORMAL
    dc_modifier: int = 0
    damage_dealt_multiplier: float = 1.0
    damage_taken_multiplier: float = 1.0
    xp_multiplier: float = 1.0
    loot_rarity_boost: float = 0.0
    status_duration_multiplier: float = 1.0
    healing_effectiveness_multiplier: float = 1.0

    def __post_init__(self) -> None:
        self._clamp()

    def _clamp(self) -> None:
        self.dc_modifier = max(-10, min(10, self.dc_modifier))
        self.damage_dealt_multiplier = max(0.1, min(3.0, self.damage_dealt_multiplier))
        self.damage_taken_multiplier = max(0.1, min(3.0, self.damage_taken_multiplier))
        self.xp_multiplier = max(0.1, min(5.0, self.xp_multiplier))
        self.loot_rarity_boost = max(-0.5, min(0.5, self.loot_rarity_boost))
        self.status_duration_multiplier = max(0.1, min(3.0, self.status_duration_multiplier))
        self.healing_effectiveness_multiplier = max(0.1, min(3.0, self.healing_effectiveness_multiplier))

    @classmethod
    def from_preset(cls, preset: str) -> DifficultySettings:
        p = DifficultyPreset.preset(preset)
        return cls(
            preset=preset,
            dc_modifier=int(p["dc_modifier"]),
            damage_dealt_multiplier=float(p["damage_dealt_multiplier"]),
            damage_taken_multiplier=float(p["damage_taken_multiplier"]),
            xp_multiplier=float(p["xp_multiplier"]),
            loot_rarity_boost=float(p["loot_rarity_boost"]),
            status_duration_multiplier=float(p["status_duration_multiplier"]),
            healing_effectiveness_multiplier=float(p["healing_effectiveness_multiplier"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset": self.preset,
            "dc_modifier": self.dc_modifier,
            "damage_dealt_multiplier": self.damage_dealt_multiplier,
            "damage_taken_multiplier": self.damage_taken_multiplier,
            "xp_multiplier": self.xp_multiplier,
            "loot_rarity_boost": self.loot_rarity_boost,
            "status_duration_multiplier": self.status_duration_multiplier,
            "healing_effectiveness_multiplier": self.healing_effectiveness_multiplier,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DifficultySettings:
        return DifficultySettings(
            preset=data.get("preset", DifficultyPreset.NORMAL),
            dc_modifier=int(data.get("dc_modifier", 0)),
            damage_dealt_multiplier=float(data.get("damage_dealt_multiplier", 1.0)),
            damage_taken_multiplier=float(data.get("damage_taken_multiplier", 1.0)),
            xp_multiplier=float(data.get("xp_multiplier", 1.0)),
            loot_rarity_boost=float(data.get("loot_rarity_boost", 0.0)),
            status_duration_multiplier=float(data.get("status_duration_multiplier", 1.0)),
            healing_effectiveness_multiplier=float(data.get("healing_effectiveness_multiplier", 1.0)),
        )


@dataclass
class AccessibilitySettings:
    """
    Accessibility options that affect UI and control behavior.
    """

    high_contrast_mode: bool = False
    simplified_combat: bool = False
    auto_advance_dialogue: bool = False
    text_size: str = AccessibilityOption.DEFAULTS[AccessibilityOption.TEXT_SIZE]
    screen_reader_mode: bool = False
    reduce_flashes: bool = False
    colorblind_support: str = AccessibilityOption.DEFAULTS[AccessibilityOption.COLORBLIND_SUPPORT]

    def __post_init__(self) -> None:
        if self.text_size not in AccessibilityOption.TEXT_SIZE_OPTIONS:
            self.text_size = AccessibilityOption.DEFAULTS[AccessibilityOption.TEXT_SIZE]
        if self.colorblind_support not in AccessibilityOption.COLORBLIND_OPTIONS:
            self.colorblind_support = AccessibilityOption.DEFAULTS[AccessibilityOption.COLORBLIND_SUPPORT]

    def to_dict(self) -> dict[str, Any]:
        return {
            "high_contrast_mode": self.high_contrast_mode,
            "simplified_combat": self.simplified_combat,
            "auto_advance_dialogue": self.auto_advance_dialogue,
            "text_size": self.text_size,
            "screen_reader_mode": self.screen_reader_mode,
            "reduce_flashes": self.reduce_flashes,
            "colorblind_support": self.colorblind_support,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AccessibilitySettings:
        return AccessibilitySettings(
            high_contrast_mode=bool(data.get("high_contrast_mode", False)),
            simplified_combat=bool(data.get("simplified_combat", False)),
            auto_advance_dialogue=bool(data.get("auto_advance_dialogue", False)),
            text_size=str(data.get("text_size", AccessibilityOption.DEFAULTS[AccessibilityOption.TEXT_SIZE])),
            screen_reader_mode=bool(data.get("screen_reader_mode", False)),
            reduce_flashes=bool(data.get("reduce_flashes", False)),
            colorblind_support=str(data.get("colorblind_support", AccessibilityOption.DEFAULTS[AccessibilityOption.COLORBLIND_SUPPORT])),
        )


# ---------------------------------------------------------------------------
# Game-session settings container
# ---------------------------------------------------------------------------

@dataclass
class GameSettings:
    """
    Top-level settings object carried by a play session.
    Bundles difficulty and accessibility under one serializable object.
    """

    difficulty: DifficultySettings = field(default_factory=DifficultySettings)
    accessibility: AccessibilitySettings = field(default_factory=AccessibilitySettings)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "difficulty": self.difficulty.to_dict(),
            "accessibility": self.accessibility.to_dict(),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> GameSettings:
        difficulty = DifficultySettings.from_dict(data.get("difficulty", {}))
        accessibility = AccessibilitySettings.from_dict(data.get("accessibility", {}))
        return GameSettings(
            difficulty=difficulty,
            accessibility=accessibility,
            metadata=dict(data.get("metadata", {})),
        )
