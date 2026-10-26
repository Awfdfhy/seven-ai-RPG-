"""
RPG-13-09: Advanced NPC AI

Extends the foundational AI scaffold with schedules, emotional state,
NPC-to-NPC social webs, faction reputation, and cross-system integration
(dialogue, quests, world events).

Concepts
--------
NPCSchedule       : daily time-blocked routine for an NPC
NPCEmotionalState : mutable mood metrics (stress, energy, happiness)
NPCSocialLink     : directed relationship between two NPCs
NPCRelationWeb    : social network graph for a group of NPCs
ReputationTrack   : reputation with a faction / organization
AdvancedNPC       : NPC with schedule, emotions, social links, reputation
AdvancedAIManager : orchestrator for social updates, reputation events,
                    and cross-system integration hooks
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Re-export core types from the foundational AI module so callers can use
# this module as a single import for the entire advanced NPC stack.
# ---------------------------------------------------------------------------
from advanced_ai import (  # noqa: E402
    AdvancedAIManager as _BaseAdvancedAIManager,
)
from advanced_ai import (
    AdvancedNPC as _BaseAdvancedNPC,
)
from advanced_ai import (
    BehaviorTransition,
    LearningProfile,
    MemoryType,
    NPCBehaviorState,
    NPCGoal,
    NPCMemoryEntry,
    NPCPersonality,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MoodTone(Enum):
    """High-level emotional tones an NPC can exhibit."""

    CALM = "calm"
    EXCITED = "excited"
    ANXIOUS = "anxious"
    ANGRY = "angry"
    SAD = "sad"
    JOYFUL = "joyful"
    TIRED = "tired"
    NEUTRAL = "neutral"


class ReputationStanding(Enum):
    """Faction reputation tiers."""

    HATED = "hated"
    DISLIKED = "disliked"
    NEUTRAL = "neutral"
    LIKED = "liked"
    HONORED = "honored"
    EXALTED = "exalted"


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

@dataclass
class NPCScheduleBlock:
    """
    A single time block in an NPC's daily schedule.

    Attributes:
        block_id      : unique identifier
        start_hour    : 0.0 .. 23.99 (inclusive start)
        end_hour      : 0.0 .. 23.99 (exclusive end; may wrap past 24)
        preferred_state: behavior state to favor during this block
        weight_boost  : additional weight multiplier for matching transitions
        location_id   : where the NPC should be during this block
    """

    block_id: str
    start_hour: float = 0.0
    end_hour: float = 24.0
    preferred_state: str = "idle"
    weight_boost: float = 1.0
    location_id: str = ""

    def contains_hour(self, hour: float) -> bool:
        """Return True if the given hour falls inside this block."""
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour < self.end_hour
        # Wraps midnight, e.g. 22:00 .. 02:00
        return hour >= self.start_hour or hour < self.end_hour

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "start_hour": self.start_hour,
            "end_hour": self.end_hour,
            "preferred_state": self.preferred_state,
            "weight_boost": self.weight_boost,
            "location_id": self.location_id,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCScheduleBlock:
        return NPCScheduleBlock(
            block_id=data["block_id"],
            start_hour=data.get("start_hour", 0.0),
            end_hour=data.get("end_hour", 24.0),
            preferred_state=data.get("preferred_state", "idle"),
            weight_boost=data.get("weight_boost", 1.0),
            location_id=data.get("location_id", ""),
        )


@dataclass
class NPCSchedule:
    """
    A full daily schedule composed of ordered blocks.

    Attributes:
        npc_id   : the NPC this schedule belongs to
        blocks   : ordered list of schedule blocks
        day_skip : optional list of day names the NPC rests (e.g. ["sunday"])
    """

    npc_id: str
    blocks: list[NPCScheduleBlock] = field(default_factory=list)
    day_skip: list[str] = field(default_factory=list)

    def active_block(self, hour: float, day_name: str | None = None) -> NPCScheduleBlock | None:
        """Return the active schedule block for the given hour (and day)."""
        if day_name and day_name.lower() in [d.lower() for d in self.day_skip]:
            return None
        for block in self.blocks:
            if block.contains_hour(hour):
                return block
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "blocks": [b.to_dict() for b in self.blocks],
            "day_skip": list(self.day_skip),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCSchedule:
        return NPCSchedule(
            npc_id=data["npc_id"],
            blocks=[NPCScheduleBlock.from_dict(b) for b in data.get("blocks", [])],
            day_skip=list(data.get("day_skip", [])),
        )


# ---------------------------------------------------------------------------
# Emotional state
# ---------------------------------------------------------------------------

@dataclass
class NPCEmotionalState:
    """
    Mutable mood metrics that influence NPC decisions and dialogue tone.

    Attributes:
        stress    : 0.0 (relaxed) .. 1.0 (overwhelmed)
        energy    : 0.0 (exhausted) .. 1.0 (energized)
        happiness : 0.0 (miserable) .. 1.0 (elated)
        fear      : 0.0 (fearless) .. 1.0 (terrified)
        anger     : 0.0 (serene) .. 1.0 (furious)
    """

    stress: float = 0.2
    energy: float = 0.7
    happiness: float = 0.5
    fear: float = 0.1
    anger: float = 0.1

    def dominant_tone(self) -> str:
        """Return the highest-intensity emotional tone."""
        tones = {
            "calm": max(0.0, 1.0 - self.stress - self.fear - self.anger),
            "anxious": self.stress * 0.7 + self.fear * 0.3,
            "angry": self.anger * 0.8 + (1.0 - self.happiness) * 0.2,
            "joyful": self.happiness * 0.6 + self.energy * 0.2,
            "tired": (1.0 - self.energy) * 0.8 + (1.0 - self.happiness) * 0.2,
            "excited": self.energy * 0.5 + self.happiness * 0.4,
        }
        return max(tones, key=tones.__getitem__)

    def adjust(self, axis: str, delta: float) -> None:
        current = getattr(self, axis, 0.5)
        setattr(self, axis, max(0.0, min(1.0, current + delta)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "stress": self.stress,
            "energy": self.energy,
            "happiness": self.happiness,
            "fear": self.fear,
            "anger": self.anger,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCEmotionalState:
        return NPCEmotionalState(
            stress=data.get("stress", 0.2),
            energy=data.get("energy", 0.7),
            happiness=data.get("happiness", 0.5),
            fear=data.get("fear", 0.1),
            anger=data.get("anger", 0.1),
        )


# ---------------------------------------------------------------------------
# Social web
# ---------------------------------------------------------------------------

@dataclass
class NPCSocialLink:
    """
    A directed social relationship between two NPCs.

    Attributes:
        source_id : the NPC who feels this way
        target_id : the NPC toward whom the feeling is directed
        affinity  : -1.0 (hatred) .. 1.0 (deep friendship)
        trust     : 0.0 (no trust) .. 1.0 (full trust)
        fear      : 0.0 (no fear) .. 1.0 (terrified)
        history   : short free-form summary of key shared events
    """

    source_id: str
    target_id: str
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    history: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.affinity = max(-1.0, min(1.0, float(self.affinity)))
        self.trust = max(0.0, min(1.0, float(self.trust)))
        self.fear = max(0.0, min(1.0, float(self.fear)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "affinity": self.affinity,
            "trust": self.trust,
            "fear": self.fear,
            "history": list(self.history),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCSocialLink:
        return NPCSocialLink(
            source_id=data["source_id"],
            target_id=data["target_id"],
            affinity=data.get("affinity", 0.0),
            trust=data.get("trust", 0.0),
            fear=data.get("fear", 0.0),
            history=list(data.get("history", [])),
        )


@dataclass
class NPCRelationWeb:
    """
    Collection of social links among a group of NPCs.

    Attributes:
        links : list of NPCSocialLink instances
    """

    links: list[NPCSocialLink] = field(default_factory=list)

    def get_link(self, source_id: str, target_id: str) -> NPCSocialLink | None:
        for link in self.links:
            if link.source_id == source_id and link.target_id == target_id:
                return link
        return None

    def ensure_link(
        self,
        source_id: str,
        target_id: str,
        affinity: float | None = None,
        trust: float | None = None,
        fear: float | None = None,
    ) -> NPCSocialLink:
        link = self.get_link(source_id, target_id)
        if link is None:
            link = NPCSocialLink(source_id=source_id, target_id=target_id)
            self.links.append(link)
        if affinity is not None:
            link.affinity = affinity
        if trust is not None:
            link.trust = trust
        if fear is not None:
            link.fear = fear
        return link

    def remove_link(self, source_id: str, target_id: str) -> None:
        self.links = [
            l for l in self.links
            if not (l.source_id == source_id and l.target_id == target_id)
        ]

    def neighbors(self, npc_id: str) -> list[str]:
        """Return IDs of NPCs that share any link with npc_id."""
        return list({l.target_id for l in self.links if l.source_id == npc_id} |
                    {l.source_id for l in self.links if l.target_id == npc_id})

    def to_dict(self) -> dict[str, Any]:
        return {"links": [l.to_dict() for l in self.links]}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NPCRelationWeb:
        web = NPCRelationWeb()
        web.links = [NPCSocialLink.from_dict(l) for l in data.get("links", [])]
        return web


# ---------------------------------------------------------------------------
# Reputation
# ---------------------------------------------------------------------------

@dataclass
class ReputationTrack:
    """
    Tracks reputation with a faction or organization.

    Attributes:
        faction_id   : unique faction identifier
        name         : display name
        standing     : current reputation tier
        points       : raw reputation points
        decay_per_day: natural point decay per in-game day
        history      : list of recent reputation event summaries
    """

    faction_id: str
    name: str = ""
    standing: str = ReputationStanding.NEUTRAL.value
    points: float = 0.0
    decay_per_day: float = 0.5
    history: list[str] = field(default_factory=list)

    def add_points(self, delta: float, reason: str = "") -> None:
        self.points += delta
        if reason:
            self.history.append(reason)
        if len(self.history) > 50:
            self.history = self.history[-50:]
        self._update_standing()

    def _update_standing(self) -> None:
        p = self.points
        if p >= 500:
            self.standing = ReputationStanding.EXALTED.value
        elif p >= 200:
            self.standing = ReputationStanding.HONORED.value
        elif p >= 50:
            self.standing = ReputationStanding.LIKED.value
        elif p > -50:
            self.standing = ReputationStanding.NEUTRAL.value
        elif p > -200:
            self.standing = ReputationStanding.DISLIKED.value
        else:
            self.standing = ReputationStanding.HATED.value

    def decay(self, days: float = 1.0) -> None:
        self.points = max(-999.0, self.points - self.decay_per_day * days)
        self._update_standing()

    def to_dict(self) -> dict[str, Any]:
        return {
            "faction_id": self.faction_id,
            "name": self.name,
            "standing": self.standing,
            "points": self.points,
            "decay_per_day": self.decay_per_day,
            "history": list(self.history),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ReputationTrack:
        return ReputationTrack(
            faction_id=data["faction_id"],
            name=data.get("name", ""),
            standing=data.get("standing", ReputationStanding.NEUTRAL.value),
            points=data.get("points", 0.0),
            decay_per_day=data.get("decay_per_day", 0.5),
            history=list(data.get("history", [])),
        )


# ---------------------------------------------------------------------------
# Advanced NPC (RPG-13-09 extension)
# ---------------------------------------------------------------------------

class AdvancedNPC(_BaseAdvancedNPC):
    """
    Extended NPC with schedule, emotional state, social links, and reputation.

    In addition to the base attributes, an RPG-13-09 NPC tracks:

        schedule        : daily routine
        emotional_state : current mood / emotional metrics
        social_links    : outward-facing social links (managed by RelationWeb)
        reputation      : faction reputations owned by this NPC
    """

    def __init__(self, npc_id: str, name: str = "") -> None:
        super().__init__(npc_id=npc_id, name=name)
        self.schedule = NPCSchedule(npc_id=npc_id)
        self.emotional_state = NPCEmotionalState()
        # social_links is a view managed externally by RelationWeb; we keep
        # a local cache for quick per-NPC access.
        self._social_links: list[NPCSocialLink] = []
        self.reputation: dict[str, ReputationTrack] = {}

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------

    def add_schedule_block(self, block: NPCScheduleBlock) -> None:
        self.schedule.blocks.append(block)
        self.schedule.blocks.sort(key=lambda b: b.start_hour)

    def get_active_schedule_block(
        self, hour: float, day_name: str | None = None
    ) -> NPCScheduleBlock | None:
        return self.schedule.active_block(hour, day_name)

    # ------------------------------------------------------------------
    # Emotional state
    # ------------------------------------------------------------------

    def set_emotion(self, axis: str, value: float) -> None:
        self.emotional_state.adjust(axis, value - getattr(self.emotional_state, axis, 0.5))

    def shift_emotion(self, axis: str, delta: float) -> None:
        self.emotional_state.adjust(axis, delta)

    def mood_tone(self) -> str:
        return self.emotional_state.dominant_tone()

    # ------------------------------------------------------------------
    # Social links (local cache; RelationWeb is the source of truth)
    # ------------------------------------------------------------------

    def refresh_social_links(self, web: NPCRelationWeb) -> None:
        self._social_links = [
            link for link in web.links if link.source_id == self.npc_id
        ]

    def social_links(self) -> list[NPCSocialLink]:
        return list(self._social_links)

    def get_social_link(self, target_id: str) -> NPCSocialLink | None:
        for link in self._social_links:
            if link.target_id == target_id:
                return link
        return None

    # ------------------------------------------------------------------
    # Reputation
    # ------------------------------------------------------------------

    def get_or_create_reputation(self, faction_id: str, name: str = "") -> ReputationTrack:
        if faction_id not in self.reputation:
            self.reputation[faction_id] = ReputationTrack(faction_id=faction_id, name=name)
        return self.reputation[faction_id]

    def add_reputation(
        self,
        faction_id: str,
        delta: float,
        reason: str = "",
        name: str = "",
        decay_per_day: float = 0.0,
    ) -> ReputationTrack:
        track = self.get_or_create_reputation(faction_id, name=name)
        track.decay_per_day = decay_per_day
        track.add_points(delta, reason=reason)
        return track

    def reputation_toward(self, faction_id: str) -> dict[str, Any]:
        if faction_id not in self.reputation:
            return {
                "faction_id": faction_id,
                "standing": ReputationStanding.NEUTRAL.value,
                "points": 0.0,
                "observations": 0,
            }
        track = self.reputation[faction_id]
        return {
            "faction_id": faction_id,
            "standing": track.standing,
            "points": track.points,
            "observations": len(track.history),
        }

    # ------------------------------------------------------------------
    # Tick / update
    # ------------------------------------------------------------------

    def record_event(
        self,
        memory_type: str,
        subject_id: str = "",
        intensity: float = 0.0,
        target_id: str = "",
        location_id: str = "",
        details: str = "",
    ) -> None:
        """Apply immediate emotional side-effects for a recorded event."""
        if memory_type == MemoryType.PLAYER_ACTION.value:
            if intensity > 2.0:
                self.shift_emotion("happiness", 0.1 * intensity)
                self.shift_emotion("stress", -0.05 * intensity)
            elif intensity < -1.0:
                self.shift_emotion("stress", 0.15 * abs(intensity))
                self.shift_emotion("fear", 0.1 * abs(intensity))
        elif memory_type == MemoryType.COMBAT.value:
            self.shift_emotion("stress", 0.2 * abs(intensity))
            self.shift_emotion("energy", -0.1 * abs(intensity))
        elif memory_type == MemoryType.TRADE.value:
            self.shift_emotion("happiness", 0.05 * intensity)

    def tick(
        self,
        hours: float = 1.0,
        context: dict[str, Any] | None = None,
        current_hour: float | None = None,
        day_name: str | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        changes: dict[str, Any] = super().tick(hours, context)

        # Schedule-aware state boosting
        if current_hour is not None:
            block = self.get_active_schedule_block(current_hour, day_name)
            if block is not None:
                if block.preferred_state and block.preferred_state != self.behavior_state.value:
                    # Nudge transition weights in evaluate_transitions by boosting
                    # matching transitions during scheduled blocks.
                    for t in self.transitions:
                        if t.to_state == block.preferred_state:
                            t.weight *= block.weight_boost
                changes["schedule_block"] = block.to_dict()

        # Emotional decay
        self.emotional_state.stress = max(0.0, self.emotional_state.stress - 0.02 * hours)
        self.emotional_state.energy = max(0.0, min(1.0,
            self.emotional_state.energy + 0.01 * hours - 0.005 * hours))
        self.emotional_state.happiness = max(0.0, min(1.0,
            self.emotional_state.happiness - 0.005 * hours))
        self.emotional_state.fear = max(0.0, self.emotional_state.fear - 0.03 * hours)
        self.emotional_state.anger = max(0.0, self.emotional_state.anger - 0.04 * hours)

        # Reputation decay
        for track in self.reputation.values():
            track.decay(days=hours / 24.0)

        changes["mood_tone"] = self.mood_tone()
        changes["emotional_state"] = self.emotional_state.to_dict()
        changes["reputation"] = {
            k: v.to_dict() for k, v in self.reputation.items()
        }
        return changes

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["schedule"] = self.schedule.to_dict()
        data["emotional_state"] = self.emotional_state.to_dict()
        data["reputation"] = {k: v.to_dict() for k, v in self.reputation.items()}
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AdvancedNPC:
        npc = AdvancedNPC.__new__(AdvancedNPC)
        npc.__dict__.update(_BaseAdvancedNPC.from_dict(data).__dict__)
        npc.schedule = NPCSchedule.from_dict(data.get("schedule", {}))
        npc.emotional_state = NPCEmotionalState.from_dict(
            data.get("emotional_state", {})
        )
        npc.reputation = {
            k: ReputationTrack.from_dict(v)
            for k, v in data.get("reputation", {}).items()
        }
        npc._social_links = []
        return npc


# ---------------------------------------------------------------------------
# Advanced AI Manager (RPG-13-09 extension)
# ---------------------------------------------------------------------------

class AdvancedAIManager(_BaseAdvancedAIManager):
    """
    Extended manager that coordinates schedules, social webs, reputation,
    and cross-system integration hooks.
    """

    def __init__(self) -> None:
        super().__init__()
        self._relation_web = NPCRelationWeb()
        self._faction_reputation: dict[str, ReputationTrack] = {}
        self._global_schedules: dict[str, NPCSchedule] = {}
        self._dialogue_manager: Any = None
        self._quest_journal: Any = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_npc(self, npc: AdvancedNPC) -> None:  # type: ignore[override]
        super().register_npc(npc)
        self._relation_web.links.extend(npc._social_links)
        if npc.npc_id not in self._global_schedules:
            self._global_schedules[npc.npc_id] = npc.schedule

    def get_npc(self, npc_id: str) -> AdvancedNPC | None:  # type: ignore[override]
        return self._npcs.get(npc_id)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Cross-system integration
    # ------------------------------------------------------------------

    def set_dialogue_manager(self, dialogue_manager: Any) -> None:
        """Attach a DialogueManager for memory-driven dialogue filtering."""
        self._dialogue_manager = dialogue_manager

    def set_quest_journal(self, quest_journal: Any) -> None:
        """Attach a QuestJournal for goal-driven behavior."""
        self._quest_journal = quest_journal

    # ------------------------------------------------------------------
    # Social web
    # ------------------------------------------------------------------

    def set_social_link(
        self,
        source_id: str,
        target_id: str,
        affinity: float = 0.0,
        trust: float = 0.0,
        fear: float = 0.0,
        history: str | None = None,
    ) -> NPCSocialLink:
        link = self._relation_web.ensure_link(source_id, target_id)
        link.affinity = max(-1.0, min(1.0, affinity))
        link.trust = max(0.0, min(1.0, trust))
        link.fear = max(0.0, min(1.0, fear))
        if history:
            link.history.append(history)
            if len(link.history) > 20:
                link.history = link.history[-20:]
        # Mirror into NPC local caches
        source_npc = self._npcs.get(source_id)
        if source_npc:
            source_npc.refresh_social_links(self._relation_web)
        return link

    def remove_social_link(self, source_id: str, target_id: str) -> None:
        self._relation_web.remove_link(source_id, target_id)
        source_npc = self._npcs.get(source_id)
        if source_npc:
            source_npc.refresh_social_links(self._relation_web)

    def get_relation_web(self) -> NPCRelationWeb:
        return self._relation_web

    def get_npc_neighbors(self, npc_id: str) -> list[str]:
        return self._relation_web.neighbors(npc_id)

    # ------------------------------------------------------------------
    # Faction reputation
    # ------------------------------------------------------------------

    def add_faction_reputation(
        self,
        npc_id: str,
        faction_id: str,
        delta: float,
        reason: str = "",
        faction_name: str = "",
    ) -> dict[str, Any]:
        npc = self._npcs.get(npc_id)
        if not npc:
            return {"error": f"NPC '{npc_id}' not found"}

        track = npc.add_reputation(faction_id, delta, reason=reason, name=faction_name)
        return {
            "npc_id": npc_id,
            "faction_id": faction_id,
            "standing": track.standing,
            "points": track.points,
        }

    def get_faction_standing(self, npc_id: str, faction_id: str) -> dict[str, Any]:
        npc = self._npcs.get(npc_id)
        if not npc:
            return {"error": f"NPC '{npc_id}' not found"}
        return npc.reputation_toward(faction_id)

    # ------------------------------------------------------------------
    # Event propagation with schedule and emotion awareness
    # ------------------------------------------------------------------

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
        details = dict(details or {})
        npc = self._npcs.get(npc_id)
        if npc:
            # Emotional side-effects
            if memory_type == MemoryType.PLAYER_ACTION.value:
                if intensity > 2.0:
                    npc.shift_emotion("happiness", 0.1 * intensity)
                    npc.shift_emotion("stress", -0.05 * intensity)
                elif intensity < -1.0:
                    npc.shift_emotion("stress", 0.15 * abs(intensity))
                    npc.shift_emotion("fear", 0.1 * abs(intensity))
            elif memory_type == MemoryType.COMBAT.value:
                npc.shift_emotion("stress", 0.2 * abs(intensity))
                npc.shift_emotion("energy", -0.1 * abs(intensity))
            elif memory_type == MemoryType.TRADE.value:
                npc.shift_emotion("happiness", 0.05 * intensity)
        super().record_event(
            npc_id=npc_id,
            memory_type=memory_type,
            subject_id=subject_id,
            intensity=intensity,
            target_id=target_id,
            location_id=location_id,
            details=details,
        )

    # ------------------------------------------------------------------
    # Tick all with schedule context
    # ------------------------------------------------------------------

    def tick_all(
        self,
        hours: float = 1.0,
        context: dict[str, Any] | None = None,
        current_hour: float | None = None,
        day_name: str | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        summaries: dict[str, Any] = {}
        for npc_id, npc in self._npcs.items():
            summaries[npc_id] = npc.tick(
                hours,
                context,
                current_hour=current_hour,
                day_name=day_name,
            )
        return summaries

    # ------------------------------------------------------------------
    # Load / export
    # ------------------------------------------------------------------

    def load_from_data(self, directory: str) -> dict[str, Any]:
        base_result = super().load_from_data(directory)
        loaded = base_result.get("loaded", 0)
        # Attempt to load RPG-13-09 extended data if present
        ext_path = os.path.join(directory, "advanced_npc_ai.json")
        if os.path.isfile(ext_path):
            try:
                with open(ext_path, encoding="utf-8") as fh:
                    ext_data = json.load(fh)
                for entry in ext_data:
                    npc_id = entry.get("npc_id")
                    npc = self._npcs.get(npc_id)
                    if not npc:
                        continue
                    # Schedule
                    sched_data = entry.get("schedule")
                    if sched_data:
                        npc.schedule = NPCSchedule.from_dict(sched_data)
                        self._global_schedules[npc_id] = npc.schedule
                    # Emotional state
                    emo_data = entry.get("emotional_state")
                    if emo_data:
                        npc.emotional_state = NPCEmotionalState.from_dict(emo_data)
                    # Reputation
                    rep_data = entry.get("reputation", {})
                    for fid, rdata in rep_data.items():
                        npc.reputation[fid] = ReputationTrack.from_dict(rdata)
                    # Social links
                    for link_data in entry.get("social_links", []):
                        self.set_social_link(
                            link_data["source_id"],
                            link_data["target_id"],
                            affinity=link_data.get("affinity", 0.0),
                            trust=link_data.get("trust", 0.0),
                            fear=link_data.get("fear", 0.0),
                            history=link_data.get("history", [""])[0] if link_data.get("history") else "",
                        )
                    loaded += 1
            except Exception:
                pass
        return {"loaded": loaded}

    def export_all(self) -> dict[str, Any]:
        base = super().export_all()
        for npc_id, npc in self._npcs.items():
            if isinstance(npc, AdvancedNPC):
                base[npc_id] = npc.to_dict()
        return base

    def summary(self) -> dict[str, Any]:
        base = super().summary()
        base["relation_web_links"] = len(self._relation_web.links)
        base["faction_reputations"] = len(self._faction_reputation)
        return base


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def build_npc_from_definition(definition: dict[str, Any]) -> AdvancedNPC:
    """
    Build an AdvancedNPC from a JSON-ready definition dict (as found in
    advanced_ai.json or advanced_npc_ai.json).
    """
    npc = AdvancedNPC(
        npc_id=definition["npc_id"],
        name=definition.get("name", ""),
    )
    if "behavior_state" in definition:
        npc.behavior_state = NPCBehaviorState(definition["behavior_state"])
    if "personality" in definition:
        npc.personality = NPCPersonality.from_dict(definition["personality"])
    for t_entry in definition.get("transitions", []):
        npc.add_transition(BehaviorTransition.from_dict(t_entry))
    for g_entry in definition.get("goals", []):
        npc.add_goal(NPCGoal.from_dict(g_entry))
    for sid, pdata in definition.get("learning_profiles", {}).items():
        npc.learning_profiles[sid] = LearningProfile.from_dict(pdata)
    for m_entry in definition.get("memories", []):
        npc.remember(NPCMemoryEntry.from_dict(m_entry))
    # RPG-13-09 extensions
    sched_data = definition.get("schedule")
    if sched_data:
        npc.schedule = NPCSchedule.from_dict(sched_data)
    emo_data = definition.get("emotional_state")
    if emo_data:
        npc.emotional_state = NPCEmotionalState.from_dict(emo_data)
    for fid, rdata in definition.get("reputation", {}).items():
        npc.reputation[fid] = ReputationTrack.from_dict(rdata)
    for link_data in definition.get("social_links", []):
        npc._social_links.append(NPCSocialLink.from_dict(link_data))
    return npc
