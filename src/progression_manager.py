"""
RPG-XX: Progression Manager
Orchestrates experience gain, level-ups, stat increases,
and skill/ability point grants.
"""

from __future__ import annotations

from typing import Any

from progression import (
    CharacterProgressionState,
    LevelUnlock,
    ProgressionSystem,
)


class ProgressionManager:
    """
    Manages per-character progression and integrates with
    SkillTreeManager and AbilityManager.
    """

    def __init__(self, system: ProgressionSystem | None = None) -> None:
        self.system = system or ProgressionSystem()
        self.character_states: dict[str, CharacterProgressionState] = {}

    def get_state(self, character_id: str) -> CharacterProgressionState:
        if character_id not in self.character_states:
            self.character_states[character_id] = CharacterProgressionState(
                character_id=character_id
            )
        return self.character_states[character_id]

    def add_experience(self, character_id: str, amount: int) -> dict[str, Any]:
        """
        Grant XP to a character and process any resulting level-ups.
        Returns a report of level-ups and point gains.
        """
        state = self.get_state(character_id)
        state.experience += amount
        report: dict[str, Any] = {
            "character_id": character_id,
            "xp_gained": amount,
            "total_experience": state.experience,
            "level_ups": [],
        }

        while True:
            next_level = state.level + 1
            needed = self.system.xp_for_level(next_level)
            if state.experience < needed:
                break
            state.experience -= needed
            state.level += 1
            state.unspent_skill_points += self.system.skill_points_per_level
            state.unspent_ability_points += self.system.ability_points_per_level
            state.unspent_stat_points += self.system.stat_points_per_level

            level_up = {
                "new_level": state.level,
                "skill_points_gained": self.system.skill_points_per_level,
                "ability_points_gained": self.system.ability_points_per_level,
                "stat_points_gained": self.system.stat_points_per_level,
            }
            report["level_ups"].append(level_up)

        return report

    def apply_stat_growth(self, character_id: str) -> dict[str, int]:
        """
        Apply automatic stat growth for the character's current level.
        Returns a dict of attribute -> total gained since last call.
        """
        state = self.get_state(character_id)
        gains: dict[str, int] = {}
        for attr, growth in self.system.stat_growth.items():
            amount = growth.amount_per_level
            if amount:
                gains[attr] = amount * state.level
        return gains

    def allocate_stat_point(
        self, character_id: str, attribute: str
    ) -> tuple[bool, str]:
        """
        Spend one unspent stat point to increase an attribute.
        """
        state = self.get_state(character_id)
        if state.unspent_stat_points <= 0:
            return False, "No unspent stat points."
        growth = self.system.stat_growth.get(attribute)
        if not growth or growth.amount_per_level <= 0:
            return False, f"Attribute '{attribute}' does not allow point allocation."
        state.unspent_stat_points -= 1
        return True, ""

    def grant_skill_points(self, character_id: str, amount: int) -> None:
        state = self.get_state(character_id)
        state.unspent_skill_points += amount

    def grant_ability_points(self, character_id: str, amount: int) -> None:
        state = self.get_state(character_id)
        state.unspent_ability_points += amount

    def get_level_unlocks(self, character_id: str) -> list[dict[str, Any]]:
        """
        Return level-based unlocks relevant to the character's current level.
        """
        state = self.get_state(character_id)
        unlocks = []
        for level, items in self.system.level_unlocks.items():
            if level <= state.level:
                for u in items:
                    unlocks.append(u.to_dict())
        return unlocks

    def get_pending_auto_unlocks(self, character_id: str) -> list[LevelUnlock]:
        """
        Return level unlocks that are set to auto-unlock and are
        at or below the character's current level.
        """
        state = self.get_state(character_id)
        pending = []
        for level, items in self.system.level_unlocks.items():
            if level <= state.level:
                for u in items:
                    if u.auto_unlock:
                        pending.append(u)
        return pending

    def sync_with_skill_manager(self, character_id: str, skill_manager: Any) -> None:
        """
        Grant unspent skill points to the skill manager and apply
        any pending auto-unlocks.
        """
        state = self.get_state(character_id)
        if state.unspent_skill_points > 0:
            skill_manager.grant_points(character_id, state.unspent_skill_points)
            state.unspent_skill_points = 0

        pending = self.get_pending_auto_unlocks(character_id)
        for unlock in pending:
            tree = skill_manager.get_tree(unlock.tree_id)
            if tree and tree.get_node(unlock.node_id):
                skill_manager.unlock_node(character_id, unlock.tree_id, unlock.node_id)

    def sync_with_ability_manager(self, character_id: str, ability_manager: Any) -> None:
        """
        Grant unspent ability points to the ability manager and apply
        any pending auto-unlocks.
        """
        state = self.get_state(character_id)
        if state.unspent_ability_points > 0:
            ability_manager.grant_ability_points(character_id, state.unspent_ability_points)
            state.unspent_ability_points = 0

        pending = self.get_pending_auto_unlocks(character_id)
        for unlock in pending:
            tree = ability_manager.get_tree(unlock.tree_id)
            if tree and tree.get_node(unlock.node_id):
                ability_manager.unlock_ability_node(character_id, unlock.tree_id, unlock.node_id)

    def get_character_summary(self, character_id: str) -> dict[str, Any]:
        state = self.get_state(character_id)
        next_level = state.level + 1
        xp_needed = self.system.xp_for_level(next_level)
        return {
            "character_id": character_id,
            "level": state.level,
            "experience": state.experience,
            "experience_to_next_level": xp_needed,
            "unspent_stat_points": state.unspent_stat_points,
            "unspent_skill_points": state.unspent_skill_points,
            "unspent_ability_points": state.unspent_ability_points,
        }
