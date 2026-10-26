"""
Tests for RPG interactive world map UI (RPG-09-02).
Run with: python tests/test_world_map_ui.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from world_map import Location, Region, TravelRoute, WorldMap, WorldMapManager
from world_map_ui import (
    _assign_markers,
    _world_to_term,
    render_ascii_map,
    render_location_info,
    render_travel_panel,
)

# ---------------------------------------------------------------------------
# Coordinate normalization
# ---------------------------------------------------------------------------

class TestWorldToTerm:
    def test_origin(self):
        x, y = _world_to_term(0, 0)
        assert x == 0
        assert y == 0

    def test_max(self):
        x, y = _world_to_term(800, 400)
        assert x == 59
        assert y == 19

    def test_mid(self):
        x, y = _world_to_term(400, 200)
        assert 25 <= x <= 35
        assert 8 <= y <= 12


# ---------------------------------------------------------------------------
# Marker assignment
# ---------------------------------------------------------------------------

class TestAssignMarkers:
    def test_single(self):
        locs = [Location(id="a", name="A")]
        m = _assign_markers(locs)
        assert m["a"] == "1"

    def test_nine(self):
        locs = [Location(id=f"l{i}", name=str(i)) for i in range(9)]
        m = _assign_markers(locs)
        assert set(m.values()) == set("123456789")

    def test_then_letters(self):
        locs = [Location(id=f"l{i}", name=str(i)) for i in range(11)]
        m = _assign_markers(locs)
        assert m["l9"] == "a"
        assert m["l10"] == "b"


# ---------------------------------------------------------------------------
# ASCII map rendering
# ---------------------------------------------------------------------------

class TestRenderAsciiMap:
    def _make_map(self) -> WorldMap:
        locs = [
            Location(id="oakhaven", name="Oakhaven", region_id="r1", x=200, y=300),
            Location(id="caves", name="Caves", region_id="r1", x=160, y=260),
            Location(id="outskirts", name="Outskirts", region_id="r1", x=240, y=340),
        ]
        routes = [
            TravelRoute(from_location_id="oakhaven", to_location_id="caves", distance=3, travel_time_hours=2),
            TravelRoute(from_location_id="oakhaven", to_location_id="outskirts", distance=2, travel_time_hours=1),
        ]
        regions = [Region(id="r1", name="Valley", x=200, y=300)]
        return WorldMap(regions=regions, locations=locs, routes=routes)

    def test_contains_current_marker(self):
        m = self._make_map()
        out = render_ascii_map(m, current_location_id="oakhaven")
        assert "★" in out

    def test_contains_discovered_marker(self):
        m = self._make_map()
        out = render_ascii_map(m, discovered_locations={"caves"})
        assert "◉" in out

    def test_contains_undiscovered_marker(self):
        m = self._make_map()
        out = render_ascii_map(m)
        assert "●" in out

    def test_dimensions(self):
        m = self._make_map()
        out = render_ascii_map(m)
        lines = out.split("\n")
        assert len(lines) == 20
        for line in lines:
            assert len(line) == 60


# ---------------------------------------------------------------------------
# Travel panel rendering
# ---------------------------------------------------------------------------

class TestRenderTravelPanel:
    def _make_manager(self) -> WorldMapManager:
        locs = [
            Location(id="oakhaven", name="Oakhaven", region_id="r1", x=200, y=300),
            Location(id="outskirts", name="Outskirts", region_id="r1", x=240, y=340, connections=[{"to": "oakhaven", "distance": 2, "travel_time_hours": 1}]),
            Location(id="caves", name="Caves", region_id="r1", x=160, y=260, connections=[{"to": "oakhaven", "distance": 3, "travel_time_hours": 2}]),
        ]
        routes = [
            TravelRoute(from_location_id="outskirts", to_location_id="oakhaven", distance=2, travel_time_hours=1),
            TravelRoute(from_location_id="caves", to_location_id="oakhaven", distance=3, travel_time_hours=2),
            TravelRoute(from_location_id="oakhaven", to_location_id="outskirts", distance=2, travel_time_hours=1),
            TravelRoute(from_location_id="oakhaven", to_location_id="caves", distance=3, travel_time_hours=2),
        ]
        regions = [Region(id="r1", name="Valley", x=200, y=300)]
        return WorldMapManager(WorldMap(regions=regions, locations=locs, routes=routes))

    def test_shows_current_location(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="oakhaven")
        panel = render_travel_panel(mgr.world_map, "w1", mgr)
        assert "Oakhaven" in panel

    def test_shows_available_routes(self):
        mgr = self._make_manager()
        mgr.ensure_world("w1", start_location_id="outskirts")
        # undiscovered destinations show as "???"
        panel = render_travel_panel(mgr.world_map, "w1", mgr)
        assert "???" in panel
        assert "1h" in panel
        # once discovered, the real name appears
        mgr.discover_location("w1", "oakhaven")
        panel = render_travel_panel(mgr.world_map, "w1", mgr)
        assert "Oakhaven" in panel


# ---------------------------------------------------------------------------
# Location info rendering
# ---------------------------------------------------------------------------

class TestRenderLocationInfo:
    def test_known_location(self):
        locs = [Location(id="oakhaven", name="Oakhaven", region_id="r1", description="A village.")]
        regions = [Region(id="r1", name="Valley")]
        routes = [TravelRoute(from_location_id="oakhaven", to_location_id="caves", distance=3, travel_time_hours=2)]
        wm = WorldMap(regions=regions, locations=locs, routes=routes)
        out = render_location_info(wm, "oakhaven", discovered=True)
        assert "Oakhaven" in out
        assert "A village." in out

    def test_unknown_location(self):
        locs = [Location(id="oakhaven", name="Oakhaven", region_id="r1")]
        regions = [Region(id="r1", name="Valley")]
        wm = WorldMap(regions=regions, locations=locs, routes=[])
        out = render_location_info(wm, "does_not_exist", discovered=True)
        assert "not found" in out.lower()


# ---------------------------------------------------------------------------
# InteractiveMapSession unit-style smoke test
# ---------------------------------------------------------------------------

class TestInteractiveMapSession:
    def test_initial_render_does_not_crash(self):

        from world_map_ui import InteractiveMapSession

        locs = [
            Location(id="oakhaven", name="Oakhaven", region_id="r1", x=200, y=300),
            Location(id="outskirts", name="Outskirts", region_id="r1", x=240, y=340, connections=[{"to": "oakhaven", "distance": 2, "travel_time_hours": 1}]),
        ]
        routes = [
            TravelRoute(from_location_id="outskirts", to_location_id="oakhaven", distance=2, travel_time_hours=1),
        ]
        regions = [Region(id="r1", name="Valley", x=200, y=300)]
        wm = WorldMap(regions=regions, locations=locs, routes=routes)
        mgr = WorldMapManager(wm)
        mgr.ensure_world("w1", start_location_id="oakhaven")
        session = InteractiveMapSession(wm, "w1", mgr)
        session._running = False
        session._render_frame()


if __name__ == "__main__":
    # Import TravelRoute for test setup
    from world_map import TravelRoute

    suites = [
        TestWorldToTerm,
        TestAssignMarkers,
        TestRenderAsciiMap,
        TestRenderTravelPanel,
        TestRenderLocationInfo,
        TestInteractiveMapSession,
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
