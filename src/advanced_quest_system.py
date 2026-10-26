"""
RPG-12-01: Advanced Quest System
Extends the base quest journal with:
  - Procedural quest generation from templates
  - Formal quest chains with branching paths
  - Dynamic objectives that adapt to world state, player level, and events
"""

from __future__ import annotations

import copy
import hashlib
import os
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from quest_journal import (
    QuestDefinition,
    QuestEntry,
    QuestJournalManager,
    QuestObjective,
)

# ---------------------------------------------------------------------------
# Procedural Quests
# ---------------------------------------------------------------------------

@dataclass
class QuestTemplate:
    """
    A reusable blueprint for generating procedural quests.

    Attributes:
        template_id   : unique identifier
        name_template : format string with {placeholders}
        description   : format string with {placeholders}
        objectives    : list of objective templates with optional conditionals
        rewards       : base reward templates (can be scaled)
        tags          : thematic / mechanical tags for filtering
        metadata      : seed hints, difficulty curve, etc.
    """

    template_id: str
    name_template: str
    description: str
    objectives: list[dict[str, Any]] = field(default_factory=list)
    rewards: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name_template": self.name_template,
            "description": self.description,
            "objectives": [copy.deepcopy(o) for o in self.objectives],
            "rewards": [copy.deepcopy(r) for r in self.rewards],
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> QuestTemplate:
        return QuestTemplate(
            template_id=data["template_id"],
            name_template=data.get("name_template", ""),
            description=data.get("description", ""),
            objectives=[copy.deepcopy(o) for o in data.get("objectives", [])],
            rewards=[copy.deepcopy(r) for r in data.get("rewards", [])],
            tags=list(data.get("tags", [])),
            metadata=dict(data.get("metadata", {})),
        )


class ProceduralQuestGenerator:
    """
    Generates quests from templates using a deterministic or random seed.

    Supports:
      - seeded generation for deterministic worlds
      - level- and world-state-aware scaling
      - tag-based template selection
    """

    def __init__(self, manager: QuestJournalManager | None = None) -> None:
        self._manager = manager or QuestJournalManager()
        self._templates: dict[str, QuestTemplate] = {}

    def register_template(self, template: QuestTemplate) -> None:
        self._templates[template.template_id] = template

    def load_templates(self, templates: list[QuestTemplate]) -> None:
        for t in templates:
            self.register_template(t)

    def generate_quest(
        self,
        template_id: str,
        world_id: str,
        session_id: str | None = None,
        seed: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> QuestEntry | None:
        """
        Instantiate a quest from a template.

        context is substituted into {placeholders} in name/description/objectives.
        If seed is provided, generation is deterministic.
        """
        template = self._templates.get(template_id)
        if template is None:
            return None

        rng = random.Random(seed) if seed is not None else random
        ctx = context or {}

        # Safe formatter that leaves unknown placeholders empty
        def _fmt(template: str) -> str:
            return template.format_map(defaultdict(str, **ctx))

        # Resolve name / description
        name = _fmt(template.name_template)
        description = _fmt(template.description)

        # Resolve objectives with optional scaling
        resolved_objectives = []
        for obj_t in template.objectives:
            oid = _fmt(obj_t["id"])
            desc = _fmt(obj_t.get("description", ""))
            required = obj_t.get("required_count", 1)
            if "scale_per_level" in obj_t:
                level = ctx.get("player_level", 1)
                required = max(1, required + obj_t["scale_per_level"] * (level - 1))
            meta = {k: (_fmt(v) if isinstance(v, str) else v) for k, v in obj_t.get("metadata", {}).items()}
            resolved_objectives.append({
                "id": oid,
                "description": desc,
                "required_count": required,
                "metadata": meta,
            })

        # Resolve rewards with scaling
        resolved_rewards = []
        for rew_t in template.rewards:
            amount = rew_t.get("amount", 0)
            if "scale_per_level" in rew_t:
                level = ctx.get("player_level", 1)
                amount = max(0, amount + rew_t["scale_per_level"] * (level - 1))
            resolved_rewards.append({
                "type": rew_t["type"],
                "amount": amount,
                "item_id": rew_t.get("item_id"),
                "metadata": dict(rew_t.get("metadata", {})),
            })

        # Deterministic quest id from template + context + seed
        raw_id = f"{template.template_id}:{ctx}:{seed}"
        quest_suffix = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:8]
        quest_id = template.metadata.get("prefix", "proc") + "_" + quest_suffix
        definition = QuestDefinition(
            id=quest_id,
            name=name,
            description=description,
            objectives=resolved_objectives,
            rewards=resolved_rewards,
            prerequisites=[],
            metadata={**template.metadata, "template_id": template_id, "seed": seed},
        )
        self._manager.register_definition(definition)
        return self._manager.start_quest(
            quest_id,
            world_id=world_id,
            session_id=session_id,
            metadata={"procedural": True, "template_id": template_id},
        )

    def get_template(self, template_id: str) -> QuestTemplate | None:
        return self._templates.get(template_id)

    def list_templates(self, tags: list[str] | None = None) -> list[dict[str, Any]]:
        templates = list(self._templates.values())
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        return [t.to_dict() for t in sorted(templates, key=lambda t: t.template_id)]


# ---------------------------------------------------------------------------
# Quest Chains
# ---------------------------------------------------------------------------

@dataclass
class QuestChainDefinition:
    """
    A sequence of quests forming a chain, with optional branching.

    Attributes:
        chain_id        : unique identifier
        name            : display name
        description     : chain flavor text
        quests          : ordered list of quest definition IDs in the main path
        branches        : optional branches (branch_point -> list of quest IDs)
        auto_progression: whether completed quests auto-start the next in chain
        metadata        : extra data
    """

    chain_id: str
    name: str
    description: str = ""
    quests: list[str] = field(default_factory=list)
    branches: dict[str, list[str]] = field(default_factory=dict)
    auto_progression: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "description": self.description,
            "quests": list(self.quests),
            "branches": {k: list(v) for k, v in self.branches.items()},
            "auto_progression": self.auto_progression,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> QuestChainDefinition:
        return QuestChainDefinition(
            chain_id=data["chain_id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            quests=list(data.get("quests", [])),
            branches={k: list(v) for k, v in data.get("branches", {}).items()},
            auto_progression=data.get("auto_progression", True),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class QuestChainEvent:
    """
    Runtime record of a player's progress through a quest chain.

    Attributes:
        chain_event_id  : unique id
        chain_id        : references QuestChainDefinition
        world_id        : the world
        session_id      : optional session
        current_quest_id: last quest that was started in this chain
        completed_quests: list of completed quest IDs in chain order
        active_branch   : currently active branch key (if any)
        status          : in_progress | completed | abandoned
        started_at      : ISO timestamp
        completed_at    : ISO timestamp or None
        metadata        : opaque extra data
    """

    chain_event_id: str
    chain_id: str
    world_id: str
    current_quest_id: str | None = None
    completed_quests: list[str] = field(default_factory=list)
    active_branch: str | None = None
    status: str = "in_progress"
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_event_id": self.chain_event_id,
            "chain_id": self.chain_id,
            "world_id": self.world_id,
            "current_quest_id": self.current_quest_id,
            "completed_quests": list(self.completed_quests),
            "active_branch": self.active_branch,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "session_id": self.session_id,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> QuestChainEvent:
        return QuestChainEvent(
            chain_event_id=data["chain_event_id"],
            chain_id=data["chain_id"],
            world_id=data["world_id"],
            current_quest_id=data.get("current_quest_id"),
            completed_quests=list(data.get("completed_quests", [])),
            active_branch=data.get("active_branch"),
            status=data.get("status", "in_progress"),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            session_id=data.get("session_id"),
            metadata=dict(data.get("metadata", {})),
        )


class QuestChainManager:
    """
    Manages quest chains and their progression through worlds.

    Integrates with QuestJournalManager so chain quests are actual quest entries,
    and chain progression is triggered when quests complete/fail.
    """

    def __init__(self, manager: QuestJournalManager | None = None) -> None:
        self._manager = manager or QuestJournalManager()
        self._chains: dict[str, QuestChainDefinition] = {}
        self._events: dict[str, QuestChainEvent] = {}
        self._chain_quest_index: dict[str, dict[str, set[str]]] = {}  # chain_id -> {world_id -> set(quest_id)}
        self._quest_chain_map: dict[str, QuestChainEvent] = {}  # quest_id -> chain event

    def register_chain(self, chain: QuestChainDefinition) -> None:
        self._chains[chain.chain_id] = chain

    def load_chains(self, chains: list[QuestChainDefinition]) -> None:
        for c in chains:
            self.register_chain(c)

    def start_chain(
        self,
        chain_id: str,
        world_id: str,
        session_id: str | None = None,
    ) -> QuestChainEvent | None:
        """
        Start a quest chain. Starts the first quest in the chain immediately.
        """
        chain = self._chains.get(chain_id)
        if chain is None or not chain.quests:
            return None

        first_quest_id = chain.quests[0]
        definition = self._manager._definitions.get(first_quest_id)
        if definition is None:
            return None

        entry = self._manager.start_quest(
            first_quest_id,
            world_id=world_id,
            session_id=session_id,
            metadata={"chain_id": chain_id},
        )
        if entry is None:
            return None

        event = QuestChainEvent(
            chain_event_id=str(uuid.uuid4()),
            chain_id=chain_id,
            world_id=world_id,
            current_quest_id=first_quest_id,
            status="in_progress",
            session_id=session_id,
        )
        self._events[event.chain_event_id] = event
        self._chain_quest_index.setdefault(chain_id, {}).setdefault(world_id, set()).add(first_quest_id)
        self._quest_chain_map[first_quest_id] = event
        return event

    def on_quest_completed(self, quest_id: str) -> QuestChainEvent | None:
        """
        Called by the game when a quest that may belong to a chain completes.
        Auto-progresses the chain if configured.
        """
        event = self._quest_chain_map.get(quest_id)
        if event is None or event.status != "in_progress":
            return event

        chain = self._chains.get(event.chain_id)
        if chain is None:
            return event

        event.completed_quests.append(quest_id)
        self._quest_chain_map.pop(quest_id, None)

        if not chain.auto_progression:
            return event

        # Determine next quest
        next_quest_id = self._resolve_next_quest(chain, event)
        if next_quest_id is None:
            event.status = "completed"
            event.completed_at = datetime.now(UTC).isoformat()
            return event

        entry = self._manager.start_quest(
            next_quest_id,
            world_id=event.world_id,
            session_id=event.session_id,
            metadata={"chain_id": event.chain_id, "chain_event_id": event.chain_event_id},
        )
        if entry:
            event.current_quest_id = next_quest_id
            self._chain_quest_index.setdefault(event.chain_id, {}).setdefault(event.world_id, set()).add(next_quest_id)
            self._quest_chain_map[next_quest_id] = event
        return event

    def on_quest_failed(self, quest_id: str) -> QuestChainEvent | None:
        """
        Called when a chain quest fails. Can mark chain failed or switch branches.
        """
        event = self._quest_chain_map.get(quest_id)
        if event is None or event.status != "in_progress":
            return event

        event.status = "failed"
        event.completed_at = datetime.now(UTC).isoformat()
        self._quest_chain_map.pop(quest_id, None)
        return event

    def _resolve_next_quest(
        self,
        chain: QuestChainDefinition,
        event: QuestChainEvent,
    ) -> str | None:
        """
        Resolve the next quest id in the chain after the last completed one.
        If the last completed quest is a branch point, follow the active branch.
        """
        completed = event.completed_quests
        if not completed:
            return chain.quests[0] if chain.quests else None

        last_completed = completed[-1]
        # Main path: find position of last completed in chain.quests
        try:
            idx = chain.quests.index(last_completed)
        except ValueError:
            # Might be in a branch
            idx = -1

        # Next in main path
        next_idx = idx + 1
        if next_idx < len(chain.quests):
            return chain.quests[next_idx]

        # Check branches from the last completed quest
        for branch_key, branch_quests in chain.branches.items():
            if branch_key == last_completed and branch_quests:
                event.active_branch = branch_key
                return branch_quests[0]

        return None

    def get_chain_event_for_quest(self, quest_id: str) -> QuestChainEvent | None:
        return self._quest_chain_map.get(quest_id)

    def list_chain_events(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        events = list(self._events.values())
        if world_id is not None:
            events = [e for e in events if e.world_id == world_id]
        if session_id is not None:
            events = [e for e in events if e.session_id == session_id]
        if status is not None:
            events = [e for e in events if e.status == status]
        return [e.to_dict() for e in sorted(events, key=lambda e: e.started_at)]

    def get_available_chain_quests(self, chain_id: str, world_id: str) -> list[dict[str, Any]]:
        """
        Return quest definitions in the chain that are unlocked for this world
        (prerequisites met or are the first in chain).
        """
        chain = self._chains.get(chain_id)
        if chain is None:
            return []
        event = next((e for e in self._events.values() if e.chain_id == chain_id and e.world_id == world_id), None)
        available: list[dict[str, Any]] = []
        for qid in chain.quests:
            if event is None:
                available.append(self._manager._definitions[qid].to_dict() if qid in self._manager._definitions else {"id": qid})
            else:
                if qid in event.completed_quests or qid == event.current_quest_id:
                    continue
                # Simple rule: available if all prior in chain.quests are completed
                idx = chain.quests.index(qid)
                if all(prev in event.completed_quests for prev in chain.quests[:idx]):
                    available.append(self._manager._definitions[qid].to_dict() if qid in self._manager._definitions else {"id": qid})
        return available


# ---------------------------------------------------------------------------
# Dynamic Objectives
# ---------------------------------------------------------------------------

@dataclass
class DynamicObjectiveTemplate:
    """
    A template for an objective that resolves differently depending on
    world state, player context, and runtime events.

    Attributes:
        template_id    : unique identifier
        objective_type : kind of dynamic objective (kill, collect, explore, etc.)
        base_id        : base objective id (may include placeholders)
        base_description: description template
        scale_rules    : rules for scaling required_count by level, difficulty, etc.
        conditions     : world-state conditions for activation
        metadata       : extra hints
    """

    template_id: str
    objective_type: str
    base_id: str
    base_description: str
    scale_rules: dict[str, Any] = field(default_factory=dict)
    conditions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "objective_type": self.objective_type,
            "base_id": self.base_id,
            "base_description": self.base_description,
            "scale_rules": copy.deepcopy(self.scale_rules),
            "conditions": copy.deepcopy(self.conditions),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DynamicObjectiveTemplate:
        return DynamicObjectiveTemplate(
            template_id=data["template_id"],
            objective_type=data.get("objective_type", "generic"),
            base_id=data.get("base_id", ""),
            base_description=data.get("base_description", ""),
            scale_rules=copy.deepcopy(data.get("scale_rules", {})),
            conditions=copy.deepcopy(data.get("conditions", {})),
            metadata=dict(data.get("metadata", {})),
        )


class DynamicObjectiveBuilder:
    """
    Builds QuestObjective instances that adapt to world state and player context.

    Scaling rules:
      - scale_per_level: int added to required_count per player level above 1
      - difficulty_multiplier: float multiplier on required_count
      - min_count / max_count: clamped output

    Conditions:
      - required_world_flags: list of flags that must be present in world_state
      - excluded_world_flags: list of flags that must NOT be present
      - required_tags: template tags that must match at least one requested tag
    """

    def __init__(self, manager: QuestJournalManager | None = None) -> None:
        self._manager = manager or QuestJournalManager()
        self._templates: dict[str, DynamicObjectiveTemplate] = {}

    def register_template(self, template: DynamicObjectiveTemplate) -> None:
        self._templates[template.template_id] = template

    def load_templates(self, templates: list[DynamicObjectiveTemplate]) -> None:
        for t in templates:
            self.register_template(t)

    def build(
        self,
        template_id: str,
        context: dict[str, Any] | None = None,
    ) -> QuestObjective | None:
        """
        Build a QuestObjective from a dynamic template.

        context must include:
          - world_state: dict of world flags
          - player_level: int (default 1)
          - difficulty: str (e.g. "easy", "medium", "hard")
          - requested_tags: list[str] (optional)
        """
        template = self._templates.get(template_id)
        if template is None:
            return None

        ctx = context or {}
        world_state = ctx.get("world_state", {})
        player_level = int(ctx.get("player_level", 1))
        difficulty = ctx.get("difficulty", "easy")
        requested_tags = ctx.get("requested_tags", [])

        # Evaluate conditions
        if not self._conditions_met(template.conditions, world_state, requested_tags):
            return None

        # Scale required count before formatting so placeholders can use it
        required = 1
        if "base_count" in template.scale_rules:
            required = int(template.scale_rules["base_count"])
        elif "count" in template.scale_rules:
            required = int(template.scale_rules["count"])

        if template.scale_rules.get("scale_per_level"):
            required += template.scale_rules["scale_per_level"] * max(0, player_level - 1)

        difficulty_map = template.scale_rules.get("difficulty_multipliers", {})
        if difficulty in difficulty_map:
            required = max(1, int(required * float(difficulty_map[difficulty])))

        required = max(
            int(template.scale_rules.get("min_count", 1)),
            min(int(template.scale_rules.get("max_count", 9999)), required),
        )

        # Include required_count in context for formatting
        fmt_ctx = defaultdict(str, **ctx)
        fmt_ctx["required_count"] = required

        def _fmt(s: str) -> str:
            return s.format_map(fmt_ctx)

        # Resolve id / description placeholders
        objective_id = _fmt(template.base_id)
        description = _fmt(template.base_description)

        meta = dict(template.metadata)
        meta["objective_type"] = template.objective_type
        meta["resolved_from_template"] = template_id

        return QuestObjective(
            id=objective_id,
            description=description,
            required_count=required,
            metadata=meta,
        )

    def _conditions_met(
        self,
        conditions: dict[str, Any],
        world_state: dict[str, Any],
        requested_tags: list[str],
    ) -> bool:
        for flag in conditions.get("required_world_flags", []):
            if not world_state.get(flag):
                return False
        for flag in conditions.get("excluded_world_flags", []):
            if world_state.get(flag):
                return False
        req_tags = conditions.get("required_tags", [])
        if req_tags and not any(tag in requested_tags for tag in req_tags):
            return False
        return True

    def get_template(self, template_id: str) -> DynamicObjectiveTemplate | None:
        return self._templates.get(template_id)

    def list_templates(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in sorted(self._templates.values(), key=lambda t: t.template_id)]


# ---------------------------------------------------------------------------
# Advanced Quest Manager (unified API)
# ---------------------------------------------------------------------------

class AdvancedQuestManager:
    """
    Facade that combines the base QuestJournalManager, procedural generator,
    chain manager, and dynamic objective builder into a single interface.
    """

    def __init__(self, data_directory: str | None = None) -> None:
        self._journal = QuestJournalManager()
        self._procedural = ProceduralQuestGenerator(manager=self._journal)
        self._chains = QuestChainManager(manager=self._journal)
        self._dynamic = DynamicObjectiveBuilder(manager=self._journal)
        self._data_directory = data_directory or os.path.join(os.path.dirname(__file__), "..", "data")
        self._load_data()

    def _load_data(self) -> None:
        # Load base quests.json
        quests_path = os.path.join(self._data_directory, "quests.json")
        if os.path.exists(quests_path):
            try:
                import json
                with open(quests_path, encoding="utf-8") as fh:
                    data = json.load(fh)
                entries = data if isinstance(data, list) else data.get("quests", [])
                for entry in entries:
                    d = QuestDefinition.from_dict(entry)
                    self._journal.register_definition(d)
            except Exception:
                pass

        # Load procedural templates
        proc_path = os.path.join(self._data_directory, "procedural_quests.json")
        if os.path.exists(proc_path):
            try:
                import json
                with open(proc_path, encoding="utf-8") as fh:
                    data = json.load(fh)
                entries = data if isinstance(data, list) else data.get("templates", [])
                for entry in entries:
                    t = QuestTemplate.from_dict(entry)
                    self._procedural.register_template(t)
            except Exception:
                pass

        # Load quest chains
        chain_path = os.path.join(self._data_directory, "quest_chains.json")
        if os.path.exists(chain_path):
            try:
                import json
                with open(chain_path, encoding="utf-8") as fh:
                    data = json.load(fh)
                entries = data if isinstance(data, list) else data.get("chains", [])
                for entry in entries:
                    c = QuestChainDefinition.from_dict(entry)
                    self._chains.register_chain(c)
            except Exception:
                pass

        # Load dynamic objective templates
        dyn_path = os.path.join(self._data_directory, "dynamic_objectives.json")
        if os.path.exists(dyn_path):
            try:
                import json
                with open(dyn_path, encoding="utf-8") as fh:
                    data = json.load(fh)
                entries = data if isinstance(data, list) else data.get("objectives", [])
                for entry in entries:
                    t = DynamicObjectiveTemplate.from_dict(entry)
                    self._dynamic.register_template(t)
            except Exception:
                pass

    # Expose sub-manager APIs for convenience
    def start_quest(self, quest_id: str, world_id: str, session_id: str | None = None, metadata: dict[str, Any] | None = None) -> QuestEntry | None:
        return self._journal.start_quest(quest_id, world_id=world_id, session_id=session_id, metadata=metadata)

    def generate_quest(self, template_id: str, world_id: str, session_id: str | None = None, seed: int | None = None, context: dict[str, Any] | None = None) -> QuestEntry | None:
        return self._procedural.generate_quest(template_id, world_id=world_id, session_id=session_id, seed=seed, context=context)

    def start_chain(self, chain_id: str, world_id: str, session_id: str | None = None) -> QuestChainEvent | None:
        return self._chains.start_chain(chain_id, world_id=world_id, session_id=session_id)

    def on_quest_completed(self, quest_id: str) -> QuestChainEvent | None:
        return self._chains.on_quest_completed(quest_id)

    def on_quest_failed(self, quest_id: str) -> QuestChainEvent | None:
        return self._chains.on_quest_failed(quest_id)

    def build_dynamic_objective(self, template_id: str, context: dict[str, Any] | None = None) -> QuestObjective | None:
        return self._dynamic.build(template_id, context=context)

    def get_progress(self, quest_id: str) -> dict[str, Any]:
        return self._journal.get_progress(quest_id)

    def update_objective(self, quest_id: str, objective_id: str, delta: int = 1) -> QuestEntry | None:
        return self._journal.update_objective(quest_id, objective_id, delta=delta)

    def complete_quest(self, quest_id: str) -> QuestEntry | None:
        return self._journal.complete_quest(quest_id)

    def fail_quest(self, quest_id: str, reason: str = "") -> QuestEntry | None:
        return self._journal.fail_quest(quest_id, reason=reason)

    def list_quests(self, world_id: str | None = None, session_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        return self._journal.list_quests(world_id=world_id, session_id=session_id, status=status)

    def list_chain_events(self, world_id: str | None = None, session_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        return self._chains.list_chain_events(world_id=world_id, session_id=session_id, status=status)

    def list_procedural_templates(self, tags: list[str] | None = None) -> list[dict[str, Any]]:
        return self._procedural.list_templates(tags=tags)

    def list_chain_definitions(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._chains._chains.values()]

    def list_definitions(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in sorted(self._journal._definitions.values(), key=lambda d: d.id)]

    def export_state(self) -> dict[str, Any]:
        return {
            "journal": self._journal.export_state(),
            "chain_events": {eid: e.to_dict() for eid, e in self._chains._events.items()},
            "quest_chain_map": {qid: event.chain_event_id for qid, event in self._chains._quest_chain_map.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._journal.import_state(state.get("journal", {}))
        self._chains._events.clear()
        self._chains._quest_chain_map.clear()
        self._chains._chain_quest_index.clear()
        for eid, edata in state.get("chain_events", {}).items():
            event = QuestChainEvent.from_dict(edata)
            self._chains._events[eid] = event
            self._chains._chain_quest_index.setdefault(event.chain_id, {}).setdefault(event.world_id, set()).add(event.current_quest_id)
            for qid in event.completed_quests:
                self._chains._chain_quest_index.setdefault(event.chain_id, {}).setdefault(event.world_id, set()).add(qid)
        for qid, ceid in state.get("quest_chain_map", {}).items():
            event = self._chains._events.get(ceid)
            if event:
                self._chains._quest_chain_map[qid] = event
