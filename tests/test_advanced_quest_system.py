"""
RPG-12-01: Advanced Quest System Tests
Covers:
  - Procedural quest generation
  - Quest chains and auto-progression
  - Dynamic objective scaling and conditions
  - AdvancedQuestManager integration
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from advanced_quest_system import (
    AdvancedQuestManager,
    DynamicObjectiveBuilder,
    DynamicObjectiveTemplate,
    ProceduralQuestGenerator,
    QuestChainDefinition,
    QuestChainManager,
    QuestTemplate,
)
from quest_journal import QuestDefinition, QuestJournalManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_advanced_manager() -> AdvancedQuestManager:
    return AdvancedQuestManager()


# ---------------------------------------------------------------------------
# Procedural quest tests
# ---------------------------------------------------------------------------

class TestProceduralQuestGenerator(unittest.TestCase):
    def test_register_and_list_templates(self):
        journal = QuestJournalManager()
        gen = ProceduralQuestGenerator(manager=journal)
        t = QuestTemplate(
            template_id="gather_herbs",
            name_template="Herb Gathering: {herb_name}",
            description="Collect {herb_name}",
            objectives=[{"id": "gather_{herb_slug}", "description": "Gather {herb_slug}", "required_count": 3}],
            rewards=[{"type": "gold", "amount": 40}],
            tags=["gathering"],
            metadata={"prefix": "proc"},
        )
        gen.register_template(t)
        results = gen.list_templates()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["template_id"], "gather_herbs")

    def test_generate_quest_from_template(self):
        journal = QuestJournalManager()
        gen = ProceduralQuestGenerator(manager=journal)
        t = QuestTemplate(
            template_id="test_template",
            name_template="Quest for {target}",
            description="A quest about {target}",
            objectives=[{"id": "obj_{target}", "description": "Do {target}", "required_count": 2}],
            rewards=[{"type": "experience", "amount": 100}],
            tags=[],
            metadata={"prefix": "test"},
        )
        gen.register_template(t)
        entry = gen.generate_quest("test_template", world_id="w1", context={"target": "dragons"}, seed=42)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "Quest for dragons")
        self.assertEqual(len(entry.objectives), 1)
        self.assertEqual(entry.objectives[0].id, "obj_dragons")
        self.assertEqual(entry.objectives[0].required_count, 2)

    def test_generate_quest_with_level_scaling(self):
        journal = QuestJournalManager()
        gen = ProceduralQuestGenerator(manager=journal)
        t = QuestTemplate(
            template_id="scale_test",
            name_template="Level quest",
            description="Scaling",
            objectives=[{"id": "kill", "description": "Kill", "required_count": 2, "scale_per_level": 1}],
            rewards=[{"type": "gold", "amount": 10, "scale_per_level": 5}],
            tags=[],
            metadata={},
        )
        gen.register_template(t)
        entry = gen.generate_quest("scale_test", world_id="w1", context={"player_level": 4}, seed=1)
        self.assertEqual(entry.objectives[0].required_count, 5)
        self.assertEqual(entry.rewards[0].amount, 25)

    def test_generate_unknown_template_returns_none(self):
        gen = ProceduralQuestGenerator()
        result = gen.generate_quest("nonexistent", world_id="w1")
        self.assertIsNone(result)

    def test_seeded_generation_is_deterministic(self):
        journal = QuestJournalManager()
        gen = ProceduralQuestGenerator(manager=journal)
        t = QuestTemplate(
            template_id="det",
            name_template="Name {token}",
            description="Desc",
            objectives=[{"id": "o_{token}", "description": "Do", "required_count": 1}],
            rewards=[],
            tags=[],
            metadata={"prefix": "det"},
        )
        gen.register_template(t)
        a = gen.generate_quest("det", world_id="w1", context={"token": "alpha"}, seed=123)
        b = gen.generate_quest("det", world_id="w2", context={"token": "alpha"}, seed=123)
        self.assertEqual(a.quest_id, b.quest_id)
        self.assertEqual(a.objectives[0].id, b.objectives[0].id)


# ---------------------------------------------------------------------------
# Quest chain tests
# ---------------------------------------------------------------------------

class TestQuestChainManager(unittest.TestCase):
    def setUp(self):
        self.journal = QuestJournalManager()
        self.manager = QuestChainManager(manager=self.journal)

    def _register_chain_quests(self):
        for qid in ["q1", "q2", "q3"]:
            self.journal.register_definition(QuestDefinition(
                id=qid, name=qid, description=qid,
                objectives=[{"id": f"obj_{qid}", "required_count": 1}],
                rewards=[], prerequisites=[],
            ))

    def test_start_chain_starts_first_quest(self):
        self._register_chain_quests()
        chain = QuestChainDefinition(
            chain_id="chain1", name="Chain 1", quests=["q1", "q2", "q3"]
        )
        self.manager.register_chain(chain)
        event = self.manager.start_chain("chain1", world_id="w1", session_id="s1")
        self.assertIsNotNone(event)
        self.assertEqual(event.status, "in_progress")
        self.assertEqual(event.current_quest_id, "q1")
        self.assertEqual(len(self.journal.list_quests(world_id="w1", status="active")), 1)

    def test_auto_progression_on_completion(self):
        self._register_chain_quests()
        chain = QuestChainDefinition(
            chain_id="chain2", name="Chain 2", quests=["q1", "q2", "q3"], auto_progression=True
        )
        self.manager.register_chain(chain)
        event = self.manager.start_chain("chain2", world_id="w1")
        self.assertEqual(event.current_quest_id, "q1")

        # Complete q1
        q1 = self.journal.get_quest(event.current_quest_id)
        self.journal.complete_objectives(q1.quest_id)
        self.journal.complete_quest(q1.quest_id)
        self.manager.on_quest_completed(q1.quest_id)
        event = self.manager._events[event.chain_event_id]

        self.assertEqual(event.completed_quests, ["q1"])
        self.assertEqual(event.current_quest_id, "q2")
        self.assertEqual(len(self.journal.list_quests(world_id="w1", status="active")), 1)

    def test_chain_completes_when_final_quest_done(self):
        self._register_chain_quests()
        chain = QuestChainDefinition(
            chain_id="chain3", name="Chain 3", quests=["q1", "q2", "q3"], auto_progression=True
        )
        self.manager.register_chain(chain)
        event = self.manager.start_chain("chain3", world_id="w1")
        for qid in ["q1", "q2", "q3"]:
            q = self.journal.get_quest(event.current_quest_id)
            self.journal.complete_objectives(q.quest_id)
            self.journal.complete_quest(q.quest_id)
            self.manager.on_quest_completed(q.quest_id)
        self.assertEqual(event.status, "completed")
        self.assertIsNotNone(event.completed_at)

    def test_no_auto_progression_without_flag(self):
        self._register_chain_quests()
        chain = QuestChainDefinition(
            chain_id="chain4", name="Chain 4", quests=["q1", "q2"], auto_progression=False
        )
        self.manager.register_chain(chain)
        event = self.manager.start_chain("chain4", world_id="w1")
        q1 = self.journal.get_quest(event.current_quest_id)
        self.journal.complete_objectives(q1.quest_id)
        self.journal.complete_quest(q1.quest_id)
        self.manager.on_quest_completed(q1.quest_id)
        self.assertEqual(event.current_quest_id, "q1")  # unchanged
        self.assertEqual(len(event.completed_quests), 1)

    def test_on_quest_failed_marks_chain_failed(self):
        self._register_chain_quests()
        chain = QuestChainDefinition(
            chain_id="chain5", name="Chain 5", quests=["q1", "q2"], auto_progression=True
        )
        self.manager.register_chain(chain)
        event = self.manager.start_chain("chain5", world_id="w1")
        q1 = self.journal.get_quest(event.current_quest_id)
        self.journal.fail_quest(q1.quest_id, reason="timeout")
        self.manager.on_quest_failed(q1.quest_id)
        self.assertEqual(event.status, "failed")
        self.assertIsNotNone(event.completed_at)

    def test_branch_progression(self):
        self.journal.register_definition(QuestDefinition(id="main1", name="Main 1", description="", objectives=[{"id": "o1", "required_count": 1}], rewards=[]))
        self.journal.register_definition(QuestDefinition(id="branch1", name="Branch 1", description="", objectives=[{"id": "ob1", "required_count": 1}], rewards=[]))
        chain = QuestChainDefinition(
            chain_id="branch_chain",
            name="Branch Chain",
            quests=["main1"],
            branches={"main1": ["branch1"]},
            auto_progression=True,
        )
        self.manager.register_chain(chain)
        event = self.manager.start_chain("branch_chain", world_id="w1")
        q1 = self.journal.get_quest(event.current_quest_id)
        self.journal.complete_objectives(q1.quest_id)
        self.journal.complete_quest(q1.quest_id)
        self.manager.on_quest_completed(q1.quest_id)
        self.assertEqual(event.current_quest_id, "branch1")
        self.assertEqual(event.active_branch, "main1")

    def test_list_chain_events_scoped(self):
        self._register_chain_quests()
        chain = QuestChainDefinition(chain_id="c1", name="C1", quests=["q1"])
        self.manager.register_chain(chain)
        self.manager.start_chain("c1", world_id="w1", session_id="s1")
        self.manager.start_chain("c1", world_id="w2", session_id="s2")
        self.assertEqual(len(self.manager.list_chain_events(world_id="w1")), 1)
        self.assertEqual(len(self.manager.list_chain_events(session_id="s2")), 1)


# ---------------------------------------------------------------------------
# Dynamic objective tests
# ---------------------------------------------------------------------------

class TestDynamicObjectiveBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = DynamicObjectiveBuilder()

    def test_build_objective_without_conditions(self):
        t = DynamicObjectiveTemplate(
            template_id="kill_wolves",
            objective_type="kill",
            base_id="kill_wolves",
            base_description="Defeat {required_count} wolves",
            scale_rules={"base_count": 3, "scale_per_level": 1, "min_count": 1, "max_count": 10},
            conditions={},
            metadata={"enemy_type": "wolf"},
        )
        self.builder.register_template(t)
        obj = self.builder.build("kill_wolves", context={"player_level": 5})
        self.assertIsNotNone(obj)
        self.assertEqual(obj.required_count, 7)
        self.assertIn("wolves", obj.description)

    def test_difficulty_multiplier(self):
        t = DynamicObjectiveTemplate(
            template_id="dynamic_kill",
            objective_type="kill",
            base_id="kill_{enemy}",
            base_description="Kill",
            scale_rules={
                "base_count": 4,
                "scale_per_level": 0,
                "difficulty_multipliers": {"easy": 0.5, "medium": 1.0, "hard": 2.0},
                "min_count": 1,
                "max_count": 20,
            },
            conditions={},
            metadata={},
        )
        self.builder.register_template(t)
        obj = self.builder.build("dynamic_kill", context={"difficulty": "hard", "player_level": 1})
        self.assertEqual(obj.required_count, 8)

    def test_conditions_block_build(self):
        t = DynamicObjectiveTemplate(
            template_id="blocked",
            objective_type="explore",
            base_id="explore_x",
            base_description="Explore X",
            scale_rules={},
            conditions={"required_world_flags": ["has_key"]},
            metadata={},
        )
        self.builder.register_template(t)
        obj = self.builder.build("blocked", context={"world_state": {}})
        self.assertIsNone(obj)

    def test_conditions_allow_build(self):
        t = DynamicObjectiveTemplate(
            template_id="allowed",
            objective_type="explore",
            base_id="explore_x",
            base_description="Explore X",
            scale_rules={},
            conditions={"required_world_flags": ["has_key"]},
            metadata={},
        )
        self.builder.register_template(t)
        obj = self.builder.build("allowed", context={"world_state": {"has_key": True}})
        self.assertIsNotNone(obj)

    def test_clamping(self):
        t = DynamicObjectiveTemplate(
            template_id="clamp",
            objective_type="generic",
            base_id="do_x",
            base_description="Do X",
            scale_rules={"base_count": 3, "scale_per_level": -5, "min_count": 2, "max_count": 4},
            conditions={},
            metadata={},
        )
        self.builder.register_template(t)
        obj = self.builder.build("clamp", context={"player_level": 10})
        self.assertEqual(obj.required_count, 2)


# ---------------------------------------------------------------------------
# AdvancedQuestManager integration tests
# ---------------------------------------------------------------------------

class TestAdvancedQuestManager(unittest.TestCase):
    def setUp(self):
        self.mgr = _make_advanced_manager()

    def test_loads_data_files(self):
        # At least the base village_guard should be present
        quests = self.mgr.list_definitions()
        quest_ids = [q["id"] for q in quests]
        self.assertIn("village_guard", quest_ids)

    def test_start_quest(self):
        entry = self.mgr.start_quest("village_guard", world_id="w1")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.status, "active")

    def test_generate_procedural_quest(self):
        entry = self.mgr.generate_quest(
            "gather_herbs",
            world_id="w1",
            context={"herb_name": "Moonflower", "herb_slug": "moonflower", "player_level": 2},
            seed=7,
        )
        self.assertIsNotNone(entry)
        self.assertIn("Moonflower", entry.name)
        # scaling: base 3 + 1 level = 4
        self.assertEqual(entry.objectives[0].required_count, 4)

    def test_chain_auto_progression_integration(self):
        event = self.mgr.start_chain("oakhaven_rising", world_id="w1")
        self.assertIsNotNone(event)
        self.assertEqual(event.current_quest_id, "village_guard")
        q = self.mgr._journal.get_quest(event.current_quest_id)
        self.mgr._journal.complete_objectives(q.quest_id)
        self.mgr._journal.complete_quest(q.quest_id)
        self.mgr.on_quest_completed(q.quest_id)
        self.assertEqual(event.current_quest_id, "lost_artifact")

    def test_dynamic_objective_integration(self):
        obj = self.mgr.build_dynamic_objective(
            "dynamic_kill",
            context={
                "player_level": 3,
                "difficulty": "medium",
                "world_state": {},
                "enemy": "goblin",
                "enemy_slug": "goblin",
                "enemy_name": "Goblin",
                "requested_tags": ["combat"],
            },
        )
        self.assertIsNotNone(obj)
        self.assertIn("goblin", obj.id)
        self.assertEqual(obj.required_count, 3)

    def test_export_and_import_state(self):
        self.mgr.start_quest("village_guard", world_id="w1")
        state = self.mgr.export_state()
        self.assertIn("journal", state)
        self.assertIn("chain_events", state)

        new_mgr = AdvancedQuestManager()
        # Prevent re-loading from disk by monkey-patching _load_data away
        new_mgr._load_data = lambda: None
        new_mgr.import_state(state)
        self.assertEqual(len(new_mgr._journal.list_quests(world_id="w1")), 1)

    def test_list_procedural_templates(self):
        templates = self.mgr.list_procedural_templates()
        ids = [t["template_id"] for t in templates]
        self.assertIn("gather_herbs", ids)
        self.assertIn("clear_bandits", ids)

    def test_list_chain_definitions(self):
        chains = self.mgr.list_chain_definitions()
        ids = [c["chain_id"] for c in chains]
        self.assertIn("oakhaven_rising", ids)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
