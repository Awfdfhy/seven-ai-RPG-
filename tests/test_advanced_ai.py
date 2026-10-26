"""
RPG-12-06: Advanced AI System tests.
Run with: python -m pytest tests/test_advanced_ai.py -v
or:       python tests/test_advanced_ai.py
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from typing import Any

from advanced_ai import (
    AdvancedAIManager,
    AdvancedNPC,
    BehaviorTransition,
    DispositionTier,
    LearningAxis,
    MemoryType,
    NPCBehaviorState,
    NPCGoal,
    NPCMemoryEntry,
    NPCMemoryStore,
    NPCPersonality,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_npc(npc_id="test_npc", name="Test NPC") -> AdvancedNPC:
    return AdvancedNPC(npc_id=npc_id, name=name)


def _make_memory(npc_id="test_npc", subject_id="player", intensity=1.0) -> NPCMemoryEntry:
    return NPCMemoryEntry(
        memory_id=str(uuid.uuid4()),
        memory_type=MemoryType.PLAYER_ACTION.value,
        timestamp="2024-01-01T00:00:00+00:00",
        subject_id=subject_id,
        target_id=npc_id,
        intensity=intensity,
    )


# ---------------------------------------------------------------------------
# NPCMemoryEntry tests
# ---------------------------------------------------------------------------

class TestNPCMemoryEntry:
    def test_default_values(self):
        entry = NPCMemoryEntry(
            memory_id="m1",
            memory_type=MemoryType.PLAYER_ACTION.value,
            timestamp="2024-01-01T00:00:00+00:00",
        )
        assert entry.memory_id == "m1"
        assert entry.subject_id == ""
        assert entry.intensity == 0.0
        assert entry.strength == 1.0

    def test_to_dict_roundtrip(self):
        entry = NPCMemoryEntry(
            memory_id="m2",
            memory_type=MemoryType.TRADE.value,
            timestamp="2024-01-01T12:00:00+00:00",
            subject_id="player",
            intensity=2.5,
            strength=0.8,
            details={"item": "sword"},
        )
        restored = NPCMemoryEntry.from_dict(entry.to_dict())
        assert restored.memory_id == "m2"
        assert restored.memory_type == MemoryType.TRADE.value
        assert restored.intensity == 2.5
        assert restored.details == {"item": "sword"}

    def test_decay_reduces_strength(self):
        entry = NPCMemoryEntry(
            memory_id="m3",
            memory_type=MemoryType.PLAYER_ACTION.value,
            timestamp="2024-01-01T00:00:00+00:00",
            strength=1.0,
            decay_rate=0.1,
        )
        entry.decay(1.0)
        assert entry.strength == 0.9

    def test_decay_floor_at_zero(self):
        entry = NPCMemoryEntry(
            memory_id="m4",
            memory_type=MemoryType.PLAYER_ACTION.value,
            timestamp="2024-01-01T00:00:00+00:00",
            strength=0.05,
            decay_rate=0.1,
        )
        entry.decay(1.0)
        assert entry.strength == 0.0


# ---------------------------------------------------------------------------
# NPCMemoryStore tests
# ---------------------------------------------------------------------------

class TestNPCMemoryStore:
    def test_add_and_query(self):
        store = NPCMemoryStore(npc_id="npc1")
        m1 = NPCMemoryEntry(
            memory_id="m1",
            memory_type=MemoryType.PLAYER_ACTION.value,
            timestamp="2024-01-01T00:00:00+00:00",
            subject_id="player",
            intensity=1.0,
        )
        m2 = NPCMemoryEntry(
            memory_id="m2",
            memory_type=MemoryType.TRADE.value,
            timestamp="2024-01-01T01:00:00+00:00",
            subject_id="player",
            intensity=0.5,
        )
        store.add(m1)
        store.add(m2)
        assert len(store.memories) == 2
        results = store.query(subject_id="player")
        assert len(results) == 2
        trade_only = store.query(memory_type=MemoryType.TRADE.value)
        assert len(trade_only) == 1
        assert trade_only[0].memory_id == "m2"

    def test_strongest(self):
        store = NPCMemoryStore(npc_id="npc2")
        weak = NPCMemoryEntry(
            memory_id="weak",
            memory_type=MemoryType.PLAYER_ACTION.value,
            timestamp="2024-01-01T00:00:00+00:00",
            strength=0.1,
        )
        strong = NPCMemoryEntry(
            memory_id="strong",
            memory_type=MemoryType.PLAYER_ACTION.value,
            timestamp="2024-01-01T00:00:00+00:00",
            strength=0.9,
        )
        store.add(weak)
        store.add(strong)
        top = store.strongest()
        assert top[0].memory_id == "strong"

    def test_total_intensity(self):
        store = NPCMemoryStore(npc_id="npc3")
        store.add(NPCMemoryEntry(
            memory_id="a",
            memory_type=MemoryType.PLAYER_ACTION.value,
            timestamp="2024-01-01T00:00:00+00:00",
            intensity=2.0,
            strength=1.0,
        ))
        store.add(NPCMemoryEntry(
            memory_id="b",
            memory_type=MemoryType.TRADE.value,
            timestamp="2024-01-01T00:00:00+00:00",
            intensity=3.0,
            strength=0.5,
        ))
        assert store.total_intensity() == 2.0 + 1.5
        assert store.total_intensity(memory_type=MemoryType.TRADE.value) == 1.5

    def test_max_memories_trims(self):
        store = NPCMemoryStore(npc_id="npc4", max_memories=3)
        for i in range(5):
            store.add(NPCMemoryEntry(
                memory_id=f"m{i}",
                memory_type=MemoryType.PLAYER_ACTION.value,
                timestamp="2024-01-01T00:00:00+00:00",
                strength=float(i),
            ))
        assert len(store.memories) == 3


# ---------------------------------------------------------------------------
# NPCPersonality tests
# ---------------------------------------------------------------------------

class TestNPCPersonality:
    def test_adjust_clamps(self):
        p = NPCPersonality(courage=0.9)
        p.adjust("courage", 0.2)
        assert p.courage == 1.0
        p.adjust("courage", -0.5)
        assert p.courage == 0.5

    def test_to_dict_roundtrip(self):
        p = NPCPersonality(openness=0.7, courage=0.3)
        restored = NPCPersonality.from_dict(p.to_dict())
        assert restored.openness == 0.7
        assert restored.courage == 0.3


# ---------------------------------------------------------------------------
# NPCGoal tests
# ---------------------------------------------------------------------------

class TestNPCGoal:
    def test_active_when_no_condition(self):
        npc = _make_npc()
        goal = NPCGoal(goal_id="g1", name="wander", priority=1.0)
        npc.add_goal(goal)
        assert len(npc.active_goals()) == 1
        assert npc.top_goal().goal_id == "g1"

    def test_satisfaction_removes_goal(self):
        npc = _make_npc()
        goal = NPCGoal(goal_id="g2", satisfaction=1.0)
        npc.add_goal(goal)
        assert len(npc.active_goals()) == 0


# ---------------------------------------------------------------------------
# AdvancedNPC tests
# ---------------------------------------------------------------------------

class TestAdvancedNPC:
    def test_remember_and_recall(self):
        npc = _make_npc("npc_a", "Alpha")
        mem = npc.remember_event(
            memory_type=MemoryType.PLAYER_ACTION.value,
            subject_id="player",
            intensity=3.0,
            details={"action": "saved_npc", "keywords": ["save", "help"]},
        )
        results = npc.recall(memory_type=MemoryType.PLAYER_ACTION.value)
        assert len(results) == 1
        assert results[0].memory_id == mem.memory_id

    def test_personality_bias(self):
        npc = _make_npc("npc_b", "Beta")
        npc.personality.courage = 0.9
        npc.personality.agreeableness = 0.2
        bias = npc.personality_bias()
        assert bias["aggression"] > 0.5
        assert bias["caution"] < 0.5

    def test_disposition_toward(self):
        npc = _make_npc("npc_c", "Gamma")
        npc.learn("player", LearningAxis.TRUST.value, 3.0)
        npc.learn("player", LearningAxis.RESPECT.value, 2.0)
        disp = npc.disposition_toward("player")
        assert disp["tier"] == DispositionTier.FRIENDLY.value
        assert disp["trust"] == 3.0

    def test_disposition_hostile(self):
        npc = _make_npc("npc_d", "Delta")
        npc.learn("player", LearningAxis.ANTAGONISM.value, 6.0)
        disp = npc.disposition_toward("player")
        assert disp["tier"] == DispositionTier.HOSTILE.value

    def test_behavior_state_transition(self):
        npc = _make_npc("npc_e", "Epsilon")
        npc.behavior_state = NPCBehaviorState.IDLE
        npc.add_transition(BehaviorTransition(
            transition_id="t1",
            from_state=None,
            to_state="work",
            weight=2.0,
            cooldown_ticks=0,
        ))
        npc.add_transition(BehaviorTransition(
            transition_id="t2",
            from_state=None,
            to_state="sleep",
            weight=1.0,
            cooldown_ticks=0,
        ))
        npc.evaluate_transitions()
        assert npc.behavior_state == NPCBehaviorState.WORK

    def test_transition_cooldown(self):
        npc = _make_npc("npc_f", "Zeta")
        npc.behavior_state = NPCBehaviorState.IDLE
        t = BehaviorTransition(
            transition_id="t1",
            from_state=None,
            to_state="work",
            weight=5.0,
            cooldown_ticks=3,
        )
        npc.add_transition(t)
        npc.evaluate_transitions()
        assert npc.behavior_state == NPCBehaviorState.WORK
        npc.behavior_state = NPCBehaviorState.IDLE
        npc.evaluate_transitions()
        assert npc.behavior_state == NPCBehaviorState.IDLE  # still on cooldown
        # Cooldown ticks down each evaluate_transitions call.
        # It takes 3 ticks to reach 0, then one more call to fire.
        for _ in range(4):
            npc.evaluate_transitions()
        assert npc.behavior_state == NPCBehaviorState.WORK

    def test_choose_action(self):
        npc = _make_npc("npc_g", "Eta")
        npc.personality.courage = 0.9
        npc.personality.agreeableness = 0.2
        action = npc.choose_action(["attack", "heal", "talk", "flee"])
        assert action in ["attack", "heal", "talk", "flee"]

    def test_tick_decays_memories(self):
        npc = _make_npc("npc_h", "Theta")
        mem = npc.remember_event(
            memory_type=MemoryType.PLAYER_ACTION.value,
            subject_id="player",
            intensity=1.0,
        )
        original_strength = mem.strength
        npc.tick(hours=10.0)
        assert mem.strength < original_strength

    def test_to_dict_roundtrip(self):
        npc = _make_npc("npc_i", "Iota")
        npc.remember_event(
            memory_type=MemoryType.TRADE.value,
            subject_id="player",
            intensity=1.5,
        )
        npc.add_goal(NPCGoal(goal_id="g1", name="trade", priority=2.0))
        npc.add_transition(BehaviorTransition(
            transition_id="t1",
            from_state=None,
            to_state="shop",
            weight=1.0,
        ))
        restored = AdvancedNPC.from_dict(npc.to_dict())
        assert restored.npc_id == "npc_i"
        assert restored.name == "Iota"
        assert len(restored.goals) == 1
        assert restored.goals[0].goal_id == "g1"
        assert len(restored.transitions) == 1


# ---------------------------------------------------------------------------
# AdvancedAIManager tests
# ---------------------------------------------------------------------------

class TestAdvancedAIManager:
    def test_register_and_get(self):
        mgr = AdvancedAIManager()
        npc = _make_npc("mgr_npc_1", "Mgr NPC")
        mgr.register_npc(npc)
        assert mgr.get_npc("mgr_npc_1") is npc
        assert mgr.get_npc("missing") is None
        assert "mgr_npc_1" in mgr.list_npcs()

    def test_record_event(self):
        mgr = AdvancedAIManager()
        npc = _make_npc("mgr_npc_2", "Recorder")
        mgr.register_npc(npc)
        mgr.record_event(
            npc_id="mgr_npc_2",
            memory_type=MemoryType.COMBAT.value,
            subject_id="player",
            intensity=4.0,
            details={"action": "saved_from_wolves"},
        )
        memories = mgr.query_memories("mgr_npc_2", memory_type=MemoryType.COMBAT.value)
        assert len(memories) == 1
        assert memories[0]["intensity"] == 4.0

    def test_get_disposition(self):
        mgr = AdvancedAIManager()
        npc = _make_npc("mgr_npc_3", "Disp")
        mgr.register_npc(npc)
        npc.learn("player", LearningAxis.TRUST.value, 4.0)
        result = mgr.get_disposition("mgr_npc_3", "player")
        assert result["tier"] == DispositionTier.FRIENDLY.value

    def test_tick_all(self):
        mgr = AdvancedAIManager()
        for i in range(3):
            mgr.register_npc(_make_npc(f"tick_npc_{i}", f"Tick{i}"))
        summary = mgr.tick_all(hours=2.0)
        assert len(summary) == 3
        for v in summary.values():
            assert "state_after" in v

    def test_summary(self):
        mgr = AdvancedAIManager()
        npc = _make_npc("sum_npc", "Sum")
        npc.remember_event(
            memory_type=MemoryType.PLAYER_ACTION.value,
            subject_id="player",
            intensity=1.0,
        )
        npc.add_goal(NPCGoal(goal_id="g1", name="wander", priority=1.0))
        mgr.register_npc(npc)
        s = mgr.summary()
        assert s["npc_count"] == 1
        assert s["total_memories"] == 1
        assert s["total_goals"] == 1

    def test_load_from_data(self):
        import json
        import tempfile

        mgr = AdvancedAIManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            data = [
                {
                    "npc_id": "ld_npc_1",
                    "name": "Loader",
                    "personality": {
                        "openness": 0.5,
                        "conscientiousness": 0.5,
                        "extraversion": 0.5,
                        "agreeableness": 0.5,
                        "neuroticism": 0.5,
                        "courage": 0.5,
                        "loyalty": 0.5,
                        "morality": 0.5,
                    },
                    "memories": [],
                    "transitions": [],
                    "goals": [],
                    "learning_profiles": {},
                }
            ]
            with open(os.path.join(tmpdir, "advanced_ai.json"), "w") as fh:
                json.dump(data, fh)
            result = mgr.load_from_data(tmpdir)
            assert result["loaded"] == 1
            assert mgr.get_npc("ld_npc_1") is not None

    def test_export_all(self):
        mgr = AdvancedAIManager()
        npc = _make_npc("exp_npc", "Export")
        mgr.register_npc(npc)
        exported = mgr.export_all()
        assert "exp_npc" in exported
        assert exported["exp_npc"]["name"] == "Export"


# ---------------------------------------------------------------------------
# Disposition tier boundary tests
# ---------------------------------------------------------------------------

class TestDispositionTiers:
    def test_tier_boundaries(self):
        npc = _make_npc("tier_npc", "Tier")
        npc.learn("player", LearningAxis.TRUST.value, 6.0)
        d = npc.disposition_toward("player")
        assert d["tier"] == DispositionTier.ALLIED.value

        npc2 = _make_npc("tier_npc2", "Tier2")
        npc2.learn("player", LearningAxis.ANTAGONISM.value, 5.0)
        d2 = npc2.disposition_toward("player")
        assert d2["tier"] == DispositionTier.HOSTILE.value

        npc3 = _make_npc("tier_npc3", "Tier3")
        d3 = npc3.disposition_toward("player")
        assert d3["tier"] == DispositionTier.NEUTRAL.value


if __name__ == "__main__":
    unittest.main()
