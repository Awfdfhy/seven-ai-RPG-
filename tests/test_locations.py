"""
Tests for RPG-09-01 Locations Directory.
Run with: python -m pytest tests/ -v
or:       python tests/test_locations.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from locations import (
    LocationDirectory,
    LocationDirectoryEntry,
    load_locations_from_data_dir,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_directory() -> LocationDirectory:
    entries = [
        LocationDirectoryEntry(
            id="oakhaven",
            name="Oakhaven",
            region_id="oakhaven_region",
            description="A small village nestled in the valley.",
            location_type="town",
            x=200,
            y=300,
            danger_level=1,
            connections=[
                {"to": "outskirts", "distance": 2, "travel_time_hours": 1},
            ],
        ),
        LocationDirectoryEntry(
            id="outskirts",
            name="Outskirts",
            region_id="oakhaven_region",
            description="The forested outskirts.",
            location_type="wilderness",
            x=240,
            y=340,
            danger_level=2,
            connections=[
                {"to": "oakhaven", "distance": 2, "travel_time_hours": 1},
            ],
        ),
        LocationDirectoryEntry(
            id="caves",
            name="Caves",
            region_id="oakhaven_region",
            description="Dark caves.",
            location_type="dungeon",
            x=160,
            y=260,
            danger_level=3,
            connections=[
                {"to": "oakhaven", "distance": 3, "travel_time_hours": 2},
            ],
        ),
        LocationDirectoryEntry(
            id="ashfall",
            name="Ashfall Entrance",
            region_id="ashfall_region",
            description="Border of the volcanic wasteland.",
            location_type="outpost",
            x=700,
            y=250,
            danger_level=5,
            connections=[],
        ),
    ]
    return LocationDirectory(locations=entries)


# ---------------------------------------------------------------------------
# LocationDirectoryEntry tests
# ---------------------------------------------------------------------------

class TestLocationDirectoryEntry:
    def test_roundtrip(self):
        entry = LocationDirectoryEntry(
            id="loc1",
            name="Test Town",
            region_id="r1",
            description="A test place.",
            location_type="town",
            x=10,
            y=20,
            danger_level=2,
            connections=[{"to": "loc2", "distance": 1, "travel_time_hours": 1}],
        )
        restored = LocationDirectoryEntry.from_dict(entry.to_dict())
        assert restored.id == "loc1"
        assert restored.name == "Test Town"
        assert restored.danger_level == 2
        assert len(restored.connections) == 1
        assert restored.connections[0]["to"] == "loc2"

    def test_defaults(self):
        entry = LocationDirectoryEntry(id="x", name="X")
        assert entry.region_id == ""
        assert entry.danger_level == 1
        assert entry.connections == []


# ---------------------------------------------------------------------------
# LocationDirectory tests
# ---------------------------------------------------------------------------

class TestLocationDirectory:
    def test_get_location_existing(self):
        mgr = _make_directory()
        loc = mgr.get_location("oakhaven")
        assert loc is not None
        assert loc["name"] == "Oakhaven"
        assert loc["description"] == "A small village nestled in the valley."

    def test_get_location_missing(self):
        mgr = _make_directory()
        assert mgr.get_location("nonexistent") is None

    def test_get_description(self):
        mgr = _make_directory()
        assert mgr.get_description("oakhaven") == "A small village nestled in the valley."
        assert mgr.get_description("missing") is None

    def test_list_locations_sorted_by_name(self):
        mgr = _make_directory()
        names = [l["name"] for l in mgr.list_locations()]
        assert names == sorted(names)
        assert "Ashfall Entrance" in names
        assert "Oakhaven" in names

    def test_list_by_region(self):
        mgr = _make_directory()
        names = [l["name"] for l in mgr.list_by_region("oakhaven_region")]
        assert "Oakhaven" in names
        assert "Outskirts" in names
        assert "Ashfall Entrance" not in names

    def test_list_by_type(self):
        mgr = _make_directory()
        names = [l["name"] for l in mgr.list_by_type("town")]
        assert names == ["Oakhaven"]
        names = [l["name"] for l in mgr.list_by_type("dungeon")]
        assert names == ["Caves"]

    def test_get_connections(self):
        mgr = _make_directory()
        conns = mgr.get_connections("oakhaven")
        assert len(conns) == 1
        assert conns[0]["to"] == "outskirts"
        assert conns[0]["to_name"] == "Outskirts"
        assert conns[0]["distance"] == 2

    def test_get_connections_missing_location(self):
        mgr = _make_directory()
        assert mgr.get_connections("missing") == []

    def test_get_connections_no_to_name_for_unknown(self):
        mgr = _make_directory()
        # ashfall has no connections, but let's test a connection to unknown
        mgr.add_location(
            LocationDirectoryEntry(
                id="unknown_conn",
                name="Unknown Conn",
                region_id="r",
                connections=[{"to": "nonexistent", "distance": 1}],
            )
        )
        conns = mgr.get_connections("unknown_conn")
        assert len(conns) == 1
        assert conns[0]["to"] == "nonexistent"
        assert "to_name" not in conns[0]

    def test_get_connected_locations(self):
        mgr = _make_directory()
        conns = mgr.get_connected_locations("oakhaven")
        assert len(conns) == 1
        assert conns[0]["id"] == "outskirts"

    def test_search_by_name(self):
        mgr = _make_directory()
        results = mgr.search("Oakhaven")
        assert len(results) == 1
        assert results[0]["id"] == "oakhaven"

    def test_search_by_description(self):
        mgr = _make_directory()
        results = mgr.search("volcanic")
        assert len(results) == 1
        assert results[0]["id"] == "ashfall"

    def test_search_case_insensitive(self):
        mgr = _make_directory()
        results = mgr.search("oakhaven")
        assert len(results) == 1
        results = mgr.search("OAKHAVEN")
        assert len(results) == 1

    def test_search_no_results(self):
        mgr = _make_directory()
        assert mgr.search("nonexistent") == []

    def test_add_location(self):
        mgr = _make_directory()
        mgr.add_location(
            LocationDirectoryEntry(
                id="new_loc", name="New Place", region_id="new_region", description="New."
            )
        )
        assert mgr.get_location("new_loc") is not None
        assert mgr.get_location("new_loc")["name"] == "New Place"

    def test_remove_location(self):
        mgr = _make_directory()
        assert mgr.remove_location("outskirts") is True
        assert mgr.get_location("outskirts") is None
        assert mgr.remove_location("outskirts") is False

    def test_export_import_roundtrip(self):
        mgr = _make_directory()
        data = mgr.export_state()
        mgr2 = LocationDirectory()
        mgr2.import_state(data)
        assert mgr2.get_location("oakhaven")["name"] == "Oakhaven"
        assert mgr2.get_location("ashfall")["danger_level"] == 5

    def test_import_clears_existing(self):
        mgr = _make_directory()
        mgr.import_state({"locations": []})
        assert mgr.list_locations() == []


# ---------------------------------------------------------------------------
# Data loader tests
# ---------------------------------------------------------------------------

class TestDataLoader:
    def test_load_from_default_data_dir(self):
        mgr = load_locations_from_data_dir()
        assert len(mgr.list_locations()) > 0

    def test_load_contains_known_location(self):
        mgr = load_locations_from_data_dir()
        loc = mgr.get_location("oakhaven")
        assert loc is not None
        assert loc["location_type"] == "town"

    def test_load_connections_present(self):
        mgr = load_locations_from_data_dir()
        conns = mgr.get_connections("oakhaven")
        assert len(conns) >= 1

    def test_load_missing_file_returns_empty(self):
        mgr = load_locations_from_data_dir(base_path="/nonexistent/path")
        assert mgr.list_locations() == []


if __name__ == "__main__":
    suites = [
        TestLocationDirectoryEntry,
        TestLocationDirectory,
        TestDataLoader,
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
