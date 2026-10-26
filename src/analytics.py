"""
RPG-12-10: Analytics System
Tracks gameplay events and computes aggregated metrics across sessions,
worlds, and characters. Designed for telemetry, balance analysis, and
player behavior insights.

Event categories
----------------
- session
- quest
- loot
- crafting
- economy
- skill
- minigame
- status
- progression
- travel
- ability
- npc
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Event type enum
# ---------------------------------------------------------------------------

class EventType:
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    QUEST_STARTED = "quest_started"
    QUEST_COMPLETED = "quest_completed"
    QUEST_FAILED = "quest_failed"
    QUEST_ABANDONED = "quest_abandoned"
    LOOT_ROLLED = "loot_rolled"
    CRAFTING_ATTEMPTED = "crafting_attempted"
    CRAFTING_COMPLETED = "crafting_completed"
    TRANSACTION_COMPLETED = "transaction_completed"
    SKILL_UNLOCKED = "skill_unlocked"
    SKILL_REFUNDED = "skill_refunded"
    MINIGAME_PLAYED = "minigame_played"
    STATUS_APPLIED = "status_applied"
    STATUS_EXPIRED = "status_expired"
    LEVEL_UP = "level_up"
    TRAVEL_EVENT = "travel_event"
    ABILITY_USED = "ability_used"
    NPC_INTERACTION = "npc_interaction"


# ---------------------------------------------------------------------------
# Event record
# ---------------------------------------------------------------------------

@dataclass
class GameplayEvent:
    """
    A single atomic gameplay event recorded for analytics.

    Attributes:
        event_id      : unique identifier
        event_type    : one of the EventType constants
        world_id      : world this event belongs to
        session_id    : optional session identifier
        character_id  : optional character identifier
        occurred_at   : ISO timestamp
        data          : event-specific payload
        metadata      : opaque extra fields
    """

    event_type: str
    world_id: str = ""
    session_id: str | None = None
    character_id: str | None = None
    occurred_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "world_id": self.world_id,
            "session_id": self.session_id,
            "character_id": self.character_id,
            "occurred_at": self.occurred_at,
            "data": dict(self.data),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> GameplayEvent:
        return GameplayEvent(
            event_id=data["event_id"],
            event_type=data["event_type"],
            world_id=data.get("world_id", ""),
            session_id=data.get("session_id"),
            character_id=data.get("character_id"),
            occurred_at=data.get("occurred_at", ""),
            data=dict(data.get("data", {})),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Metric snapshot
# ---------------------------------------------------------------------------

@dataclass
class AnalyticsMetric:
    """
    An aggregated metric computed from gameplay events.

    Attributes:
        metric_id   : unique identifier
        metric_name : human-readable name
        world_id    : scope
        session_id  : optional session scope
        character_id: optional character scope
        value       : numeric value
        category    : metric category (progression, economy, etc.)
        computed_at : ISO timestamp
        metadata    : extra context
    """

    metric_name: str
    value: float
    world_id: str = ""
    session_id: str | None = None
    character_id: str | None = None
    category: str = "general"
    computed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metric_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "metric_name": self.metric_name,
            "world_id": self.world_id,
            "session_id": self.session_id,
            "character_id": self.character_id,
            "value": self.value,
            "category": self.category,
            "computed_at": self.computed_at,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AnalyticsMetric:
        return AnalyticsMetric(
            metric_id=data["metric_id"],
            metric_name=data["metric_name"],
            world_id=data.get("world_id", ""),
            session_id=data.get("session_id"),
            character_id=data.get("character_id"),
            value=float(data.get("value", 0)),
            category=data.get("category", "general"),
            computed_at=data.get("computed_at", ""),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class AnalyticsManager:
    """
    Records gameplay events and computes aggregated metrics.

    Typical usage:
        am = AnalyticsManager()
        am.record_event(GameplayEvent(event_type=EventType.LEVEL_UP, ...))
        am.record_event(GameplayEvent(event_type=EventType.LOOT_ROLLED, ...))
        summary = am.get_world_summary(world_id)
    """

    def __init__(self) -> None:
        self._events: dict[str, GameplayEvent] = {}
        self._metrics: dict[str, AnalyticsMetric] = {}
        self._world_events: dict[str, set[str]] = {}
        self._session_events: dict[str, set[str]] = {}
        self._character_events: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_event(self, event: GameplayEvent) -> GameplayEvent:
        """
        Store a gameplay event and index it by world, session, and character.
        """
        self._events[event.event_id] = event
        self._world_events.setdefault(event.world_id, set()).add(event.event_id)
        if event.session_id:
            self._session_events.setdefault(event.session_id, set()).add(event.event_id)
        if event.character_id:
            self._character_events.setdefault(event.character_id, set()).add(event.event_id)
        return event

    def record_metric(self, metric: AnalyticsMetric) -> AnalyticsMetric:
        """
        Store a computed metric.
        """
        self._metrics[metric.metric_id] = metric
        return metric

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_event(self, event_id: str) -> GameplayEvent | None:
        return self._events.get(event_id)

    def get_events(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
        character_id: str | None = None,
        event_type: str | None = None,
        limit: int = 200,
    ) -> list[GameplayEvent]:
        events = list(self._events.values())
        if world_id is not None:
            events = [e for e in events if e.world_id == world_id]
        if session_id is not None:
            events = [e for e in events if e.session_id == session_id]
        if character_id is not None:
            events = [e for e in events if e.character_id == character_id]
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        events.sort(key=lambda e: e.occurred_at, reverse=True)
        return events[:limit]

    def get_metric(self, metric_id: str) -> AnalyticsMetric | None:
        return self._metrics.get(metric_id)

    def get_metrics(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
        character_id: str | None = None,
        category: str | None = None,
        limit: int = 200,
    ) -> list[AnalyticsMetric]:
        metrics = list(self._metrics.values())
        if world_id is not None:
            metrics = [m for m in metrics if m.world_id == world_id]
        if session_id is not None:
            metrics = [m for m in metrics if m.session_id == session_id]
        if character_id is not None:
            metrics = [m for m in metrics if m.character_id == character_id]
        if category is not None:
            metrics = [m for m in metrics if m.category == category]
        metrics.sort(key=lambda m: m.computed_at, reverse=True)
        return metrics[:limit]

    # ------------------------------------------------------------------
    # Aggregated reports
    # ------------------------------------------------------------------

    def get_world_summary(self, world_id: str) -> dict[str, Any]:
        """
        Compute a gameplay summary for a world.

        Includes session count, event counts by category, top characters
        by activity, and aggregate economic figures.
        """
        events = self.get_events(world_id=world_id, limit=10_000)
        event_type_counts = Counter(e.event_type for e in events)

        # Character activity
        character_event_counts: Counter = Counter()
        for e in events:
            if e.character_id:
                character_event_counts[e.character_id] += 1

        # Sessions
        session_ids = {e.session_id for e in events if e.session_id}
        session_count = len(session_ids)

        # Economic events
        tx_events = [e for e in events if e.event_type == EventType.TRANSACTION_COMPLETED]
        total_gold_spent = sum(e.data.get("total_price", 0) for e in tx_events if e.data.get("transaction_type") == "buy")
        total_gold_earned = sum(e.data.get("total_price", 0) for e in tx_events if e.data.get("transaction_type") == "sell")

        # Level-ups
        level_ups = event_type_counts.get(EventType.LEVEL_UP, 0)

        # Quests
        quests_completed = event_type_counts.get(EventType.QUEST_COMPLETED, 0)
        quests_failed = event_type_counts.get(EventType.QUEST_FAILED, 0)

        # Loot
        loot_rolls = event_type_counts.get(EventType.LOOT_ROLLED, 0)
        rarity_breakdown = Counter()
        for e in events:
            if e.event_type == EventType.LOOT_ROLLED:
                for item in e.data.get("items", []):
                    rarity_breakdown[item.get("rarity", "common")] += item.get("quantity", 1)

        # Mini-games
        minigames_played = event_type_counts.get(EventType.MINIGAME_PLAYED, 0)
        minigame_wins = sum(
            1 for e in events
            if e.event_type == EventType.MINIGAME_PLAYED and e.data.get("success")
        )

        # Crafting
        crafting_completed = event_type_counts.get(EventType.CRAFTING_COMPLETED, 0)

        # Status conditions
        status_applied = event_type_counts.get(EventType.STATUS_APPLIED, 0)

        return {
            "world_id": world_id,
            "total_events": len(events),
            "session_count": session_count,
            "event_type_counts": dict(event_type_counts),
            "top_characters_by_activity": [
                {"character_id": cid, "event_count": count}
                for cid, count in character_event_counts.most_common(10)
            ],
            "economy": {
                "total_transactions": len(tx_events),
                "total_gold_spent": total_gold_spent,
                "total_gold_earned": total_gold_earned,
                "net_gold": total_gold_earned - total_gold_spent,
            },
            "progression": {
                "total_level_ups": level_ups,
            },
            "quests": {
                "completed": quests_completed,
                "failed": quests_failed,
                "completion_rate": quests_completed / max(1, quests_completed + quests_failed),
            },
            "loot": {
                "total_rolls": loot_rolls,
                "rarity_breakdown": dict(rarity_breakdown),
            },
            "minigames": {
                "played": minigames_played,
                "won": minigame_wins,
                "win_rate": minigame_wins / max(1, minigames_played),
            },
            "crafting": {
                "completed": crafting_completed,
            },
            "status": {
                "applied": status_applied,
            },
        }

    def get_character_summary(self, world_id: str, character_id: str) -> dict[str, Any]:
        """
        Compute a gameplay summary for a single character within a world.
        """
        events = self.get_events(world_id=world_id, character_id=character_id, limit=10_000)
        event_type_counts = Counter(e.event_type for e in events)

        # Level-ups
        level_ups = event_type_counts.get(EventType.LEVEL_UP, 0)

        # Quests
        quests_completed = event_type_counts.get(EventType.QUEST_COMPLETED, 0)
        quests_failed = event_type_counts.get(EventType.QUEST_FAILED, 0)

        # Loot
        loot_events = [e for e in events if e.event_type == EventType.LOOT_ROLLED]
        rarity_breakdown = Counter()
        for e in loot_events:
            for item in e.data.get("items", []):
                rarity_breakdown[item.get("rarity", "common")] += item.get("quantity", 1)

        # Transactions
        tx_events = [e for e in events if e.event_type == EventType.TRANSACTION_COMPLETED]
        total_gold_spent = sum(e.data.get("total_price", 0) for e in tx_events if e.data.get("transaction_type") == "buy")
        total_gold_earned = sum(e.data.get("total_price", 0) for e in tx_events if e.data.get("transaction_type") == "sell")

        # Skills
        skills_unlocked = event_type_counts.get(EventType.SKILL_UNLOCKED, 0)

        # Mini-games
        minigame_events = [e for e in events if e.event_type == EventType.MINIGAME_PLAYED]
        minigame_wins = sum(1 for e in minigame_events if e.data.get("success"))

        # Crafting
        crafting_completed = event_type_counts.get(EventType.CRAFTING_COMPLETED, 0)

        # Status
        status_applied = event_type_counts.get(EventType.STATUS_APPLIED, 0)

        # Abilities
        abilities_used = event_type_counts.get(EventType.ABILITY_USED, 0)

        return {
            "world_id": world_id,
            "character_id": character_id,
            "total_events": len(events),
            "event_type_counts": dict(event_type_counts),
            "progression": {
                "total_level_ups": level_ups,
            },
            "quests": {
                "completed": quests_completed,
                "failed": quests_failed,
                "completion_rate": quests_completed / max(1, quests_completed + quests_failed),
            },
            "loot": {
                "total_rolls": len(loot_events),
                "rarity_breakdown": dict(rarity_breakdown),
            },
            "economy": {
                "total_transactions": len(tx_events),
                "total_gold_spent": total_gold_spent,
                "total_gold_earned": total_gold_earned,
                "net_gold": total_gold_earned - total_gold_spent,
            },
            "skills": {
                "unlocked": skills_unlocked,
            },
            "minigames": {
                "played": len(minigame_events),
                "won": minigame_wins,
                "win_rate": minigame_wins / max(1, len(minigame_events)),
            },
            "crafting": {
                "completed": crafting_completed,
            },
            "status": {
                "applied": status_applied,
            },
            "abilities": {
                "used": abilities_used,
            },
        }

    def get_session_summary(self, world_id: str, session_id: str) -> dict[str, Any]:
        """
        Compute a gameplay summary for a single session.
        """
        events = self.get_events(world_id=world_id, session_id=session_id, limit=10_000)
        event_type_counts = Counter(e.event_type for e in events)

        character_ids = {e.character_id for e in events if e.character_id}
        active_characters = len(character_ids)

        # Duration from first to last event
        if events:
            sorted_events = sorted(events, key=lambda e: e.occurred_at)
            first = sorted_events[0].occurred_at
            last = sorted_events[-1].occurred_at
            duration_seconds = (
                datetime.fromisoformat(last) - datetime.fromisoformat(first)
            ).total_seconds()
        else:
            duration_seconds = 0.0

        # Top character in session
        character_event_counts: Counter = Counter()
        for e in events:
            if e.character_id:
                character_event_counts[e.character_id] += 1
        top_character = character_event_counts.most_common(1)[0] if character_event_counts else None

        return {
            "world_id": world_id,
            "session_id": session_id,
            "total_events": len(events),
            "active_characters": active_characters,
            "duration_seconds": duration_seconds,
            "event_type_counts": dict(event_type_counts),
            "top_character": {
                "character_id": top_character[0],
                "event_count": top_character[1],
            } if top_character else None,
        }

    def get_event_type_breakdown(self, world_id: str | None = None, limit: int = 50) -> dict[str, int]:
        """
        Return event type counts, optionally filtered by world.
        """
        events = self.get_events(world_id=world_id, limit=10_000)
        return dict(Counter(e.event_type for e in events).most_common(limit))

    def get_rarity_distribution(self, world_id: str) -> dict[str, int]:
        """
        Aggregate loot rarity counts for a world.
        """
        events = self.get_events(world_id=world_id, event_type=EventType.LOOT_ROLLED, limit=10_000)
        breakdown: Counter = Counter()
        for e in events:
            for item in e.data.get("items", []):
                breakdown[item.get("rarity", "common")] += item.get("quantity", 1)
        return dict(breakdown)

    def get_progression_timeline(
        self, world_id: str, character_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Return a timeline of level-up events.
        """
        events = self.get_events(
            world_id=world_id,
            character_id=character_id,
            event_type=EventType.LEVEL_UP,
            limit=10_000,
        )
        timeline = []
        for e in events:
            timeline.append({
                "event_id": e.event_id,
                "character_id": e.character_id,
                "new_level": e.data.get("new_level"),
                "occurred_at": e.occurred_at,
                "skill_points_gained": e.data.get("skill_points_gained"),
                "ability_points_gained": e.data.get("ability_points_gained"),
                "stat_points_gained": e.data.get("stat_points_gained"),
            })
        timeline.sort(key=lambda x: x["occurred_at"])
        return timeline

    def get_economy_timeline(
        self, world_id: str, character_id: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        """
        Return a timeline of transaction events.
        """
        events = self.get_events(
            world_id=world_id,
            character_id=character_id,
            event_type=EventType.TRANSACTION_COMPLETED,
            limit=limit,
        )
        timeline = []
        for e in events:
            timeline.append({
                "event_id": e.event_id,
                "character_id": e.character_id,
                "transaction_type": e.data.get("transaction_type"),
                "item_id": e.data.get("item_id"),
                "quantity": e.data.get("quantity"),
                "unit_price": e.data.get("unit_price"),
                "total_price": e.data.get("total_price"),
                "occurred_at": e.occurred_at,
            })
        timeline.sort(key=lambda x: x["occurred_at"], reverse=True)
        return timeline

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "events": {eid: e.to_dict() for eid, e in self._events.items()},
            "metrics": {mid: m.to_dict() for mid, m in self._metrics.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._events.clear()
        self._metrics.clear()
        self._world_events.clear()
        self._session_events.clear()
        self._character_events.clear()

        for eid, edata in state.get("events", {}).items():
            event = GameplayEvent.from_dict(edata)
            self._events[eid] = event
            self._world_events.setdefault(event.world_id, set()).add(eid)
            if event.session_id:
                self._session_events.setdefault(event.session_id, set()).add(eid)
            if event.character_id:
                self._character_events.setdefault(event.character_id, set()).add(eid)

        for mid, mdata in state.get("metrics", {}).items():
            self._metrics[mid] = AnalyticsMetric.from_dict(mdata)
