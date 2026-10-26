"""
Tests for the analytics and metrics system.
"""

from __future__ import annotations

import pytest

from analytics import AnalyticsManager, AnalyticsMetric, EventType, GameplayEvent


class TestGameplayEvent:
    def test_to_dict_roundtrip(self):
        event = GameplayEvent(
            event_type=EventType.LEVEL_UP,
            world_id="world-1",
            session_id="sess-1",
            character_id="char-1",
            data={"new_level": 5, "skill_points_gained": 1},
        )
        d = event.to_dict()
        restored = GameplayEvent.from_dict(d)
        assert restored.event_type == event.event_type
        assert restored.world_id == event.world_id
        assert restored.session_id == event.session_id
        assert restored.character_id == event.character_id
        assert restored.data == event.data
        assert restored.event_id == event.event_id


class TestAnalyticsMetric:
    def test_to_dict_roundtrip(self):
        metric = AnalyticsMetric(
            metric_name="test_metric",
            value=42.5,
            world_id="world-1",
            category="progression",
            metadata={"source": "unit_test"},
        )
        d = metric.to_dict()
        restored = AnalyticsMetric.from_dict(d)
        assert restored.metric_name == metric.metric_name
        assert restored.value == pytest.approx(metric.value)
        assert restored.world_id == metric.world_id
        assert restored.category == metric.category
        assert restored.metadata == metric.metadata


class TestAnalyticsManager:
    def test_record_and_retrieve_event(self):
        manager = AnalyticsManager()
        event = GameplayEvent(event_type=EventType.QUEST_COMPLETED, world_id="w1")
        manager.record_event(event)
        assert manager.get_event(event.event_id) == event

    def test_record_and_retrieve_metric(self):
        manager = AnalyticsManager()
        metric = AnalyticsMetric(metric_name="m", value=1.0)
        manager.record_metric(metric)
        assert manager.get_metric(metric.metric_id) == metric

    def test_get_events_filters(self):
        manager = AnalyticsManager()
        e1 = GameplayEvent(event_type=EventType.LEVEL_UP, world_id="w1", character_id="c1")
        e2 = GameplayEvent(event_type=EventType.LOOT_ROLLED, world_id="w2", character_id="c1")
        e3 = GameplayEvent(event_type=EventType.LEVEL_UP, world_id="w1", character_id="c2")
        manager.record_event(e1)
        manager.record_event(e2)
        manager.record_event(e3)

        world_events = manager.get_events(world_id="w1")
        assert len(world_events) == 2
        assert all(e.world_id == "w1" for e in world_events)

        char_events = manager.get_events(character_id="c1")
        assert len(char_events) == 2

        type_events = manager.get_events(event_type=EventType.LEVEL_UP)
        assert len(type_events) == 2

    def test_world_summary_basic(self):
        manager = AnalyticsManager()
        manager.record_event(GameplayEvent(event_type=EventType.LEVEL_UP, world_id="w1", data={"new_level": 2}))
        manager.record_event(GameplayEvent(event_type=EventType.LEVEL_UP, world_id="w1", data={"new_level": 3}))
        manager.record_event(GameplayEvent(event_type=EventType.QUEST_COMPLETED, world_id="w1"))
        manager.record_event(GameplayEvent(event_type=EventType.QUEST_FAILED, world_id="w1"))
        manager.record_event(
            GameplayEvent(
                event_type=EventType.TRANSACTION_COMPLETED,
                world_id="w1",
                data={"transaction_type": "buy", "total_price": 100},
            )
        )
        manager.record_event(
            GameplayEvent(
                event_type=EventType.TRANSACTION_COMPLETED,
                world_id="w1",
                data={"transaction_type": "sell", "total_price": 200},
            )
        )

        summary = manager.get_world_summary("w1")
        assert summary["progression"]["total_level_ups"] == 2
        assert summary["quests"]["completed"] == 1
        assert summary["quests"]["failed"] == 1
        assert summary["economy"]["total_gold_spent"] == 100
        assert summary["economy"]["total_gold_earned"] == 200
        assert summary["economy"]["net_gold"] == 100

    def test_character_summary_basic(self):
        manager = AnalyticsManager()
        manager.record_event(GameplayEvent(event_type=EventType.SKILL_UNLOCKED, world_id="w1", character_id="c1"))
        manager.record_event(GameplayEvent(event_type=EventType.ABILITY_USED, world_id="w1", character_id="c1"))
        summary = manager.get_character_summary("w1", "c1")
        assert summary["skills"]["unlocked"] == 1
        assert summary["abilities"]["used"] == 1

    def test_session_summary_basic(self):
        manager = AnalyticsManager()
        manager.record_event(GameplayEvent(event_type=EventType.LEVEL_UP, world_id="w1", session_id="s1", character_id="c1"))
        manager.record_event(GameplayEvent(event_type=EventType.LOOT_ROLLED, world_id="w1", session_id="s1", character_id="c2"))
        summary = manager.get_session_summary("w1", "s1")
        assert summary["total_events"] == 2
        assert summary["active_characters"] == 2

    def test_export_import_state(self):
        manager = AnalyticsManager()
        manager.record_event(GameplayEvent(event_type=EventType.LEVEL_UP, world_id="w1"))
        manager.record_metric(AnalyticsMetric(metric_name="m", value=7.0, world_id="w1"))
        state = manager.export_state()
        new_manager = AnalyticsManager()
        new_manager.import_state(state)
        assert len(new_manager._events) == 1
        assert len(new_manager._metrics) == 1
