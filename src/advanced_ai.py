"""
RPG-12-06: Advanced AI
Dynamic NPC behavior, memory, learning, and personality systems.

Concepts
--------
NPCMemoryEntry      : a single remembered event involving the player or world
NPCMemoryStore      : collection of memories with decay over time
NPCPersonality      : mutable personality traits that shift with experience
NPCBehaviorState    : current behavioral state of an NPC
BehaviorTransition  : conditional rule for changing behavior state
NPCGoal             : a goal driving NPC action selection
LearningProfile     : accumulated knowledge about the player and world
AdvancedNPC         : an NPC with memory, personality, learning, and behavior
AdvancedAIManager   : owns all advanced NPCs, ticks updates, exposes queries
"""

from __future__ import annotations

import json
import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Constants / Enums
# ---------------------------------------------------------------------------

class NPCBehaviorState(Enum):
    """High-level behavioral states an NPC can be in."""

    IDLE = "idle"
    PATROL = "patrol"
    WORK = "work"
    REST = "rest"
    SLEEP = "sleep"
    COMBAT = "combat"
    FLEE = "flee"
    INVESTIGATE = "investigate"
    SOCIALIZE = "socialize"
    SHOP = "shop"
    TRAVEL = "travel"


class MemoryType(Enum):
    """Categories of memories an NPC can store."""

    PLAYER_ACTION = "player_action"
    WORLD_EVENT = "world_event"
    NPC_INTERACTION = "npc_interaction"
    PROMISE = "promise"
    BETRAYAL = "betrayal"
    TRADE = "trade"
    COMBAT = "combat"
    DIALOGUE = "dialogue"


class DispositionTier(Enum):
    """Numeric disposition mapped to tiers for dialogue/behavior."""

    HOSTILE = "hostile"
    UNFRIENDLY = "unfriendly"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    ALLIED = "allied"


class LearningAxis(Enum):
    """Dimensions along which NPCs learn about the player."""

    TRUST = "trust"
    FEAR = "fear"
    RESPECT = "respect"
    AFFECTION = "affection"
    ANTAGONISM = "antagonism"


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

@dataclass
class NPCMemoryEntry:
    """
    A single memory stored by an NPC.

    Attributes:
        memory_id    : unique identifier
        memory_type  : category of memory (see MemoryType)
        timestamp    : when the event occurred (ISO string)
        subject_id   : who/what triggered the memory (often the player)
        target_id    : who/what was affected
        location_id  : where it happened
        intensity    : emotional weight (negative = bad, positive = good)
        details      : free-form extra data
        decay_rate   : how quickly this memory fades per tick
        strength     : current remembered strength (0.0 .. 1.0+)
    """

    memory_id: str
    memory_type: str
    timestamp: str
    subject_id: str = ""
    target_id: str = ""
    location_id: str = ""
    intensity: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    decay_rate: float = 0.01
    strength: float = 1.0

    def age(self) -> float:
        """Return hours elapsed since the memory was formed."""
        try:
            then = datetime.fromisoformat(self.timestamp)
            now = datetime.now(UTC)
            return max((now - then).total_seconds() / 3600.0, 0.0)
        except Exception:
            return 0.0

    def decay(self, hours: float = 1.0) -> float:
        """
        Apply time-based decay. Returns the new strength.
        """
        self.strength = max(0.0, self.strength - self.decay_rate * hours)
        return self.strength

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp,
            "subject_id": self.subject_id,
            "target_id": self.target_id,
            "location_id": self.location_id,
            "intensity": self.intensity,
            "details": dict(self.details),
            "decay_rate": self.decay_rate,
            "strength": self.strength,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCMemoryEntry:
        return NPCMemoryEntry(
            memory_id=data["memory_id"],
            memory_type=data["memory_type"],
            timestamp=data.get("timestamp", ""),
            subject_id=data.get("subject_id", ""),
            target_id=data.get("target_id", ""),
            location_id=data.get("location_id", ""),
            intensity=data.get("intensity", 0.0),
            details=dict(data.get("details", {})),
            decay_rate=data.get("decay_rate", 0.01),
            strength=data.get("strength", 1.0),
        )


@dataclass
class NPCMemoryStore:
    """
    Collection of memories for a single NPC, with decay and query helpers.
    """

    npc_id: str
    memories: list[NPCMemoryEntry] = field(default_factory=list)
    max_memories: int = 200

    def add(self, memory: NPCMemoryEntry) -> None:
        self.memories.append(memory)
        # Trim oldest weak memories if over limit
        if len(self.memories) > self.max_memories:
            self.memories.sort(key=lambda m: (m.strength, m.timestamp))
            self.memories = self.memories[-self.max_memories:]

    def query(
        self,
        *,
        memory_type: str | None = None,
        subject_id: str | None = None,
        min_strength: float = 0.0,
        limit: int = 50,
    ) -> list[NPCMemoryEntry]:
        results = self.memories
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        if subject_id:
            results = [m for m in results if m.subject_id == subject_id]
        results = [m for m in results if m.strength >= min_strength]
        results.sort(key=lambda m: m.timestamp, reverse=True)
        return results[:limit]

    def strongest(self, memory_type: str | None = None, min_strength: float = 0.0, limit: int = 10) -> list[NPCMemoryEntry]:
        results = self.memories
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        results = [m for m in results if m.strength >= min_strength]
        results.sort(key=lambda m: m.strength, reverse=True)
        return results[:limit]

    def decay_all(self, hours: float = 1.0) -> None:
        for m in self.memories:
            m.decay(hours)

    def total_intensity(self, memory_type: str | None = None) -> float:
        return sum(m.intensity * m.strength for m in self.memories if memory_type is None or m.memory_type == memory_type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "memories": [m.to_dict() for m in self.memories],
            "max_memories": self.max_memories,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCMemoryStore:
        store = NPCMemoryStore(
            npc_id=data["npc_id"],
            max_memories=data.get("max_memories", 200),
        )
        store.memories = [NPCMemoryEntry.from_dict(m) for m in data.get("memories", [])]
        return store


# ---------------------------------------------------------------------------
# Personality
# ---------------------------------------------------------------------------

@dataclass
class NPCPersonality:
    """
    Mutable personality traits that shift with experience.

    Attributes:
        openness        : curiosity vs. caution
        conscientiousness: discipline vs. spontaneity
        extraversion    : sociability vs. reserve
        agreeableness   : cooperation vs. competition
        neuroticism     : emotional volatility vs. stability
        courage         : bravery vs. cowardice
        loyalty         : fidelity to allies/ideals
        morality        : ethical rigidity
    """

    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5
    courage: float = 0.5
    loyalty: float = 0.5
    morality: float = 0.5

    def adjust(self, axis: str, delta: float) -> None:
        current = getattr(self, axis, 0.5)
        setattr(self, axis, max(0.0, min(1.0, current + delta)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
            "courage": self.courage,
            "loyalty": self.loyalty,
            "morality": self.morality,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCPersonality:
        return NPCPersonality(
            openness=data.get("openness", 0.5),
            conscientiousness=data.get("conscientiousness", 0.5),
            extraversion=data.get("extraversion", 0.5),
            agreeableness=data.get("agreeableness", 0.5),
            neuroticism=data.get("neuroticism", 0.5),
            courage=data.get("courage", 0.5),
            loyalty=data.get("loyalty", 0.5),
            morality=data.get("morality", 0.5),
        )


# ---------------------------------------------------------------------------
# Behavior transitions and goals
# ---------------------------------------------------------------------------

@dataclass
class BehaviorTransition:
    """
    A conditional rule that may trigger a behavior state change.

    Attributes:
        transition_id   : unique identifier
        from_state      : source state (None = any)
        to_state        : target state
        condition       : callable taking (AdvancedNPC, dict) -> bool
        weight          : priority when multiple transitions match
        cooldown_ticks  : minimum ticks between activations
    """

    transition_id: str
    from_state: str | None
    to_state: str
    condition: Any = None  # callable
    weight: float = 1.0
    cooldown_ticks: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "weight": self.weight,
            "cooldown_ticks": self.cooldown_ticks,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> BehaviorTransition:
        return BehaviorTransition(
            transition_id=data["transition_id"],
            from_state=data.get("from_state"),
            to_state=data["to_state"],
            weight=data.get("weight", 1.0),
            cooldown_ticks=data.get("cooldown_ticks", 0),
        )


@dataclass
class NPCGoal:
    """
    A goal that drives NPC action selection.

    Attributes:
        goal_id         : unique identifier
        name            : human-readable name
        priority        : higher = more important
        active_condition: callable taking (AdvancedNPC, dict) -> bool
        satisfaction    : 0.0 (unsatisfied) .. 1.0 (complete)
        decay_per_tick  : how much satisfaction drops naturally
    """

    goal_id: str
    name: str = ""
    priority: float = 1.0
    active_condition: Any = None  # callable
    satisfaction: float = 0.0
    decay_per_tick: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "priority": self.priority,
            "satisfaction": self.satisfaction,
            "decay_per_tick": self.decay_per_tick,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCGoal:
        return NPCGoal(
            goal_id=data["goal_id"],
            name=data.get("name", ""),
            priority=data.get("priority", 1.0),
            satisfaction=data.get("satisfaction", 0.0),
            decay_per_tick=data.get("decay_per_tick", 0.0),
        )


# ---------------------------------------------------------------------------
# Learning profile
# ---------------------------------------------------------------------------

@dataclass
class LearningProfile:
    """
    Accumulated knowledge about a subject (usually the player) that
    influences NPC behavior and dialogue.
    """

    subject_id: str
    axes: dict[str, float] = field(default_factory=dict)
    observations: int = 0

    def observe(self, axis: str, delta: float) -> None:
        self.axes[axis] = self.axes.get(axis, 0.0) + delta
        self.observations += 1

    def score(self, axis: str) -> float:
        return self.axes.get(axis, 0.0)

    def dominant_axis(self) -> tuple[str, float]:
        if not self.axes:
            return ("", 0.0)
        return max(self.axes.items(), key=lambda kv: abs(kv[1]))

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "axes": dict(self.axes),
            "observations": self.observations,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LearningProfile:
        return LearningProfile(
            subject_id=data["subject_id"],
            axes=dict(data.get("axes", {})),
            observations=data.get("observations", 0),
        )


# ---------------------------------------------------------------------------
# Advanced NPC
# ---------------------------------------------------------------------------

class AdvancedNPC:
    """
    An NPC with memory, personality, learning, goals, and a behavior state
    machine.

    Attributes:
        npc_id          : unique NPC identifier
        name            : display name
        behavior_state  : current NPCBehaviorState
        personality     : mutable personality traits
        memory_store    : episodic memory
        goals           : active goals (priority-sorted)
        transitions     : available behavior transitions
        learning_profiles: what this NPC knows about other entities
        last_tick       : timestamp of last update (ISO string)
        tick_count      : number of update cycles processed
    """

    def __init__(self, npc_id: str, name: str = "") -> None:
        self.npc_id = npc_id
        self.name = name or npc_id
        self.behavior_state: NPCBehaviorState = NPCBehaviorState.IDLE
        self.personality = NPCPersonality()
        self.memory_store = NPCMemoryStore(npc_id=npc_id)
        self.goals: list[NPCGoal] = []
        self.transitions: list[BehaviorTransition] = []
        self.learning_profiles: dict[str, LearningProfile] = {}
        self.last_tick: str = datetime.now(UTC).isoformat()
        self.tick_count: int = 0
        self._transition_cooldowns: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def remember(self, memory: NPCMemoryEntry) -> None:
        self.memory_store.add(memory)

    def remember_event(
        self,
        memory_type: str,
        subject_id: str,
        intensity: float,
        target_id: str = "",
        location_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> NPCMemoryEntry:
        memory = NPCMemoryEntry(
            memory_id=str(uuid.uuid4()),
            memory_type=memory_type,
            timestamp=datetime.now(UTC).isoformat(),
            subject_id=subject_id,
            target_id=target_id,
            location_id=location_id,
            intensity=intensity,
            details=details or {},
        )
        self.remember(memory)
        return memory

    def recall(
        self,
        memory_type: str | None = None,
        subject_id: str | None = None,
        min_strength: float = 0.0,
        limit: int = 50,
    ) -> list[NPCMemoryEntry]:
        return self.memory_store.query(
            memory_type=memory_type,
            subject_id=subject_id,
            min_strength=min_strength,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Personality
    # ------------------------------------------------------------------

    def shift_personality(self, axis: str, delta: float) -> None:
        self.personality.adjust(axis, delta)

    def personality_bias(self) -> dict[str, float]:
        p = self.personality
        return {
            "aggression": (1.0 - p.agreeableness) * 0.5 + p.courage * 0.5,
            "caution": p.neuroticism * 0.6 + (1.0 - p.courage) * 0.4,
            "sociability": p.extraversion * 0.7 + p.agreeableness * 0.3,
            "initiative": p.openness * 0.5 + p.conscientiousness * 0.3 + p.courage * 0.2,
        }

    # ------------------------------------------------------------------
    # Goals
    # ------------------------------------------------------------------

    def add_goal(self, goal: NPCGoal) -> None:
        self.goals.append(goal)
        self.goals.sort(key=lambda g: g.priority, reverse=True)

    def remove_goal(self, goal_id: str) -> None:
        self.goals = [g for g in self.goals if g.goal_id != goal_id]

    def active_goals(self) -> list[NPCGoal]:
        now = datetime.now(UTC)
        active = []
        for g in self.goals:
            if g.satisfaction >= 1.0:
                continue
            if g.active_condition is None or g.active_condition(self, {}):
                active.append(g)
        return active

    def top_goal(self) -> NPCGoal | None:
        return self.active_goals()[0] if self.active_goals() else None

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------

    def get_or_create_profile(self, subject_id: str) -> LearningProfile:
        if subject_id not in self.learning_profiles:
            self.learning_profiles[subject_id] = LearningProfile(subject_id=subject_id)
        return self.learning_profiles[subject_id]

    def learn(self, subject_id: str, axis: str, delta: float) -> None:
        profile = self.get_or_create_profile(subject_id)
        profile.observe(axis, delta)

    def disposition_toward(self, subject_id: str) -> dict[str, Any]:
        profile = self.get_or_create_profile(subject_id)
        trust = profile.score(LearningAxis.TRUST.value)
        fear = profile.score(LearningAxis.FEAR.value)
        respect = profile.score(LearningAxis.RESPECT.value)
        affection = profile.score(LearningAxis.AFFECTION.value)
        antagonism = profile.score(LearningAxis.ANTAGONISM.value)

        raw = trust + respect + affection - fear - antagonism
        if raw > 5:
            tier = DispositionTier.ALLIED
        elif raw >= 2:
            tier = DispositionTier.FRIENDLY
        elif raw >= -2:
            tier = DispositionTier.NEUTRAL
        elif raw > -5:
            tier = DispositionTier.UNFRIENDLY
        else:
            tier = DispositionTier.HOSTILE

        return {
            "subject_id": subject_id,
            "tier": tier.value,
            "raw_score": raw,
            "trust": trust,
            "fear": fear,
            "respect": respect,
            "affection": affection,
            "antagonism": antagonism,
            "observations": profile.observations,
        }

    # ------------------------------------------------------------------
    # Behavior state machine
    # ------------------------------------------------------------------

    def add_transition(self, transition: BehaviorTransition) -> None:
        self.transitions.append(transition)

    def evaluate_transitions(self, context: dict[str, Any] | None = None) -> NPCBehaviorState:
        context = context or {}
        candidates: list[tuple[float, BehaviorTransition]] = []
        for t in self.transitions:
            if t.from_state is not None and t.from_state != self.behavior_state.value:
                continue
            if t.transition_id in self._transition_cooldowns:
                self._transition_cooldowns[t.transition_id] -= 1
                if self._transition_cooldowns[t.transition_id] > 0:
                    continue
            if t.condition is None or t.condition(self, context):
                candidates.append((t.weight, t))

        if not candidates:
            return self.behavior_state

        candidates.sort(key=lambda x: x[0], reverse=True)
        chosen = candidates[0][1]
        new_state = NPCBehaviorState(chosen.to_state)
        if new_state != self.behavior_state:
            self.behavior_state = new_state
            self._transition_cooldowns[chosen.transition_id] = chosen.cooldown_ticks
        return self.behavior_state

    # ------------------------------------------------------------------
    # Action selection
    # ------------------------------------------------------------------

    def choose_action(
        self,
        available_actions: list[str],
        context: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Select an action using goal priorities, personality biases, and
        recent memory salience.
        """
        context = context or {}
        if not available_actions:
            return None

        bias = self.personality_bias()
        top_goal = self.top_goal()
        recent_memories = self.memory_store.strongest(limit=5)

        scores: dict[str, float] = {a: random.uniform(0.1, 1.0) for a in available_actions}

        # Goal alignment
        if top_goal and top_goal.name:
            for action in available_actions:
                if top_goal.name.lower().replace(" ", "_") in action.lower():
                    scores[action] += top_goal.priority * 2.0

        # Personality alignment
        for action in available_actions:
            al = action.lower()
            if "attack" in al or "fight" in al:
                scores[action] += bias.get("aggression", 0.0) * 2.0
            if "flee" in al or "run" in al:
                scores[action] += bias.get("caution", 0.0) * 2.0
            if "talk" in al or "greet" in al:
                scores[action] += bias.get("sociability", 0.0) * 2.0
            if "explore" in al or "search" in al:
                scores[action] += bias.get("initiative", 0.0) * 2.0

        # Memory salience
        for memory in recent_memories:
            for action in available_actions:
                if any(
                    keyword in action.lower()
                    for keyword in memory.details.get("keywords", [])
                ):
                    scores[action] += memory.strength * memory.intensity

        # Contextual modifiers
        danger = context.get("danger_level", 0.0)
        for action in available_actions:
            if "heal" in action.lower() or "defend" in action.lower():
                scores[action] += danger * 1.5
            if "attack" in action.lower():
                scores[action] += max(0.0, 1.0 - danger) * 1.0

        best = max(scores, key=lambda a: scores[a])
        return best

    # ------------------------------------------------------------------
    # Tick / update
    # ------------------------------------------------------------------

    def tick(self, hours: float = 1.0, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Advance the NPC by a time step.

        Returns a summary of what changed.
        """
        context = context or {}
        changes: dict[str, Any] = {
            "npc_id": self.npc_id,
            "tick": self.tick_count,
            "state_before": self.behavior_state.value,
        }

        # Decay memories
        self.memory_store.decay_all(hours)

        # Decay goals
        for g in self.goals:
            g.satisfaction = max(0.0, g.satisfaction - g.decay_per_tick * hours)

        # Evaluate behavior transitions
        self.evaluate_transitions(context)

        # Remove fully satisfied goals
        self.goals = [g for g in self.goals if g.satisfaction < 1.0]

        self.last_tick = datetime.now(UTC).isoformat()
        self.tick_count += 1

        changes["state_after"] = self.behavior_state.value
        changes["active_goals"] = len(self.active_goals())
        changes["strong_memories"] = len(self.memory_store.strongest(min_strength=0.3))
        return changes

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "name": self.name,
            "behavior_state": self.behavior_state.value,
            "personality": self.personality.to_dict(),
            "memory_store": self.memory_store.to_dict(),
            "goals": [g.to_dict() for g in self.goals],
            "transitions": [t.to_dict() for t in self.transitions],
            "learning_profiles": {k: v.to_dict() for k, v in self.learning_profiles.items()},
            "last_tick": self.last_tick,
            "tick_count": self.tick_count,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AdvancedNPC:
        npc = AdvancedNPC(
            npc_id=data["npc_id"],
            name=data.get("name", ""),
        )
        npc.behavior_state = NPCBehaviorState(data.get("behavior_state", "idle"))
        npc.personality = NPCPersonality.from_dict(data.get("personality", {}))
        npc.memory_store = NPCMemoryStore.from_dict(data.get("memory_store", {}))
        npc.goals = [NPCGoal.from_dict(g) for g in data.get("goals", [])]
        npc.transitions = [BehaviorTransition.from_dict(t) for t in data.get("transitions", [])]
        for sid, pdata in data.get("learning_profiles", {}).items():
            npc.learning_profiles[sid] = LearningProfile.from_dict(pdata)
        npc.last_tick = data.get("last_tick", npc.last_tick)
        npc.tick_count = data.get("tick_count", 0)
        return npc


# ---------------------------------------------------------------------------
# Advanced AI Manager
# ---------------------------------------------------------------------------

class AdvancedAIManager:
    """
    Owns and updates all advanced NPC instances.

    Usage:
        manager = AdvancedAIManager()
        manager.register_npc(npc)
        manager.load_from_data("data/advanced_ai.json")
        summary = manager.tick_all(hours=1.0, context={...})
    """

    def __init__(self) -> None:
        self._npcs: dict[str, AdvancedNPC] = {}
        self._global_events: list[dict[str, Any]] = []

    def register_npc(self, npc: AdvancedNPC) -> None:
        self._npcs[npc.npc_id] = npc

    def get_npc(self, npc_id: str) -> AdvancedNPC | None:
        return self._npcs.get(npc_id)

    def list_npcs(self) -> list[str]:
        return list(self._npcs.keys())

    def record_event(
        self,
        npc_id: str,
        memory_type: str,
        subject_id: str,
        intensity: float,
        target_id: str = "",
        location_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        npc = self._npcs.get(npc_id)
        if npc:
            npc.remember_event(
                memory_type=memory_type,
                subject_id=subject_id,
                intensity=intensity,
                target_id=target_id,
                location_id=location_id,
                details=details,
            )

    def record_global_event(self, event: dict[str, Any]) -> None:
        self._global_events.append(event)
        # Propagate to NPCs in the same region if specified
        region = event.get("region_id", "")
        intensity = event.get("intensity", 1.0)
        for npc in self._npcs.values():
            npc_loc = ""
            # If we had location data we'd match here; for now we pass through
            npc.remember_event(
                memory_type=MemoryType.WORLD_EVENT.value,
                subject_id=event.get("event_id", "world"),
                intensity=intensity,
                location_id=npc_loc,
                details={"event": event},
            )

    def tick_all(self, hours: float = 1.0, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        summaries: dict[str, Any] = {}
        for npc_id, npc in self._npcs.items():
            summaries[npc_id] = npc.tick(hours, context)
        return summaries

    def get_disposition(self, npc_id: str, subject_id: str) -> dict[str, Any]:
        npc = self._npcs.get(npc_id)
        if not npc:
            return {"error": f"NPC '{npc_id}' not found"}
        return npc.disposition_toward(subject_id)

    def query_memories(
        self,
        npc_id: str,
        *,
        memory_type: str | None = None,
        subject_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        npc = self._npcs.get(npc_id)
        if not npc:
            return []
        return [
            m.to_dict()
            for m in npc.recall(memory_type=memory_type, subject_id=subject_id, limit=limit)
        ]

    def load_from_data(self, directory: str) -> dict[str, Any]:
        """
        Load NPC definitions from advanced_ai.json in the given directory.
        """
        path = os.path.join(directory, "advanced_ai.json")
        if not os.path.isfile(path):
            return {"loaded": 0, "error": f"File not found: {path}"}
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh) if 'json' in globals() else __import__('json').load(fh)
        except Exception as exc:
            return {"loaded": 0, "error": str(exc)}

        loaded = 0
        for entry in data:
            npc = AdvancedNPC(
                npc_id=entry["npc_id"],
                name=entry.get("name", ""),
            )
            if "behavior_state" in entry:
                npc.behavior_state = NPCBehaviorState(entry["behavior_state"])
            if "personality" in entry:
                npc.personality = NPCPersonality.from_dict(entry["personality"])
            for t_entry in entry.get("transitions", []):
                npc.add_transition(BehaviorTransition.from_dict(t_entry))
            for g_entry in entry.get("goals", []):
                npc.add_goal(NPCGoal.from_dict(g_entry))
            for sid, pdata in entry.get("learning_profiles", {}).items():
                npc.learning_profiles[sid] = LearningProfile.from_dict(pdata)
            for m_entry in entry.get("memories", []):
                npc.remember(NPCMemoryEntry.from_dict(m_entry))
            self.register_npc(npc)
            loaded += 1
        return {"loaded": loaded}

    def export_all(self) -> dict[str, Any]:
        return {npc_id: npc.to_dict() for npc_id, npc in self._npcs.items()}

    def summary(self) -> dict[str, Any]:
        return {
            "npc_count": len(self._npcs),
            "total_memories": sum(len(n.memory_store.memories) for n in self._npcs.values()),
            "total_goals": sum(len(n.goals) for n in self._npcs.values()),
            "npc_ids": list(self._npcs.keys()),
        }
