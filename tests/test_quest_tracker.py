"""
Tests for RPG-10-15: Quest Tracker
Run with: python -m pytest tests/test_quest_tracker.py -v
or:       python tests/test_quest_tracker.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from quest_journal import QuestDefinition, QuestEntry, QuestJournalManager, QuestObjective
from quest_tracker import (
    QuestTracker,
    QuestTrackerSession,
    render_objective,
    render_progress_bar,
    render_quest_card,
    render_quest_summary,
    render_quest_tracker,
    render_rewards,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager() -> QuestJournalManager:
    mgr = QuestJournalManager()
    mgr.load_definitions([
        QuestDefinition(
            id="kill_wolves",
            name="Village Guard",
            description="Help Oakhaven with wolves.",
            objectives=[
                {"id": "kill_wolves", "description": "Defeat 5 wolves", "required_count": 5},
                {"id": "return_sentry", "description": "Return to Sentry Aldric", "required_count": 1},
            ],
            rewards=[
                {"type": "gold", "amount": 150},
                {"type": "experience", "amount": 300},
            ],
            prerequisites=[],
            metadata={"difficulty": "easy"},
        ),
    ])
    return mgr


def _start_quest(mgr: QuestJournalManager) -> QuestEntry:
    return mgr.start_quest("kill_wolves", world_id="w1", session_id="s1")


# ---------------------------------------------------------------------------
# Progress bar tests
# ---------------------------------------------------------------------------

class TestRenderProgressBar:
    def test_empty_bar(self):
        bar = render_progress_bar(0, 5)
        assert "0/5" in bar
        assert "░" in bar

    def test_full_bar(self):
        bar = render_progress_bar(5, 5)
        assert "5/5" in bar
        assert "█" in bar
        assert "░" not in bar

    def test_half_bar(self):
        bar = render_progress_bar(3, 6)
        assert "3/6" in bar
        assert "█" in bar
        assert "░" in bar

    def test_zero_required(self):
        bar = render_progress_bar(0, 0)
        assert "0/0" in bar
        assert "█" in bar


# ---------------------------------------------------------------------------
# Objective rendering tests
# ---------------------------------------------------------------------------

class TestRenderObjective:
    def test_incomplete_objective(self):
        obj = QuestObjective(id="o1", description="Do thing", required_count=5, current_count=2)
        out = render_objective(obj)
        assert "Do thing" in out
        assert "2/5" in out

    def test_complete_objective(self):
        obj = QuestObjective(id="o1", description="Do thing", required_count=5, current_count=5)
        out = render_objective(obj)
        assert "✔" in out
        assert "5/5" in out

    def test_accessibility_integration(self):
        from accessibility import AccessibilityHelper
        acc = AccessibilityHelper()
        obj = QuestObjective(id="o1", description="Do thing", required_count=1, current_count=1)
        out = render_objective(obj, accessibility=acc)
        assert isinstance(out, str)
        assert "Do thing" in out


# ---------------------------------------------------------------------------
# Reward rendering tests
# ---------------------------------------------------------------------------

class TestRenderRewards:
    def test_empty_rewards(self):
        out = render_rewards([])
        assert out == ""

    def test_single_reward(self):
        rewards = [{"type": "gold", "amount": 100}]
        out = render_rewards(rewards)
        assert "gold" in out
        assert "100" in out

    def test_item_reward(self):
        rewards = [{"type": "item", "item_id": "sword", "amount": 1}]
        out = render_rewards(rewards)
        assert "sword" in out


# ---------------------------------------------------------------------------
# Quest card rendering tests
# ---------------------------------------------------------------------------

class TestRenderQuestCard:
    def test_active_quest_card(self):
        mgr = _make_manager()
        entry = _start_quest(mgr)
        out = render_quest_card(entry)
        assert "Village Guard" in out
        assert "ACTIVE" in out
        assert "Defeat 5 wolves" in out

    def test_completed_quest_card_shows_rewards(self):
        mgr = _make_manager()
        entry = _start_quest(mgr)
        entry.status = "completed"
        entry.completed_at = "2024-01-01T00:00:00+00:00"
        out = render_quest_card(entry)
        assert "COMPLETED" in out
        assert "gold" in out

    def test_failed_quest_card(self):
        mgr = _make_manager()
        entry = _start_quest(mgr)
        entry.status = "failed"
        out = render_quest_card(entry)
        assert "FAILED" in out


# ---------------------------------------------------------------------------
# Quest summary rendering tests
# ---------------------------------------------------------------------------

class TestRenderQuestSummary:
    def test_empty_manager(self):
        mgr = QuestJournalManager()
        out = render_quest_summary(mgr)
        assert "Active: 0" in out
        assert "Completed: 0" in out
        assert "Failed: 0" in out

    def test_with_active_quest(self):
        mgr = _make_manager()
        mgr.start_quest("kill_wolves", world_id="w1", session_id="s1")
        out = render_quest_summary(mgr, world_id="w1", session_id="s1")
        assert "Active: 1" in out

    def test_accessibility(self):
        from accessibility import AccessibilityHelper
        mgr = QuestJournalManager()
        acc = AccessibilityHelper()
        out = render_quest_summary(mgr, accessibility=acc)
        assert "Active: 0" in out


# ---------------------------------------------------------------------------
# Quest tracker panel rendering tests
# ---------------------------------------------------------------------------

class TestRenderQuestTracker:
    def test_empty_tracker(self):
        mgr = QuestJournalManager()
        out = render_quest_tracker(mgr)
        assert "QUEST TRACKER" in out
        assert "No quests found" in out

    def test_active_quest_displayed(self):
        mgr = _make_manager()
        _start_quest(mgr)
        out = render_quest_tracker(mgr, world_id="w1", session_id="s1")
        assert "Village Guard" in out
        assert "ACTIVE" in out

    def test_completed_section(self):
        mgr = _make_manager()
        entry = _start_quest(mgr)
        mgr.complete_objectives(entry.quest_id)
        mgr.complete_quest(entry.quest_id)
        out = render_quest_tracker(mgr, status="completed")
        assert "COMPLETED" in out
        assert "Village Guard" in out

    def test_failed_section(self):
        mgr = _make_manager()
        entry = _start_quest(mgr)
        mgr.fail_quest(entry.quest_id, reason="timeout")
        out = render_quest_tracker(mgr, status="failed")
        assert "FAILED" in out

    def test_world_filter(self):
        mgr = _make_manager()
        _start_quest(mgr)
        mgr.start_quest("kill_wolves", world_id="w2", session_id="s1")
        out = render_quest_tracker(mgr, world_id="w2")
        assert "Village Guard" in out
        # Should only show w2 quest
        assert out.count("Village Guard") == 1

    def test_accessibility_integration(self):
        from accessibility import AccessibilityHelper
        mgr = _make_manager()
        _start_quest(mgr)
        acc = AccessibilityHelper()
        out = render_quest_tracker(mgr, accessibility=acc)
        assert "QUEST TRACKER" in out
        assert "Village Guard" in out


# ---------------------------------------------------------------------------
# QuestTracker facade tests
# ---------------------------------------------------------------------------

class TestQuestTracker:
    def setup_method(self):
        self.mgr = _make_manager()
        self.tracker = QuestTracker(manager=self.mgr)

    def test_show_full_tracker(self):
        _start_quest(self.mgr)
        out = self.tracker.show_full_tracker(world_id="w1", session_id="s1")
        assert "QUEST TRACKER" in out
        assert "Village Guard" in out

    def test_show_active_quests(self):
        _start_quest(self.mgr)
        out = self.tracker.show_active_quests(world_id="w1", session_id="s1")
        assert "ACTIVE" in out

    def test_show_completed_quests(self):
        entry = _start_quest(self.mgr)
        self.mgr.complete_objectives(entry.quest_id)
        self.mgr.complete_quest(entry.quest_id)
        out = self.tracker.show_completed_quests(world_id="w1")
        assert "COMPLETED" in out

    def test_show_failed_quests(self):
        entry = _start_quest(self.mgr)
        self.mgr.fail_quest(entry.quest_id)
        out = self.tracker.show_failed_quests(world_id="w1")
        assert "FAILED" in out

    def test_show_quest_detail_not_found(self):
        out = self.tracker.show_quest_detail("nonexistent")
        assert "not found" in out.lower()

    def test_show_quest_detail(self):
        entry = _start_quest(self.mgr)
        out = self.tracker.show_quest_detail(entry.quest_id)
        assert "Village Guard" in out

    def test_show_summary(self):
        _start_quest(self.mgr)
        out = self.tracker.show_summary(world_id="w1", session_id="s1")
        assert "Active: 1" in out

    def test_show_objective_progress(self):
        entry = _start_quest(self.mgr)
        self.mgr.update_objective(entry.quest_id, "kill_wolves", delta=3)
        progress = self.tracker.show_objective_progress(entry.quest_id)
        assert progress["objectives_completed"] >= 3
        assert progress["status"] == "active"

    def test_accessibility_setting(self):
        from accessibility import AccessibilityHelper
        acc = AccessibilityHelper()
        tracker = QuestTracker(manager=self.mgr, accessibility=acc)
        _start_quest(self.mgr)
        out = tracker.show_full_tracker(world_id="w1", session_id="s1")
        assert "Village Guard" in out


# ---------------------------------------------------------------------------
# Interactive session smoke tests
# ---------------------------------------------------------------------------

class TestQuestTrackerSession:
    def test_initial_render_does_not_crash(self):
        mgr = _make_manager()
        session = QuestTrackerSession(mgr, "w1", "s1")
        session._running = False
        session._render_frame()

    def test_session_run_stops_immediately(self):
        mgr = _make_manager()
        session = QuestTrackerSession(mgr, "w1", "s1")
        session._running = False
        result = session.run()
        assert result is None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback

    suites = [
        TestRenderProgressBar,
        TestRenderObjective,
        TestRenderRewards,
        TestRenderQuestCard,
        TestRenderQuestSummary,
        TestRenderQuestTracker,
        TestQuestTracker,
        TestQuestTrackerSession,
    ]
    passed = 0
    failed = 0
    for suite in suites:
        instance = suite()
        for method in dir(instance):
            if method.startswith("test_"):
                try:
                    if hasattr(instance, "setup_method"):
                        instance.setup_method()
                    getattr(instance, method)()
                    print(f"  PASS  {suite.__name__}.{method}")
                    passed += 1
                except Exception as exc:
                    print(f"  FAIL  {suite.__name__}.{method}: {exc}")
                    traceback.print_exc()
                    failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
