"""
RPG-02-15: Offline Read-Only Mode with Cached Data

Provides an offline read-only mode that caches game data locally so the
game remains playable without a network connection. Network-dependent
operations (cloud sync, multiplayer, updates, analytics upload) are
blocked or queued while in offline mode.

Cache layout (under ``offline_cache_dir``):

  data/
    <filename>.json   -> cached copy of each data file
  state.json          -> offline mode state (active flag, timestamps)
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from typing import Any


class OfflineModeError(Exception):
    """Raised when a network-dependent operation is attempted offline."""


class OfflineMode:
    """
    Offline read-only mode manager.

    Usage::

        mode = OfflineMode()
        mode.enable()          # enter offline mode, cache data
        mode.is_offline()      # -> True
        data = mode.get_cached_data("abilities.json")
        # Network ops raise OfflineModeError:
        mode.require_online()  # raises OfflineModeError
    """

    def __init__(
        self,
        data_directory: str | None = None,
        offline_cache_dir: str | None = None,
    ) -> None:
        if data_directory is None:
            data_directory = os.path.join(
                os.path.dirname(__file__), "..", "data"
            )
        self.data_directory = os.path.abspath(data_directory)

        if offline_cache_dir is None:
            offline_cache_dir = os.path.join(
                os.path.expanduser("~"), ".seven-rpg", "offline_cache"
            )
        self.offline_cache_dir = os.path.abspath(offline_cache_dir)
        self.cache_data_dir = os.path.join(self.offline_cache_dir, "data")
        self.state_path = os.path.join(self.offline_cache_dir, "state.json")

        self._offline: bool = False
        self._enabled_at: str | None = None
        self._cached_files: list[str] = []
        self._load_state()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def enable(self) -> dict[str, Any]:
        """
        Enter offline mode. Copies all data files to the cache directory
        so they remain available without network access.

        Returns status dict with cache metadata.
        """
        os.makedirs(self.cache_data_dir, exist_ok=True)
        self._cached_files = self._cache_data_files()
        self._offline = True
        self._enabled_at = self._now_iso()
        self._save_state()
        return {
            "success": True,
            "offline": True,
            "enabled_at": self._enabled_at,
            "cached_files": len(self._cached_files),
            "cache_dir": self.offline_cache_dir,
        }

    def disable(self) -> dict[str, Any]:
        """
        Exit offline mode. Clears the offline flag but preserves the
        cached files for future offline sessions.

        Returns status dict.
        """
        self._offline = False
        disabled_at = self._now_iso()
        self._save_state()
        return {
            "success": True,
            "offline": False,
            "disabled_at": disabled_at,
        }

    def is_offline(self) -> bool:
        """Return True if offline read-only mode is active."""
        return self._offline

    def status(self) -> dict[str, Any]:
        """Return current offline mode status and cache info."""
        cache_exists = os.path.isdir(self.cache_data_dir)
        cached_count = 0
        if cache_exists:
            cached_count = len([
                f for f in os.listdir(self.cache_data_dir)
                if f.endswith(".json")
            ])
        return {
            "offline": self._offline,
            "enabled_at": self._enabled_at,
            "cache_dir": self.offline_cache_dir,
            "cache_exists": cache_exists,
            "cached_files": cached_count,
        }

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get_cached_data_path(self, filename: str) -> str | None:
        """
        Return the path to a cached data file, or None if not cached.

        The ``filename`` should be a basename like ``"abilities.json"``.
        """
        if not filename.endswith(".json"):
            filename += ".json"
        cached = os.path.join(self.cache_data_dir, filename)
        if os.path.exists(cached):
            return cached
        # Fall back to the source data directory
        source = os.path.join(self.data_directory, filename)
        if os.path.exists(source):
            return source
        return None

    def load_cached_data(self, filename: str) -> Any | None:
        """
        Load and return parsed JSON from the cache or source data directory.

        Returns None if the file is missing or invalid JSON.
        """
        path = self.get_cached_data_path(filename)
        if path is None:
            return None
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None

    def get_data_directory(self) -> str:
        """
        Return the best available data directory.

        If offline mode is active, returns the cache directory so that
        managers loading data will read from the cache. Otherwise
        returns the source data directory.
        """
        if self._offline and os.path.isdir(self.cache_data_dir):
            return self.cache_data_dir
        return self.data_directory

    # ------------------------------------------------------------------
    # Network guard
    # ------------------------------------------------------------------

    def require_online(self) -> None:
        """
        Raise ``OfflineModeError`` if offline mode is active.

        Call this at the entry point of any network-dependent operation
        (cloud sync push/pull, multiplayer connect, update check, etc.).
        """
        if self._offline:
            raise OfflineModeError(
                "Operation unavailable in offline read-only mode."
            )

    def offline_error(self, operation: str) -> dict[str, Any]:
        """
        Return a standard failure dict for an offline-blocked operation.

        Use this instead of raising when you prefer a non-exception flow.
        """
        return {
            "success": False,
            "reason": f"'{operation}' is unavailable in offline read-only mode.",
            "offline": True,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cache_data_files(self) -> list[str]:
        """Copy all JSON data files to the cache directory."""
        copied: list[str] = []
        if not os.path.isdir(self.data_directory):
            return copied
        for fname in os.listdir(self.data_directory):
            if not fname.endswith(".json"):
                continue
            src = os.path.join(self.data_directory, fname)
            dst = os.path.join(self.cache_data_dir, fname)
            try:
                shutil.copy2(src, dst)
                copied.append(fname)
            except Exception:
                pass
        return copied

    def _save_state(self) -> None:
        parent = os.path.dirname(self.state_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        state = {
            "offline": self._offline,
            "enabled_at": self._enabled_at,
            "cached_files": self._cached_files,
        }
        with open(self.state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)

    def _load_state(self) -> None:
        if not os.path.exists(self.state_path):
            return
        try:
            with open(self.state_path, encoding="utf-8") as fh:
                state = json.load(fh)
            self._offline = bool(state.get("offline", False))
            self._enabled_at = state.get("enabled_at")
            self._cached_files = list(state.get("cached_files", []))
        except Exception:
            pass

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()
