"""
RPG-10-05: NPC Dialogue System
Branching conversations with player choices, conditions, and effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Definitions (static, data-driven)
# ---------------------------------------------------------------------------

@dataclass
class DialogueChoice:
    """
    One player-facing choice within a dialogue node.

    Attributes:
        id            : unique choice identifier within the node
        text          : text shown to the player
        next_node_id  : the node to transition to on selection
        conditions    : list of condition dicts that must all pass for the
                        choice to appear
        effects       : list of effect dicts executed on selection
        skill_check   : optional skill-check block used by UI / resolver
    """

    id: str
    text: str
    next_node_id: str | None = None
    conditions: list[dict[str, Any]] = field(default_factory=list)
    effects: list[dict[str, Any]] = field(default_factory=list)
    skill_check: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "next_node_id": self.next_node_id,
            "conditions": list(self.conditions),
            "effects": list(self.effects),
            "skill_check": dict(self.skill_check) if self.skill_check else None,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DialogueChoice:
        return DialogueChoice(
            id=data["id"],
            text=data.get("text", ""),
            next_node_id=data.get("next_node_id"),
            conditions=list(data.get("conditions", [])),
            effects=list(data.get("effects", [])),
            skill_check=dict(data["skill_check"]) if data.get("skill_check") else None,
        )


@dataclass
class DialogueNode:
    """
    A single beat in a conversation spoken by the NPC, player, or narrator.

    Attributes:
        id       : unique node identifier within the dialogue
        speaker  : who speaks ("npc_id", "player", "narrator")
        text     : the line spoken
        choices  : list of choices the player can make
        condition: optional condition dict; if present the node is only
                    reachable when the condition evaluates to True
        on_enter : effects triggered when the node is entered
    """

    id: str
    speaker: str
    text: str
    choices: list[DialogueChoice] = field(default_factory=list)
    condition: dict[str, Any] | None = None
    on_enter: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "speaker": self.speaker,
            "text": self.text,
            "choices": [c.to_dict() for c in self.choices],
            "condition": dict(self.condition) if self.condition else None,
            "on_enter": list(self.on_enter),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DialogueNode:
        return DialogueNode(
            id=data["id"],
            speaker=data.get("speaker", "narrator"),
            text=data.get("text", ""),
            choices=[DialogueChoice.from_dict(c) for c in data.get("choices", [])],
            condition=dict(data["condition"]) if data.get("condition") else None,
            on_enter=list(data.get("on_enter", [])),
        )


@dataclass
class DialogueDefinition:
    """
    Static definition of a full conversation with an NPC.

    Attributes:
        id            : unique dialogue identifier
        npc_id        : the NPC this dialogue belongs to
        start_node_id : entry-point node when the conversation begins
        nodes         : ordered list of all nodes in the graph
        metadata      : free-form metadata (difficulty, tags, etc.)
    """

    id: str
    npc_id: str
    start_node_id: str
    nodes: list[DialogueNode] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "npc_id": self.npc_id,
            "start_node_id": self.start_node_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DialogueDefinition:
        return DialogueDefinition(
            id=data["id"],
            npc_id=data["npc_id"],
            start_node_id=data["start_node_id"],
            nodes=[DialogueNode.from_dict(n) for n in data.get("nodes", [])],
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Session (runtime, per character per conversation)
# ---------------------------------------------------------------------------

@dataclass
class DialogueSession:
    """
    Runtime state for an active conversation between one character and one NPC.

    Attributes:
        dialogue_id    : which dialogue definition is active
        character_id   : the player character in the conversation
        current_node_id: the node currently being displayed
        visited_nodes  : set of node IDs the character has already seen
        history        : ordered list of (node_id, choice_id) tuples
        flags          : free-form boolean / value store for conditions
        metadata       : optional session-scoped metadata (session_id, etc.)
    """

    dialogue_id: str
    character_id: str
    current_node_id: str
    visited_nodes: set[str] = field(default_factory=set)
    history: list[dict[str, Any]] = field(default_factory=list)
    flags: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dialogue_id": self.dialogue_id,
            "character_id": self.character_id,
            "current_node_id": self.current_node_id,
            "visited_nodes": sorted(self.visited_nodes),
            "history": list(self.history),
            "flags": dict(self.flags),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DialogueSession:
        return DialogueSession(
            dialogue_id=data["dialogue_id"],
            character_id=data["character_id"],
            current_node_id=data["current_node_id"],
            visited_nodes=set(data.get("visited_nodes", [])),
            history=list(data.get("history", [])),
            flags=dict(data.get("flags", {})),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class DialogueManager:
    """
    Manages dialogue definitions, conversation sessions, choice resolution,
    condition evaluation, and effect execution.
    """

    def __init__(
        self,
        title_manager: Any | None = None,
        quest_journal: Any | None = None,
        inventory_manager: Any | None = None,
        world_state: dict[str, Any] | None = None,
        npc_reaction_resolver: Any | None = None,
    ) -> None:
        self._definitions: dict[str, DialogueDefinition] = {}
        self._sessions: dict[str, DialogueSession] = {}

        self.title_manager = title_manager
        self.quest_journal = quest_journal
        self.inventory_manager = inventory_manager
        self.world_state = world_state or {}
        self.npc_reaction_resolver = npc_reaction_resolver

    # -- Registration / Loading --

    def register_definition(self, definition: DialogueDefinition) -> None:
        self._definitions[definition.id] = definition

    def load_definitions(self, definitions: list[DialogueDefinition]) -> None:
        for d in definitions:
            self.register_definition(d)

    def load_definitions_from_json(self, path: str) -> int:
        """
        Load dialogue definitions from a JSON file.
        Returns the number of definitions loaded.
        """
        import json

        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        definitions = [DialogueDefinition.from_dict(d) for d in raw]
        self.load_definitions(definitions)
        return len(definitions)

    # -- Session lifecycle --

    def _session_key(self, dialogue_id: str, character_id: str) -> str:
        return f"{dialogue_id}:{character_id}"

    def start_dialogue(
        self,
        dialogue_id: str,
        character_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> DialogueSession | None:
        definition = self._definitions.get(dialogue_id)
        if definition is None:
            return None

        key = self._session_key(dialogue_id, character_id)
        session = DialogueSession(
            dialogue_id=dialogue_id,
            character_id=character_id,
            current_node_id=definition.start_node_id,
            metadata=metadata or {},
        )
        self._sessions[key] = session
        return session

    def get_session(
        self,
        dialogue_id: str,
        character_id: str,
    ) -> DialogueSession | None:
        return self._sessions.get(self._session_key(dialogue_id, character_id))

    def end_dialogue(
        self,
        dialogue_id: str,
        character_id: str,
    ) -> DialogueSession | None:
        session = self.get_session(dialogue_id, character_id)
        if session is not None:
            session.flags["_ended"] = True
        return session

    def is_dialogue_ended(
        self,
        dialogue_id: str,
        character_id: str,
    ) -> bool:
        session = self.get_session(dialogue_id, character_id)
        if not session:
            return True
        return bool(session.flags.get("_ended", False))

    # -- Node resolution --

    def _get_node(self, dialogue_id: str, node_id: str) -> DialogueNode | None:
        definition = self._definitions.get(dialogue_id)
        if definition is None:
            return None
        for node in definition.nodes:
            if node.id == node_id:
                return node
        return None

    def get_current_node(
        self,
        dialogue_id: str,
        character_id: str,
    ) -> DialogueNode | None:
        session = self.get_session(dialogue_id, character_id)
        if session is None:
            return None
        return self._get_node(dialogue_id, session.current_node_id)

    def get_node_choices(
        self,
        dialogue_id: str,
        character_id: str,
    ) -> list[dict[str, Any]]:
        """
        Return the currently available choices as plain dicts, filtered
        by their conditions.
        """
        session = self.get_session(dialogue_id, character_id)
        if session is None:
            return []

        node = self.get_current_node(dialogue_id, character_id)
        if node is None:
            return []

        available: list[dict[str, Any]] = []
        for choice in node.choices:
            if not all(self._check_condition(c, character_id, session) for c in choice.conditions):
                continue
            available.append({
                "id": choice.id,
                "text": choice.text,
                "skill_check": choice.skill_check,
            })
        return available

    # -- Conditions & Effects --

    def _check_condition(
        self,
        condition: dict[str, Any],
        character_id: str,
        session: DialogueSession,
    ) -> bool:
        """
        Evaluate a single condition dict against the current game state.
        Unknown condition types evaluate to True (fail-safe).
        """
        if not condition:
            return True

        cond_type = condition.get("type")

        if cond_type == "has_quest":
            quest_id = condition.get("quest_id")
            status = condition.get("status", "active")
            if self.quest_journal:
                quest = self.quest_journal.get_quest(quest_id)
                if quest and quest.status == status:
                    return True
            return False

        if cond_type == "not_has_quest":
            quest_id = condition.get("quest_id")
            status = condition.get("status", "active")
            if self.quest_journal:
                quest = self.quest_journal.get_quest(quest_id)
                if quest and quest.status == status:
                    return False
            return True

        if cond_type == "has_item":
            item_id = condition.get("item_id")
            if self.inventory_manager:
                inv = self.inventory_manager.get_inventory(character_id)
                if inv and any(
                    slot.item is not None and slot.item.id == item_id
                    for slot in inv.slots
                ):
                    return True
            return False

        if cond_type == "title_rank":
            title_id = condition.get("title_id")
            min_rank = condition.get("min_rank", 1)
            if self.title_manager:
                state = self.title_manager.get_character_state(character_id)
                return state.title_ranks.get(title_id, 0) >= min_rank
            return False

        if cond_type == "disposition":
            npc_id = condition.get("npc_id")
            threshold = condition.get("threshold", 0)
            if self.npc_reaction_resolver:
                from npc_reaction import NPCProfile
                profile = NPCProfile(id=npc_id, name=npc_id)
                result = self.npc_reaction_resolver.resolve_disposition(character_id, profile)
                return result["disposition"] >= threshold
            return False

        if cond_type == "visited_node":
            return condition.get("node_id") in session.visited_nodes

        if cond_type == "flag":
            flag_name = condition.get("name")
            expected = condition.get("value")
            actual = session.flags.get(flag_name, self.world_state.get(flag_name))
            if expected is None:
                return actual is not None
            return actual == expected

        # Fail-safe: unknown condition types pass
        return True

    def _apply_effects(
        self,
        effects: list[dict[str, Any]],
        character_id: str,
        session: DialogueSession,
    ) -> list[str]:
        """
        Execute a list of effect dicts and return human-readable labels.
        """
        applied: list[str] = []
        for effect in effects:
            effect_type = effect.get("type")

            if effect_type == "start_quest":
                quest_id = effect.get("quest_id")
                if self.quest_journal:
                    entry = self.quest_journal.start_quest(
                        quest_id,
                        world_id=effect.get("world_id", "default"),
                        session_id=session.metadata.get("session_id"),
                    )
                    if entry:
                        applied.append(f"started_quest:{quest_id}")

            elif effect_type == "complete_quest":
                quest_id = effect.get("quest_id")
                if self.quest_journal:
                    quest = self.quest_journal.get_quest(quest_id)
                    if quest and quest.status == "active":
                        self.quest_journal.complete_quest(quest_id)
                        applied.append(f"completed_quest:{quest_id}")

            elif effect_type == "fail_quest":
                quest_id = effect.get("quest_id")
                reason = effect.get("reason", "")
                if self.quest_journal:
                    self.quest_journal.fail_quest(quest_id, reason=reason)
                    applied.append(f"failed_quest:{quest_id}")

            elif effect_type == "give_item":
                item_id = effect.get("item_id")
                amount = effect.get("amount", 1)
                if self.inventory_manager:
                    from inventory import Item, ItemCategory, ItemRarity
                    item = Item(
                        id=item_id,
                        name=effect.get("name", item_id),
                        description=effect.get("description", ""),
                        item_type=ItemCategory(effect.get("item_type", "misc")),
                        rarity=ItemRarity(effect.get("rarity", "common")),
                        stackable=effect.get("stackable", True),
                        max_stack=effect.get("max_stack", 99),
                        metadata=effect.get("metadata", {}),
                    )
                    result = self.inventory_manager.add_item(character_id, item, quantity=amount)
                    if result.get("success"):
                        applied.append(f"gave_item:{item_id}:{amount}")

            elif effect_type == "set_flag":
                name = effect.get("name")
                value = effect.get("value", True)
                session.flags[name] = value
                applied.append(f"set_flag:{name}:{value}")

            elif effect_type == "end_dialogue":
                session.flags["_ended"] = True
                applied.append("dialogue_ended")

        return applied

    # -- Player action --

    def choose(
        self,
        dialogue_id: str,
        character_id: str,
        choice_id: str,
    ) -> dict[str, Any] | None:
        """
        Make a choice in the current dialogue node.

        Returns a result dict with:
            - choice: the DialogueChoice as a dict
            - effects_applied: list of effect labels executed
            - current_node: the new node as a dict
            - available_choices: list of choice dicts for the new node

        Returns None if the dialogue session does not exist, the node does not
        exist, or the choice ID is invalid.
        """
        session = self.get_session(dialogue_id, character_id)
        if session is None:
            return None

        node = self.get_current_node(dialogue_id, character_id)
        if node is None:
            return None

        choice = next((c for c in node.choices if c.id == choice_id), None)
        if choice is None:
            return None

        # Record history
        session.history.append({
            "node_id": session.current_node_id,
            "choice_id": choice_id,
            "speaker": node.speaker,
            "text": node.text,
        })
        session.visited_nodes.add(session.current_node_id)

        # Apply choice effects
        applied = self._apply_effects(choice.effects, character_id, session)

        # Advance to next node
        next_node_id = choice.next_node_id
        if next_node_id:
            session.current_node_id = next_node_id

        # Apply on_enter for the new node
        new_node = self.get_current_node(dialogue_id, character_id)
        on_enter_effects: list[str] = []
        if new_node and new_node.id == session.current_node_id:
            on_enter_effects = self._apply_effects(new_node.on_enter, character_id, session)
            session.visited_nodes.add(new_node.id)

        return {
            "choice": choice.to_dict(),
            "effects_applied": applied + on_enter_effects,
            "current_node": new_node.to_dict() if new_node else None,
            "available_choices": self.get_node_choices(dialogue_id, character_id),
        }
