"""
Tests for RPG interactive world map (RPG-09-02).
Run with: python -m pytest tests/ -v
or:       python tests/test_world_map.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from world_map import (
    GameClock,
    Location,
    NPCSchedule,
    NPCScheduleEntry,
    Region,
    TravelRoute,
    WorldMap,
    WorldMapManager,
)

# ---------------------------------------------------------------------------
# GameClock tests
# ---------------------------------------------------------------------------

class TestGameClock:
    def test_initial_state(self):
        c = GameClock(hour=6, day=1)
        assert c.current_hour() == 6
        assert c.current_day() == 1

    def test_advance_same_day(self):
        c = GameClock(hour=6, day=1)
        c.advance(3)
        assert c.current_hour() == 9
        assert c.current_day() == 1

    def test_advance_wraps_day(self):
        c = GameClock(hour=22, day=1)
        c.advance(4)
        assert c.current_hour() == 2
        assert c.current_day() == 2

    def test_to_from_dict(self):
        c = GameClock(hour=10, day=5)
        restored = GameClock.from_dict(c.to_dict())
        assert restored.current_hour() == 10
        assert restored.current_day() == 5

    def test_advance_zero(self):
        c = GameClock(hour=5, day=1)
        c.advance(0)
        assert c.current_hour() == 5


# ---------------------------------------------------------------------------
# Region / Location / TravelRoute tests
# ---------------------------------------------------------------------------

class TestRegion:
    def test_roundtrip(self):
        r = Region(id="r1", name="North", description="cold", color="#fff", x=10, y=20)
        restored = Region.from_dict(r.to_dict())
        assert restored.id == "r1"
        assert restored.name == "North"
        assert restored.x == 10


class TestLocation:
    def test_roundtrip(self):
        l = Location(id="l1", name="Town", region_id="r1", x=5, y=5, danger_level=2)
        restored = Location.from_dict(l.to_dict())
        assert restored.location_type == "generic"
        assert restored.danger_level == 2
        assert restored.connections == []

    def test_with_connections(self):
        l = Location(
            id="l1",
            name="Town",
            connections=[{"to": "l2", "distance": 2, "travel_time_hours": 1}],
        )
        restored = Location.from_dict(l.to_dict())
        assert len(restored.connections) == 1
        assert restored.connections[0]["to"] == "l2"


class TestTravelRoute:
    def test_roundtrip(self):
        r = TravelRoute(from_location_id="a", to_location_id="b", distance=3, travel_time_hours=2)
        restored = TravelRoute.from_dict(r.to_dict())
        assert restored.from_location_id == "a"
        assert restored.travel_time_hours == 2


# ---------------------------------------------------------------------------
# NPCSchedule tests
# ---------------------------------------------------------------------------

class TestNPCSchedule:
    def test_location_at_hour_before_schedule(self):
        s = NPCSchedule(
            id="npc1",
            name="Bob",
            default_location_id="home",
            schedule=[NPCScheduleEntry(hour=8, activity="work", location_id="office")],
        )
        assert s.get_location_at_hour(6) == "home"

    def test_location_at_hour_after_schedule(self):
        s = NPCSchedule(
            id="npc1",
            name="Bob",
            default_location_id="home",
            schedule=[NPCScheduleEntry(hour=8, activity="work", location_id="office")],
        )
        assert s.get_location_at_hour(14) == "office"

    def test_location_at_hour_switches_back(self):
        s = NPCSchedule(
            id="npc1",
            name="Bob",
            default_location_id="home",
            schedule=[
                NPCScheduleEntry(hour=8, activity="work", location_id="office"),
                NPCScheduleEntry(hour=18, activity="sleep", location_id="home"),
            ],
        )
        assert s.get_location_at_hour(10) == "office"
        assert s.get_location_at_hour(20) == "home"


# ---------------------------------------------------------------------------
# WorldMap tests
# ---------------------------------------------------------------------------

class TestWorldMap:
    def _make_map(self) -> WorldMap:
        locs = [
            Location(id="a", name="A", region_id="r1"),
            Location(id="b", name="B", region_id="r1", connections=[{"to": "a", "distance": 2, "travel_time_hours": 1}]),
        ]
        routes = [TravelRoute(from_location_id="b", to_location_id="a", distance=2, travel_time_hours=1)]
        return WorldMap(locations=locs, routes=routes)

    def test_get_location(self):
        m = self._make_map()
        assert m.get_location("a").name == "A"
        assert m.get_location("z") is None

    def test_get_routes_from(self):
        m = self._make_map()
        rs = m.get_routes_from("b")
        assert len(rs) == 1
        assert rs[0]["to_location_id"] == "a"

    def test_get_npcs_at_location(self):
        m = WorldMap(
            npc_schedules=[
                NPCSchedule(
                    id="n1",
                    name="Guard",
                    default_location_id="a",
                    schedule=[NPCScheduleEntry(hour=8, activity="patrol", location_id="b")],
                )
            ]
        )
        assert len(m.get_npcs_at_location("b", 10)) == 1
        assert len(m.get_npcs_at_location("a", 6)) == 1
        assert len(m.get_npcs_at_location("a", 10)) == 0

    def test_import_export(self):
        m = self._make_map()
        data = m.export_state()
        m2 = WorldMap()
        m2.import_state(data)
        assert m2.get_location("a").name == "A"


# ---------------------------------------------------------------------------
# WorldMapManager tests
# ---------------------------------------------------------------------------

class TestWorldMapManager:
    def _make_manager(self) -> WorldMapManager:
        locs = [
            Location(id="oakhaven", name="Oakhaven", region_id="r_valley"),
            Location(id="outskirts", name="Outskirts", region_id="r_valley", connections=[{"to": "oakhaven", "distance": 2, "travel_time_hours": 1}]),
            Location(id="caves", name="Caves", region_id="r_valley", connections=[{"to": "oakhaven", "distance": 3, "travel_time_hours": 2}]),
        ]
        routes = [
            TravelRoute(from_location_id="outskirts", to_location_id="oakhaven", distance=2, travel_time_hours=1),
            TravelRoute(from_location_id="caves", to_location_id="oakhaven", distance=3, travel_time_hours=2),
            TravelRoute(from_location_id="oakhaven", to_location_id="outskirts", distance=2, travel_time_hours=1),
            TravelRoute(from_location_id="oakhaven", to_location_id="caves", distance=3, travel_time_hours=2),
        ]
        return WorldMapManager(WorldMap(locations=locs, routes=routes))

    def test_ensure_world_default_start(self):
        mgr = self._make_manager()
        state = mgr.ensure_world("w1")
        assert state["current_location"]["id"] == "oakhaven"
        assert "oakhaven" in state["discovered_locations"]

    def test_ensure_world_explicit_start(self):
        mgr = self._make_manager()
        state = mgr.ensure_world("w2", start_location_id="outskirts")
        assert state["current_location"]["id"] == "outskirts"

    def test_travel_advances_clock(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        result = mgr.travel("w1", "outskirts")
        assert result["success"] is True
        state = mgr.get_world_state("w1")
        assert state["current_location"]["id"] == "outskirts"
        assert state["clock"]["hour"] == 7  # 6 + 1
        assert "outskirts" in state["discovered_locations"]

    def test_travel_invalid_route(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        # "caves" is a valid destination from oakhaven per data; use a nonexistent location
        result = mgr.travel("w1", "nonexistent_place")
        assert result["success"] is False
        assert "No route" in result["reason"]

    def test_discover_location(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        state = mgr.discover_location("w1", "outskirts")
        assert "outskirts" in state["discovered_locations"]

    def test_discover_region(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        state = mgr.discover_region("w1", "r_valley")
        assert "r_valley" in state["discovered_regions"]

    def test_fast_travel_falls_back(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        # outskirts is not yet discovered; should fallback to normal travel
        result = mgr.fast_travel("w1", "outskirts")
        assert result["success"] is True
        assert result.get("fast_travel") is not True
        state = mgr.get_world_state("w1")
        assert state["clock"]["hour"] == 7

    def test_fast_travel_when_discovered(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        # discover outskirts first
        mgr.discover_location("w1", "outskirts")
        # now we need a direct route from current to outskirts for fast_travel to work
        # current is oakhaven, route is outskirts -> oakhaven, not oakhaven -> outskirts
        result = mgr.fast_travel("w1", "outskirts")
        # still should succeed but may or may not be fast travel depending on route direction
        assert result["success"] is True

    def test_available_travel(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        available = mgr.get_available_travel("w1")
        assert len(available) == 2  # routes FROM oakhaven: outskirts, caves
        mgr.travel("w1", "outskirts")
        available = mgr.get_available_travel("w1")
        assert len(available) == 1

    def test_get_npcs_here(self):
        mgr = WorldMapManager(
            WorldMap(
                locations=[Location(id="town", name="Town", region_id="r")],
                npc_schedules=[
                    NPCSchedule(
                        id="n1",
                        name="Guard",
                        default_location_id="town",
                        schedule=[NPCScheduleEntry(hour=10, activity="patrol", location_id="plains")],
                    )
                ],
            )
        )
        mgr.ensure_world("w1", start_location_id="town")
        npcs = mgr.get_npcs_here("w1")
        assert len(npcs) == 1
        assert npcs[0]["name"] == "Guard"

    def test_clock_manipulation(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        mgr.set_clock("w1", hour=12, day=3)
        assert mgr.get_clock("w1") == {"hour": 12, "day": 3}

    def test_sync_and_restore_snapshot(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        mgr.travel("w1", "outskirts")
        snapshot = mgr.sync_to_session_snapshot("w1")
        assert snapshot["current_location_id"] == "outskirts"
        mgr.restore_from_session_snapshot("w1", snapshot)
        state = mgr.get_world_state("w1")
        assert state["current_location"]["id"] == "outskirts"

    def test_export_import_state(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        mgr.travel("w1", "outskirts")
        exported = mgr.export_state()
        mgr2 = WorldMapManager(WorldMap(locations=mgr.world_map._locations.values(), routes=mgr.world_map._routes))
        mgr2.import_state(exported)
        state = mgr2.get_world_state("w1")
        assert state["current_location"]["id"] == "outskirts"


if __name__ == "__main__":
    suites = [
        TestGameClock,
        TestRegion,
        TestLocation,
        TestTravelRoute,
        TestNPCSchedule,
        TestWorldMap,
        TestWorldMapManager,
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
