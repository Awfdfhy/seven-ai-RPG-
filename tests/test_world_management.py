"""
Tests for RPG world management: WorldLibrary, WorldSession, WorldBridge.
Run with: python -m pytest tests/ -v
or:       python tests/test_world_management.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from world_bridge import WorldBridge
from world_library import WorldEntry, WorldLibrary
from world_session import WorldSessionManager

# ---------------------------------------------------------------------------
# WorldLibrary tests
# ---------------------------------------------------------------------------

class TestWorldLibrary:
    def test_create_and_get(self):
        lib = WorldLibrary()
        entry = lib.create_world(name="Azeroth", description="The world of warcraft.")
        assert entry.world_id is not None
        assert lib.get_world(entry.world_id).name == "Azeroth"

    def test_list_active_excludes_archived(self):
        lib = WorldLibrary()
        w1 = lib.create_world(name="Active World")
        w2 = lib.create_world(name="Old World")
        lib.archive_world(w2.world_id)
        names = [w["name"] for w in lib.list_worlds(include_archived=False)]
        assert "Active World" in names
        assert "Old World" not in names

    def test_list_includes_archived_when_requested(self):
        lib = WorldLibrary()
        w1 = lib.create_world(name="Keep")
        w2 = lib.create_world(name="Hide")
        lib.archive_world(w2.world_id)
        names = [w["name"] for w in lib.list_worlds(include_archived=True)]
        assert "Keep" in names
        assert "Hide" in names

    def test_rename_world(self):
        lib = WorldLibrary()
        w = lib.create_world(name="Old Name")
        assert lib.rename_world(w.world_id, "New Name") is True
        assert lib.get_world(w.world_id).name == "New Name"

    def test_rename_missing_world(self):
        lib = WorldLibrary()
        assert lib.rename_world("nonexistent", "New Name") is False

    def test_archive_and_unarchive(self):
        lib = WorldLibrary()
        w = lib.create_world(name="World")
        assert lib.archive_world(w.world_id) is True
        assert lib.get_world(w.world_id).status == "archived"
        assert lib.unarchive_world(w.world_id) is True
        assert lib.get_world(w.world_id).status == "active"

    def test_archive_missing(self):
        lib = WorldLibrary()
        assert lib.archive_world("nonexistent") is False

    def test_unarchive_missing(self):
        lib = WorldLibrary()
        assert lib.unarchive_world("nonexistent") is False

    def test_export_import_roundtrip(self):
        lib = WorldLibrary()
        w = lib.create_world(name="Roundtrip", description="test", metadata={"key": "value"})
        lib.archive_world(w.world_id)
        state = lib.export_state()
        lib2 = WorldLibrary()
        lib2.import_state(state)
        assert lib2.get_world(w.world_id).name == "Roundtrip"
        assert lib2.get_world(w.world_id).status == "archived"

    def test_to_from_dict_roundtrip(self):
        entry = WorldEntry(
            world_id="wid-1",
            name="Test",
            description="desc",
            status="active",
            metadata={"a": 1},
        )
        restored = WorldEntry.from_dict(entry.to_dict())
        assert restored.world_id == "wid-1"
        assert restored.name == "Test"
        assert restored.status == "active"
        assert restored.metadata == {"a": 1}


# ---------------------------------------------------------------------------
# WorldSession tests
# ---------------------------------------------------------------------------

class TestWorldSession:
    def test_create_session(self):
        mgr = WorldSessionManager()
        session = mgr.create_session("world-1", metadata={"hero": "Thrall"})
        assert session.world_id == "world-1"
        assert session.status == "active"
        assert session.metadata["hero"] == "Thrall"

    def test_get_session(self):
        mgr = WorldSessionManager()
        session = mgr.create_session("world-1")
        assert mgr.get_session(session.session_id).session_id == session.session_id
        assert mgr.get_session("missing") is None

    def test_end_session(self):
        mgr = WorldSessionManager()
        session = mgr.create_session("world-1")
        assert mgr.end_session(session.session_id) is True
        assert mgr.get_session(session.session_id).status == "ended"
        assert mgr.end_session(session.session_id) is False  # already ended

    def test_list_active_sessions(self):
        mgr = WorldSessionManager()
        s1 = mgr.create_session("w1")
        s2 = mgr.create_session("w1")
        mgr.end_session(s1.session_id)
        actives = mgr.list_active_sessions()
        assert len(actives) == 1
        assert actives[0]["session_id"] == s2.session_id

    def test_update_snapshot(self):
        mgr = WorldSessionManager()
        session = mgr.create_session("w1")
        ok = mgr.update_snapshot(session.session_id, {"hp": 42})
        assert ok is True
        assert mgr.get_session(session.session_id).snapshot["hp"] == 42
        # cannot snapshot ended session
        mgr.end_session(session.session_id)
        assert mgr.update_snapshot(session.session_id, {"hp": 0}) is False


# ---------------------------------------------------------------------------
# WorldBridge tests
# ---------------------------------------------------------------------------

class TestWorldBridge:
    def test_open_world_creates_library_entry(self):
        bridge = WorldBridge()
        result = bridge.open_world(name="New World")
        assert "session" in result
        assert "world" in result
        assert result["world"]["name"] == "New World"

    def test_open_existing_world(self):
        bridge = WorldBridge()
        w = bridge.library.create_world(name="Existing")
        result = bridge.open_world(world_id=w.world_id)
        assert result["world"]["world_id"] == w.world_id

    def test_rename_world_via_bridge(self):
        bridge = WorldBridge()
        w = bridge.library.create_world(name="Old")
        result = bridge.rename_world(w.world_id, "New")
        assert result["success"] is True
        assert result["new_name"] == "New"
        assert bridge.library.get_world(w.world_id).name == "New"

    def test_rename_missing_world_via_bridge(self):
        bridge = WorldBridge()
        result = bridge.rename_world("missing", "New")
        assert result["success"] is False

    def test_archive_world_ends_active_sessions(self):
        bridge = WorldBridge()
        w = bridge.library.create_world(name="ToArchive")
        bridge.open_world(world_id=w.world_id)
        result = bridge.archive_world(w.world_id)
        assert result["success"] is True
        assert len(result["ended_sessions"]) == 1
        # world no longer in active list
        lib_list = bridge.list_world_library(include_archived=False)
        assert all(x["world_id"] != w.world_id for x in lib_list)

    def test_unarchive_world(self):
        bridge = WorldBridge()
        w = bridge.library.create_world(name="Hidden")
        bridge.library.archive_world(w.world_id)
        result = bridge.unarchive_world(w.world_id)
        assert result["success"] is True
        lib_list = bridge.list_world_library(include_archived=False)
        assert any(x["world_id"] == w.world_id for x in lib_list)

    def test_close_session(self):
        bridge = WorldBridge()
        result = bridge.open_world(name="SessionWorld")
        session_id = result["session"]["session_id"]
        close_result = bridge.close_session(session_id)
        assert close_result["success"] is True
        assert bridge.get_session(session_id)["status"] == "ended"

    def test_list_queries(self):
        bridge = WorldBridge()
        bridge.open_world(name="W1")
        bridge.open_world(name="W2")
        assert len(bridge.list_world_library()) == 2
        assert len(bridge.list_active_sessions()) == 2

    def test_trigger_milestone_via_bridge(self):
        bridge = WorldBridge()
        result = bridge.open_world(name="BridgeWorld")
        world_id = result["world"]["world_id"]
        session_id = result["session"]["session_id"]
        evt = bridge.trigger_milestone("village_guard_completed", world_id, session_id=session_id)
        assert evt is not None
        assert evt["milestone_id"] == "village_guard_completed"
        assert evt["status"] == "achieved"

    def test_get_world_milestones_via_bridge(self):
        bridge = WorldBridge()
        result = bridge.open_world(name="BridgeWorld")
        world_id = result["world"]["world_id"]
        bridge.trigger_milestone("village_guard_completed", world_id)
        milestones = bridge.get_world_milestones(world_id)
        assert len(milestones) == 1
        assert milestones[0]["milestone_id"] == "village_guard_completed"

    def test_get_available_milestones_via_bridge(self):
        bridge = WorldBridge()
        result = bridge.open_world(name="BridgeWorld")
        world_id = result["world"]["world_id"]
        available = bridge.get_available_milestones(world_id)
        ids = [m["id"] for m in available]
        assert "village_guard_completed" in ids
        # trigger it
        bridge.trigger_milestone("village_guard_completed", world_id)
        available = bridge.get_available_milestones(world_id)
        ids = [m["id"] for m in available]
        assert "artifact_retrieved" in ids
        assert "village_guard_completed" not in ids

    def test_get_milestone_effects_via_bridge(self):
        bridge = WorldBridge()
        result = bridge.open_world(name="BridgeWorld")
        world_id = result["world"]["world_id"]
        bridge.trigger_milestone("village_guard_completed", world_id)
        effects = bridge.get_milestone_effects(world_id)
        assert len(effects) == 2

    def test_get_milestone_narration_via_bridge(self):
        bridge = WorldBridge()
        result = bridge.open_world(name="BridgeWorld")
        world_id = result["world"]["world_id"]
        bridge.trigger_milestone("village_guard_completed", world_id)
        hooks = bridge.get_milestone_narration(world_id)
        assert len(hooks) == 1
        assert hooks[0]["scope"] == "region"


if __name__ == "__main__":
    suites = [
        TestWorldLibrary,
        TestWorldSession,
        TestWorldBridge,
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
