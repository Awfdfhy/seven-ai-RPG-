"""
Tests for RPG Quest Journal System.
Run with: python -m pytest tests/ -v
or:       python tests/test_quest_journal.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from quest_journal import (
    QuestDefinition,
    QuestJournalManager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_definitions() -> list[QuestDefinition]:
    return [
        QuestDefinition(
            id="village_guard",
            name="Village Guard",
            description="Help Oakhaven deal with wolves.",
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
        QuestDefinition(
            id="lost_artifact",
            name="The Lost Artifact",
            description="Retrieve an ancient artifact.",
            objectives=[
                {"id": "enter_caves", "description": "Enter the Whispering Caves", "required_count": 1},
                {"id": "find_artifact", "description": "Locate the artifact", "required_count": 1},
                {"id": "escape_caves", "description": "Escape the caves", "required_count": 1},
            ],
            rewards=[
                {"type": "gold", "amount": 500},
                {"type": "experience", "amount": 800},
            ],
            prerequisites=["village_guard"],
            metadata={"difficulty": "medium"},
        ),
    ]


def _make_journal() -> QuestJournalManager:
    journal = QuestJournalManager()
    journal.load_definitions(_sample_definitions())
    return journal


# ---------------------------------------------------------------------------
# Definition tests
# ---------------------------------------------------------------------------

class TestQuestDefinition(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "id": "dragon_threat",
            "name": "Dragon Threat",
            "description": "Investigate a dragon.",
            "objectives": [{"id": "scout", "required_count": 1}],
            "rewards": [{"type": "gold", "amount": 1000}],
            "prerequisites": ["lost_artifact"],
            "metadata": {"difficulty": "hard"},
        }
        d = QuestDefinition.from_dict(data)
        self.assertEqual(d.id, "dragon_threat")
        self.assertEqual(len(d.objectives), 1)
        self.assertEqual(d.prerequisites, ["lost_artifact"])

    def test_to_dict(self):
        d = QuestDefinition(
            id="test",
            name="Test",
            description="desc",
            objectives=[{"id": "o1"}],
            rewards=[{"type": "xp"}],
        )
        data = d.to_dict()
        self.assertEqual(data["id"], "test")
        self.assertEqual(len(data["objectives"]), 1)


# ---------------------------------------------------------------------------
# Manager tests
# ---------------------------------------------------------------------------

class TestQuestJournalManager(unittest.TestCase):
    def test_start_quest(self):
        journal = _make_journal()
        entry = journal.start_quest("village_guard", world_id="world-1", session_id="sess-1")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.status, "active")
        self.assertEqual(len(entry.objectives), 2)
        self.assertEqual(entry.world_id, "world-1")
        self.assertEqual(entry.session_id, "sess-1")

    def test_start_unknown_quest_returns_none(self):
        journal = _make_journal()
        self.assertIsNone(journal.start_quest("nonexistent", world_id="w"))

    def test_list_quests_scoped(self):
        journal = _make_journal()
        journal.start_quest("village_guard", world_id="w1", session_id="s1")
        journal.start_quest("lost_artifact", world_id="w2", session_id="s2")
        self.assertEqual(len(journal.list_quests(world_id="w1")), 1)
        self.assertEqual(len(journal.list_quests(session_id="s2")), 1)
        self.assertEqual(len(journal.list_quests(status="active")), 2)

    def test_update_objective(self):
        journal = _make_journal()
        entry = journal.start_quest("village_guard", world_id="w")
        journal.update_objective(entry.quest_id, "kill_wolves", delta=3)
        wolf_obj = next(o for o in entry.objectives if o.id == "kill_wolves")
        self.assertEqual(wolf_obj.current_count, 3)

    def test_set_objective(self):
        journal = _make_journal()
        entry = journal.start_quest("village_guard", world_id="w")
        journal.set_objective(entry.quest_id, "kill_wolves", count=5)
        wolf_obj = next(o for o in entry.objectives if o.id == "kill_wolves")
        self.assertEqual(wolf_obj.current_count, 5)

    def test_complete_objectives(self):
        journal = _make_journal()
        entry = journal.start_quest("village_guard", world_id="w")
        journal.complete_objectives(entry.quest_id)
        self.assertTrue(all(o.current_count >= o.required_count for o in entry.objectives))

    def test_complete_quest(self):
        journal = _make_journal()
        entry = journal.start_quest("village_guard", world_id="w")
        journal.complete_objectives(entry.quest_id)
        result = journal.complete_quest(entry.quest_id)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(result.completed_at)

    def test_cannot_complete_incomplete(self):
        journal = _make_journal()
        entry = journal.start_quest("village_guard", world_id="w")
        journal.update_objective(entry.quest_id, "kill_wolves", delta=2)
        result = journal.complete_quest(entry.quest_id)
        self.assertEqual(result.status, "active")

    def test_fail_quest(self):
        journal = _make_journal()
        entry = journal.start_quest("village_guard", world_id="w")
        result = journal.fail_quest(entry.quest_id, reason="Time ran out")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.failed_at)
        self.assertIn("Time ran out", result.metadata.get("failure_reasons", []))

    def test_get_progress(self):
        journal = _make_journal()
        entry = journal.start_quest("village_guard", world_id="w")
        journal.update_objective(entry.quest_id, "kill_wolves", delta=5)
        progress = journal.get_progress(entry.quest_id)
        self.assertEqual(progress["objectives_completed"], 5 + 0)
        self.assertAlmostEqual(progress["progress"], 5 / 6, places=2)

    def test_get_rewards(self):
        journal = _make_journal()
        entry = journal.start_quest("village_guard", world_id="w")
        rewards = journal.get_rewards(entry.quest_id)
        self.assertEqual(len(rewards), 2)
        self.assertEqual(rewards[0]["type"], "gold")
        self.assertEqual(rewards[0]["amount"], 150)

    def test_abandon_quest(self):
        journal = _make_journal()
        entry = journal.start_quest("village_guard", world_id="w")
        self.assertIsNotNone(journal.get_quest(entry.quest_id))
        result = journal.abandon_quest(entry.quest_id)
        self.assertIsNotNone(result)
        self.assertIsNone(journal.get_quest(entry.quest_id))


if __name__ == "__main__":
    unittest.main()
