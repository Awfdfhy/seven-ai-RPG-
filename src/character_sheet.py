"""
RPG-XX: Character Sheet
Aggregates character information including stats, skill trees, and titles
into a displayable character sheet.
"""

from __future__ import annotations

from typing import Any

from character_stats import StatsManager
from skill_tree_manager import SkillTreeManager
from title_system import TitleManager


class CharacterSheet:
    """
    Formats a character's complete sheet, including stats, skills, and titles.
    """

    def __init__(
        self,
        skill_manager: SkillTreeManager | None = None,
        title_manager: TitleManager | None = None,
        stats_manager: StatsManager | None = None,
    ) -> None:
        self.skill_manager = skill_manager or SkillTreeManager()
        self.title_manager = title_manager or TitleManager()
        self.stats_manager = stats_manager or StatsManager()
        self.stats_manager.load_from_json()

    def render_sheet(self, character_id: str, base_name: str) -> dict[str, Any]:
        """
        Build a full character sheet dictionary.

        Returns:
            {
                "character_id": str,
                "display_name": str,
                "stats_summary": dict,
                "skill_summaries": [dict],
                "title_summary": dict,
                "formatted_titles": str,
            }
        """
        display_name = self.title_manager.format_character_name(character_id, base_name)
        title_summary = self.title_manager.get_character_titles_summary(character_id)
        stats_summary = self.stats_manager.get_character_stats_summary(character_id)

        skill_summaries = []
        for tree in self.skill_manager.trees.values():
            skill_summaries.append(self.skill_manager.get_character_summary(character_id, tree.id))

        formatted_titles = self._format_titles(title_summary)

        return {
            "character_id": character_id,
            "display_name": display_name,
            "stats_summary": stats_summary,
            "skill_summaries": skill_summaries,
            "title_summary": title_summary,
            "formatted_titles": formatted_titles,
        }

    def _format_titles(self, title_summary: dict[str, Any]) -> str:
        parts: list[str] = []
        honorific = title_summary.get("active_honorific")
        if honorific:
            parts.append(honorific["name"])
        for title in title_summary.get("earned_titles", []):
            if title["type"] == "prestige":
                parts.append(f"[{title['name']}]")
            else:
                parts.append(title["name"])
        return " ".join(parts) if parts else ""
