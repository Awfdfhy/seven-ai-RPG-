"""
RPG-XX: Title System
Core data model for character titles, prestige ranks, and honorifics.
Titles appear on the character sheet and modify NPC reactions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TitleType(Enum):
    TITLE = "title"
    PRESTIGE = "prestige"
    HONORIFIC = "honorific"


@dataclass
class TitleDefinition:
    """
    One definition of a title, prestige rank, or honorific.

    Attributes:
        id            : unique identifier (e.g. "novice_adventurer")
        name          : human-readable display name
        description   : flavor / mechanical text
        title_type    : kind of title (title | prestige | honorific)
        requirements  : dict of stat/value gates (e.g. {"quests_completed": 1})
        effects       : opaque effect dict (npc_reaction_modifier, etc.)
        display_format: template string for rendering the title on a character sheet.
                        Placeholders: {name}, {title}, {rank}
    """

    id: str
    name: str
    description: str = ""
    title_type: TitleType = TitleType.TITLE
    requirements: dict[str, Any] = field(default_factory=dict)
    effects: dict[str, Any] = field(default_factory=dict)
    display_format: str = "{name} the {title}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "title_type": self.title_type.value,
            "requirements": dict(self.requirements),
            "effects": dict(self.effects),
            "display_format": self.display_format,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TitleDefinition:
        return TitleDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            title_type=TitleType(data.get("title_type", "title")),
            requirements=data.get("requirements", {}),
            effects=data.get("effects", {}),
            display_format=data.get("display_format", "{name} the {title}"),
        )


@dataclass
class CharacterTitleState:
    """
    Tracks which titles a character has earned, at what tier/rank,
    plus accumulated prestige points and active honorific.
    """

    character_id: str
    prestige_points: int = 0
    # title_id -> current tier/rank achieved
    title_ranks: dict[str, int] = field(default_factory=dict)
    active_honorific: str | None = None
    # Tracked stats used for title requirements
    stats: dict[str, int] = field(default_factory=dict)

    def get_title_rank(self, title_id: str) -> int:
        return self.title_ranks.get(title_id, 0)

    def set_title_rank(self, title_id: str, rank: int) -> None:
        if rank <= 0:
            self.title_ranks.pop(title_id, None)
        else:
            self.title_ranks[title_id] = rank

    def has_title(self, title_id: str) -> bool:
        return self.title_ranks.get(title_id, 0) > 0

    def increment_prestige(self, points: int) -> None:
        self.prestige_points += points

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "prestige_points": self.prestige_points,
            "title_ranks": dict(self.title_ranks),
            "active_honorific": self.active_honorific,
            "stats": dict(self.stats),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CharacterTitleState:
        return CharacterTitleState(
            character_id=data["character_id"],
            prestige_points=data.get("prestige_points", 0),
            title_ranks=data.get("title_ranks", {}),
            active_honorific=data.get("active_honorific"),
            stats=data.get("stats", {}),
        )


class TitleManager:
    """
    Singleton-style manager that loads all title definitions and provides
    methods for character title interaction and NPC reaction resolution.
    """

    def __init__(self, data_directory: str | None = None) -> None:
        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self.titles: dict[str, TitleDefinition] = {}
        self.prestige_ranks: dict[str, TitleDefinition] = {}
        self.honorifics: dict[str, TitleDefinition] = {}
        self.character_states: dict[str, CharacterTitleState] = {}

        self._load_titles(data_directory)

    def _load_titles(self, directory: str) -> None:
        import json
        import os

        path = os.path.join(directory, "titles.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        for entry in data.get("titles", []):
            t = TitleDefinition.from_dict(entry)
            self.titles[t.id] = t

        for entry in data.get("prestige_ranks", []):
            t = TitleDefinition.from_dict(entry)
            self.prestige_ranks[t.id] = t

        for entry in data.get("honorifics", []):
            t = TitleDefinition.from_dict(entry)
            self.honorifics[t.id] = t

    def get_title(self, title_id: str) -> TitleDefinition | None:
        return self.titles.get(title_id)

    def get_prestige_rank(self, rank_id: str) -> TitleDefinition | None:
        return self.prestige_ranks.get(rank_id)

    def get_honorific(self, honorific_id: str) -> TitleDefinition | None:
        return self.honorifics.get(honorific_id)

    def get_character_state(self, character_id: str) -> CharacterTitleState:
        if character_id not in self.character_states:
            self.character_states[character_id] = CharacterTitleState(character_id=character_id)
        return self.character_states[character_id]

    def update_stat(self, character_id: str, stat_name: str, value: int) -> None:
        state = self.get_character_state(character_id)
        state.stats[stat_name] = value
        self._check_title_unlocks(character_id)

    def update_stats(self, character_id: str, stats: dict[str, int]) -> None:
        state = self.get_character_state(character_id)
        state.stats.update(stats)
        self._check_title_unlocks(character_id)

    def add_prestige_points(self, character_id: str, points: int) -> None:
        state = self.get_character_state(character_id)
        state.increment_prestige(points)
        self._check_prestige_unlocks(character_id)

    def _check_title_unlocks(self, character_id: str) -> None:
        state = self.get_character_state(character_id)
        for title_id, title in self.titles.items():
            if state.has_title(title_id):
                continue
            if self._requirements_met(title.requirements, state):
                state.set_title_rank(title_id, 1)

    def _check_prestige_unlocks(self, character_id: str) -> None:
        state = self.get_character_state(character_id)
        eligible_ranks = sorted(
            [r for r in self.prestige_ranks.values()],
            key=lambda r: r.requirements.get("prestige_points", 0),
        )
        highest_eligible = None
        for rank in eligible_ranks:
            req = rank.requirements.get("prestige_points", 0)
            if state.prestige_points >= req:
                highest_eligible = rank

        # Prestige ranks are mutually exclusive — keep only the highest
        for rank_id in list(state.title_ranks.keys()):
            if rank_id in self.prestige_ranks:
                state.set_title_rank(rank_id, 0)

        if highest_eligible:
            state.set_title_rank(highest_eligible.id, 1)

    def _requirements_met(self, requirements: dict[str, Any], state: CharacterTitleState) -> bool:
        for stat, value in requirements.items():
            if stat == "level":
                continue
            if isinstance(value, str):
                continue  # Non-int requirements (e.g. alignment) not tracked in int stats
            if state.stats.get(stat, 0) < value:
                return False
        return True

    def set_active_honorific(self, character_id: str, honorific_id: str) -> dict[str, Any]:
        state = self.get_character_state(character_id)
        honorific = self.honorifics.get(honorific_id)
        if honorific is None:
            return {"success": False, "reason": f"Honorific '{honorific_id}' not found."}
        if not self._requirements_met(honorific.requirements, state):
            return {"success": False, "reason": "Requirements not met for this honorific."}
        state.active_honorific = honorific_id
        return {"success": True, "honorific": honorific_id}

    def get_npc_reaction_modifier(self, character_id: str) -> int:
        state = self.get_character_state(character_id)
        modifier = 0
        for title_id, rank in state.title_ranks.items():
            title = self.titles.get(title_id) or self.prestige_ranks.get(title_id)
            if title:
                modifier += title.effects.get("npc_reaction_modifier", 0) * rank
        if state.active_honorific:
            honorific = self.honorifics.get(state.active_honorific)
            if honorific:
                modifier += honorific.effects.get("npc_reaction_modifier", 0)
        return modifier

    def get_character_titles_summary(self, character_id: str) -> dict[str, Any]:
        state = self.get_character_state(character_id)
        earned = []
        for title_id, rank in state.title_ranks.items():
            title = self.titles.get(title_id) or self.prestige_ranks.get(title_id)
            if title:
                earned.append({
                    "id": title.id,
                    "name": title.name,
                    "type": title.title_type.value,
                    "rank": rank,
                    "effects": title.effects,
                })
        honorific = None
        if state.active_honorific:
            h = self.honorifics.get(state.active_honorific)
            if h:
                honorific = {"id": h.id, "name": h.name, "effects": h.effects}
        return {
            "character_id": character_id,
            "prestige_points": state.prestige_points,
            "earned_titles": earned,
            "active_honorific": honorific,
            "npc_reaction_modifier": self.get_npc_reaction_modifier(character_id),
        }

    def format_character_name(self, character_id: str, base_name: str) -> str:
        state = self.get_character_state(character_id)
        # Honorific takes precedence in display formatting
        if state.active_honorific:
            honorific = self.honorifics.get(state.active_honorific)
            if honorific:
                return honorific.display_format.format(name=base_name, title="", rank="")

        # Show highest prestige rank or title
        best = None
        best_priority = -1
        for title_id, rank in state.title_ranks.items():
            title = self.titles.get(title_id) or self.prestige_ranks.get(title_id)
            if title and rank > 0:
                # Prestige ranks generally outrank titles
                priority = 2 if title.title_type == TitleType.PRESTIGE else 1
                if priority > best_priority:
                    best = title
                    best_priority = priority

        if best:
            return best.display_format.format(name=base_name, title=best.name, rank="")

        return base_name
