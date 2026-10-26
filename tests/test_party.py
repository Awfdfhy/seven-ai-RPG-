"""
Tests for RPG-10-06 Party and Companions system.
Run with: python -m pytest tests/test_party.py -v
or:       python tests/test_party.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from party import (
    CompanionAI,
    CompanionArchetype,
    CompanionInstance,
    CompanionRole,
    CompanionStance,
    PartyFormation,
    PartyManager,
    PartySlot,
    PartyState,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_archetype(archetype_id="test_companion", role=CompanionRole.FIGHTER) -> CompanionArchetype:
    return CompanionArchetype(
        id=archetype_id,
        name="Test Companion",
        description="A test companion.",
        role=role,
        base_stats={"strength": 10, "vitality": 10},
        preferred_skills=["test_skill.one", "test_skill.two"],
        default_stance=CompanionStance.AGGRESSIVE,
        personality={"courage": 7, "loyalty": 8, "caution": 5},
        availability={"min_character_level": 1, "reputation_required": "neutral"},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCompanionArchetype(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        arch = _make_archetype("roundtrip")
        data = arch.to_dict()
        restored = CompanionArchetype.from_dict(data)
        self.assertEqual(restored.id, arch.id)
        self.assertEqual(restored.role, arch.role)
        self.assertEqual(restored.default_stance, arch.default_stance)

    def test_from_dict_with_string_values(self):
        data = {
            "id": "lyra",
            "name": "Lyra",
            "role": "rogue",
            "default_stance": "aggressive",
        }
        arch = CompanionArchetype.from_dict(data)
        self.assertEqual(arch.role, CompanionRole.ROGUE)
        self.assertEqual(arch.default_stance, CompanionStance.AGGRESSIVE)


class TestCompanionInstance(unittest.TestCase):
    def test_effective_stance_falls_back_to_default(self):
        arch = _make_archetype()
        instance = CompanionInstance(
            companion_id="cmp1",
            archetype_id="test",
            character_id="cmp1",
        )
        self.assertEqual(instance.effective_stance(CompanionStance.DEFENSIVE), CompanionStance.DEFENSIVE)

    def test_to_dict_roundtrip(self):
        instance = CompanionInstance(
            companion_id="cmp1",
            archetype_id="test",
            character_id="cmp1",
            loyalty=75,
            current_stance=CompanionStance.SUPPORT,
            behavior_flags={"flag1": True},
        )
        data = instance.to_dict()
        restored = CompanionInstance.from_dict(data)
        self.assertEqual(restored.companion_id, instance.companion_id)
        self.assertEqual(restored.loyalty, 75)
        self.assertEqual(restored.current_stance, CompanionStance.SUPPORT)


class TestPartySlot(unittest.TestCase):
    def test_is_filled(self):
        slot = PartySlot(slot_index=0, character_id="char1")
        self.assertTrue(slot.is_filled())
        slot2 = PartySlot(slot_index=1)
        self.assertFalse(slot2.is_filled())

    def test_occupant_id_priority(self):
        slot = PartySlot(slot_index=0, character_id="char1", companion_id="cmp1")
        self.assertEqual(slot.occupant_id(), "char1")


class TestPartyFormation(unittest.TestCase):
    def test_requirements_met(self):
        formation = PartyFormation(
            formation_id="test",
            name="Test",
            requirements={"min_members": 2, "required_roles": ["tank", "mage"]},
        )
        mgr = PartyManager()
        party = PartyState(party_id="p1", size_limit=4)
        party.slots[0] = PartySlot(slot_index=0, character_id="char1", role="tank")
        party.slots[1] = PartySlot(slot_index=1, character_id="char2", role="mage")
        self.assertTrue(mgr._formation_requirements_met(party, formation))

    def test_requirements_not_met(self):
        formation = PartyFormation(
            formation_id="test",
            name="Test",
            requirements={"min_members": 3},
        )
        mgr = PartyManager()
        party = PartyState(party_id="p1", size_limit=4)
        party.slots[0] = PartySlot(slot_index=0, character_id="char1")
        party.slots[1] = PartySlot(slot_index=1, character_id="char2")
        self.assertFalse(mgr._formation_requirements_met(party, formation))


class TestPartyManager(unittest.TestCase):
    def setUp(self):
        self.mgr = PartyManager(data_directory=os.path.join(os.path.dirname(__file__), "..", "data"))

    def test_auto_load_companions(self):
        self.assertIn("lyra", self.mgr._archetypes)
        self.assertIn("garrick", self.mgr._archetypes)
        self.assertIn("elara", self.mgr._archetypes)

    def test_create_party(self):
        result = self.mgr.create_party(leader_id="hero", party_id="party1")
        self.assertTrue(result["success"])
        self.assertEqual(result["party_id"], "party1")
        party = self.mgr.get_party("party1")
        self.assertEqual(party.leader_id, "hero")
        self.assertEqual(party.slots[0].role, "leader")

    def test_create_party_duplicate(self):
        self.mgr.create_party(leader_id="hero", party_id="party1")
        result = self.mgr.create_party(leader_id="hero2", party_id="party1")
        self.assertFalse(result["success"])

    def test_add_and_remove_character(self):
        self.mgr.create_party(leader_id="hero", party_id="p1")
        result = self.mgr.add_character("p1", "ally1")
        self.assertTrue(result["success"])
        self.assertIn("ally1", self.mgr.get_party("p1").member_ids())
        result = self.mgr.remove_character("p1", "ally1")
        self.assertTrue(result["success"])
        self.assertNotIn("ally1", self.mgr.get_party("p1").member_ids())

    def test_add_character_to_specific_slot(self):
        self.mgr.create_party(leader_id="hero", party_id="p1")
        result = self.mgr.add_character("p1", "ally1", slot_index=2)
        self.assertTrue(result["success"])
        self.assertEqual(self.mgr.get_party("p1").slots[2].character_id, "ally1")

    def test_remove_leader_clears_leader(self):
        self.mgr.create_party(leader_id="hero", party_id="p1")
        self.mgr.remove_character("p1", "hero")
        party = self.mgr.get_party("p1")
        self.assertIsNone(party.leader_id)

    def test_recruit_companion(self):
        self.mgr.create_party(leader_id="hero", party_id="p1")
        result = self.mgr.recruit_companion("p1", "lyra")
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["companion_id"])
        companion = self.mgr.get_companion(result["companion_id"])
        self.assertEqual(companion.archetype_id, "lyra")
        self.assertEqual(companion.current_stance, CompanionStance.AGGRESSIVE)

    def test_recruit_companion_full_party(self):
        self.mgr.create_party(leader_id="hero", party_id="p1", size_limit=1)
        result = self.mgr.recruit_companion("p1", "lyra")
        self.assertFalse(result["success"])

    def test_dismiss_companion(self):
        self.mgr.create_party(leader_id="hero", party_id="p1")
        result = self.mgr.recruit_companion("p1", "lyra")
        cmp_id = result["companion_id"]
        result = self.mgr.dismiss_companion("p1", cmp_id)
        self.assertTrue(result["success"])
        self.assertIsNone(self.mgr.get_party("p1").slot_for(cmp_id))
        # Companion instance persists (can be re-recruited)
        self.assertIsNotNone(self.mgr.get_companion(cmp_id))

    def test_set_companion_stance(self):
        self.mgr.create_party(leader_id="hero", party_id="p1")
        result = self.mgr.recruit_companion("p1", "lyra")
        cmp_id = result["companion_id"]
        result = self.mgr.set_companion_stance(cmp_id, CompanionStance.DEFENSIVE)
        self.assertTrue(result["success"])
        self.assertEqual(result["stance"], "defensive")

    def test_companion_choose_skill(self):
        self.mgr.create_party(leader_id="hero", party_id="p1")
        result = self.mgr.recruit_companion("p1", "lyra")
        cmp_id = result["companion_id"]
        skill = self.mgr.companion_choose_skill(cmp_id, ["shadow_stealth.shadow_step", "fire_magic.fireball"])
        self.assertEqual(skill, "shadow_stealth.shadow_step")

    def test_set_formation(self):
        formation = PartyFormation(
            formation_id="balanced",
            name="Balanced",
            requirements={"min_members": 2},
        )
        self.mgr.register_formation(formation)
        self.mgr.create_party(leader_id="hero", party_id="p1")
        self.mgr.add_character("p1", "ally1")
        result = self.mgr.set_formation("p1", "balanced")
        self.assertTrue(result["success"])

    def test_set_formation_requirements_not_met(self):
        formation = PartyFormation(
            formation_id="balanced",
            name="Balanced",
            requirements={"min_members": 3},
        )
        self.mgr.register_formation(formation)
        self.mgr.create_party(leader_id="hero", party_id="p1")
        result = self.mgr.set_formation("p1", "balanced")
        self.assertFalse(result["success"])

    def test_get_formation_bonuses(self):
        formation = PartyFormation(
            formation_id="bonus_test",
            name="Bonus Test",
            slot_bonuses={0: {"attack": 5}},
            party_bonus={"defense": 2},
        )
        self.mgr.register_formation(formation)
        self.mgr.create_party(leader_id="hero", party_id="p1")
        self.mgr.set_formation("p1", "bonus_test")
        bonuses = self.mgr.get_formation_bonuses("p1")
        self.assertEqual(bonuses["attack"], 5)
        self.assertEqual(bonuses["defense"], 2)

    def test_get_party_summary(self):
        self.mgr.create_party(leader_id="hero", party_id="p1")
        self.mgr.recruit_companion("p1", "lyra")
        summary = self.mgr.get_party_summary("p1")
        self.assertEqual(summary["party_id"], "p1")
        self.assertEqual(summary["member_count"], 2)
        self.assertEqual(len(summary["companions"]), 1)

    def test_serialization_roundtrip(self):
        self.mgr.create_party(leader_id="hero", party_id="p1")
        self.mgr.add_character("p1", "ally1")
        self.mgr.recruit_companion("p1", "lyra")
        data = self.mgr.to_dict()
        restored = PartyManager.from_dict(data)
        self.assertEqual(restored.get_party("p1").party_id, "p1")
        self.assertEqual(len(restored.get_party("p1").members()), 3)

    def test_get_party_for_character(self):
        self.mgr.create_party(leader_id="hero", party_id="p1")
        party = self.mgr.get_party_for_character("hero")
        self.assertIsNotNone(party)
        self.assertEqual(party.party_id, "p1")


class TestCompanionAI(unittest.TestCase):
    def test_choose_stance(self):
        arch = _make_archetype()
        instance = CompanionInstance(
            companion_id="cmp1",
            archetype_id="test",
            character_id="cmp1",
            current_stance=CompanionStance.SUPPORT,
        )
        ai = CompanionAI(instance=instance, archetype=arch)
        self.assertEqual(ai.choose_stance(), CompanionStance.SUPPORT)

    def test_choose_skill_prefers_archetype(self):
        arch = _make_archetype()
        instance = CompanionInstance(companion_id="cmp1", archetype_id="test", character_id="cmp1")
        ai = CompanionAI(instance=instance, archetype=arch)
        skill = ai.choose_skill(["other_skill.one", "test_skill.one", "other_skill.two"])
        self.assertEqual(skill, "test_skill.one")

    def test_choose_target(self):
        instance = CompanionInstance(companion_id="cmp1", archetype_id="test", character_id="cmp1")
        ai = CompanionAI(instance=instance)
        self.assertEqual(ai.choose_target(["target_b", "target_a"]), "target_b")

    def test_set_stance(self):
        instance = CompanionInstance(companion_id="cmp1", archetype_id="test", character_id="cmp1")
        ai = CompanionAI(instance=instance)
        result = ai.set_stance(CompanionStance.FOLLOW)
        self.assertTrue(result["success"])
        self.assertEqual(instance.current_stance, CompanionStance.FOLLOW)


if __name__ == "__main__":
    unittest.main()
