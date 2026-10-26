"""
Tests for RPG-10-03 World Persistence.

Run with: python -m pytest tests/ -v
or:       python tests/test_world_persistence.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from milestone import MilestoneManager
from world_library import WorldLibrary
from world_persistence import WorldPersistence
from world_session import WorldSessionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_persistence():
    lib = WorldLibrary()
    lib.create_world(name="Azeroth", description="The world of warcraft.")
    lib.create_world(name="Krynn", description="Dragonlance.")
    sessions = WorldSessionManager()
    s = sessions.create_session("some-world", metadata={"hero": "Thrall"})
    return WorldPersistence(library=lib, sessions=sessions), s


def _write_tmp(suffix=".json") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


# ---------------------------------------------------------------------------
# WorldPersistence tests
# ---------------------------------------------------------------------------

class TestWorldPersistence:
    def test_save_and_load_full_state(self):
        pers, s = _make_persistence()
        path = _write_tmp()

        save_info = pers.save(path)
        assert save_info["success"] is True
        assert save_info["worlds"] == 2
        assert save_info["sessions"] == 1

        # Load into fresh instances
        pers2 = WorldPersistence(library=WorldLibrary(), sessions=WorldSessionManager())
        load_info = pers2.load(path)
        assert load_info["success"] is True
        assert load_info["worlds"] == 2
        assert load_info["sessions"] == 1

        names = [w["name"] for w in pers2.library.list_worlds(include_archived=True)]
        assert "Azeroth" in names
        assert "Krynn" in names

        session = pers2.sessions.get_session(s.session_id)
        assert session is not None
        assert session.metadata.get("hero") == "Thrall"

        os.remove(path)

    def test_save_creates_nested_dirs(self):
        pers, _ = _make_persistence()
        tmpdir = tempfile.mkdtemp()
        nested = os.path.join(tmpdir, "nested", "dir", "save.json")

        info = pers.save(nested)
        assert info["success"] is True
        assert os.path.exists(nested)

        os.remove(nested)
        os.rmdir(os.path.dirname(nested))
        os.rmdir(os.path.dirname(os.path.dirname(nested)))
        os.rmdir(tmpdir)

    def test_load_missing_file_raises(self):
        pers, _ = _make_persistence()
        try:
            pers.load("/no/such/path/world_state.json")
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("Expected FileNotFoundError")

    def test_save_library_only(self):
        pers, _ = _make_persistence()
        path = _write_tmp()

        info = pers.save_library(path)
        assert info["success"] is True
        assert info["worlds"] == 2

        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        assert "sessions" not in payload
        assert "worlds" in payload

        os.remove(path)

    def test_load_library_only(self):
        pers, _ = _make_persistence()
        path = _write_tmp()
        pers.save_library(path)

        fresh = WorldPersistence(library=WorldLibrary(), sessions=WorldSessionManager())
        info = fresh.load_library(path)
        assert info["success"] is True
        assert info["worlds"] == 2
        assert len(fresh.sessions._sessions) == 0

        os.remove(path)

    def test_roundtrip_preserves_archived_status(self):
        pers, _ = _make_persistence()
        w = pers.library.create_world(name="Old")
        pers.library.archive_world(w.world_id)
        path = _write_tmp()

        pers.save(path)
        pers2 = WorldPersistence(library=WorldLibrary(), sessions=WorldSessionManager())
        pers2.load(path)

        entry = pers2.library.get_world(w.world_id)
        assert entry.status == "archived"

        os.remove(path)

    def test_roundtrip_preserves_session_snapshot(self):
        pers, _ = _make_persistence()
        path = _write_tmp()

        session_id = next(iter(pers.sessions._sessions.values())).session_id
        pers.sessions.update_snapshot(session_id=session_id,
                                       snapshot={"hp": 42, "location": "oakhaven"})
        pers.save(path)

        pers2 = WorldPersistence(library=WorldLibrary(), sessions=WorldSessionManager())
        pers2.load(path)

        for s in pers2.sessions._sessions.values():
            assert s.snapshot.get("hp") == 42
            assert s.snapshot.get("location") == "oakhaven"

        os.remove(path)

    def test_save_and_load_with_milestones(self):
        lib = WorldLibrary()
        sessions = WorldSessionManager()
        milestones = MilestoneManager()

        w = lib.create_world(name="SaveWorld", description="with milestones")
        s = sessions.create_session(w.world_id)
        milestones.trigger_milestone("village_guard_completed", w.world_id, session_id=s.session_id)
        milestones.trigger_milestone("shadow_mastery", w.world_id)

        pers = WorldPersistence(library=lib, sessions=sessions, milestones=milestones)
        path = _write_tmp()
        result = pers.save(path)
        assert result["success"] is True
        assert result["milestone_events"] == 2

        # Load into fresh instances
        lib2 = WorldLibrary()
        sessions2 = WorldSessionManager()
        milestones2 = MilestoneManager()
        pers2 = WorldPersistence(library=lib2, sessions=sessions2, milestones=milestones2)
        load_info = pers2.load(path)
        assert load_info["success"] is True
        assert load_info["milestone_events"] == 2
        assert milestones2.get_world_milestone_event("village_guard_completed", w.world_id) is not None
        assert milestones2.get_world_milestone_event("shadow_mastery", w.world_id) is not None

        os.remove(path)

    def test_roundtrip_preserves_milestone_effects(self):
        lib = WorldLibrary()
        sessions = WorldSessionManager()
        milestones = MilestoneManager()

        w = lib.create_world(name="EffectsWorld")
        s = sessions.create_session(w.world_id)
        milestones.trigger_milestone("village_guard_completed", w.world_id, session_id=s.session_id)

        pers = WorldPersistence(library=lib, sessions=sessions, milestones=milestones)
        path = _write_tmp()
        pers.save(path)

        lib2 = WorldLibrary()
        sessions2 = WorldSessionManager()
        milestones2 = MilestoneManager()
        pers2 = WorldPersistence(library=lib2, sessions=sessions2, milestones=milestones2)
        pers2.load(path)

        effects = milestones2.get_world_effects(w.world_id)
        assert len(effects) == 2
        types = [e["type"] for e in effects]
        assert "npc_reaction_modifier" in types
        assert "unlock_region" in types

        os.remove(path)


if __name__ == "__main__":
    suites = [TestWorldPersistence]
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
