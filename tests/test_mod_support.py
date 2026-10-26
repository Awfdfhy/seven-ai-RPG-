"""
RPG-11-01: Mod Support System tests.
Run with: python -m pytest tests/test_mod_support.py -v
or:       python tests/test_mod_support.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mod_integration import integrate_skill_tree_manager
from mod_manager import ModDefinition, ModManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_mod(base_dir: str, mod_id: str, enabled: bool = True) -> str:
    mod_dir = os.path.join(base_dir, mod_id)
    data_dir = os.path.join(mod_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    manifest = {
        "id": mod_id,
        "name": f"Test Mod {mod_id}",
        "version": "1.0.0",
        "description": "A test mod.",
        "author": "Test",
        "enabled": enabled,
    }
    with open(os.path.join(mod_dir, "mod.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)
    with open(os.path.join(data_dir, "test_data.json"), "w", encoding="utf-8") as fh:
        json.dump({"test": True}, fh)
    return mod_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestModDefinition(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        mod = ModDefinition(
            id="test",
            name="Test",
            version="1.0.0",
            description="desc",
            author="author",
            enabled=False,
            path="/mods/test",
            data_files=["data/a.json"],
            metadata={"key": "value"},
        )
        data = mod.to_dict()
        restored = ModDefinition.from_dict(data)
        self.assertEqual(restored.id, "test")
        self.assertEqual(restored.name, "Test")
        self.assertEqual(restored.version, "1.0.0")
        self.assertEqual(restored.description, "desc")
        self.assertEqual(restored.author, "author")
        self.assertFalse(restored.enabled)
        self.assertEqual(restored.path, "/mods/test")
        self.assertEqual(restored.data_files, ["data/a.json"])
        self.assertEqual(restored.metadata, {"key": "value"})

    def test_from_dict_defaults(self):
        data = {"id": "minimal"}
        mod = ModDefinition.from_dict(data)
        self.assertEqual(mod.id, "minimal")
        self.assertEqual(mod.name, "minimal")
        self.assertEqual(mod.version, "0.0.0")
        self.assertTrue(mod.enabled)
        self.assertEqual(mod.data_files, [])


class TestModManagerDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mods_dir = os.path.join(self.tmpdir, "mods")
        os.makedirs(self.mods_dir)

    def test_discover_empty(self):
        mgr = ModManager(self.mods_dir)
        self.assertEqual(mgr.discover(), [])
        self.assertEqual(mgr.list_mods(), [])

    def test_discover_single_mod(self):
        _create_test_mod(self.mods_dir, "mod_a")
        mgr = ModManager(self.mods_dir)
        discovered = mgr.discover()
        self.assertEqual(discovered, ["mod_a"])
        self.assertEqual(len(mgr.list_mods()), 1)
        mod = mgr.get_mod("mod_a")
        self.assertIsNotNone(mod)
        self.assertTrue(mod.enabled)
        self.assertIn("test_data.json", mod.data_files[0])

    def test_discover_multiple_mods(self):
        _create_test_mod(self.mods_dir, "mod_a")
        _create_test_mod(self.mods_dir, "mod_b")
        mgr = ModManager(self.mods_dir)
        discovered = mgr.discover()
        self.assertEqual(sorted(discovered), ["mod_a", "mod_b"])

    def test_discover_ignores_non_mod_dirs(self):
        os.makedirs(os.path.join(self.mods_dir, "random_folder"))
        _create_test_mod(self.mods_dir, "mod_a")
        mgr = ModManager(self.mods_dir)
        discovered = mgr.discover()
        self.assertEqual(discovered, ["mod_a"])

    def test_discover_skips_invalid_manifest(self):
        bad_dir = os.path.join(self.mods_dir, "bad_mod")
        os.makedirs(bad_dir)
        with open(os.path.join(bad_dir, "mod.json"), "w", encoding="utf-8") as fh:
            fh.write("not json")
        _create_test_mod(self.mods_dir, "good_mod")
        mgr = ModManager(self.mods_dir)
        discovered = mgr.discover()
        self.assertEqual(discovered, ["good_mod"])

    def test_discover_auto_discovers_data_files(self):
        _create_test_mod(self.mods_dir, "mod_a")
        mgr = ModManager(self.mods_dir)
        mgr.discover()
        mod = mgr.get_mod("mod_a")
        self.assertEqual(len(mod.data_files), 1)
        self.assertTrue(mod.data_files[0].endswith("test_data.json"))


class TestModManagerState(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mods_dir = os.path.join(self.tmpdir, "mods")
        os.makedirs(self.mods_dir)
        _create_test_mod(self.mods_dir, "mod_a", enabled=True)
        _create_test_mod(self.mods_dir, "mod_b", enabled=False)
        self.mgr = ModManager(self.mods_dir)
        self.mgr.discover()

    def test_get_enabled_mods(self):
        enabled = self.mgr.get_enabled_mods()
        self.assertEqual(len(enabled), 1)
        self.assertEqual(enabled[0].id, "mod_a")

    def test_get_disabled_mods(self):
        disabled = self.mgr.get_disabled_mods()
        self.assertEqual(len(disabled), 1)
        self.assertEqual(disabled[0].id, "mod_b")

    def test_is_enabled(self):
        self.assertTrue(self.mgr.is_enabled("mod_a"))
        self.assertFalse(self.mgr.is_enabled("mod_b"))
        self.assertFalse(self.mgr.is_enabled("nonexistent"))

    def test_enable_disable(self):
        self.assertTrue(self.mgr.enable_mod("mod_a"))
        self.assertTrue(self.mgr.is_enabled("mod_a"))
        self.assertTrue(self.mgr.disable_mod("mod_a"))
        self.assertFalse(self.mgr.is_enabled("mod_a"))
        self.assertTrue(self.mgr.enable_mod("mod_b"))
        self.assertTrue(self.mgr.is_enabled("mod_b"))
        self.assertTrue(self.mgr.disable_mod("mod_b"))
        self.assertFalse(self.mgr.is_enabled("mod_b"))
        self.assertFalse(self.mgr.is_enabled("mod_a"))
        self.assertFalse(self.mgr.enable_mod("nonexistent"))

    def test_get_mod(self):
        self.assertIsNotNone(self.mgr.get_mod("mod_a"))
        self.assertIsNone(self.mgr.get_mod("nonexistent"))

    def test_list_mods(self):
        mods = self.mgr.list_mods()
        self.assertEqual(len(mods), 2)
        ids = {m["id"] for m in mods}
        self.assertEqual(ids, {"mod_a", "mod_b"})


class TestModManagerDataPaths(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mods_dir = os.path.join(self.tmpdir, "mods")
        os.makedirs(self.mods_dir)
        _create_test_mod(self.mods_dir, "mod_a", enabled=True)
        _create_test_mod(self.mods_dir, "mod_b", enabled=False)
        self.mgr = ModManager(self.mods_dir)
        self.mgr.discover()

    def test_get_enabled_mod_data_directories(self):
        dirs = self.mgr.get_enabled_mod_data_directories()
        self.assertEqual(len(dirs), 1)
        self.assertTrue(
            dirs[0].replace("\\", "/").endswith("mods/mod_a/data")
        )

    def test_get_mod_data_files(self):
        paths = self.mgr.get_mod_data_files("test_data.json")
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].endswith("test_data.json"))


class TestModIntegration(unittest.TestCase):
    def test_integrate_skill_tree_manager(self):
        from skill_tree_manager import SkillTreeManager

        tmpdir = tempfile.mkdtemp()
        data_dir = os.path.join(tmpdir, "data")
        os.makedirs(data_dir)
        tree_def = {
            "id": "mod_tree",
            "name": "Mod Tree",
            "description": "Added by mod.",
            "nodes": [
                {
                    "id": "mod_tree.root",
                    "name": "Mod Root",
                    "description": "",
                    "category": "combat",
                    "node_type": "root",
                    "max_rank": 1,
                    "point_cost": 0,
                    "parent_ids": [],
                }
            ],
        }
        with open(os.path.join(data_dir, "mod_tree.json"), "w", encoding="utf-8") as fh:
            json.dump(tree_def, fh)

        mgr = SkillTreeManager()
        self.assertIsNone(mgr.get_tree("mod_tree"))
        integrate_skill_tree_manager(mgr, data_dir)
        self.assertIsNotNone(mgr.get_tree("mod_tree"))
        self.assertEqual(mgr.get_tree("mod_tree").name, "Mod Tree")


class TestExampleMod(unittest.TestCase):
    def test_example_mod_manifest_exists(self):
        manifest_path = os.path.join(
            os.path.dirname(__file__), "..", "mods", "example_mod", "mod.json"
        )
        self.assertTrue(os.path.isfile(manifest_path))
        with open(manifest_path, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["id"], "example_mod")
        self.assertTrue(data["enabled"])
        self.assertEqual(data["version"], "1.0.0")

    def test_example_mod_data_file_exists(self):
        data_path = os.path.join(
            os.path.dirname(__file__), "..", "mods", "example_mod", "data", "skill_tree.json"
        )
        self.assertTrue(os.path.isfile(data_path))
        with open(data_path, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertIn("id", data)
        self.assertEqual(data["id"], "example_tree")


if __name__ == "__main__":
    unittest.main()
