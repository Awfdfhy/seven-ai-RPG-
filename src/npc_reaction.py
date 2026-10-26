"""
RPG-XX: NPC Reaction System
Resolves NPC disposition and dialogue tone using character titles,
prestige ranks, and honorifics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from title_system import TitleManager


@dataclass
class NPCProfile:
    """
    Represents an NPC's base disposition and preferences.

    Attributes:
        id                : unique NPC identifier
        name              : display name
        base_disposition  : starting reaction modifier (usually 0)
        preferred_honorifics: list of honorific IDs this NPC respects
        feared_titles     : list of title IDs that cause fear
        admired_titles    : list of title IDs that cause admiration
        dialogue_tone_bias: default dialogue tone preference
    """

    id: str
    name: str
    base_disposition: int = 0
    preferred_honorifics: list[str] = field(default_factory=list)
    feared_titles: list[str] = field(default_factory=list)
    admired_titles: list[str] = field(default_factory=list)
    dialogue_tone_bias: str = "neutral"


class NPCReactionResolver:
    """
    Resolves NPC reactions given a character's title state and the NPC's profile.
    """

    def __init__(self, title_manager: TitleManager | None = None) -> None:
        self.title_manager = title_manager or TitleManager()

    def resolve_disposition(
        self,
        character_id: str,
        npc: NPCProfile,
    ) -> dict[str, Any]:
        """
        Compute the NPC's reaction to a character.

        Returns:
            {
                "disposition": int,           # net modifier
                "dialogue_tone": str,         # "neutral" | "respectful" | "fearful" | ...
                "active_effects": list[str],  # human-readable effects applied
            }
        """
        title_state = self.title_manager.get_character_state(character_id)
        disposition = npc.base_disposition
        active_effects: list[str] = []

        # Base title/prestige/honorific modifier
        base_modifier = self.title_manager.get_npc_reaction_modifier(character_id)
        disposition += base_modifier
        if base_modifier != 0:
            active_effects.append(f"titles_modifier: +{base_modifier}")

        # NPC-specific title reactions
        for title_id, rank in title_state.title_ranks.items():
            if title_id in npc.feared_titles and rank > 0:
                disposition += 2 * rank
                active_effects.append(f"feared_title_{title_id}: +{2 * rank}")
            if title_id in npc.admired_titles and rank > 0:
                disposition += 3 * rank
                active_effects.append(f"admired_title_{title_id}: +{3 * rank}")

        # Honorific preference
        dialogue_tone = npc.dialogue_tone_bias
        if title_state.active_honorific:
            honorific = self.title_manager.honorifics.get(title_state.active_honorific)
            if honorific:
                if title_state.active_honorific in npc.preferred_honorifics:
                    disposition += 2
                    active_effects.append("preferred_honorific: +2")
                tone = honorific.effects.get("dialogue_tone")
                if tone:
                    dialogue_tone = tone

        return {
            "disposition": disposition,
            "dialogue_tone": dialogue_tone,
            "active_effects": active_effects,
        }

    def resolve_skill_check_modifier(
        self,
        character_id: str,
        npc: NPCProfile,
        skill_category: str | None = None,
    ) -> int:
        """
        Return an additive modifier for skill checks involving this NPC.
        Titles and honorifics can grant bonuses to social or combat checks.
        """
        disposition = self.resolve_disposition(character_id, npc)
        base = disposition["disposition"]

        if skill_category == "social":
            # Social checks benefit more from positive disposition
            return max(0, base // 2)
        if skill_category == "combat":
            # Fear-based titles grant combat advantage
            title_state = self.title_manager.get_character_state(character_id)
            fear_bonus = sum(
                2 * rank
                for title_id, rank in title_state.title_ranks.items()
                if title_id in npc.feared_titles and rank > 0
            )
            return fear_bonus

        return max(0, base // 3)
