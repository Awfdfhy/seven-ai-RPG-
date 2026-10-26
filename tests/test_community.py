"""
Tests for RPG-11-02 Community Features.
Run with: python -m unittest tests.test_community -v
or:       python tests/test_community.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from typing import Any

from community import (
    LeaderboardCategory,
    LeaderboardEntry,
    LeaderboardManager,
    ShareableBuild,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_manager(tmp_dir: str | None = None) -> LeaderboardManager:
    if tmp_dir:
        return LeaderboardManager(data_directory=tmp_dir)
    return LeaderboardManager()


def _sample_snapshot(char_id: str, **overrides) -> dict[str, Any]:
    base = {
        "character_id": char_id,
        "display_name": char_id.replace("_", " ").title(),
        "level": 1,
        "prestige_points": 0,
        "total_xp": 0,
        "quests_completed": 0,
        "titles_earned": 0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Category tests
# ---------------------------------------------------------------------------

class TestLeaderboardCategory(unittest.TestCase):
    def test_round_trip_serialization(self):
        cat = LeaderboardCategory(
            id="level",
            name="Level",
            description="Highest character level",
            metric="level",
            higher_is_better=True,
        )
        data = cat.to_dict()
        restored = LeaderboardCategory.from_dict(data)
        assert restored.id == "level"
        assert restored.metric == "level"
        assert restored.higher_is_better is True

    def test_defaults(self):
        cat = LeaderboardCategory(id="x", name="")
        assert cat.name == ""
        assert cat.description == ""
        assert cat.metric == "level"
        assert cat.higher_is_better is True


# ---------------------------------------------------------------------------
# Manager tests
# ---------------------------------------------------------------------------

class TestLeaderboardManager(unittest.TestCase):
    def test_auto_load_default_categories(self):
        mgr = _default_manager()
        assert "level" in mgr.categories
        assert "prestige" in mgr.categories
        assert "quests" in mgr.categories

    def test_register_category(self):
        mgr = _default_manager()
        cat = LeaderboardCategory(id="gold", name="Gold", metric="gold")
        mgr.register_category(cat)
        assert mgr.get_category("gold") is not None

    def test_submit_snapshot_ranks(self):
        mgr = _default_manager()
        mgr.submit_snapshot("hero_a", _sample_snapshot("hero_a", level=10, total_xp=500))
        mgr.submit_snapshot("hero_b", _sample_snapshot("hero_b", level=20, total_xp=1200))
        mgr.submit_snapshot("hero_c", _sample_snapshot("hero_c", level=5, total_xp=100))

        board = mgr.get_leaderboard("level")
        assert len(board) == 3
        assert board[0]["character_id"] == "hero_b"
        assert board[0]["score"] == 20
        assert board[0]["rank"] == 1
        assert board[1]["character_id"] == "hero_a"
        assert board[2]["character_id"] == "hero_c"

    def test_prestige_lower_is_better(self):
        mgr = _default_manager()
        mgr.register_category(LeaderboardCategory(id="deaths", name="Deaths", metric="deaths", higher_is_better=False))
        mgr.submit_snapshot("x", _sample_snapshot("x", deaths=5))
        mgr.submit_snapshot("y", _sample_snapshot("y", deaths=1))

        board = mgr.get_leaderboard("deaths")
        assert board[0]["character_id"] == "y"
        assert board[0]["score"] == 1
        assert board[1]["character_id"] == "x"
        assert board[1]["score"] == 5

    def test_get_character_rank(self):
        mgr = _default_manager()
        mgr.submit_snapshot("a", _sample_snapshot("a", level=1))
        mgr.submit_snapshot("b", _sample_snapshot("b", level=5))

        rank = mgr.get_character_rank("a", "level")
        assert rank is not None
        assert rank["rank"] == 2
        assert rank["score"] == 1

        missing = mgr.get_character_rank("z", "level")
        assert missing is None

    def test_remove_character(self):
        mgr = _default_manager()
        mgr.submit_snapshot("a", _sample_snapshot("a", level=5))
        mgr.submit_snapshot("b", _sample_snapshot("b", level=10))
        mgr.remove_character("a")
        board = mgr.get_leaderboard("level")
        assert len(board) == 1
        assert board[0]["character_id"] == "b"

    def test_limit(self):
        mgr = _default_manager()
        for i in range(20):
            mgr.submit_snapshot(f"h{i}", _sample_snapshot(f"h{i}", level=i + 1))
        board = mgr.get_leaderboard("level", limit=5)
        assert len(board) == 5
        assert board[0]["score"] == 20

    def test_list_categories(self):
        mgr = _default_manager()
        cats = mgr.list_categories()
        assert len(cats) >= 3
        ids = [c["id"] for c in cats]
        assert "level" in ids
        assert "prestige" in ids

    def test_share_build(self):
        mgr = _default_manager()
        snap = _sample_snapshot("hero", level=7, display_name="Hero One")
        result = mgr.share_build("hero", snap)
        assert result["success"] is True
        assert "code" in result
        assert "build_id" in result

    def test_import_build(self):
        mgr = _default_manager()
        snap = _sample_snapshot("hero", level=7, display_name="Hero One")
        share = mgr.share_build("hero", snap)
        code = share["code"]

        mgr2 = _default_manager()
        result = mgr2.import_build(code)
        assert result["success"] is True
        assert result["build"]["display_name"] == "Hero One"
        assert result["build"]["data"]["level"] == 7

    def test_import_invalid_code(self):
        mgr = _default_manager()
        result = mgr.import_build("not-a-valid-code!!!")
        assert result["success"] is False
        assert "reason" in result

    def test_list_shared_builds(self):
        mgr = _default_manager()
        mgr.share_build("a", _sample_snapshot("a"))
        mgr.share_build("b", _sample_snapshot("b"))
        builds = mgr.list_shared_builds()
        assert len(builds) == 2

    def test_get_shared_build(self):
        mgr = _default_manager()
        share = mgr.share_build("a", _sample_snapshot("a"))
        build = mgr.get_shared_build(share["build_id"])
        assert build is not None
        assert build["character_id"] == "a"
        assert build["version"] == 1

    def test_export_import_roundtrip(self):
        mgr = _default_manager()
        mgr.submit_snapshot("a", _sample_snapshot("a", level=10))
        mgr.submit_snapshot("b", _sample_snapshot("b", level=20))
        mgr.share_build("a", _sample_snapshot("a"))

        state = mgr.export_state()
        mgr2 = _default_manager()
        mgr2.import_state(state)

        assert len(mgr2.categories) == len(mgr.categories)
        assert len(mgr2.get_leaderboard("level")) == 2
        assert len(mgr2.list_shared_builds()) == 1
        assert mgr2.get_leaderboard("level")[0]["character_id"] == "b"


# ---------------------------------------------------------------------------
# ShareableBuild tests
# ---------------------------------------------------------------------------

class TestShareableBuild(unittest.TestCase):
    def test_round_trip(self):
        build = ShareableBuild(
            build_id="abc123",
            character_id="hero",
            display_name="Hero",
            created_at="2024-01-01T00:00:00+00:00",
            data={"level": 5},
            version=1,
        )
        data = build.to_dict()
        restored = ShareableBuild.from_dict(data)
        assert restored.build_id == "abc123"
        assert restored.data["level"] == 5


# ---------------------------------------------------------------------------
# LeaderboardEntry tests
# ---------------------------------------------------------------------------

class TestLeaderboardEntry(unittest.TestCase):
    def test_round_trip(self):
        entry = LeaderboardEntry(
            rank=1,
            character_id="hero",
            display_name="Hero One",
            score=50,
            snapshot={"level": 5},
        )
        data = entry.to_dict()
        restored = LeaderboardEntry.from_dict(data)
        assert restored.rank == 1
        assert restored.score == 50
        assert restored.snapshot["level"] == 5


if __name__ == "__main__":
    unittest.main()
