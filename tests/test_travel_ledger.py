"""
Tests for RPG Travel Ledger System.
Run with: python -m pytest tests/ -v
or:       python tests/test_travel_ledger.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from travel_ledger import (
    CalendarProvider,
    JourneyEvent,
    LocationDefinition,
    TravelEntry,
    TravelLedgerManager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_locations() -> list[LocationDefinition]:
    return [
        LocationDefinition(id="loc_a", name="Oakhaven", region="Forest", danger_level=1, terrain="plains"),
        LocationDefinition(id="loc_b", name="Whispering Caves", region="Mountain", danger_level=3, terrain="cave"),
        LocationDefinition(id="loc_c", name="Silverport", region="Coastal", danger_level=2, terrain="road"),
        LocationDefinition(id="loc_d", name="Greenhollow", region="Forest", danger_level=1, terrain="plains"),
    ]


def _make_manager() -> TravelLedgerManager:
    mgr = TravelLedgerManager()
    mgr.load_locations(_make_locations())
    return mgr


# ---------------------------------------------------------------------------
# CalendarProvider tests
# ---------------------------------------------------------------------------

class TestCalendarProvider:
    def test_default_now_returns_utc(self):
        cal = CalendarProvider()
        now = cal.now()
        assert now.tzinfo is not None

    def test_add_time_advances_clock(self):
        cal = CalendarProvider()
        base = cal.now()
        future = cal.add_time(base, 120.0)
        delta = (future - base).total_seconds()
        assert abs(delta - 120.0) < 0.01


# ---------------------------------------------------------------------------
# Location tests
# ---------------------------------------------------------------------------

class TestLocation:
    def test_register_and_get(self):
        mgr = _make_manager()
        loc = mgr.get_location("loc_a")
        assert loc is not None
        assert loc.name == "Oakhaven"
        assert loc.region == "Forest"

    def test_list_locations(self):
        mgr = _make_manager()
        names = [l["name"] for l in mgr.list_locations()]
        assert "Oakhaven" in names
        assert "Silverport" in names

    def test_missing_location_returns_none(self):
        mgr = _make_manager()
        assert mgr.get_location("nope") is None


# ---------------------------------------------------------------------------
# TravelLedgerManager tests
# ---------------------------------------------------------------------------

class TestTravelLedgerManager:
    def test_start_journey_basic(self):
        mgr = _make_manager()
        travel = mgr.start_journey(
            world_id="w1",
            from_location_id="loc_a",
            to_location_id="loc_c",
            session_id="s1",
        )
        assert travel is not None
        assert travel.status == "in_progress"
        assert travel.from_location_id == "loc_a"
        assert travel.to_location_id == "loc_c"
        assert travel.world_id == "w1"
        assert travel.session_id == "s1"

    def test_start_journey_missing_location_returns_none(self):
        mgr = _make_manager()
        assert mgr.start_journey("w1", "loc_a", "missing") is None
        assert mgr.start_journey("w1", "missing", "loc_c") is None

    def test_complete_journey(self):
        mgr = _make_manager()
        travel = mgr.start_journey("w1", "loc_a", "loc_b")
        assert travel is not None
        # Fast-forward the internal clock by mocking CalendarProvider.now
        fake_time = datetime.fromisoformat(travel.started_at) + timedelta(minutes=15)
        mgr.calendar.now = lambda: fake_time
        completed = mgr.complete_journey(travel.travel_id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.actual_duration_seconds is not None
        assert abs(completed.actual_duration_seconds - 900.0) < 1.0

    def test_cancel_journey(self):
        mgr = _make_manager()
        travel = mgr.start_journey("w1", "loc_a", "loc_b")
        assert travel is not None
        cancelled = mgr.cancel_journey(travel.travel_id, reason="River flooded")
        assert cancelled is not None
        assert cancelled.status == "cancelled"
        assert "River flooded" in cancelled.metadata.get("cancel_reasons", [])

    def test_add_event_to_journey(self):
        mgr = _make_manager()
        travel = mgr.start_journey("w1", "loc_a", "loc_c", session_id="s1")
        assert travel is not None
        event = mgr.add_event(travel.travel_id, "encounter", "Bandits on the road")
        assert event is not None
        assert event.event_type == "encounter"
        assert len(travel.events) == 1

    def test_cannot_add_event_to_completed_journey(self):
        mgr = _make_manager()
        travel = mgr.start_journey("w1", "loc_a", "loc_b")
        mgr.complete_journey(travel.travel_id)
        event = mgr.add_event(travel.travel_id, "noop", "Should not appear")
        assert event is None
        assert len(travel.events) == 0

    def test_cannot_complete_already_completed(self):
        mgr = _make_manager()
        travel = mgr.start_journey("w1", "loc_a", "loc_b")
        mgr.complete_journey(travel.travel_id)
        result = mgr.complete_journey(travel.travel_id)
        assert result is None

    def test_cannot_cancel_completed(self):
        mgr = _make_manager()
        travel = mgr.start_journey("w1", "loc_a", "loc_b")
        mgr.complete_journey(travel.travel_id)
        result = mgr.cancel_journey(travel.travel_id)
        assert result is None

    def test_list_travels_scoped_by_world(self):
        mgr = _make_manager()
        mgr.start_journey("w1", "loc_a", "loc_b")
        mgr.start_journey("w2", "loc_a", "loc_c")
        assert len(mgr.list_travels(world_id="w1")) == 1
        assert len(mgr.list_travels(world_id="w2")) == 1

    def test_list_travels_scoped_by_session(self):
        mgr = _make_manager()
        t1 = mgr.start_journey("w1", "loc_a", "loc_b", session_id="s1")
        t2 = mgr.start_journey("w1", "loc_a", "loc_c", session_id="s2")
        assert len(mgr.list_travels(session_id="s1")) == 1
        assert len(mgr.list_travels(session_id="s2")) == 1

    def test_list_travels_scoped_by_status(self):
        mgr = _make_manager()
        t1 = mgr.start_journey("w1", "loc_a", "loc_b")
        mgr.complete_journey(t1.travel_id)
        mgr.start_journey("w1", "loc_a", "loc_c")
        assert len(mgr.list_travels(status="completed")) == 1
        assert len(mgr.list_travels(status="in_progress")) == 1

    def test_get_journey_events(self):
        mgr = _make_manager()
        travel = mgr.start_journey("w1", "loc_a", "loc_b")
        mgr.add_event(travel.travel_id, "encounter", "Goblin")
        mgr.add_event(travel.travel_id, "discovery", "Ancient ruin")
        events = mgr.get_journey_events(travel.travel_id)
        assert len(events) == 2
        assert events[0]["event_type"] == "encounter"

    def test_get_travel_log(self):
        mgr = _make_manager()
        mgr.start_journey("w1", "loc_a", "loc_b")
        mgr.start_journey("w2", "loc_a", "loc_c")
        log = mgr.get_travel_log(world_id="w1")
        assert len(log) == 1
        assert log[0]["from_location_id"] == "loc_a"
        assert log[0]["to_location_id"] == "loc_b"

    def test_get_location_stats(self):
        mgr = _make_manager()
        t1 = mgr.start_journey("w1", "loc_a", "loc_b")
        mgr.add_event(t1.travel_id, "sighting", "Deer")
        mgr.complete_journey(t1.travel_id)
        mgr.start_journey("w1", "loc_c", "loc_a")
        stats = mgr.get_location_stats("loc_a")
        assert stats["journeys_as_origin"] == 1
        assert stats["journeys_as_destination"] == 1
        assert stats["total_events_logged"] == 1

    def test_estimate_travel_time(self):
        mgr = _make_manager()
        expected = mgr.estimate_travel_time("loc_a", "loc_c", travel_speed="normal")
        assert expected is not None
        assert expected > 0
        # fast should be shorter
        fast = mgr.estimate_travel_time("loc_a", "loc_c", travel_speed="fast")
        assert fast < expected
        # slow should be longer
        slow = mgr.estimate_travel_time("loc_a", "loc_c", travel_speed="slow")
        assert slow > expected

    def test_estimate_travel_time_missing_location(self):
        mgr = _make_manager()
        assert mgr.estimate_travel_time("loc_a", "missing") is None
        assert mgr.estimate_travel_time("missing", "loc_a") is None

    def test_cross_region_distance(self):
        mgr = _make_manager()
        cross = mgr.estimate_travel_time("loc_a", "loc_b")  # Forest -> Mountain
        same = mgr.estimate_travel_time("loc_a", "loc_d")   # Forest -> Forest
        assert cross > same

    def test_export_import_roundtrip(self):
        mgr = _make_manager()
        t1 = mgr.start_journey("w1", "loc_a", "loc_b", session_id="s1")
        mgr.add_event(t1.travel_id, "encounter", "Wolf")
        mgr.complete_journey(t1.travel_id)
        state = mgr.export_state()
        mgr2 = TravelLedgerManager()
        mgr2.import_state(state)
        assert len(mgr2.list_travels()) == 1
        assert mgr2.get_location("loc_a").name == "Oakhaven"
        events = mgr2.get_journey_events(t1.travel_id)
        assert len(events) == 1
        assert events[0]["event_type"] == "encounter"

    def test_get_travel_returns_none_for_unknown(self):
        mgr = _make_manager()
        assert mgr.get_travel("missing-travel-id") is None


# ---------------------------------------------------------------------------
# Dataclass serialization tests
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_location_roundtrip(self):
        loc = LocationDefinition(id="x", name="X", region="R", danger_level=5, terrain="desert")
        restored = LocationDefinition.from_dict(loc.to_dict())
        assert restored.id == "x"
        assert restored.danger_level == 5

    def test_journey_event_roundtrip(self):
        evt = JourneyEvent(id="e1", event_type="discovery", description="Found gold")
        restored = JourneyEvent.from_dict(evt.to_dict())
        assert restored.event_type == "discovery"

    def test_travel_entry_roundtrip(self):
        travel = TravelEntry(
            travel_id="t1",
            world_id="w",
            from_location_id="l1",
            to_location_id="l2",
            status="completed",
            events=[
                JourneyEvent(id="e1", event_type="test", description="hi")
            ],
        )
        restored = TravelEntry.from_dict(travel.to_dict())
        assert restored.travel_id == "t1"
        assert restored.status == "completed"
        assert len(restored.events) == 1
        assert restored.events[0].event_type == "test"


if __name__ == "__main__":
    suites = [
        TestCalendarProvider,
        TestLocation,
        TestTravelLedgerManager,
        TestSerialization,
    ]
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
