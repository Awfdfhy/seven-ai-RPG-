"""
RPG-11-04: Update System
Manages content patches and data migrations for game updates.
Discovers update definitions, applies them to game data files, and tracks
which updates have been applied so they are not re-applied.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ContentUpdate:
    """
    Represents a single content update / patch.

    Attributes:
        id          : unique identifier (e.g. "v1_2_add_fireball")
        version     : target content version after this update (e.g. "1.2.0")
        description : human-readable summary of the change
        changes     : ordered list of patch operations to apply
        applied_at  : ISO timestamp set once the update is applied
    """

    id: str
    version: str
    description: str = ""
    changes: list[dict[str, Any]] = field(default_factory=list)
    applied_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "changes": copy.deepcopy(self.changes),
            "applied_at": self.applied_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ContentUpdate:
        return ContentUpdate(
            id=data["id"],
            version=data.get("version", ""),
            description=data.get("description", ""),
            changes=[copy.deepcopy(c) for c in data.get("changes", [])],
            applied_at=data.get("applied_at", ""),
        )


class UpdateManager:
    """
    Discovers update definitions, applies them to game data files,
    and tracks applied state.

    Usage:
        mgr = UpdateManager()  # defaults to data/ and data/updates/
        mgr.discover()
        result = mgr.apply_update("v1_2_add_fireball")
        pending = mgr.get_pending_updates()
    """

    def __init__(
        self,
        data_directory: str | None = None,
        updates_directory: str | None = None,
        backup_directory: str | None = None,
    ) -> None:
        if data_directory is None:
            data_directory = os.path.join(
                os.path.dirname(__file__), "..", "data"
            )
        self.data_directory = os.path.abspath(data_directory)

        if updates_directory is None:
            updates_directory = os.path.join(self.data_directory, "updates")
        self.updates_directory = os.path.abspath(updates_directory)

        if backup_directory is None:
            backup_directory = os.path.join(self.data_directory, "updates_backups")
        self.backup_directory = os.path.abspath(backup_directory)
        os.makedirs(self.backup_directory, exist_ok=True)

        self._updates: dict[str, ContentUpdate] = {}
        self._applied: dict[str, dict[str, Any]] = {}

        self._load_applied_state()

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _get_state_path(self) -> str:
        return os.path.join(self.data_directory, "update_state.json")

    def _load_applied_state(self) -> None:
        path = self._get_state_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self._applied = data.get("applied", {})
        except Exception:
            pass

    def _save_applied_state(self) -> None:
        path = self._get_state_path()
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"applied": self._applied}, fh, indent=2)

    # ------------------------------------------------------------------
    # Backups
    # ------------------------------------------------------------------

    def _create_backup(self, target_file: str) -> str | None:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        backup_name = f"backup_{ts}_{os.path.basename(target_file)}"
        backup_path = os.path.join(self.backup_directory, backup_name)
        try:
            shutil.copy2(
                os.path.join(self.data_directory, target_file),
                backup_path,
            )
            return backup_path
        except Exception:
            return None

    def list_backups(self, target_file: str | None = None) -> list[dict[str, Any]]:
        """Return metadata about available backups."""
        result: list[dict[str, Any]] = []
        if not os.path.isdir(self.backup_directory):
            return result
        prefix = "backup_"
        suffix = ".json"
        base = os.path.basename(target_file) if target_file else None
        for fname in sorted(os.listdir(self.backup_directory)):
            if not fname.startswith(prefix) or not fname.endswith(suffix):
                continue
            if base is not None and not fname.endswith(f"_{base}"):
                continue
            path = os.path.join(self.backup_directory, fname)
            try:
                size = os.path.getsize(path)
                mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=UTC)
                result.append({
                    "filename": fname,
                    "path": path,
                    "size_bytes": size,
                    "modified": mtime.isoformat(),
                })
            except Exception:
                continue
        return result

    def restore_backup(self, backup_filename: str) -> dict[str, Any]:
        """
        Restore a backup file back into the data directory.
        The backup filename must match ``backup_<ts>_<original_name>.json``.
        """
        backup_path = os.path.join(self.backup_directory, backup_filename)
        if not os.path.exists(backup_path):
            return {"success": False, "reason": f"Backup not found: {backup_filename}"}
        # Derive original filename from backup filename
        # backup_<ts>_<original>.json
        original = backup_filename[len("backup_"):]
        # Remove the timestamp prefix (<timestamp>_)
        parts = original.split("_", 1)
        if len(parts) == 2:
            original = parts[1]
        target_path = os.path.join(self.data_directory, original)
        try:
            shutil.copy2(backup_path, target_path)
            return {"success": True, "restored_to": target_path}
        except Exception as exc:
            return {"success": False, "reason": str(exc)}

    # ------------------------------------------------------------------
    # Patch application
    # ------------------------------------------------------------------

    def discover(self) -> list[str]:
        """
        Scan the updates directory for ``.json`` update definitions.
        Returns a list of discovered update IDs sorted by version.
        """
        discovered: list[str] = []
        if not os.path.isdir(self.updates_directory):
            return discovered
        for fname in sorted(os.listdir(self.updates_directory)):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self.updates_directory, fname)
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                update = ContentUpdate.from_dict(data)
                self._updates[update.id] = update
                discovered.append(update.id)
            except Exception:
                continue
        return sorted(discovered, key=lambda uid: self._updates[uid].version)

    def get_update(self, update_id: str) -> ContentUpdate | None:
        """Return the update definition, or None."""
        return self._updates.get(update_id)

    def list_updates(self) -> list[dict[str, Any]]:
        """Return all discovered updates as dictionaries."""
        return [
            u.to_dict() for u in sorted(self._updates.values(), key=lambda u: u.version)
        ]

    # ------------------------------------------------------------------
    # Status queries
    # ------------------------------------------------------------------

    def is_applied(self, update_id: str) -> bool:
        """True if the update has already been applied."""
        return update_id in self._applied

    def get_pending_updates(self) -> list[ContentUpdate]:
        """Return updates that have not yet been applied, in version order."""
        return [
            u
            for u in sorted(self._updates.values(), key=lambda u: u.version)
            if u.id not in self._applied
        ]

    def get_applied_updates(self) -> list[dict[str, Any]]:
        """Return applied update metadata."""
        return [
            {"id": uid, **info} for uid, info in self._applied.items()
        ]

    # ------------------------------------------------------------------
    # Patch application
    # ------------------------------------------------------------------

    def apply_update(self, update_id: str, *, backup: bool = True) -> dict[str, Any]:
        """
        Apply a single update by ID.

        Args:
            update_id: The update to apply.
            backup: If True, create file backups before applying.

        Returns ``{"success": True, ...}`` or ``{"success": False, "reason": ...}``.
        """
        update = self._updates.get(update_id)
        if update is None:
            return {"success": False, "reason": f"Update '{update_id}' not found."}
        if update_id in self._applied:
            return {"success": False, "reason": f"Update '{update_id}' already applied."}

        # Collect unique target files for backup
        targets: set[str] = set()
        if backup:
            for change in update.changes:
                target_file = change.get("target")
                if target_file:
                    targets.add(target_file)
            for target_file in targets:
                self._create_backup(target_file)

        results: list[dict[str, Any]] = []
        for change in update.changes:
            result = self._apply_change(change)
            results.append(result)

        failed = [r for r in results if not r.get("success")]
        if failed:
            return {
                "success": False,
                "reason": failed[0].get("reason", "Unknown failure"),
                "failures": failed,
            }

        self._applied[update_id] = {
            "applied_at": datetime.now(UTC).isoformat(),
            "changes": results,
        }
        self._save_applied_state()

        return {
            "success": True,
            "update_id": update_id,
            "version": update.version,
            "changes_applied": len(results),
        }

    def apply_all_pending(self, *, backup: bool = True) -> list[dict[str, Any]]:
        """Apply every pending update in version order."""
        results: list[dict[str, Any]] = []
        for update in self.get_pending_updates():
            results.append(self.apply_update(update.id, backup=backup))
        return results

    def dry_run_update(self, update_id: str) -> dict[str, Any]:
        """
        Simulate applying an update without writing to disk.

        Returns the same structure as apply_update but with
        ``dry_run: True`` in the result.
        """
        update = self._updates.get(update_id)
        if update is None:
            return {"success": False, "reason": f"Update '{update_id}' not found."}
        if update_id in self._applied:
            return {"success": False, "reason": f"Update '{update_id}' already applied."}

        results: list[dict[str, Any]] = []
        for change in update.changes:
            result = self._dry_run_change(change)
            results.append(result)

        failed = [r for r in results if not r.get("success")]
        if failed:
            return {
                "success": False,
                "reason": failed[0].get("reason", "Unknown failure"),
                "failures": failed,
                "dry_run": True,
            }

        return {
            "success": True,
            "update_id": update_id,
            "version": update.version,
            "changes_applied": len(results),
            "dry_run": True,
        }

    def _apply_change(self, change: dict[str, Any]) -> dict[str, Any]:
        action = change.get("action")
        target_file = change.get("target")
        if not target_file or not action:
            return {"success": False, "reason": "Change missing 'action' or 'target'."}

        target_path = os.path.join(self.data_directory, target_file)
        if not os.path.exists(target_path):
            return {
                "success": False,
                "reason": f"Target file not found: {target_file}",
            }

        try:
            with open(target_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            return {"success": False, "reason": f"Failed to load {target_file}: {exc}"}

        try:
            if action == "add":
                self._do_add(data, change)
            elif action == "modify":
                self._do_modify(data, change)
            elif action == "remove":
                self._do_remove(data, change)
            elif action == "increment":
                self._do_increment(data, change)
            else:
                return {"success": False, "reason": f"Unknown action '{action}'."}
        except Exception as exc:
            return {"success": False, "reason": str(exc)}

        try:
            with open(target_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            return {"success": True, "action": action, "target": target_file}
        except Exception as exc:
            return {"success": False, "reason": f"Failed to write {target_file}: {exc}"}

    def _dry_run_change(self, change: dict[str, Any]) -> dict[str, Any]:
        """
        Simulate a change on a copy of the data without writing to disk.
        """
        action = change.get("action")
        target_file = change.get("target")
        if not target_file or not action:
            return {"success": False, "reason": "Change missing 'action' or 'target'."}

        target_path = os.path.join(self.data_directory, target_file)
        if not os.path.exists(target_path):
            return {
                "success": False,
                "reason": f"Target file not found: {target_file}",
            }

        try:
            with open(target_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            return {"success": False, "reason": f"Failed to load {target_file}: {exc}"}

        data_copy = copy.deepcopy(data)

        try:
            if action == "add":
                self._do_add(data_copy, change)
            elif action == "modify":
                self._do_modify(data_copy, change)
            elif action == "remove":
                self._do_remove(data_copy, change)
            elif action == "increment":
                self._do_increment(data_copy, change)
            else:
                return {"success": False, "reason": f"Unknown action '{action}'."}
        except Exception as exc:
            return {"success": False, "reason": str(exc)}

        return {
            "success": True,
            "action": action,
            "target": target_file,
            "dry_run": True,
        }

    # ------------------------------------------------------------------
    # Patch primitives
    # ------------------------------------------------------------------

    @staticmethod
    def _do_add(data: Any, change: dict[str, Any]) -> None:
        entry = change.get("entry")
        if entry is None:
            return
        if isinstance(data, dict):
            key = change.get("key")
            if key:
                if key not in data or not isinstance(data[key], list):
                    data[key] = []
                data[key].append(entry)
        elif isinstance(data, list):
            data.append(entry)

    @staticmethod
    def _do_modify(data: Any, change: dict[str, Any]) -> None:
        entry_id = change.get("id")
        entry = change.get("entry")
        if entry is None or entry_id is None:
            return
        key = change.get("key")

        def _modify_list(lst: list[Any]) -> None:
            for item in lst:
                if item.get("id") == entry_id:
                    item.update(entry)
                    return
            lst.append(entry)

        if isinstance(data, dict):
            if key and key in data and isinstance(data[key], list):
                _modify_list(data[key])
            else:
                for k in data:
                    if isinstance(data[k], list):
                        _modify_list(data[k])
                        return
        elif isinstance(data, list):
            _modify_list(data)

    @staticmethod
    def _do_remove(data: Any, change: dict[str, Any]) -> None:
        entry_id = change.get("id")
        if entry_id is None:
            return
        removed = False
        key = change.get("key")

        def _filter_list(lst: list[Any]) -> list[Any]:
            return [e for e in lst if e.get("id") != entry_id]

        if isinstance(data, dict):
            if key and key in data and isinstance(data[key], list):
                new_list = _filter_list(data[key])
                if len(new_list) != len(data[key]):
                    data[key] = new_list
                    removed = True
            else:
                for k in data:
                    if isinstance(data[k], list):
                        new_list = _filter_list(data[k])
                        if len(new_list) != len(data[k]):
                            data[k] = new_list
                            removed = True
        elif isinstance(data, list):
            new_list = _filter_list(data)
            if len(new_list) != len(data):
                data[:] = new_list
                removed = True

    @staticmethod
    def _do_increment(data: Any, change: dict[str, Any]) -> None:
        entry_id = change.get("id")
        field = change.get("field")
        amount = change.get("amount", 1)
        if entry_id is None or field is None:
            return
        key = change.get("key")

        def _increment_in_list(lst: list[Any]) -> None:
            for item in lst:
                if item.get("id") == entry_id:
                    if field in item and isinstance(item[field], (int, float)):
                        item[field] = item[field] + amount
                    return

        if isinstance(data, dict):
            if key and key in data and isinstance(data[key], list):
                _increment_in_list(data[key])
            else:
                for k in data:
                    if isinstance(data[k], list):
                        _increment_in_list(data[k])
                        return
        elif isinstance(data, list):
            _increment_in_list(data)

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback(self, update_id: str) -> dict[str, Any]:
        """
        Remove an update from the applied set so it can be re-applied.
        This does NOT revert the file modifications; for that, restore from
        a backup. Use this to mark an update as unapplied for re-application
        after restoring files.
        """
        if update_id not in self._applied:
            return {"success": False, "reason": f"Update '{update_id}' was not applied."}
        del self._applied[update_id]
        self._save_applied_state()
        return {"success": True, "update_id": update_id}

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        """Export the applied-updates tracking state."""
        return {"applied": dict(self._applied)}

    def import_state(self, state: dict[str, Any]) -> None:
        """Import applied-updates tracking state and persist it."""
        self._applied = state.get("applied", {})
        self._save_applied_state()
