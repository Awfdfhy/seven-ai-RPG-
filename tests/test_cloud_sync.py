"""
Tests for RPG-12-11 Cloud Sync.

Run with: python -m pytest tests/test_cloud_sync.py -v
or:       python tests/test_cloud_sync.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cloud_sync import CloudSyncError, CloudSyncManager
from world_library import WorldLibrary
from world_persistence import WorldPersistence
from world_session import WorldSessionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_persistence():
    lib = WorldLibrary()
    lib.create_world(name="Azeroth", description="The world of warcraft.")
    sessions = WorldSessionManager()
    s = sessions.create_session("some-world", metadata={"hero": "Thrall"})
    return WorldPersistence(library=lib, sessions=sessions), s


def _tmp_cloud_dir() -> str:
    return tempfile.mkdtemp(prefix="rpg_cloud_")


# ---------------------------------------------------------------------------
# CloudSyncManager tests
# ---------------------------------------------------------------------------

class TestCloudSyncManager:
    def test_push_creates_cloud_save(self):
        pers, _ = _make_persistence()
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())

        result = cloud.push(pers)
        assert result["success"] is True
        assert os.path.exists(cloud.latest_path)
        assert result["worlds"] == 1
        assert result["sessions"] == 1

    def test_push_creates_backup(self):
        pers, _ = _make_persistence()
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())

        cloud.push(pers)
        backups = cloud.list_backups()
        assert len(backups) >= 1
        assert backups[0]["filename"].startswith("backup_")

    def test_pull_restores_state(self):
        pers, session = _make_persistence()
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())
        cloud.push(pers)

        # Fresh state
        fresh = WorldPersistence(library=WorldLibrary(), sessions=WorldSessionManager())
        info = cloud.pull(fresh)
        assert info["success"] is True
        assert info["worlds"] == 1
        assert info["sessions"] == 1
        assert fresh.library.get_world(next(iter(fresh.library._worlds.keys()))).name == "Azeroth"

    def test_pull_raises_without_cloud_save(self):
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())
        try:
            cloud.pull(WorldPersistence())
        except CloudSyncError:
            pass
        else:
            raise AssertionError("Expected CloudSyncError")

    def test_sync_status_reports_no_conflict_initially(self):
        pers, _ = _make_persistence()
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())
        cloud.push(pers)

        status = cloud.sync_status(pers)
        assert status["latest_exists"] is True
        assert status["conflict_detected"] is False
        assert status["last_push"] is not None

    def test_sync_status_detects_conflict(self):
        pers, _ = _make_persistence()
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())
        cloud.push(pers)

        # Simulate local change
        time.sleep(0.05)
        pers.library.create_world(name="LocalOnly", description="changed locally")

        # Simulate cloud change by touching the latest file
        time.sleep(0.05)
        with open(cloud.latest_path, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "worlds": {}, "sessions": []}, fh)
        os.utime(cloud.latest_path, None)  # update mtime to now

        # Also update local mirror to simulate local change after push
        time.sleep(0.05)
        os.utime(cloud.local_mirror_path, None)

        status = cloud.sync_status(pers)
        assert status["conflict_detected"] is True

    def test_list_backups_returns_metadata(self):
        pers, _ = _make_persistence()
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())
        cloud.push(pers)

        backups = cloud.list_backups()
        assert len(backups) == 1
        assert backups[0]["size_bytes"] > 0
        assert "modified" in backups[0]

    def test_restore_backup(self):
        pers, _ = _make_persistence()
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())
        cloud.push(pers)

        fresh = WorldPersistence(library=WorldLibrary(), sessions=WorldSessionManager())
        backup_name = cloud.list_backups()[0]["filename"]
        info = cloud.restore_backup(fresh, backup_name)
        assert info["success"] is True
        assert info["worlds"] == 1

    def test_restore_backup_raises_for_missing_file(self):
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())
        try:
            cloud.restore_backup(WorldPersistence(), "nonexistent.json")
        except CloudSyncError:
            pass
        else:
            raise AssertionError("Expected CloudSyncError")

    def test_prune_backups_respects_limit(self):
        pers, _ = _make_persistence()
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())
        cloud._max_backups = 3

        for _ in range(5):
            cloud.push(pers)
            time.sleep(0.01)

        backups = cloud.list_backups()
        assert len(backups) <= 3

    def test_push_twice_keeps_multiple_backups(self):
        pers, _ = _make_persistence()
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())

        cloud.push(pers)
        time.sleep(0.05)
        cloud.push(pers)

        backups = cloud.list_backups()
        assert len(backups) >= 2

    def test_pull_updates_last_pull_meta(self):
        pers, _ = _make_persistence()
        cloud = CloudSyncManager(cloud_dir=_tmp_cloud_dir())
        cloud.push(pers)

        fresh = WorldPersistence(library=WorldLibrary(), sessions=WorldSessionManager())
        cloud.pull(fresh)

        meta = cloud._read_meta()
        assert "last_pull" in meta

    def test_save_creates_nested_cloud_dir(self):
        nested = os.path.join(_tmp_cloud_dir(), "nested", "dir", "cloud")
        cloud = CloudSyncManager(cloud_dir=nested)
        pers, _ = _make_persistence()

        result = cloud.push(pers)
        assert result["success"] is True
        assert os.path.exists(cloud.latest_path)


if __name__ == "__main__":
    suites = [TestCloudSyncManager]
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
