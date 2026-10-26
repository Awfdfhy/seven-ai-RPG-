"""
Tests for RPG-12-02: Dynamic World Events
Run with: python -m pytest tests/ -v
or:       python tests/test_world_events.py
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from world_events import (
    EventCategory,
    EventStatus,
    EventTrigger,
    WorldEventDefinition,
    WorldEventInstance,
    WorldEventManager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_definitions() -> list[WorldEventDefinition]:
    return [
        WorldEventDefinition(
            id="wolf_pack_hunt",
            name="Wolf Pack on the Hunt",
            description="A hungry wolf pack stalks the roads.",
            category=EventCategory.RANDOM,
            triggers=[
                EventTrigger(trigger_type="time_of_day", hours=[20, 21, 22, 23]),
                EventTrigger(trigger_type="location", location_ids=["oakhaven_outskirts"]),
            ],
            narration="Howls pierce the night around {location_name}.",
            effects=[{"type": "danger_increase", "amount": 2}],
            follow_up_events=["wolf_alpha_appears"],
            duration_hours=6,
            metadata={"rarity": "common", "min_level": 2},
        ),
        WorldEventDefinition(
            id="wolf_alpha_appears",
            name="The Alpha Rises",
            description="The alpha wolf appears.",
            category=EventCategory.STORY,
            triggers=[
                EventTrigger(trigger_type="after_event", event_id="wolf_pack_hunt", probability=1.0),
            ],
            narration="The alpha wolf steps from the shadows.",
            effects=[{"type": "spawn_enemy", "enemy_type": "wolf_alpha"}],
            follow_up_events=[],
            duration_hours=3,
            metadata={"rarity": "uncommon", "min_level": 3},
        ),
        WorldEventDefinition(
            id="festival_night",
            name="Village Festival",
            description="A festival is tonight.",
            category=EventCategory.WORLD,
            triggers=[
                EventTrigger(trigger_type="random_chance", weight=0.3),
                EventTrigger(trigger_type="location", location_types=["village"]),
                EventTrigger(trigger_type="time_of_day", hours=[17, 18, 19]),
            ],
            narration="Lanterns glow over {location_name}.",
            effects=[{"type": "gold_bonus", "amount": 50}],
            follow_up_events=[],
            duration_hours=6,
            metadata={"rarity": "uncommon", "min_level": 1},
        ),
    ]


def _make_manager(tmp_data_dir: str | None = None) -> WorldEventManager:
    mgr = WorldEventManager(data_directory=tmp_data_dir or "")
    mgr.load_definitions(_sample_definitions())
    return mgr


# ---------------------------------------------------------------------------
# Definition tests
# ---------------------------------------------------------------------------

class TestWorldEventDefinition(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "id": "test_event",
            "name": "Test Event",
            "description": "A test event.",
            "category": EventCategory.RANDOM,
            "triggers": [{"type": "random_chance", "weight": 0.5}],
            "narration": "Something happens.",
            "effects": [{"type": "gold_bonus", "amount": 10}],
            "follow_up_events": ["follow_up_1"],
            "duration_hours": 4,
            "metadata": {"rarity": "common"},
        }
        d = WorldEventDefinition.from_dict(data)
        self.assertEqual(d.id, "test_event")
        self.assertEqual(d.category, EventCategory.RANDOM)
        self.assertEqual(len(d.triggers), 1)
        self.assertEqual(d.triggers[0].weight, 0.5)
        self.assertEqual(d.duration_hours, 4)
        self.assertEqual(d.follow_up_events, ["follow_up_1"])

    def test_to_dict_roundtrip(self):
        d = _sample_definitions()[0]
        data = d.to_dict()
        d2 = WorldEventDefinition.from_dict(data)
        self.assertEqual(d.id, d2.id)
        self.assertEqual(d.name, d2.name)
        self.assertEqual(len(d.triggers), len(d2.triggers))
        self.assertEqual(d.duration_hours, d2.duration_hours)


class TestEventTrigger(unittest.TestCase):
    def test_from_dict(self):
        t = EventTrigger.from_dict({
            "type": "time_of_day",
            "hours": [9, 17, 20],
            "location_ids": ["loc_a"],
            "location_types": ["village"],
            "region_ids": ["reg_a"],
            "condition": "rain",
            "min_intensity": "moderate",
            "weight": 0.5,
            "min_level": 3,
            "probability": 0.7,
            "event_id": "evt_1",
            "milestone_id": "ms_1",
        })
        self.assertEqual(t.trigger_type, "time_of_day")
        self.assertEqual(t.hours, [9, 17, 20])
        self.assertEqual(t.location_ids, ["loc_a"])
        self.assertEqual(t.weight, 0.5)
        self.assertEqual(t.probability, 0.7)

    def test_to_dict_roundtrip(self):
        t = EventTrigger(
            trigger_type="weather",
            condition="rain",
            min_intensity="heavy",
            weight=1.5,
        )
        data = t.to_dict()
        t2 = EventTrigger.from_dict(data)
        self.assertEqual(t.trigger_type, t2.trigger_type)
        self.assertEqual(t.condition, t2.condition)
        self.assertEqual(t.min_intensity, t2.min_intensity)


# ---------------------------------------------------------------------------
# Instance tests
# ---------------------------------------------------------------------------

class TestWorldEventInstance(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "instance_id": "inst_1",
            "definition_id": "evt_1",
            "world_id": "world_1",
            "session_id": "sess_1",
            "status": EventStatus.ACTIVE,
            "triggered_at": "2024-01-01T00:00:00+00:00",
            "expires_at": "2024-01-01T06:00:00+00:00",
            "effects_applied": [{"type": "gold_bonus", "amount": 10}],
            "trigger_context": {"current_location_id": "loc_a"},
            "metadata": {"key": "val"},
        }
        inst = WorldEventInstance.from_dict(data)
        self.assertEqual(inst.instance_id, "inst_1")
        self.assertEqual(inst.status, EventStatus.ACTIVE)
        self.assertEqual(len(inst.effects_applied), 1)

    def test_to_dict_roundtrip(self):
        inst = WorldEventInstance(
            instance_id="inst_x",
            definition_id="evt_x",
            world_id="world_x",
            session_id="sess_x",
            status=EventStatus.ACTIVE,
            trigger_context={"loc": "a"},
            metadata={"k": "v"},
        )
        data = inst.to_dict()
        inst2 = WorldEventInstance.from_dict(data)
        self.assertEqual(inst.instance_id, inst2.instance_id)
        self.assertEqual(inst.status, inst2.status)


# ---------------------------------------------------------------------------
# Manager tests
# ---------------------------------------------------------------------------

class TestWorldEventManager(unittest.TestCase):
    def setUp(self):
        self.mgr = _make_manager()

    def test_load_definitions_from_data_file(self):
        # Default data dir should load world_events.json
        mgr = WorldEventManager()
        # At least our 10 events should be loaded
        defs = mgr.list_definitions()
        self.assertGreaterEqual(len(defs), 10)

    def test_list_definitions(self):
        defs = self.mgr.list_definitions()
        self.assertEqual(len(defs), 3)

    def test_list_definitions_filter_category(self):
        defs = self.mgr.list_definitions(category=EventCategory.RANDOM)
        self.assertEqual(len(defs), 1)
        self.assertEqual(defs[0]["id"], "wolf_pack_hunt")

    def test_trigger_event_manual(self):
        inst = self.mgr.trigger_event(
            "wolf_pack_hunt", "world_1",
            session_id="sess_1",
            trigger_context={"current_location_id": "oakhaven_outskirts"},
        )
        self.assertIsNotNone(inst)
        self.assertEqual(inst.status, EventStatus.ACTIVE)
        self.assertEqual(inst.world_id, "world_1")
        self.assertEqual(inst.session_id, "sess_1")

    def test_trigger_event_unknown_returns_none(self):
        inst = self.mgr.trigger_event("nonexistent", "world_1")
        self.assertIsNone(inst)

    def test_get_instance(self):
        inst = self.mgr.trigger_event("wolf_pack_hunt", "world_1")
        found = self.mgr.get_instance(inst.instance_id)
        self.assertEqual(found.definition_id, "wolf_pack_hunt")

    def test_get_active_events(self):
        self.mgr.trigger_event("wolf_pack_hunt", "world_1")
        active = self.mgr.get_active_events("world_1")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["definition"]["id"], "wolf_pack_hunt")

    def test_get_events_for_location(self):
        self.mgr.trigger_event("wolf_pack_hunt", "world_1",
                               trigger_context={"current_location_id": "oakhaven_outskirts"})
        events = self.mgr.get_events_for_location("world_1", "oakhaven_outskirts")
        self.assertEqual(len(events), 1)
        # Different location should return empty
        events_other = self.mgr.get_events_for_location("world_1", "other_loc")
        self.assertEqual(len(events_other), 0)

    def test_resolve_event(self):
        inst = self.mgr.trigger_event("wolf_pack_hunt", "world_1")
        result = self.mgr.resolve_event(inst.instance_id, status=EventStatus.RESOLVED)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, EventStatus.RESOLVED)
        active = self.mgr.get_active_events("world_1")
        self.assertEqual(len(active), 0)

    def test_resolve_event_unknown_returns_none(self):
        result = self.mgr.resolve_event("nonexistent")
        self.assertIsNone(result)

    def test_narration_hooks(self):
        inst = self.mgr.trigger_event("wolf_pack_hunt", "world_1")
        hooks = self.mgr.get_narration_hooks("world_1")
        self.assertEqual(len(hooks), 1)
        self.assertIn("howls", hooks[0]["text"].lower())

    def test_world_effects_aggregation(self):
        self.mgr.trigger_event("wolf_pack_hunt", "world_1")
        effects = self.mgr.get_world_effects("world_1")
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["type"], "danger_increase")

    def test_cooldown_prevents_repeat(self):
        # Trigger the same event twice in quick succession
        inst1 = self.mgr.trigger_event("wolf_pack_hunt", "world_1")
        inst2 = self.mgr.trigger_event("wolf_pack_hunt", "world_1")
        # Second trigger should be blocked by cooldown — but manual trigger
        # bypasses cooldown. Let's test via evaluate_triggers.
        ctx = {
            "current_hour": 21,
            "current_location_id": "oakhaven_outskirts",
            "party_level": 5,
            "current_day": 1,
            "action": "arrival",
        }
        instances = self.mgr.check_and_trigger("world_1", ctx)
        # Should not trigger because cooldown is active (day 1)
        self.assertEqual(len(instances), 0)

    def test_trigger_after_cooldown_expires(self):
        # First trigger manually
        inst = self.mgr.trigger_event("wolf_pack_hunt", "world_1")
        # Simulate 4 days passing by updating cooldown directly
        self.mgr._cooldowns.setdefault("world_1", {})["wolf_pack_hunt"] = -3
        ctx = {
            "current_hour": 21,
            "current_location_id": "oakhaven_outskirts",
            "party_level": 5,
            "current_day": 4,
            "action": "arrival",
        }
        instances = self.mgr.check_and_trigger("world_1", ctx)
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].definition_id, "wolf_pack_hunt")

    def test_event_chaining(self):
        inst = self.mgr.trigger_event("wolf_pack_hunt", "world_1")
        chained = self.mgr.try_chain(inst.instance_id)
        # wolf_alpha_appears should chain with probability 1.0 (since we set it)
        self.assertIsNotNone(chained)
        self.assertEqual(chained.definition_id, "wolf_alpha_appears")
        self.assertEqual(chained.metadata.get("chained_from"), inst.instance_id)

    def test_event_chain_probability_filter(self):
        # wolf_alpha_appears has probability 1.0 in our sample, but if we
        # test with a lower probability event that doesn't match, no chain.
        # festival_night has no follow_up_events, so it won't chain.
        inst = self.mgr.trigger_event("festival_night", "world_1")
        chained = self.mgr.try_chain(inst.instance_id)
        self.assertIsNone(chained)

    def test_tick_expires_events(self):
        # Create an event with a very short duration
        mgr = WorldEventManager(data_directory="")
        d = WorldEventDefinition(
            id="quick_event",
            name="Quick",
            category=EventCategory.AMBIENT,
            triggers=[EventTrigger(trigger_type="random_chance", weight=0.0)],
            narration="Quick.",
            effects=[],
            duration_hours=1,
        )
        mgr.register_definition(d)
        ctx = {"current_day": 1, "party_level": 1}
        inst = mgr.trigger_event("quick_event", "world_1", trigger_context={
            "triggered_hour": 10,
            "current_day": 1,
        })
        self.assertEqual(inst.status, EventStatus.ACTIVE)
        # Tick with hour = 12 (2 hours after triggered_hour=10, duration=1)
        expired = mgr.tick("world_1", current_hour=12, current_day=1)
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0]["instance_id"], inst.instance_id)
        self.assertEqual(expired[0]["status"], EventStatus.EXPIRED)

    def test_list_instances_with_filters(self):
        self.mgr.trigger_event("wolf_pack_hunt", "world_1", session_id="sess_1")
        self.mgr.trigger_event("wolf_pack_hunt", "world_2", session_id="sess_2")

        # Filter by world
        w1 = self.mgr.list_instances(world_id="world_1")
        self.assertEqual(len(w1), 1)
        self.assertEqual(w1[0]["definition"]["id"], "wolf_pack_hunt")

        # Filter by session
        s1 = self.mgr.list_instances(session_id="sess_1")
        self.assertEqual(len(s1), 1)

        # Filter by status
        active = self.mgr.list_instances(status=EventStatus.ACTIVE)
        self.assertEqual(len(active), 2)

    def test_export_import_state(self):
        self.mgr.trigger_event("wolf_pack_hunt", "world_1",
                               trigger_context={"loc": "a"})
        state = self.mgr.export_state()
        self.assertIn("events", state)
        self.assertIn("cooldowns", state)

        mgr2 = WorldEventManager(data_directory="")
        mgr2.load_definitions(_sample_definitions())
        mgr2.import_state(state)
        self.assertEqual(len(mgr2._events), 1)
        self.assertEqual(len(mgr2._world_events.get("world_1", set())), 1)

    def test_definition_serialization_does_not_mutate_original(self):
        d = _sample_definitions()[0]
        original_effects = copy.deepcopy(d.effects)
        data = d.to_dict()
        data["effects"][0]["amount"] = 99999
        # Original should be unchanged
        self.assertEqual(d.effects[0]["amount"], original_effects[0]["amount"])


class TestWorldEventTriggerEvaluation(unittest.TestCase):
    def setUp(self):
        self.mgr = _make_manager()

    def test_time_of_day_match(self):
        d = self.mgr.get_definition("wolf_pack_hunt")
        ctx = {"current_hour": 21, "current_location_id": "oakhaven_outskirts"}
        self.assertTrue(self.mgr.evaluate_triggers("world_1", d, ctx))

    def test_time_of_day_miss(self):
        d = self.mgr.get_definition("wolf_pack_hunt")
        ctx = {"current_hour": 6, "current_location_id": "oakhaven_outskirts"}
        self.assertFalse(self.mgr.evaluate_triggers("world_1", d, ctx))

    def test_location_match(self):
        d = self.mgr.get_definition("wolf_pack_hunt")
        ctx = {"current_hour": 21, "current_location_id": "oakhaven_outskirts"}
        self.assertTrue(self.mgr.evaluate_triggers("world_1", d, ctx))

    def test_location_miss(self):
        d = self.mgr.get_definition("wolf_pack_hunt")
        ctx = {"current_hour": 21, "current_location_id": "some_other_place"}
        self.assertFalse(self.mgr.evaluate_triggers("world_1", d, ctx))

    def test_random_chance_fires(self):
        d = WorldEventDefinition(
            id="always_fire",
            name="Always Fire",
            category=EventCategory.RANDOM,
            triggers=[EventTrigger(trigger_type="random_chance", weight=1.0, min_level=1)],
            narration="Fires.",
            effects=[],
        )
        # With weight=1.0, random chance is always <= 1.0
        ctx = {"party_level": 1, "current_day": 1}
        self.assertTrue(self.mgr.evaluate_triggers("world_1", d, ctx))

    def test_random_chance_level_requirement(self):
        d = WorldEventDefinition(
            id="high_level_event",
            name="High Level",
            category=EventCategory.RANDOM,
            triggers=[EventTrigger(trigger_type="random_chance", weight=1.0, min_level=10)],
            narration="Fires.",
            effects=[],
        )
        ctx = {"party_level": 1, "current_day": 1}
        self.assertFalse(self.mgr.evaluate_triggers("world_1", d, ctx))

    def test_after_event_trigger(self):
        d = self.mgr.get_definition("wolf_alpha_appears")
        ctx = {"triggering_event_id": "wolf_pack_hunt", "current_day": 1}
        self.assertTrue(self.mgr.evaluate_triggers("world_1", d, ctx))

    def test_after_event_mismatch(self):
        d = self.mgr.get_definition("wolf_alpha_appears")
        ctx = {"triggering_event_id": "wrong_event", "current_day": 1}
        self.assertFalse(self.mgr.evaluate_triggers("world_1", d, ctx))

    def test_all_triggers_must_match(self):
        d = self.mgr.get_definition("wolf_pack_hunt")
        # Match time but miss location
        ctx = {"current_hour": 21, "current_location_id": "wrong_place"}
        self.assertFalse(self.mgr.evaluate_triggers("world_1", d, ctx))

    def test_check_and_trigger_returns_list(self):
        ctx = {
            "current_hour": 17,
            "current_location_id": "oakhaven_village",
            "current_location_type": "village",
            "party_level": 1,
            "current_day": 1,
            "action": "arrival",
        }
        # Should trigger festival_night (time + location_type match)
        instances = self.mgr.check_and_trigger("world_1", ctx)
        self.assertGreaterEqual(len(instances), 1)
        ids = [i.definition_id for i in instances]
        self.assertIn("festival_night", ids)


class TestWorldEventsIntegration(unittest.TestCase):
    """Integration tests that exercise persistence and bridge patterns."""

    def test_persistence_roundtrip(self):
        mgr = _make_manager()
        inst = mgr.trigger_event("wolf_pack_hunt", "world_1",
                                 trigger_context={"current_location_id": "oakhaven_outskirts"})
        state = mgr.export_state()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": 1, "world_events": state}, f)
            tmp_path = f.name

        try:
            mgr2 = WorldEventManager(data_directory="")
            mgr2.load_definitions(_sample_definitions())
            mgr2.import_state(state)

            # Verify event restored
            active = mgr2.get_active_events("world_1")
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["definition"]["id"], "wolf_pack_hunt")
            self.assertEqual(active[0]["trigger_context"]["current_location_id"], "oakhaven_outskirts")
        finally:
            os.unlink(tmp_path)

    def test_bridge_trigger_and_query(self):
        from world_bridge import WorldBridge
        bridge = WorldBridge()
        result = bridge.trigger_world_event(
            "wolf_pack_hunt", "world_bridge_test",
            session_id="sess_bridge",
            trigger_context={"current_location_id": "oakhaven_outskirts"},
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["definition"]["id"], "wolf_pack_hunt")

        active = bridge.get_active_world_events("world_bridge_test")
        self.assertEqual(len(active), 1)

        hooks = bridge.get_world_event_narration("world_bridge_test")
        self.assertGreaterEqual(len(hooks), 1)

        resolved = bridge.resolve_world_event(result["instance_id"], status="resolved")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["status"], "resolved")

    def test_bridge_check_triggers(self):
        from world_bridge import WorldBridge
        bridge = WorldBridge()
        ctx = {
            "current_hour": 18,
            "current_location_id": "oakhaven_village",
            "current_location_type": "village",
            "party_level": 1,
            "current_day": 1,
            "action": "arrival",
        }
        results = bridge.check_world_event_triggers("world_bridge_test", ctx)
        # festival_night should fire (18 is in hours [17, 18, 19] and type is village)
        ids = [r["definition"]["id"] for r in results]
        self.assertIn("festival_night", ids)

    def test_persistence_full_roundtrip_with_bridge(self):
        from world_bridge import WorldBridge
        from world_persistence import WorldPersistence

        bridge = WorldBridge()
        bridge.trigger_world_event("wolf_pack_hunt", "persist_world",
                                   trigger_context={"current_location_id": "oakhaven_outskirts"})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            persistence = WorldPersistence(
                library=bridge.library,
                sessions=bridge.sessions,
                milestones=bridge.milestones,
                world_events=bridge.world_events,
            )
            save_result = persistence.save(tmp_path)
            self.assertTrue(save_result["success"])
            self.assertEqual(save_result["world_events"], 1)

            # Load into fresh state
            bridge2 = WorldBridge()
            persistence2 = WorldPersistence(
                library=bridge2.library,
                sessions=bridge2.sessions,
                milestones=bridge2.milestones,
                world_events=bridge2.world_events,
            )
            load_result = persistence2.load(tmp_path)
            self.assertTrue(load_result["success"])
            self.assertEqual(load_result["world_events"], 1)

            active = bridge2.get_active_world_events("persist_world")
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["definition"]["id"], "wolf_pack_hunt")
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
