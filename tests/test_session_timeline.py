"""
Tests for the session timeline system.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from session_timeline import (
    TimelineEntry,
    TimelineEventType,
    SessionTimelineManager,
)


# ---------------------------------------------------------------------------
# TimelineEntry tests
# ---------------------------------------------------------------------------

class TestTimelineEntry:
    def test_to_dict_roundtrip(self):
        entry = TimelineEntry(
            event_type=TimelineEventType.LEVEL_UP,
            session_id="sess-1",
            world_id="world-1",
            branch_id="branch-1",
            character_id="char-1",
            title="Reached level 5",
            description="Gained a skill point",
            data={"new_level": 5, "skill_points_gained": 1},
            metadata={"source": "unit_test"},
        )
        d = entry.to_dict()
        restored = TimelineEntry.from_dict(d)
        assert restored.entry_id == entry.entry_id
        assert restored.event_type == entry.event_type
        assert restored.session_id == entry.session_id
        assert restored.world_id == entry.world_id
        assert restored.branch_id == entry.branch_id
        assert restored.character_id == entry.character_id
        assert restored.title == entry.title
        assert restored.description == entry.description
        assert restored.data == entry.data
        assert restored.metadata == entry.metadata


# ---------------------------------------------------------------------------
# SessionTimelineManager tests
# ---------------------------------------------------------------------------

class TestSessionTimelineManager:
    def test_record_and_retrieve(self):
        mgr = SessionTimelineManager()
        entry = mgr.record(
            event_type=TimelineEventType.QUEST_COMPLETED,
            session_id="sess-1",
            world_id="world-1",
            title="Defeated the dragon",
        )
        assert entry.event_type == TimelineEventType.QUEST_COMPLETED
        assert mgr.get_entry(entry.entry_id) is entry

    def test_get_session_timeline(self):
        mgr = SessionTimelineManager()
        mgr.record(TimelineEventType.SESSION_START, session_id="s1", world_id="w1")
        mgr.record(TimelineEventType.LEVEL_UP, session_id="s1", world_id="w1", data={"new_level": 2})
        mgr.record(TimelineEventType.QUEST_COMPLETED, session_id="s1", world_id="w1")
        timeline = mgr.get_session_timeline("s1")
        assert len(timeline) == 3
        assert timeline[0]["event_type"] == TimelineEventType.SESSION_START
        assert timeline[-1]["event_type"] == TimelineEventType.QUEST_COMPLETED

    def test_get_session_timeline_filter_by_event_type(self):
        mgr = SessionTimelineManager()
        mgr.record(TimelineEventType.SESSION_START, session_id="s1", world_id="w1")
        mgr.record(TimelineEventType.LEVEL_UP, session_id="s1", world_id="w1")
        mgr.record(TimelineEventType.QUEST_COMPLETED, session_id="s1", world_id="w1")
        timeline = mgr.get_session_timeline("s1", event_type=TimelineEventType.LEVEL_UP)
        assert len(timeline) == 1
        assert timeline[0]["event_type"] == TimelineEventType.LEVEL_UP

    def test_get_session_timeline_reverse(self):
        mgr = SessionTimelineManager()
        mgr.record(TimelineEventType.SESSION_START, session_id="s1", world_id="w1")
        mgr.record(TimelineEventType.QUEST_COMPLETED, session_id="s1", world_id="w1")
        timeline = mgr.get_session_timeline("s1", reverse=True)
        assert timeline[0]["event_type"] == TimelineEventType.QUEST_COMPLETED

    def test_get_branch_timeline(self):
        mgr = SessionTimelineManager()
        mgr.record(
            TimelineEventType.CHECKPOINT_CREATED,
            session_id="s1",
            branch_id="b1",
            world_id="w1",
        )
        mgr.record(
            TimelineEventType.COMBAT_STARTED,
            session_id="s1",
            branch_id="b1",
            world_id="w1",
        )
        mgr.record(
            TimelineEventType.COMBAT_ENDED,
            session_id="s1",
            branch_id="b2",
            world_id="w1",
        )
        branch_tl = mgr.get_branch_timeline("b1")
        assert len(branch_tl) == 2
        assert all(e["branch_id"] == "b1" for e in branch_tl)

    def test_get_world_timeline(self):
        mgr = SessionTimelineManager()
        mgr.record(TimelineEventType.LEVEL_UP, session_id="s1", world_id="w1", character_id="c1")
        mgr.record(TimelineEventType.QUEST_COMPLETED, session_id="s1", world_id="w1")
        mgr.record(TimelineEventType.TRAVEL_STARTED, session_id="s2", world_id="w2")
        world_tl = mgr.get_world_timeline("w1")
        assert len(world_tl) == 2
        world_tl_s1 = mgr.get_world_timeline("w1", session_id="s1")
        assert len(world_tl_s1) == 2

    def test_get_session_summary(self):
        mgr = SessionTimelineManager()
        mgr.record(TimelineEventType.SESSION_START, session_id="s1", world_id="w1")
        mgr.record(TimelineEventType.LEVEL_UP, session_id="s1", world_id="w1", character_id="c1")
        mgr.record(TimelineEventType.QUEST_COMPLETED, session_id="s1", world_id="w1", character_id="c1")
        summary = mgr.get_session_summary("s1")
        assert summary["session_id"] == "s1"
        assert summary["total_events"] == 3
        assert summary["active_characters"] == 1
        assert "w1" in summary["world_ids"]
        assert abs(summary["duration_seconds"]) < 0.01

    def test_export_import_roundtrip(self):
        mgr = SessionTimelineManager()
        mgr.record(
            TimelineEventType.LEVEL_UP,
            session_id="sess-1",
            world_id="world-1",
            branch_id="branch-1",
            character_id="char-1",
            data={"new_level": 5},
        )
        state = mgr.export_state()

        mgr2 = SessionTimelineManager()
        mgr2.import_state(state)
        timeline = mgr2.get_session_timeline("sess-1")
        assert len(timeline) == 1
        assert timeline[0]["event_type"] == TimelineEventType.LEVEL_UP
        assert timeline[0]["data"]["new_level"] == 5

    def test_limit(self):
        mgr = SessionTimelineManager()
        for i in range(10):
            mgr.record(
                TimelineEventType.CUSTOM,
                session_id="s1",
                world_id="w1",
                title=f"Event {i}",
            )
        timeline = mgr.get_session_timeline("s1", limit=3)
        assert len(timeline) == 3


if __name__ == "__main__":
    suites = [TestTimelineEntry, TestSessionTimelineManager]
    passed = 0
    failed = 0
    for suite in suites:
        instance = suite()
        for method in dir(instance):
            if method.startswith("test_"):
                try:
                    getattr(instance, method)()
                    print(f"  PASS  {suite.__name__}.{method}")
                    passed += 1
                except Exception as exc:
                    print(f"  FAIL  {suite.__name__}.{method}: {exc}")
                    import traceback
                    traceback.print_exc()
                    failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
