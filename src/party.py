"""
RPG-10-06: Party and Companions
Manages party formation, companion instances, companion AI behavior,
and formation bonuses for multi-character parties.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CompanionRole(Enum):
    """Combat role a companion fills."""

    TANK = "tank"
    FIGHTER = "fighter"
    ROGUE = "rogue"
    MAGE = "mage"
    SUPPORT = "support"


class CompanionStance(Enum):
    """AI stance controlling behavior in combat."""

    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    SUPPORT = "support"
    FOLLOW = "follow"


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

@dataclass
class CompanionArchetype:
    """
    Definition of a companion type: stats, role, preferences, and lore.
    """

    id: str
    name: str
    description: str = ""
    role: CompanionRole = CompanionRole.FIGHTER
    base_stats: dict[str, Any] = field(default_factory=dict)
    preferred_skills: list[str] = field(default_factory=list)
    default_stance: CompanionStance = CompanionStance.FOLLOW
    personality: dict[str, Any] = field(default_factory=dict)
    availability: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "role": self.role.value,
            "base_stats": dict(self.base_stats),
            "preferred_skills": list(self.preferred_skills),
            "default_stance": self.default_stance.value,
            "personality": dict(self.personality),
            "availability": dict(self.availability),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CompanionArchetype:
        role = CompanionRole(data["role"]) if not isinstance(data.get("role"), CompanionRole) else data["role"]
        stance = CompanionStance(data["default_stance"]) if not isinstance(data.get("default_stance"), CompanionStance) else data["default_stance"]
        return CompanionArchetype(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            role=role,
            base_stats=dict(data.get("base_stats", {})),
            preferred_skills=list(data.get("preferred_skills", [])),
            default_stance=stance,
            personality=dict(data.get("personality", {})),
            availability=dict(data.get("availability", {})),
        )


@dataclass
class CompanionInstance:
    """
    Runtime companion bound to a character, carrying state.
    """

    companion_id: str
    archetype_id: str
    character_id: str
    loyalty: int = 50
    current_stance: CompanionStance | None = None
    behavior_flags: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.current_stance, str):
            self.current_stance = CompanionStance(self.current_stance)

    def effective_stance(self, default: CompanionStance) -> CompanionStance:
        return self.current_stance or default

    def to_dict(self) -> dict[str, Any]:
        return {
            "companion_id": self.companion_id,
            "archetype_id": self.archetype_id,
            "character_id": self.character_id,
            "loyalty": self.loyalty,
            "current_stance": self.current_stance.value if self.current_stance else None,
            "behavior_flags": dict(self.behavior_flags),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CompanionInstance:
        return CompanionInstance(
            companion_id=data["companion_id"],
            archetype_id=data["archetype_id"],
            character_id=data["character_id"],
            loyalty=data.get("loyalty", 50),
            current_stance=data.get("current_stance"),
            behavior_flags=dict(data.get("behavior_flags", {})),
        )


# ---------------------------------------------------------------------------
# Party structure
# ---------------------------------------------------------------------------

@dataclass
class PartySlot:
    """One position within a party."""

    slot_index: int
    character_id: str | None = None
    companion_id: str | None = None
    role: str = "member"

    def is_filled(self) -> bool:
        return self.character_id is not None or self.companion_id is not None

    def occupant_id(self) -> str | None:
        return self.character_id or self.companion_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_index": self.slot_index,
            "character_id": self.character_id,
            "companion_id": self.companion_id,
            "role": self.role,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PartySlot:
        return PartySlot(
            slot_index=data["slot_index"],
            character_id=data.get("character_id"),
            companion_id=data.get("companion_id"),
            role=data.get("role", "member"),
        )


@dataclass
class PartyFormation:
    """
    Defines position-based bonuses for a party arrangement.
    """

    formation_id: str
    name: str
    description: str = ""
    slot_bonuses: dict[int, dict[str, Any]] = field(default_factory=dict)
    party_bonus: dict[str, Any] = field(default_factory=dict)
    requirements: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "formation_id": self.formation_id,
            "name": self.name,
            "description": self.description,
            "slot_bonuses": {int(k): dict(v) for k, v in self.slot_bonuses.items()},
            "party_bonus": dict(self.party_bonus),
            "requirements": dict(self.requirements),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PartyFormation:
        return PartyFormation(
            formation_id=data["formation_id"],
            name=data["name"],
            description=data.get("description", ""),
            slot_bonuses={int(k): dict(v) for k, v in data.get("slot_bonuses", {}).items()},
            party_bonus=dict(data.get("party_bonus", {})),
            requirements=dict(data.get("requirements", {})),
        )


@dataclass
class PartyState:
    """
    Full state of one active party.
    """

    party_id: str
    leader_id: str | None = None
    slots: list[PartySlot] = field(default_factory=list)
    formation_id: str = "standard"
    size_limit: int = 4

    def __post_init__(self) -> None:
        if not self.slots:
            self.slots = [PartySlot(slot_index=i) for i in range(self.size_limit)]

    def members(self) -> list[PartySlot]:
        return [s for s in self.slots if s.is_filled()]

    def member_ids(self) -> list[str]:
        return [oid for s in self.members() for oid in [s.occupant_id()] if oid is not None]

    def slot_for(self, occupant_id: str) -> PartySlot | None:
        for slot in self.slots:
            if slot.occupant_id() == occupant_id:
                return slot
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_id": self.party_id,
            "leader_id": self.leader_id,
            "slots": [s.to_dict() for s in self.slots],
            "formation_id": self.formation_id,
            "size_limit": self.size_limit,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PartyState:
        state = PartyState(
            party_id=data["party_id"],
            leader_id=data.get("leader_id"),
            formation_id=data.get("formation_id", "standard"),
            size_limit=data.get("size_limit", 4),
        )
        state.slots = [PartySlot.from_dict(s) for s in data.get("slots", [])]
        return state


# ---------------------------------------------------------------------------
# Companion AI
# ---------------------------------------------------------------------------

class CompanionAI:
    """
    Holds and resolves AI behavior for a companion instance.
    """

    def __init__(
        self,
        instance: CompanionInstance,
        archetype: CompanionArchetype | None = None,
    ) -> None:
        self.instance = instance
        self.archetype = archetype
        self._cooldowns: dict[str, float] = {}

    def choose_stance(self, context: dict[str, Any] | None = None) -> CompanionStance:
        context = context or {}
        if self.instance.current_stance:
            return self.instance.current_stance
        if self.archetype:
            return self.archetype.default_stance
        return CompanionStance.FOLLOW

    def choose_skill(self, available: list[str]) -> str | None:
        if not available:
            return None
        preferred = []
        if self.archetype:
            preferred = [s for s in available if s in self.archetype.preferred_skills]
        return preferred[0] if preferred else available[0]

    def choose_target(self, targets: list[str]) -> str | None:
        if not targets:
            return None
        return targets[0]

    def behavior_rule(self, rule_id: str) -> dict[str, Any]:
        return self.instance.behavior_flags.get(rule_id, {})

    def set_stance(self, stance: CompanionStance) -> dict[str, Any]:
        self.instance.current_stance = stance
        return {"success": True, "stance": stance.value}

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance": self.instance.to_dict(),
            "archetype_id": self.archetype.id if self.archetype else None,
            "cooldowns": dict(self._cooldowns),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CompanionAI:
        instance = CompanionInstance.from_dict(data["instance"])
        ai = CompanionAI(instance=instance)
        ai._cooldowns = dict(data.get("cooldowns", {}))
        return ai


# ---------------------------------------------------------------------------
# Party Manager
# ---------------------------------------------------------------------------

class PartyManager:
    """
    Creates and tracks parties and companion instances.
    """

    def __init__(
        self,
        party_limit: int = 4,
        data_directory: str | None = None,
    ) -> None:
        self._parties: dict[str, PartyState] = {}
        self._archetypes: dict[str, CompanionArchetype] = {}
        self._companions: dict[str, CompanionInstance] = {}
        self._party_ai: dict[str, CompanionAI] = {}
        self._formations: dict[str, PartyFormation] = {}
        self._character_to_party: dict[str, str] = {}

        self._register_default_formation()
        if data_directory:
            self._load_companions_from_data(data_directory)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def register_archetype(self, archetype: CompanionArchetype) -> None:
        self._archetypes[archetype.id] = archetype

    def add_companion(
        self,
        character_id: str,
        archetype_id: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create a default party for the character and recruit a companion."""
        party_id = f"party_{character_id}"
        if party_id not in self._parties:
            result = self.create_party(leader_id=character_id, party_id=party_id)
            if not result.get("success"):
                return result
        return self.recruit_companion(
            party_id=party_id,
            archetype_id=archetype_id,
            companion_id=None,
        )

    def register_formation(self, formation: PartyFormation) -> None:
        self._formations[formation.formation_id] = formation

    def _register_default_formation(self) -> None:
        self._formations["standard"] = PartyFormation(
            formation_id="standard",
            name="Standard",
            description="No formation bonus.",
            slot_bonuses={},
            party_bonus={},
            requirements={},
        )

    def _load_companions_from_data(self, directory: str) -> None:
        """Auto-load companion archetypes from companions.json if present."""
        if not os.path.isdir(directory):
            return
        path = os.path.join(directory, "companions.json")
        if not os.path.isfile(path):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            for archetype_data in data:
                archetype = CompanionArchetype.from_dict(archetype_data)
                self.register_archetype(archetype)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Party lifecycle
    # ------------------------------------------------------------------

    def create_party(self, leader_id: str, party_id: str | None = None, size_limit: int = 4) -> dict[str, Any]:
        party_id = party_id or str(uuid.uuid4())
        if party_id in self._parties:
            return {"success": False, "reason": f"Party '{party_id}' already exists."}
        party = PartyState(party_id=party_id, leader_id=leader_id, size_limit=size_limit)
        party.slots[0] = PartySlot(slot_index=0, character_id=leader_id, role="leader")
        self._parties[party_id] = party
        self._character_to_party[leader_id] = party_id
        return {"success": True, "party_id": party_id}

    def get_party(self, party_id: str) -> PartyState | None:
        return self._parties.get(party_id)

    def get_party_for_character(self, character_id: str) -> PartyState | None:
        pid = self._character_to_party.get(character_id)
        return self._parties.get(pid) if pid else None

    def list_parties(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._parties.values()]

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------

    def add_character(self, party_id: str, character_id: str, slot_index: int | None = None) -> dict[str, Any]:
        party = self._parties.get(party_id)
        if party is None:
            return {"success": False, "reason": "Party not found."}
        existing = self._character_to_party.get(character_id)
        if existing and existing != party_id:
            return {"success": False, "reason": f"Character already in party '{existing}'."}
        if character_id in party.member_ids():
            return {"success": False, "reason": "Character already in this party."}
        if slot_index is not None:
            if slot_index < 0 or slot_index >= party.size_limit:
                return {"success": False, "reason": "Slot index out of range."}
            target = party.slots[slot_index]
            if target.is_filled():
                return {"success": False, "reason": "Slot already occupied."}
            target.character_id = character_id
            target.companion_id = None
        else:
            for slot in party.slots:
                if not slot.is_filled():
                    slot.character_id = character_id
                    slot.companion_id = None
                    break
            else:
                return {"success": False, "reason": "Party is full."}
        self._character_to_party[character_id] = party_id
        return {"success": True, "party_id": party_id, "character_id": character_id}

    def remove_character(self, party_id: str, character_id: str) -> dict[str, Any]:
        party = self._parties.get(party_id)
        if party is None:
            return {"success": False, "reason": "Party not found."}
        slot = party.slot_for(character_id)
        if slot is None:
            return {"success": False, "reason": "Character not in party."}
        if party.leader_id == character_id:
            party.leader_id = None
        slot.character_id = None
        slot.companion_id = None
        del self._character_to_party[character_id]
        return {"success": True}

    def set_leader(self, party_id: str, character_id: str) -> dict[str, Any]:
        party = self._parties.get(party_id)
        if party is None:
            return {"success": False, "reason": "Party not found."}
        if character_id not in party.member_ids():
            return {"success": False, "reason": "Character not in party."}
        party.leader_id = character_id
        return {"success": True, "leader_id": character_id}

    # ------------------------------------------------------------------
    # Companions
    # ------------------------------------------------------------------

    def register_companion(self, archetype: CompanionArchetype) -> dict[str, Any]:
        self._archetypes[archetype.id] = archetype
        return {"success": True, "archetype_id": archetype.id}

    def recruit_companion(
        self,
        party_id: str,
        archetype_id: str,
        companion_id: str | None = None,
    ) -> dict[str, Any]:
        party = self._parties.get(party_id)
        if party is None:
            return {"success": False, "reason": "Party not found."}
        archetype = self._archetypes.get(archetype_id)
        if archetype is None:
            return {"success": False, "reason": "Archetype not found."}
        if len(party.members()) >= party.size_limit:
            return {"success": False, "reason": "Party is full."}
        companion_id = companion_id or f"cmp_{uuid.uuid4()}"
        instance = CompanionInstance(
            companion_id=companion_id,
            archetype_id=archetype_id,
            character_id=companion_id,
            current_stance=archetype.default_stance,
        )
        self._companions[companion_id] = instance
        ai = CompanionAI(instance=instance, archetype=archetype)
        self._party_ai[companion_id] = ai
        # Find empty slot
        for slot in party.slots:
            if not slot.is_filled():
                slot.companion_id = companion_id
                slot.character_id = None
                slot.role = "companion"
                self._character_to_party[companion_id] = party_id
                return {"success": True, "companion_id": companion_id}
        return {"success": False, "reason": "Party is full."}

    def dismiss_companion(self, party_id: str, companion_id: str) -> dict[str, Any]:
        party = self._parties.get(party_id)
        if party is None:
            return {"success": False, "reason": "Party not found."}
        slot = party.slot_for(companion_id)
        if slot is None:
            return {"success": False, "reason": "Companion not in party."}
        slot.companion_id = None
        slot.character_id = None
        self._character_to_party.pop(companion_id, None)
        return {"success": True}

    def get_companion(self, companion_id: str) -> CompanionInstance | None:
        return self._companions.get(companion_id)

    def get_companion_ai(self, companion_id: str) -> CompanionAI | None:
        return self._party_ai.get(companion_id)

    def set_companion_stance(self, companion_id: str, stance: CompanionStance) -> dict[str, Any]:
        ai = self._party_ai.get(companion_id)
        if ai is None:
            return {"success": False, "reason": "Companion AI not found."}
        return ai.set_stance(stance)

    def companion_choose_skill(self, companion_id: str, available: list[str]) -> str | None:
        ai = self._party_ai.get(companion_id)
        if ai is None:
            return None
        return ai.choose_skill(available)

    # ------------------------------------------------------------------
    # Formations
    # ------------------------------------------------------------------

    def set_formation(self, party_id: str, formation_id: str) -> dict[str, Any]:
        party = self._parties.get(party_id)
        if party is None:
            return {"success": False, "reason": "Party not found."}
        formation = self._formations.get(formation_id)
        if formation is None:
            return {"success": False, "reason": "Formation not found."}
        if not self._formation_requirements_met(party, formation):
            return {"success": False, "reason": "Party does not meet formation requirements."}
        party.formation_id = formation_id
        return {"success": True, "formation_id": formation_id}

    def get_formation_bonuses(self, party_id: str) -> dict[str, Any]:
        party = self._parties.get(party_id)
        if party is None:
            return {}
        formation = self._formations.get(party.formation_id)
        if formation is None:
            return {}
        bonuses: dict[str, Any] = dict(formation.party_bonus)
        for slot in party.members():
            slot_bonus = formation.slot_bonuses.get(slot.slot_index, {})
            for stat, value in slot_bonus.items():
                bonuses[stat] = bonuses.get(stat, 0) + value
        return bonuses

    def _formation_requirements_met(self, party: PartyState, formation: PartyFormation) -> bool:
        req = formation.requirements
        if "min_members" in req and len(party.members()) < req["min_members"]:
            return False
        if "max_members" in req and len(party.members()) > req["max_members"]:
            return False
        if "required_roles" in req:
            roles = {slot.role for slot in party.members()}
            for r in req["required_roles"]:
                if r not in roles:
                    return False
        return True

    # ------------------------------------------------------------------
    # Summary / serialization
    # ------------------------------------------------------------------

    def get_party_summary(self, party_id: str) -> dict[str, Any]:
        party = self._parties.get(party_id)
        if party is None:
            return {"success": False, "reason": "Party not found."}
        return {
            "party_id": party.party_id,
            "leader_id": party.leader_id,
            "size_limit": party.size_limit,
            "member_count": len(party.members()),
            "members": party.member_ids(),
            "formation_id": party.formation_id,
            "formation_bonuses": self.get_formation_bonuses(party_id),
            "companions": [
                {
                    "companion_id": cid,
                    "archetype_id": self._companions[cid].archetype_id,
                    "loyalty": self._companions[cid].loyalty,
                    "stance": self._party_ai[cid].instance.current_stance.value if self._party_ai[cid].instance.current_stance else None,
                }
                for slot in party.members()
                if slot.companion_id and slot.companion_id in self._companions
                for cid in [slot.companion_id]
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "parties": {pid: p.to_dict() for pid, p in self._parties.items()},
            "archetypes": {aid: a.to_dict() for aid, a in self._archetypes.items()},
            "companions": {cid: c.to_dict() for cid, c in self._companions.items()},
            "formations": {fid: f.to_dict() for fid, f in self._formations.items()},
            "character_to_party": dict(self._character_to_party),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PartyManager:
        mgr = PartyManager()
        for fid, fdata in data.get("formations", {}).items():
            mgr._formations[fid] = PartyFormation.from_dict(fdata)
        for aid, adata in data.get("archetypes", {}).items():
            mgr._archetypes[aid] = CompanionArchetype.from_dict(adata)
        for cid, cdata in data.get("companions", {}).items():
            mgr._companions[cid] = CompanionInstance.from_dict(cdata)
            ai_data = data.get("party_ai", {}).get(cid)
            if ai_data:
                mgr._party_ai[cid] = CompanionAI.from_dict(ai_data)
            else:
                archetype = mgr._archetypes.get(mgr._companions[cid].archetype_id)
                mgr._party_ai[cid] = CompanionAI(instance=mgr._companions[cid], archetype=archetype)
        for pid, pdata in data.get("parties", {}).items():
            mgr._parties[pid] = PartyState.from_dict(pdata)
        mgr._character_to_party = dict(data.get("character_to_party", {}))
        return mgr
