"""
RPG-13-09: Advanced NPC AI tests.
Run with: python -m pytest tests/test_rpg_13_09_advanced_npc_ai.py -v
or:       python tests/test_rpg_13_09_advanced_npc_ai.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from advanced_ai import (
    MemoryType,
)
from rpg_13_09_advanced_npc_ai import (
    AdvancedAIManager,
    AdvancedNPC,
    NPCEmotionalState,
    NPCRelationWeb,
    NPCSchedule,
    NPCScheduleBlock,
    NPCSocialLink,
    ReputationStanding,
    ReputationTrack,
    build_npc_from_definition,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_extended_npc(npc_id="ext_npc", name="Ext NPC") -> AdvancedNPC:
    return AdvancedNPC(npc_id=npc_id, name=name)


# ---------------------------------------------------------------------------
# NPCScheduleBlock tests
# ---------------------------------------------------------------------------

class TestNPCScheduleBlock:
    def test_contains_hour_inside_range(self):
        block = NPCScheduleBlock(block_id="b1", start_hour=9.0, end_hour=17.0)
        assert block.contains_hour(12.0)
        assert not block.contains_hour(8.9)
        assert not block.contains_hour(17.0)

    def test_contains_hour_wraps_midnight(self):
        block = NPCScheduleBlock(block_id="b2", start_hour=22.0, end_hour=2.0)
        assert block.contains_hour(23.0)
        assert block.contains_hour(1.0)
        assert not block.contains_hour(12.0)

    def test_to_dict_roundtrip(self):
        block = NPCScheduleBlock(block_id="b3", start_hour=10.0, end_hour=18.0,
                                 preferred_state="work", weight_boost=1.5, location_id="town")
        restored = NPCScheduleBlock.from_dict(block.to_dict())
        assert restored.block_id == "b3"
        assert restored.start_hour == 10.0
        assert restored.preferred_state == "work"
        assert restored.weight_boost == 1.5


# ---------------------------------------------------------------------------
# NPCSchedule tests
# ---------------------------------------------------------------------------

class TestNPCSchedule:
    def test_active_block_day_off(self):
        schedule = NPCSchedule(npc_id="npc1", day_skip=["sunday"])
        assert schedule.active_block(10.0, day_name="sunday") is None
        assert schedule.active_block(10.0, day_name="monday") is None  # no blocks

    def test_active_block_finds_first_match(self):
        block = NPCScheduleBlock(block_id="b1", start_hour=8.0, end_hour=12.0,
                                 preferred_state="work")
        schedule = NPCSchedule(npc_id="npc2", blocks=[block])
        found = schedule.active_block(10.0)
        assert found is not None
        assert found.block_id == "b1"

    def test_to_dict_roundtrip(self):
        block = NPCScheduleBlock(block_id="b1", start_hour=8.0, end_hour=12.0)
        schedule = NPCSchedule(npc_id="npc3", blocks=[block], day_skip=["sunday"])
        restored = NPCSchedule.from_dict(schedule.to_dict())
        assert restored.npc_id == "npc3"
        assert len(restored.blocks) == 1
        assert restored.day_skip == ["sunday"]


# ---------------------------------------------------------------------------
# NPCEmotionalState tests
# ---------------------------------------------------------------------------

class TestNPCEmotionalState:
    def test_dominant_tone_calm(self):
        state = NPCEmotionalState(stress=0.1, fear=0.1, anger=0.1, happiness=0.8, energy=0.6)
        assert state.dominant_tone() == "calm"

    def test_dominant_tone_anxious(self):
        state = NPCEmotionalState(stress=0.9, fear=0.8, anger=0.1, happiness=0.1, energy=0.5)
        assert state.dominant_tone() == "anxious"

    def test_dominant_tone_angry(self):
        state = NPCEmotionalState(stress=0.5, fear=0.1, anger=0.9, happiness=0.2, energy=0.6)
        assert state.dominant_tone() == "angry"

    def test_adjust_clamps(self):
        state = NPCEmotionalState(energy=0.9)
        state.adjust("energy", 0.2)
        assert state.energy == 1.0
        state.adjust("energy", -0.5)
        assert state.energy == 0.5

    def test_to_dict_roundtrip(self):
        state = NPCEmotionalState(stress=0.3, energy=0.8, happiness=0.6, fear=0.2, anger=0.1)
        restored = NPCEmotionalState.from_dict(state.to_dict())
        assert restored.stress == 0.3
        assert restored.energy == 0.8


# ---------------------------------------------------------------------------
# NPCSocialLink tests
# ---------------------------------------------------------------------------

class TestNPCSocialLink:
    def test_to_dict_roundtrip(self):
        link = NPCSocialLink(source_id="a", target_id="b", affinity=0.7, trust=0.5, fear=0.1,
                             history=["met in tavern"])
        restored = NPCSocialLink.from_dict(link.to_dict())
        assert restored.source_id == "a"
        assert restored.affinity == 0.7
        assert restored.history == ["met in tavern"]

    def test_affinity_clamps(self):
        link = NPCSocialLink(source_id="a", target_id="b", affinity=2.0)
        assert link.affinity == 1.0


# ---------------------------------------------------------------------------
# NPCRelationWeb tests
# ---------------------------------------------------------------------------

class TestNPCRelationWeb:
    def test_ensure_link_creates_new(self):
        web = NPCRelationWeb()
        link = web.ensure_link("npc1", "npc2")
        assert link.source_id == "npc1"
        assert link.target_id == "npc2"

    def test_ensure_link_reuses_existing(self):
        web = NPCRelationWeb()
        web.ensure_link("npc1", "npc2")
        link2 = web.ensure_link("npc1", "npc2")
        assert link2 is web.links[0]

    def test_remove_link(self):
        web = NPCRelationWeb()
        web.ensure_link("npc1", "npc2")
        web.remove_link("npc1", "npc2")
        assert len(web.links) == 0

    def test_neighbors(self):
        web = NPCRelationWeb()
        web.ensure_link("npc1", "npc2")
        web.ensure_link("npc3", "npc2")
        neighbors = web.neighbors("npc2")
        assert "npc1" in neighbors
        assert "npc3" in neighbors

    def test_to_dict_roundtrip(self):
        web = NPCRelationWeb()
        web.ensure_link("a", "b", affinity=0.5)
        restored = NPCRelationWeb.from_dict(web.to_dict())
        assert len(restored.links) == 1
        assert restored.links[0].affinity == 0.5


# ---------------------------------------------------------------------------
# ReputationTrack tests
# ---------------------------------------------------------------------------

class TestReputationTrack:
    def test_add_points_updates_standing(self):
        track = ReputationTrack(faction_id="f1", name="Village Guard")
        track.add_points(250, reason="helped_village")
        assert track.standing == ReputationStanding.HONORED.value

    def test_decay_reduces_points(self):
        track = ReputationTrack(faction_id="f2", points=100.0, decay_per_day=10.0)
        track.decay(days=2.0)
        assert track.points == 80.0

    def test_to_dict_roundtrip(self):
        track = ReputationTrack(faction_id="f3", name="Mages Guild", points=75.0,
                                standing=ReputationStanding.LIKED.value, history=["saved_library"])
        restored = ReputationTrack.from_dict(track.to_dict())
        assert restored.faction_id == "f3"
        assert restored.standing == ReputationStanding.LIKED.value
        assert restored.history == ["saved_library"]


# ---------------------------------------------------------------------------
# AdvancedNPC (RPG-13-09) tests
# ---------------------------------------------------------------------------

class TestAdvancedNPC:
    def test_schedule_integration(self):
        npc = _make_extended_npc("sched_npc", "Scheduler")
        block = NPCScheduleBlock(block_id="work_block", start_hour=9.0, end_hour=17.0,
                                 preferred_state="work", weight_boost=2.0)
        npc.add_schedule_block(block)
        active = npc.get_active_schedule_block(12.0)
        assert active is not None
        assert active.block_id == "work_block"

    def test_schedule_off_day(self):
        npc = _make_extended_npc("sched_npc2", "Sched2")
        npc.schedule.day_skip = ["sunday"]
        assert npc.get_active_schedule_block(10.0, day_name="sunday") is None

    def test_emotional_state_defaults(self):
        npc = _make_extended_npc("emo_npc", "Emo")
        assert npc.emotional_state.stress == 0.2
        assert npc.emotional_state.energy == 0.7

    def test_emotion_adjust(self):
        npc = _make_extended_npc("emo_npc2", "Emo2")
        npc.shift_emotion("stress", 0.5)
        assert npc.emotional_state.stress == 0.7
        npc.shift_emotion("stress", -0.8)
        assert npc.emotional_state.stress == 0.0

    def test_mood_tone(self):
        npc = _make_extended_npc("mood_npc", "Mood")
        npc.emotional_state.anger = 0.8
        npc.emotional_state.stress = 0.3
        assert npc.mood_tone() == "angry"

    def test_social_links_local_cache(self):
        npc = _make_extended_npc("soc_npc", "Social")
        web = NPCRelationWeb()
        web.ensure_link("soc_npc", "other", affinity=0.4)
        npc.refresh_social_links(web)
        assert len(npc.social_links()) == 1
        assert npc.social_links()[0].affinity == 0.4

    def test_reputation_default(self):
        npc = _make_extended_npc("rep_npc", "Rep")
        info = npc.reputation_toward("faction_x")
        assert info["standing"] == ReputationStanding.NEUTRAL.value
        assert info["points"] == 0.0

    def test_add_reputation(self):
        npc = _make_extended_npc("rep_npc2", "Rep2")
        track = npc.add_reputation("faction_y", 60.0, reason="helped_member")
        assert track.standing == ReputationStanding.LIKED.value
        assert track.points == 60.0
        assert len(track.history) == 1

    def test_tick_decays_emotion(self):
        npc = _make_extended_npc("tick_emo", "TickEmo")
        npc.emotional_state.stress = 0.8
        npc.emotional_state.energy = 0.9
        npc.emotional_state.fear = 0.6
        npc.emotional_state.anger = 0.7
        npc.tick(hours=5.0)
        assert npc.emotional_state.stress < 0.8
        assert npc.emotional_state.fear < 0.6
        assert npc.emotional_state.anger < 0.7

    def test_tick_decays_reputation(self):
        npc = _make_extended_npc("tick_rep", "TickRep")
        npc.add_reputation("faction_z", 100.0, decay_per_day=10.0)
        npc.tick(hours=24.0)
        assert npc.reputation["faction_z"].points == 90.0

    def test_tick_includes_mood_tone(self):
        npc = _make_extended_npc("tick_mood", "TickMood")
        summary = npc.tick(hours=1.0)
        assert "mood_tone" in summary
        assert "emotional_state" in summary
        assert "reputation" in summary

    def test_event_emotional_side_effects(self):
        npc = _make_extended_npc("event_emo", "EventEmo")
        npc.record_event(
            memory_type=MemoryType.PLAYER_ACTION.value,
            subject_id="player",
            intensity=3.0,
        )
        assert npc.emotional_state.happiness > 0.5

    def test_combat_event_emotional_side_effects(self):
        npc = _make_extended_npc("combat_emo", "CombatEmo")
        initial_stress = npc.emotional_state.stress
        npc.record_event(
            memory_type=MemoryType.COMBAT.value,
            subject_id="player",
            intensity=2.0,
        )
        assert npc.emotional_state.stress > initial_stress

    def test_to_dict_roundtrip(self):
        npc = _make_extended_npc("round_npc", "Round")
        npc.add_schedule_block(NPCScheduleBlock(block_id="bb", start_hour=8.0, end_hour=16.0,
                                                 preferred_state="work"))
        npc.shift_emotion("happiness", 0.3)
        npc.add_reputation("faction_a", 150.0, reason="heroic_deeds")
        restored = AdvancedNPC.from_dict(npc.to_dict())
        assert restored.npc_id == "round_npc"
        assert restored.schedule.blocks[0].block_id == "bb"
        assert restored.emotional_state.happiness > 0.5
        assert restored.reputation["faction_a"].points == 150.0

    def test_choose_action_with_emotion(self):
        npc = _make_extended_npc("action_emo", "ActionEmo")
        npc.emotional_state.fear = 0.8
        action = npc.choose_action(["attack", "heal", "flee", "talk"])
        assert action in ["attack", "heal", "flee", "talk"]


# ---------------------------------------------------------------------------
# AdvancedAIManager (RPG-13-09) tests
# ---------------------------------------------------------------------------

class TestAdvancedAIManager:
    def test_register_and_get_extended(self):
        mgr = AdvancedAIManager()
        npc = _make_extended_npc("mgr_ext", "MgrExt")
        mgr.register_npc(npc)
        assert mgr.get_npc("mgr_ext") is npc

    def test_set_social_link(self):
        mgr = AdvancedAIManager()
        npc1 = _make_extended_npc("soc1", "Soc1")
        npc2 = _make_extended_npc("soc2", "Soc2")
        mgr.register_npc(npc1)
        mgr.register_npc(npc2)
        link = mgr.set_social_link("soc1", "soc2", affinity=0.6, trust=0.4)
        assert link.affinity == 0.6
        assert len(mgr.get_relation_web().links) == 1

    def test_remove_social_link(self):
        mgr = AdvancedAIManager()
        npc1 = _make_extended_npc("soc3", "Soc3")
        npc2 = _make_extended_npc("soc4", "Soc4")
        mgr.register_npc(npc1)
        mgr.register_npc(npc2)
        mgr.set_social_link("soc3", "soc4")
        mgr.remove_social_link("soc3", "soc4")
        assert len(mgr.get_relation_web().links) == 0

    def test_faction_reputation(self):
        mgr = AdvancedAIManager()
        npc = _make_extended_npc("fac_npc", "Fac")
        mgr.register_npc(npc)
        result = mgr.add_faction_reputation("fac_npc", "guild", 120.0, reason="completed_quest")
        assert result["standing"] == ReputationStanding.LIKED.value
        assert result["points"] == 120.0

    def test_get_faction_standing(self):
        mgr = AdvancedAIManager()
        npc = _make_extended_npc("fac_npc2", "Fac2")
        mgr.register_npc(npc)
        info = mgr.get_faction_standing("fac_npc2", "guild2")
        assert info["standing"] == ReputationStanding.NEUTRAL.value

    def test_tick_all_with_hour(self):
        mgr = AdvancedAIManager()
        npc = _make_extended_npc("tick_all_npc", "TickAll")
        npc.add_schedule_block(NPCScheduleBlock(block_id="tb", start_hour=8.0, end_hour=18.0,
                                                 preferred_state="work", weight_boost=1.5))
        mgr.register_npc(npc)
        summaries = mgr.tick_all(hours=2.0, current_hour=10.0, day_name="monday")
        assert "tick_all_npc" in summaries
        assert "schedule_block" in summaries["tick_all_npc"]

    def test_event_propagates_to_emotions(self):
        mgr = AdvancedAIManager()
        npc = _make_extended_npc("event_npc", "Event")
        mgr.register_npc(npc)
        mgr.record_event(
            npc_id="event_npc",
            memory_type=MemoryType.PLAYER_ACTION.value,
            subject_id="player",
            intensity=3.0,
        )
        assert npc.emotional_state.happiness > 0.5

    def test_summary_includes_relation_web(self):
        mgr = AdvancedAIManager()
        npc = _make_extended_npc("sum_npc", "Sum")
        mgr.register_npc(npc)
        s = mgr.summary()
        assert "relation_web_links" in s

    def test_build_npc_from_definition(self):
        definition = {
            "npc_id": "def_npc",
            "name": "Def NPC",
            "behavior_state": "idle",
            "personality": {
                "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                "agreeableness": 0.5, "neuroticism": 0.5, "courage": 0.5,
                "loyalty": 0.5, "morality": 0.5,
            },
            "transitions": [],
            "goals": [],
            "learning_profiles": {},
            "memories": [],
            "schedule": {
                "npc_id": "def_npc",
                "blocks": [
                    {"block_id": "wb", "start_hour": 9.0, "end_hour": 17.0,
                     "preferred_state": "work", "weight_boost": 1.0, "location_id": "town"}
                ],
                "day_skip": [],
            },
            "emotional_state": {"stress": 0.3, "energy": 0.8, "happiness": 0.6, "fear": 0.2, "anger": 0.1},
            "reputation": {
                "faction_x": {"faction_id": "faction_x", "name": "Guard", "standing": "liked",
                              "points": 75.0, "decay_per_day": 0.5, "history": ["helped"]},
            },
            "social_links": [
                {"source_id": "def_npc", "target_id": "other", "affinity": 0.3, "trust": 0.2,
                 "fear": 0.0, "history": ["first_meeting"]},
            ],
        }
        npc = build_npc_from_definition(definition)
        assert isinstance(npc, AdvancedNPC)
        assert len(npc.schedule.blocks) == 1
        assert npc.emotional_state.stress == 0.3
        assert npc.reputation["faction_x"].points == 75.0
        assert len(npc._social_links) == 1


if __name__ == "__main__":
    unittest.main()
