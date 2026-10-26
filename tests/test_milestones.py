"""
Tests for RPG Milestone System.
Run with: python -m pytest tests/ -v
or:       python tests/test_milestones.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from milestone import (
    MilestoneDefinition,
    MilestoneEvent,
    MilestoneManager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_definitions() -> list[MilestoneDefinition]:
    return [
        MilestoneDefinition(
            id="village_guard_completed",
            name="Oakhaven Secured",
            description="The wolves have been driven off.",
            category="story",
            prerequisites=[],
            world_effects=[
                {"type": "npc_reaction_modifier", "target": "oakhaven_villagers", "modifier": 10},
                {"type": "unlock_region", "region": "oakhaven_outskirts"},
            ],
            narration_hooks=[
                {
                    "scope": "region",
                    "target": "oakhaven",
                    "template": "The people of Oakhaven breathe easier now.",
                }
            ],
            metadata={"difficulty": "easy"},
        ),
        MilestoneDefinition(
            id="artifact_retrieved",
            name="Ancient Knowledge Restored",
            description="The artifact was recovered.",
            category="story",
            prerequisites=["village_guard_completed"],
            world_effects=[{"type": "unlock_region", "region": "whispering_caves"}],
            narration_hooks=[],
            metadata={"difficulty": "medium"},
        ),
        MilestoneDefinition(
            id="dragon_defeated",
            name="The Dragon's Fall",
            description="The dragon was slain.",
            category="story",
            prerequisites=["artifact_retrieved"],
            world_effects=[
                {"type": "world_flag", "flag": "dragon_threat_ended", "value": True},
            ],
            narration_hooks=[
                {
                    "scope": "region",
                    "target": "northern_pass",
                    "template": "Trade resumes along the Northern Pass.",
                }
            ],
            metadata={"difficulty": "hard"},
        ),
        MilestoneDefinition(
            id="shadow_mastery",
            name="Master of Shadows",
            description="Mastered stealth.",
            category="character",
            prerequisites=[],
            world_effects=[{"type": "character_buff", "stat": "stealth", "value": 15}],
            narration_hooks=[],
            metadata={"difficulty": "hard"},
        ),
    ]


def _make_manager() -> MilestoneManager:
    mgr = MilestoneManager(data_directory="")
    mgr.load_definitions(_sample_definitions())
    return mgr


# ---------------------------------------------------------------------------
# Definition tests
# ---------------------------------------------------------------------------

class TestMilestoneDefinition(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "id": "test",
            "name": "Test Milestone",
            "description": "A test milestone.",
            "category": "story",
            "prerequisites": ["pre1"],
            "world_effects": [{"type": "unlock_region", "region": "test"}],
            "narration_hooks": [{"scope": "global", "target": "world", "template": "Hello"}],
            "metadata": {"difficulty": "easy"},
        }
        d = MilestoneDefinition.from_dict(data)
        assert d.id == "test"
        assert d.category == "story"
        assert d.prerequisites == ["pre1"]
        assert len(d.world_effects) == 1
        assert len(d.narration_hooks) == 1

    def test_to_dict(self):
        d = MilestoneDefinition(
            id="test",
            name="Test",
            description="desc",
            category="character",
            world_effects=[{"type": "buff"}],
            narration_hooks=[{"scope": "region", "target": "r", "template": "t"}],
            prerequisites=["a"],
            metadata={"key": "val"},
        )
        data = d.to_dict()
        assert data["id"] == "test"
        assert data["category"] == "character"
        assert len(data["world_effects"]) == 1
        assert len(data["narration_hooks"]) == 1
        assert data["prerequisites"] == ["a"]
        assert data["metadata"] == {"key": "val"}

    def test_to_from_dict_roundtrip(self):
        original = MilestoneDefinition(
            id="rt",
            name="Roundtrip",
            description="desc",
            world_effects=[{"type": "unlock", "region": "x"}],
            narration_hooks=[{"scope": "global", "target": "world", "template": "ok"}],
            prerequisites=["p"],
            metadata={"m": 1},
        )
        restored = MilestoneDefinition.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.category == original.category
        assert restored.world_effects == original.world_effects
        assert restored.narration_hooks == original.narration_hooks
        assert restored.prerequisites == original.prerequisites
        assert restored.metadata == original.metadata


# ---------------------------------------------------------------------------
# Event tests
# ---------------------------------------------------------------------------

class TestMilestoneEvent(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "event_id": "evt-1",
            "milestone_id": "ms-1",
            "world_id": "w-1",
            "triggered_at": "2024-01-01T00:00:00+00:00",
            "session_id": "s-1",
            "status": "achieved",
            "effects_applied": [{"type": "unlock_region"}],
            "metadata": {"source": "quest"},
        }
        e = MilestoneEvent.from_dict(data)
        assert e.event_id == "evt-1"
        assert e.milestone_id == "ms-1"
        assert e.world_id == "w-1"
        assert e.status == "achieved"
        assert len(e.effects_applied) == 1

    def test_to_dict(self):
        e = MilestoneEvent(
            event_id="evt-1",
            milestone_id="ms-1",
            world_id="w-1",
            triggered_at="2024-01-01T00:00:00+00:00",
            session_id="s-1",
            status="failed",
            effects_applied=[{"type": "buff"}],
            metadata={"reason": "timeout"},
        )
        data = e.to_dict()
        assert data["event_id"] == "evt-1"
        assert data["status"] == "failed"
        assert len(data["effects_applied"]) == 1
        assert data["metadata"]["reason"] == "timeout"

    def test_to_from_dict_roundtrip(self):
        original = MilestoneEvent(
            event_id="evt-1",
            milestone_id="ms-1",
            world_id="w-1",
            triggered_at="2024-01-01T00:00:00+00:00",
            session_id="s-1",
            status="achieved",
            effects_applied=[{"type": "unlock"}],
            metadata={"k": "v"},
        )
        restored = MilestoneEvent.from_dict(original.to_dict())
        assert restored.event_id == original.event_id
        assert restored.milestone_id == original.milestone_id
        assert restored.world_id == original.world_id
        assert restored.status == original.status
        assert restored.effects_applied == original.effects_applied
        assert restored.metadata == original.metadata


# ---------------------------------------------------------------------------
# Manager tests
# ---------------------------------------------------------------------------

class TestMilestoneManager(unittest.TestCase):
    def test_trigger_no_prereqs(self):
        mgr = _make_manager()
        event = mgr.trigger_milestone("village_guard_completed", world_id="w1")
        assert event is not None
        assert event.status == "achieved"
        assert event.world_id == "w1"
        assert event.milestone_id == "village_guard_completed"

    def test_trigger_with_prereqs_met(self):
        mgr = _make_manager()
        mgr.trigger_milestone("village_guard_completed", world_id="w1")
        event = mgr.trigger_milestone("artifact_retrieved", world_id="w1")
        assert event is not None
        assert event.status == "achieved"

    def test_trigger_prereqs_not_met(self):
        mgr = _make_manager()
        event = mgr.trigger_milestone("artifact_retrieved", world_id="w1")
        assert event is None

    def test_trigger_unknown_returns_none(self):
        mgr = _make_manager()
        assert mgr.trigger_milestone("nonexistent", world_id="w1") is None

    def test_trigger_already_triggered(self):
        mgr = _make_manager()
        e1 = mgr.trigger_milestone("village_guard_completed", world_id="w1")
        e2 = mgr.trigger_milestone("village_guard_completed", world_id="w1")
        assert e1 is not None
        assert e2 is not None
        assert e1.event_id == e2.event_id

    def test_list_events_scoped(self):
        mgr = _make_manager()
        mgr.trigger_milestone("village_guard_completed", world_id="w1")
        mgr.trigger_milestone("shadow_mastery", world_id="w2")
        assert len(mgr.list_events(world_id="w1")) == 1
        assert len(mgr.list_events(world_id="w2")) == 1
        assert len(mgr.list_events()) == 2

    def test_list_events_status_filter(self):
        mgr = _make_manager()
        mgr.trigger_milestone("village_guard_completed", world_id="w1")
        mgr.trigger_milestone("shadow_mastery", world_id="w1")
        mgr.fail_milestone(mgr.get_world_milestone_event("shadow_mastery", "w1").event_id, reason="rules")
        assert len(mgr.list_achieved(world_id="w1")) == 1
        assert len(mgr.list_failed(world_id="w1")) == 1

    def test_fail_milestone(self):
        mgr = _make_manager()
        event = mgr.trigger_milestone("village_guard_completed", world_id="w1")
        result = mgr.fail_milestone(event.event_id, reason="Time ran out")
        assert result is not None
        assert result.status == "failed"
        assert "Time ran out" in result.metadata.get("failure_reasons", [])

    def test_fail_already_failed_returns_none(self):
        mgr = _make_manager()
        event = mgr.trigger_milestone("village_guard_completed", world_id="w1")
        mgr.fail_milestone(event.event_id)
        assert mgr.fail_milestone(event.event_id) is None

    def test_fail_missing_returns_none(self):
        mgr = _make_manager()
        assert mgr.fail_milestone("missing-evt") is None

    def test_get_event(self):
        mgr = _make_manager()
        event = mgr.trigger_milestone("village_guard_completed", world_id="w1")
        fetched = mgr.get_event(event.event_id)
        assert fetched is not None
        assert fetched.event_id == event.event_id
        assert mgr.get_event("missing") is None

    def test_get_world_milestone_event(self):
        mgr = _make_manager()
        mgr.trigger_milestone("village_guard_completed", world_id="w1")
        event = mgr.get_world_milestone_event("village_guard_completed", "w1")
        assert event is not None
        assert event.world_id == "w1"
        assert mgr.get_world_milestone_event("shadow_mastery", "w1") is None

    def test_world_effects_aggregation(self):
        mgr = _make_manager()
        mgr.trigger_milestone("village_guard_completed", world_id="w1")
        mgr.trigger_milestone("shadow_mastery", world_id="w1")
        effects = mgr.get_world_effects("w1")
        assert len(effects) == 3  # 2 from village_guard + 1 from shadow_mastery

    def test_get_narration_hooks(self):
        mgr = _make_manager()
        mgr.trigger_milestone("village_guard_completed", world_id="w1")
        hooks = mgr.get_narration_hooks("w1")
        assert len(hooks) == 1
        assert hooks[0]["scope"] == "region"
        assert hooks[0]["target"] == "oakhaven"

    def test_get_narration_hooks_filtered_by_scope(self):
        mgr = _make_manager()
        mgr.trigger_milestone("village_guard_completed", world_id="w1")
        mgr.trigger_milestone("artifact_retrieved", world_id="w1")
        mgr.trigger_milestone("dragon_defeated", world_id="w1")
        hooks = mgr.get_narration_hooks("w1", scope="region")
        assert len(hooks) == 2  # village_guard_completed + dragon_defeated
        assert all(h["scope"] == "region" for h in hooks)
        targets = [h["target"] for h in hooks]
        assert "oakhaven" in targets
        assert "northern_pass" in targets

    def test_get_available_milestones(self):
        mgr = _make_manager()
        mgr.trigger_milestone("village_guard_completed", world_id="w1")
        available = mgr.get_available_milestones("w1")
        ids = [m["id"] for m in available]
        assert "artifact_retrieved" in ids
        assert "shadow_mastery" in ids
        assert "village_guard_completed" not in ids
        assert "dragon_defeated" not in ids  # prereqs not fully met

    def test_get_available_milestones_chain(self):
        mgr = _make_manager()
        mgr.trigger_milestone("village_guard_completed", world_id="w1")
        mgr.trigger_milestone("artifact_retrieved", world_id="w1")
        available = mgr.get_available_milestones("w1")
        ids = [m["id"] for m in available]
        assert "dragon_defeated" in ids

    def test_list_definitions(self):
        mgr = _make_manager()
        defs = mgr.list_definitions()
        assert len(defs) == 4
        ids = [d["id"] for d in defs]
        assert "village_guard_completed" in ids
        assert "dragon_defeated" in ids

    def test_get_definition(self):
        mgr = _make_manager()
        d = mgr.get_definition("village_guard_completed")
        assert d is not None
        assert d.name == "Oakhaven Secured"
        assert mgr.get_definition("missing") is None

    def test_export_import_roundtrip(self):
        mgr = _make_manager()
        mgr.trigger_milestone("village_guard_completed", world_id="w1", session_id="s1")
        mgr.trigger_milestone("shadow_mastery", world_id="w2")
        state = mgr.export_state()

        mgr2 = MilestoneManager()
        mgr2.load_definitions(_sample_definitions())
        mgr2.import_state(state)
        assert len(mgr2.list_events()) == 2
        assert len(mgr2.list_events(world_id="w1")) == 1
        assert len(mgr2.list_events(world_id="w2")) == 1
        assert mgr2.get_world_milestone_event("village_guard_completed", "w1") is not None
        assert mgr2.get_world_milestone_event("shadow_mastery", "w2") is not None

    def test_session_scoping(self):
        mgr = _make_manager()
        mgr.trigger_milestone("shadow_mastery", world_id="w1", session_id="s1")
        mgr.trigger_milestone("shadow_mastery", world_id="w1", session_id="s2")
        assert len(mgr.list_events(world_id="w1")) == 1  # deduped per world
        # The session_id of the existing event is s1
        event = mgr.get_world_milestone_event("shadow_mastery", "w1")
        assert event.session_id == "s1"

    def test_trigger_with_metadata(self):
        mgr = _make_manager()
        event = mgr.trigger_milestone(
            "village_guard_completed",
            world_id="w1",
            session_id="s1",
            metadata={"source": "quest_journal", "quest_id": "village_guard"},
        )
        assert event is not None
        assert event.metadata["source"] == "quest_journal"
        assert event.metadata["quest_id"] == "village_guard"

    def test_auto_load_from_data_directory(self):
        mgr = MilestoneManager()
        assert len(mgr.list_definitions()) == 5
        assert mgr.get_definition("village_guard_completed") is not None
        assert mgr.get_definition("artifact_retrieved") is not None

    def test_auto_load_missing_directory(self):
        mgr = MilestoneManager(data_directory="/nonexistent/path/that/does/not/exist")
        assert len(mgr.list_definitions()) == 0

    def test_load_definitions_after_auto_load(self):
        mgr = MilestoneManager()
        # data/ has 5; sample defs share 4 ids and overwrite them -> total 5
        mgr.load_definitions(_sample_definitions())
        assert len(mgr.list_definitions()) == 5


if __name__ == "__main__":
    unittest.main()
