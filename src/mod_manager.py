"""
RPG-11-01: Mod Support System
Discovers, validates, and manages game mods.
Each mod lives in mods/<mod_id>/ and contains a mod.json manifest plus
optional data/ directory with JSON content that integrates with existing
game managers.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModDefinition:
    """
    Metadata and state for one installed mod.

    Attributes:
        id          : unique identifier (e.g. "extra_abilities")
        name        : human-readable display name
        version     : semantic version string
        description : short summary
        author      : mod author
        enabled     : whether the mod is active
        path        : absolute path to the mod directory
        data_files  : list of JSON data files provided by the mod
        metadata    : opaque extra data
    """

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    enabled: bool = True
    path: str = ""
    data_files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "path": self.path,
            "data_files": list(self.data_files),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ModDefinition:
        return ModDefinition(
            id=data["id"],
            name=data.get("name", data["id"]),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            enabled=data.get("enabled", True),
            path=data.get("path", ""),
            data_files=list(data.get("data_files", [])),
            metadata=dict(data.get("metadata", {})),
        )


class ModManager:
    """
    Discovers mods in a mods/ directory, validates their manifests,
    and tracks enabled/disabled state.

    Usage:
        mgr = ModManager()
        mgr.discover()
        for mod in mgr.get_enabled_mods():
            print(mod.id, mod.name)
    """

    def __init__(self, mods_directory: str | None = None) -> None:
        if mods_directory is None:
            # Default: <project_root>/mods
            mods_directory = os.path.join(
                os.path.dirname(__file__), "..", "mods"
            )
        self.mods_directory = os.path.abspath(mods_directory)
        self._mods: dict[str, ModDefinition] = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> list[str]:
        """
        Scan the mods directory for mod.json manifests.
        Returns list of discovered mod IDs.
        """
        discovered: list[str] = []
        if not os.path.isdir(self.mods_directory):
            return discovered
        for entry in os.listdir(self.mods_directory):
            mod_dir = os.path.join(self.mods_directory, entry)
            if not os.path.isdir(mod_dir):
                continue
            manifest_path = os.path.join(mod_dir, "mod.json")
            if not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path, encoding="utf-8") as fh:
                    data = json.load(fh)
                mod = ModDefinition.from_dict(data)
                mod.path = mod_dir
                # Auto-discover data files in mod's data/ directory
                data_dir = os.path.join(mod_dir, "data")
                if os.path.isdir(data_dir):
                    for fname in os.listdir(data_dir):
                        if fname.endswith(".json"):
                            mod.data_files.append(os.path.join(data_dir, fname))
                self._mods[mod.id] = mod
                discovered.append(mod.id)
            except Exception:
                continue
        return discovered

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_mod(self, mod_id: str) -> ModDefinition | None:
        return self._mods.get(mod_id)

    def list_mods(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self._mods.values()]

    def get_enabled_mods(self) -> list[ModDefinition]:
        return [m for m in self._mods.values() if m.enabled]

    def get_disabled_mods(self) -> list[ModDefinition]:
        return [m for m in self._mods.values() if not m.enabled]

    def is_enabled(self, mod_id: str) -> bool:
        mod = self._mods.get(mod_id)
        return mod.enabled if mod else False

    # ------------------------------------------------------------------
    # Toggle
    # ------------------------------------------------------------------

    def enable_mod(self, mod_id: str) -> bool:
        mod = self._mods.get(mod_id)
        if mod is None:
            return False
        mod.enabled = True
        return True

    def disable_mod(self, mod_id: str) -> bool:
        mod = self._mods.get(mod_id)
        if mod is None:
            return False
        mod.enabled = False
        return True

    # ------------------------------------------------------------------
    # Data paths
    # ------------------------------------------------------------------

    def get_enabled_mod_data_directories(self) -> list[str]:
        """Return paths to data/ directories for all enabled mods."""
        dirs: list[str] = []
        for mod in self.get_enabled_mods():
            data_dir = os.path.join(mod.path, "data")
            if os.path.isdir(data_dir):
                dirs.append(data_dir)
        return dirs

    def get_mod_data_files(self, filename: str) -> list[str]:
        """Return full paths to a specific data file across all enabled mods."""
        paths: list[str] = []
        for mod in self.get_enabled_mods():
            for f in mod.data_files:
                if os.path.basename(f) == filename:
                    paths.append(f)
        return paths
