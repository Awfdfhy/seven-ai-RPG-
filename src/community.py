"""
RPG-11-02: Community Features
Leaderboards and character build sharing.

Leaderboard categories:
- level       : character level
- prestige    : prestige points
- total_xp    : total experience earned
- quests      : completed quest count
- titles      : number of titles earned

Sharing encodes a character snapshot into a portable share code.
"""

from __future__ import annotations

import base64
import copy
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Leaderboard Definitions
# ---------------------------------------------------------------------------

@dataclass
class LeaderboardCategory:
    """
    Static definition of a leaderboard category.

    Attributes:
        id          : unique identifier (e.g. "level")
        name        : human-readable display name
        description : flavor text
        metric      : key used to look up the score from a character snapshot
                      (e.g. "level", "prestige_points", "total_xp", "quests_completed", "titles_earned")
        higher_is_better : True for ranking highest first, False for lowest first
    """

    id: str
    name: str
    description: str = ""
    metric: str = "level"
    higher_is_better: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "metric": self.metric,
            "higher_is_better": self.higher_is_better,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LeaderboardCategory:
        return LeaderboardCategory(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            metric=data.get("metric", "level"),
            higher_is_better=data.get("higher_is_better", True),
        )


@dataclass
class LeaderboardEntry:
    """
    One ranked entry on a leaderboard.

    Attributes:
        rank        : 1-based rank position
        character_id: unique character identifier
        display_name: display name (may include titles/honorifics)
        score       : raw metric value
        snapshot    : lightweight character snapshot for detail views
    """

    rank: int = 0
    character_id: str = ""
    display_name: str = ""
    score: int = 0
    snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "character_id": self.character_id,
            "display_name": self.display_name,
            "score": self.score,
            "snapshot": copy.deepcopy(self.snapshot),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LeaderboardEntry:
        return LeaderboardEntry(
            rank=data.get("rank", 0),
            character_id=data.get("character_id", ""),
            display_name=data.get("display_name", ""),
            score=data.get("score", 0),
            snapshot=copy.deepcopy(data.get("snapshot", {})),
        )


# ---------------------------------------------------------------------------
# Sharing
# ---------------------------------------------------------------------------

@dataclass
class ShareableBuild:
    """
    A portable character build snapshot that can be shared via a code.

    Attributes:
        build_id    : unique identifier for this share
        character_id: original character identifier (empty if imported)
        display_name: character display name
        created_at  : ISO timestamp
        data        : lightweight build snapshot (level, key stats, skills, titles)
        version     : schema version for forward compatibility
    """

    build_id: str = ""
    character_id: str = ""
    display_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    data: dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "build_id": self.build_id,
            "character_id": self.character_id,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "data": copy.deepcopy(self.data),
            "version": self.version,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ShareableBuild:
        return ShareableBuild(
            build_id=data.get("build_id", ""),
            character_id=data.get("character_id", ""),
            display_name=data.get("display_name", ""),
            created_at=data.get("created_at", ""),
            data=copy.deepcopy(data.get("data", {})),
            version=data.get("version", 1),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class LeaderboardManager:
    """
    Manages leaderboard categories, rankings, and shared builds.

    Usage:
        mgr = LeaderboardManager()
        mgr.register_category(LeaderboardCategory(id="level", name="Level", metric="level"))
        mgr.submit_snapshot("hero_1", {"level": 10, "prestige_points": 5, ...})
        board = mgr.get_leaderboard("level")
        code = mgr.share_build("hero_1", {"level": 10, ...})
        build = mgr.import_build(code)
    """

    def __init__(self, data_directory: str | None = None) -> None:
        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self.categories: dict[str, LeaderboardCategory] = {}
        self._entries: dict[str, list[LeaderboardEntry]] = {}
        self._shared_builds: dict[str, ShareableBuild] = {}
        self._character_snapshots: dict[str, dict[str, Any]] = {}

        self._load_categories(data_directory)

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    def register_category(self, category: LeaderboardCategory) -> None:
        self.categories[category.id] = category
        self._entries.setdefault(category.id, [])

    def load_categories(self, categories: list[LeaderboardCategory]) -> None:
        for cat in categories:
            self.register_category(cat)

    def get_category(self, category_id: str) -> LeaderboardCategory | None:
        return self.categories.get(category_id)

    def list_categories(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in sorted(self.categories.values(), key=lambda c: c.id)]

    # ------------------------------------------------------------------
    # Snapshots & Leaderboards
    # ------------------------------------------------------------------

    def submit_snapshot(self, character_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        """
        Accept a character snapshot and refresh all leaderboard rankings.

        Returns a summary of updated leaderboards.
        """
        self._character_snapshots[character_id] = copy.deepcopy(snapshot)
        self._rebuild_leaderboards()
        return {
            "success": True,
            "character_id": character_id,
            "leaderboards_updated": list(self._entries.keys()),
        }

    def remove_character(self, character_id: str) -> None:
        self._character_snapshots.pop(character_id, None)
        self._rebuild_leaderboards()

    def get_leaderboard(self, category_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return the top `limit` entries for the given category, ranked.
        """
        entries = self._entries.get(category_id, [])[:limit]
        return [e.to_dict() for e in entries]

    def get_character_rank(self, character_id: str, category_id: str) -> dict[str, Any] | None:
        """
        Return the specific rank entry for a character in a category.
        """
        for entry in self._entries.get(category_id, []):
            if entry.character_id == character_id:
                return entry.to_dict()
        return None

    # ------------------------------------------------------------------
    # Sharing
    # ------------------------------------------------------------------

    def share_build(self, character_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        """
        Create a shareable build code from a character snapshot.

        Returns:
            {"success": True, "code": str, "build_id": str}
        """
        if character_id not in self._character_snapshots:
            self._character_snapshots[character_id] = copy.deepcopy(snapshot)

        build_id = str(uuid.uuid4())[:8]
        display_name = snapshot.get("display_name", character_id)

        build = ShareableBuild(
            build_id=build_id,
            character_id=character_id,
            display_name=display_name,
            data=copy.deepcopy(snapshot),
        )
        self._shared_builds[build_id] = build

        code = self._encode_build(build)
        return {"success": True, "code": code, "build_id": build_id}

    def import_build(self, code: str) -> dict[str, Any]:
        """
        Import a build from a share code.

        Returns:
            {"success": True, "build": ShareableBuild.to_dict()}
            or {"success": False, "reason": str}
        """
        try:
            payload = json.loads(base64.urlsafe_b64decode(code.encode("utf-8")).decode("utf-8"))
        except Exception:
            return {"success": False, "reason": "Invalid share code."}

        build = ShareableBuild.from_dict(payload)
        self._shared_builds[build.build_id] = build
        return {"success": True, "build": build.to_dict()}

    def get_shared_build(self, build_id: str) -> dict[str, Any] | None:
        build = self._shared_builds.get(build_id)
        return build.to_dict() if build else None

    def list_shared_builds(self) -> list[dict[str, Any]]:
        return [b.to_dict() for b in sorted(self._shared_builds.values(), key=lambda b: b.created_at)]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "categories": [c.to_dict() for c in self.categories.values()],
            "entries": {
                cat_id: [e.to_dict() for e in entries]
                for cat_id, entries in self._entries.items()
            },
            "shared_builds": [b.to_dict() for b in self._shared_builds.values()],
        }

    def import_state(self, data: dict[str, Any]) -> None:
        self.categories.clear()
        self._entries.clear()
        self._shared_builds.clear()

        for cat_data in data.get("categories", []):
            cat = LeaderboardCategory.from_dict(cat_data)
            self.register_category(cat)

        for cat_id, entries in data.get("entries", {}).items():
            self._entries[cat_id] = [LeaderboardEntry.from_dict(e) for e in entries]

        for build_data in data.get("shared_builds", []):
            build = ShareableBuild.from_dict(build_data)
            self._shared_builds[build.build_id] = build

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_categories(self, directory: str) -> None:
        path = os.path.join(directory, "community.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for entry in data.get("categories", []):
            cat = LeaderboardCategory.from_dict(entry)
            self.register_category(cat)

    def _rebuild_leaderboards(self) -> None:
        for cat_id in self.categories:
            entries: list[LeaderboardEntry] = []
            for char_id, snap in self._character_snapshots.items():
                cat = self.categories[cat_id]
                raw = snap.get(cat.metric, 0)
                if not isinstance(raw, (int, float)):
                    raw = 0
                display_name = snap.get("display_name", char_id)
                entries.append(
                    LeaderboardEntry(
                        character_id=char_id,
                        display_name=display_name,
                        score=int(raw),
                        snapshot=copy.deepcopy(snap),
                    )
                )
            entries.sort(key=lambda e: e.score, reverse=self.categories[cat_id].higher_is_better)
            for idx, entry in enumerate(entries, start=1):
                entry.rank = idx
            self._entries[cat_id] = entries

    @staticmethod
    def _encode_build(build: ShareableBuild) -> str:
        payload = json.dumps(build.to_dict(), separators=(",", ":"))
        return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
