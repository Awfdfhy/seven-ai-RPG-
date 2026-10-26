"""
RPG-12-11: Cloud Sync

Provides file-based cloud sync for RPG save state via a configurable
sync directory (OneDrive, Dropbox, Google Drive, etc.).  Creates versioned
backups, detects conflicts, and exposes push/pull/status operations.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from typing import Any

from world_persistence import WorldPersistence


class CloudSyncError(Exception):
    """Raised when a cloud sync operation fails."""


class CloudSyncManager:
    """
    File-based cloud sync manager.

    Layout under `cloud_dir`:
      latest.json         -> last successfully synced full state
      local_mirror.json   -> last known local state (for conflict detection)
      backups/            -> timestamped snapshot backups, oldest pruned first
      sync_meta.json      -> high-level sync metadata (timestamps, counts)
    """

    def __init__(self, cloud_dir: str | None = None) -> None:
        self.cloud_dir = cloud_dir or os.path.join(
            os.path.expanduser("~"), "seven-rpg-cloud"
        )
        self.latest_path = os.path.join(self.cloud_dir, "latest.json")
        self.local_mirror_path = os.path.join(self.cloud_dir, "local_mirror.json")
        self.meta_path = os.path.join(self.cloud_dir, "sync_meta.json")
        self.backups_dir = os.path.join(self.cloud_dir, "backups")
        self._max_backups = 20
        os.makedirs(self.cloud_dir, exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push(self, persistence: WorldPersistence) -> dict[str, Any]:
        """
        Push local state to the cloud. Creates a versioned backup first,
        then writes `latest.json` and updates metadata.

        Returns:
            {"success": bool, "backup": str, "path": str,
             "worlds": int, "sessions": int, ...}
        """
        tmp_path = self._tmp_path("push")
        info = persistence.save(tmp_path)
        if not info.get("success"):
            raise CloudSyncError(f"Save failed: {info}")

        # Create versioned backup
        backup_path = self._create_backup(tmp_path)
        # Write latest cloud snapshot
        shutil.copy2(tmp_path, self.latest_path)
        # Update local mirror so conflict detection has a baseline
        shutil.copy2(tmp_path, self.local_mirror_path)
        os.remove(tmp_path)

        meta = self._read_meta()
        meta.update({
            "last_push": self._now_iso(),
            "last_push_worlds": info.get("worlds", 0),
            "last_push_sessions": info.get("sessions", 0),
        })
        self._write_meta(meta)
        self._prune_backups()

        return {
            "success": True,
            "backup": backup_path,
            "path": self.latest_path,
            **{k: info.get(k) for k in
               ["worlds", "sessions", "milestone_events", "tutorial_instances"]
               if k in info},
        }

    def pull(self, persistence: WorldPersistence) -> dict[str, Any]:
        """
        Pull cloud state into the local persistence object.

        Raises CloudSyncError if the cloud has no save data yet.

        Returns:
            {"success": bool, "path": str, "worlds": int, "sessions": int, ...}
        """
        if not os.path.exists(self.latest_path):
            raise CloudSyncError(
                "No cloud save found. Run push() first."
            )
        info = persistence.load(self.latest_path)
        info["path"] = self.latest_path
        meta = self._read_meta()
        meta["last_pull"] = self._now_iso()
        self._write_meta(meta)
        return info

    def sync_status(self, persistence: WorldPersistence) -> dict[str, Any]:
        """
        Return current sync status including conflict detection.

        Conflict: local state and cloud state both changed since the last
        known common baseline (local_mirror.json).
        """
        meta = self._read_meta()
        local_modified = self._modified_since(
            self.local_mirror_path
        ) if os.path.exists(self.local_mirror_path) else None
        cloud_modified = self._modified_since(
            self.latest_path
        ) if os.path.exists(self.latest_path) else None
        conflict = (
            local_modified is not None
            and cloud_modified is not None
            and local_modified > cloud_modified
            and meta.get("last_push")
            and datetime.fromisoformat(meta["last_push"]) < local_modified
        )
        return {
            "cloud_dir": self.cloud_dir,
            "latest_exists": os.path.exists(self.latest_path),
            "local_mirror_exists": os.path.exists(self.local_mirror_path),
            "backups_count": len(self._list_backups()),
            "last_push": meta.get("last_push"),
            "last_pull": meta.get("last_pull"),
            "conflict_detected": conflict,
            "local_modified": self._iso(local_modified),
            "cloud_modified": self._iso(cloud_modified),
        }

    def list_backups(self) -> list[dict[str, Any]]:
        """Return metadata about all versioned backups."""
        result = []
        for path in sorted(self._list_backups(), reverse=True):
            result.append({
                "path": path,
                "filename": os.path.basename(path),
                "size_bytes": os.path.getsize(path),
                "modified": self._iso(self._mtime(path)),
            })
        return result

    def restore_backup(self, persistence: WorldPersistence, filename: str) -> dict[str, Any]:
        """
        Restore a specific backup file into `persistence`.

        The backup file must exist under `backups/`.
        """
        path = os.path.join(self.backups_dir, filename)
        if not os.path.exists(path):
            raise CloudSyncError(f"Backup not found: {path}")
        info = persistence.load(path)
        info["path"] = path
        return info

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _tmp_path(self, prefix: str) -> str:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.cloud_dir, f".tmp_{prefix}_{ts}.json")

    def _create_backup(self, source_path: str) -> str:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        backup_path = os.path.join(self.backups_dir, f"backup_{ts}.json")
        shutil.copy2(source_path, backup_path)
        return backup_path

    def _list_backups(self) -> list[str]:
        if not os.path.isdir(self.backups_dir):
            return []
        return [
            os.path.join(self.backups_dir, f)
            for f in os.listdir(self.backups_dir)
            if f.startswith("backup_") and f.endswith(".json")
        ]

    def _prune_backups(self) -> None:
        backups = sorted(self._list_backups())
        while len(backups) > self._max_backups:
            oldest = backups.pop(0)
            os.remove(oldest)

    def _read_meta(self) -> dict[str, Any]:
        if os.path.exists(self.meta_path):
            with open(self.meta_path, encoding="utf-8") as fh:
                return json.load(fh)
        return {}

    def _write_meta(self, meta: dict[str, Any]) -> None:
        with open(self.meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2)

    def _modified_since(self, path: str) -> datetime | None:
        """Return mtime as datetime, or None if file missing."""
        if not os.path.exists(path):
            return None
        return datetime.fromtimestamp(os.path.getmtime(path), tz=UTC)

    def _mtime(self, path: str) -> datetime:
        return datetime.fromtimestamp(os.path.getmtime(path), tz=UTC)

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()

    def _iso(self, dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None
