"""
RPG-11-04: Update System tests.
Run with: python -m pytest tests/test_update_system.py -v
or:       python tests/test_update_system.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from update_system import ContentUpdate, UpdateManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_update(tmpdir: str, update_id: str, version: str, changes: list[dict]) -> str:
    updates_dir = os.path.join(tmpdir, "data", "updates")
    os.makedirs(updates_dir, exist_ok=True)
    update = ContentUpdate(
        id=update_id,
        version=version,
        description=f"Test update {update_id}",
        changes=changes,
    )
    path = os.path.join(updates_dir, f"{update_id}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(update.to_dict(), fh)
    return path


def _create_data_file(tmpdir: str, filename: str, content) -> str:
    data_dir = os.path.join(tmpdir, "data")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(content, fh, indent=2)
    return path


# ---------------------------------------------------------------------------
# ContentUpdate tests
# ---------------------------------------------------------------------------

class TestContentUpdate(unittest.TestCase):
    def test_roundtrip(self):
        update = ContentUpdate(
            id="add_sword",
            version="1.1.0",
            description="Add iron sword",
            changes=[{"action": "add", "target": "items.json", "entry": {"id": "iron_sword"}}],
        )
        data = update.to_dict()
        restored = ContentUpdate.from_dict(data)
        self.assertEqual(restored.id, "add_sword")
        self.assertEqual(restored.version, "1.1.0")
        self.assertEqual(len(restored.changes), 1)

    def test_from_dict_defaults(self):
        update = ContentUpdate.from_dict({"id": "x"})
        self.assertEqual(update.id, "x")
        self.assertEqual(update.version, "")
        self.assertEqual(update.changes, [])
        self.assertEqual(update.applied_at, "")


# ---------------------------------------------------------------------------
# UpdateManager tests
# ---------------------------------------------------------------------------

class TestUpdateManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmpdir, "data")
        os.makedirs(self.data_dir)

    def _make_manager(self):
        return UpdateManager(data_directory=self.data_dir)

    # Discovery

    def test_discover_empty(self):
        mgr = self._make_manager()
        self.assertEqual(mgr.discover(), [])

    def test_discover_single_update(self):
        _create_update(self.tmpdir, "add_ability", "1.1.0", [])
        mgr = self._make_manager()
        mgr.discover()
        self.assertEqual(len(mgr.list_updates()), 1)
        self.assertEqual(mgr.get_update("add_ability").version, "1.1.0")

    def test_discover_multiple_updates_sorted_by_version(self):
        _create_update(self.tmpdir, "u2", "1.2.0", [])
        _create_update(self.tmpdir, "u1", "1.1.0", [])
        mgr = self._make_manager()
        ids = mgr.discover()
        self.assertEqual(ids, ["u1", "u2"])

    # Status

    def test_is_applied_initially_false(self):
        mgr = self._make_manager()
        self.assertFalse(mgr.is_applied("anything"))

    def test_get_pending_returns_unapplied(self):
        _create_update(self.tmpdir, "u1", "1.1.0", [])
        mgr = self._make_manager()
        mgr.discover()
        pending = mgr.get_pending_updates()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].id, "u1")

    # Apply: add to dict-based file

    def test_apply_add_to_dict_file(self):
        _create_data_file(
            self.tmpdir,
            "abilities.json",
            {"abilities": [{"id": "fireball", "name": "Fireball"}]},
        )
        _create_update(
            self.tmpdir,
            "add_ability",
            "1.1.0",
            [
                {
                    "action": "add",
                    "target": "abilities.json",
                    "key": "abilities",
                    "entry": {"id": "icebolt", "name": "Icebolt"},
                }
            ],
        )
        mgr = self._make_manager()
        mgr.discover()
        result = mgr.apply_update("add_ability")
        self.assertTrue(result["success"])
        with open(os.path.join(self.data_dir, "abilities.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(len(data["abilities"]), 2)
        self.assertEqual(data["abilities"][1]["id"], "icebolt")

    # Apply: add to list-based file

    def test_apply_add_to_list_file(self):
        _create_data_file(
            self.tmpdir,
            "milestones.json",
            [{"id": "m1", "name": "First"}],
        )
        _create_update(
            self.tmpdir,
            "add_milestone",
            "1.1.0",
            [
                {
                    "action": "add",
                    "target": "milestones.json",
                    "entry": {"id": "m2", "name": "Second"},
                }
            ],
        )
        mgr = self._make_manager()
        mgr.discover()
        mgr.apply_update("add_milestone")
        with open(os.path.join(self.data_dir, "milestones.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[1]["id"], "m2")

    # Apply: modify

    def test_apply_modify_existing_entry(self):
        _create_data_file(
            self.tmpdir,
            "world_locations.json",
            [{"id": "oakhaven", "name": "Oakhaven", "danger_level": 1}],
        )
        _create_update(
            self.tmpdir,
            "modify_danger",
            "1.1.0",
            [
                {
                    "action": "modify",
                    "target": "world_locations.json",
                    "id": "oakhaven",
                    "entry": {"danger_level": 5},
                }
            ],
        )
        mgr = self._make_manager()
        mgr.discover()
        mgr.apply_update("modify_danger")
        with open(os.path.join(self.data_dir, "world_locations.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data[0]["danger_level"], 5)
        self.assertEqual(data[0]["name"], "Oakhaven")

    # Apply: remove

    def test_apply_remove_entry(self):
        _create_data_file(
            self.tmpdir,
            "abilities.json",
            {"abilities": [
                {"id": "fireball", "name": "Fireball"},
                {"id": "icebolt", "name": "Icebolt"},
            ]},
        )
        _create_update(
            self.tmpdir,
            "remove_icebolt",
            "1.1.0",
            [
                {
                    "action": "remove",
                    "target": "abilities.json",
                    "id": "icebolt",
                }
            ],
        )
        mgr = self._make_manager()
        mgr.discover()
        mgr.apply_update("remove_icebolt")
        with open(os.path.join(self.data_dir, "abilities.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(len(data["abilities"]), 1)
        self.assertEqual(data["abilities"][0]["id"], "fireball")

    # Already applied guard

    def test_apply_twice_returns_false(self):
        _create_update(self.tmpdir, "u1", "1.1.0", [])
        mgr = self._make_manager()
        mgr.discover()
        mgr.apply_update("u1")
        result = mgr.apply_update("u1")
        self.assertFalse(result["success"])
        self.assertIn("already applied", result["reason"])

    # Pending after apply

    def test_pending_clears_after_apply(self):
        _create_update(self.tmpdir, "u1", "1.1.0", [])
        mgr = self._make_manager()
        mgr.discover()
        mgr.apply_update("u1")
        self.assertEqual(len(mgr.get_pending_updates()), 0)

    # apply_all_pending

    def test_apply_all_pending(self):
        _create_data_file(
            self.tmpdir,
            "items.json",
            {"items": [{"id": "a"}]},
        )
        _create_update(
            self.tmpdir,
            "u1",
            "1.1.0",
            [
                {
                    "action": "add",
                    "target": "items.json",
                    "key": "items",
                    "entry": {"id": "b"},
                }
            ],
        )
        _create_update(
            self.tmpdir,
            "u2",
            "1.2.0",
            [
                {
                    "action": "add",
                    "target": "items.json",
                    "key": "items",
                    "entry": {"id": "c"},
                }
            ],
        )
        mgr = self._make_manager()
        mgr.discover()
        results = mgr.apply_all_pending()
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["success"] for r in results))
        with open(os.path.join(self.data_dir, "items.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(len(data["items"]), 3)

    # Rollback

    def test_rollback(self):
        _create_update(self.tmpdir, "u1", "1.1.0", [])
        mgr = self._make_manager()
        mgr.discover()
        mgr.apply_update("u1")
        self.assertTrue(mgr.is_applied("u1"))
        result = mgr.rollback("u1")
        self.assertTrue(result["success"])
        self.assertFalse(mgr.is_applied("u1"))

    def test_rollback_not_applied(self):
        mgr = self._make_manager()
        result = mgr.rollback("u1")
        self.assertFalse(result["success"])

    # State persistence

    def test_export_import_state(self):
        _create_update(self.tmpdir, "u1", "1.1.0", [])
        mgr = self._make_manager()
        mgr.discover()
        mgr.apply_update("u1")
        state = mgr.export_state()
        self.assertIn("u1", state["applied"])

        mgr2 = UpdateManager(data_directory=self.data_dir)
        mgr2.import_state(state)
        self.assertTrue(mgr2.is_applied("u1"))

    # Missing target file

    def test_apply_missing_target_file(self):
        _create_update(
            self.tmpdir,
            "u1",
            "1.1.0",
            [{"action": "add", "target": "nonexistent.json", "entry": {}}],
        )
        mgr = self._make_manager()
        mgr.discover()
        result = mgr.apply_update("u1")
        self.assertFalse(result["success"])
        self.assertIn("not found", result["reason"])

    # Unknown update

    def test_apply_unknown_update(self):
        mgr = self._make_manager()
        result = mgr.apply_update("nonexistent")
        self.assertFalse(result["success"])
        self.assertIn("not found", result["reason"])


if __name__ == "__main__":
    unittest.main()
