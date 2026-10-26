"""
Tests for RPG-02-15 Offline Read-Only Mode.
Run with: python -m pytest tests/test_offline_mode.py -v
or:       python tests/test_offline_mode.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from offline_mode import OfflineMode, OfflineModeError


class TestOfflineMode(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmpdir, "data")
        os.makedirs(self.data_dir)
        # Create a couple of test data files
        with open(os.path.join(self.data_dir, "abilities.json"), "w", encoding="utf-8") as f:
            json.dump({"abilities": [{"id": "fireball", "name": "Fireball"}]}, f)
        with open(os.path.join(self.data_dir, "quests.json"), "w", encoding="utf-8") as f:
            json.dump({"quests": [{"id": "q1", "name": "First Quest"}]}, f)
        with open(os.path.join(self.data_dir, "readme.txt"), "w", encoding="utf-8") as f:
            f.write("not json")

        self.cache_dir = os.path.join(self.tmpdir, "cache")
        self.mode = OfflineMode(
            data_directory=self.data_dir,
            offline_cache_dir=self.cache_dir,
        )

    def tearDown(self):
        # Clean up cache dir between tests
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def test_initially_not_offline(self):
        self.assertFalse(self.mode.is_offline())

    def test_enable_enters_offline_mode(self):
        result = self.mode.enable()
        self.assertTrue(result["success"])
        self.assertTrue(result["offline"])
        self.assertIsNotNone(result["enabled_at"])
        self.assertEqual(result["cached_files"], 2)  # only .json files
        self.assertTrue(self.mode.is_offline())

    def test_enable_creates_cached_files(self):
        self.mode.enable()
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, "data", "abilities.json")))
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, "data", "quests.json")))
        # Non-json file should not be cached
        self.assertFalse(os.path.exists(os.path.join(self.cache_dir, "data", "readme.txt")))

    def test_disable_exits_offline_mode(self):
        self.mode.enable()
        result = self.mode.disable()
        self.assertTrue(result["success"])
        self.assertFalse(result["offline"])
        self.assertIsNotNone(result["disabled_at"])
        self.assertFalse(self.mode.is_offline())

    def test_enable_twice_is_idempotent(self):
        r1 = self.mode.enable()
        r2 = self.mode.enable()
        self.assertTrue(r1["success"])
        self.assertTrue(r2["success"])
        self.assertTrue(self.mode.is_offline())

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def test_status_when_offline(self):
        self.mode.enable()
        status = self.mode.status()
        self.assertTrue(status["offline"])
        self.assertEqual(status["cached_files"], 2)
        self.assertTrue(status["cache_exists"])

    def test_status_when_online(self):
        status = self.mode.status()
        self.assertFalse(status["offline"])
        self.assertFalse(status["cache_exists"])

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def test_get_cached_data_path_offline(self):
        self.mode.enable()
        path = self.mode.get_cached_data_path("abilities.json")
        self.assertIsNotNone(path)
        self.assertTrue(path.startswith(self.cache_dir))

    def test_get_cached_data_path_online(self):
        path = self.mode.get_cached_data_path("abilities.json")
        self.assertIsNotNone(path)
        self.assertTrue(path.startswith(self.data_dir))

    def test_get_cached_data_path_missing_file(self):
        path = self.mode.get_cached_data_path("nonexistent.json")
        self.assertIsNone(path)

    def test_load_cached_data_offline(self):
        self.mode.enable()
        data = self.mode.load_cached_data("abilities.json")
        self.assertIsNotNone(data)
        self.assertEqual(data["abilities"][0]["id"], "fireball")

    def test_load_cached_data_online(self):
        data = self.mode.load_cached_data("quests.json")
        self.assertIsNotNone(data)
        self.assertEqual(data["quests"][0]["id"], "q1")

    def test_load_cached_data_missing(self):
        data = self.mode.load_cached_data("nonexistent.json")
        self.assertIsNone(data)

    def test_get_data_directory_offline(self):
        self.mode.enable()
        dd = self.mode.get_data_directory()
        self.assertTrue(dd.startswith(self.cache_dir))

    def test_get_data_directory_online(self):
        dd = self.mode.get_data_directory()
        self.assertEqual(dd, self.data_dir)

    # ------------------------------------------------------------------
    # Network guard
    # ------------------------------------------------------------------

    def test_require_online_raises_when_offline(self):
        self.mode.enable()
        with self.assertRaises(OfflineModeError):
            self.mode.require_online()

    def test_require_online_passes_when_online(self):
        self.mode.require_online()  # should not raise

    def test_offline_error_returns_dict(self):
        self.mode.enable()
        result = self.mode.offline_error("cloud_push")
        self.assertFalse(result["success"])
        self.assertIn("cloud_push", result["reason"])
        self.assertTrue(result["offline"])

    def test_offline_error_when_online(self):
        result = self.mode.offline_error("cloud_push")
        # Even when online, offline_error returns a dict (it does not raise)
        self.assertFalse(result["success"])

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def test_state_persists_across_instances(self):
        self.mode.enable()
        state_path = self.mode.state_path
        self.assertTrue(os.path.exists(state_path))

        # Create a new instance pointing at the same cache
        mode2 = OfflineMode(
            data_directory=self.data_dir,
            offline_cache_dir=self.cache_dir,
        )
        self.assertTrue(mode2.is_offline())
        self.assertEqual(mode2.status()["cached_files"], 2)

    def test_state_file_contents(self):
        self.mode.enable()
        with open(self.mode.state_path, encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertTrue(state["offline"])
        self.assertIn("abilities.json", state["cached_files"])
        self.assertIn("quests.json", state["cached_files"])

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_enable_with_missing_data_directory(self):
        empty_dir = os.path.join(self.tmpdir, "empty")
        os.makedirs(empty_dir, exist_ok=True)
        mode = OfflineMode(
            data_directory=empty_dir,
            offline_cache_dir=os.path.join(self.tmpdir, "empty_cache"),
        )
        result = mode.enable()
        self.assertTrue(result["success"])
        self.assertEqual(result["cached_files"], 0)

    def test_cached_files_survive_disable(self):
        self.mode.enable()
        self.mode.disable()
        # Cache files should still exist after disable
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, "data", "abilities.json")))
        self.assertTrue(self.mode.get_cached_data_path("abilities.json") is not None)


if __name__ == "__main__":
    unittest.main()
