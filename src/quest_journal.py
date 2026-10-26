"""
RPG Quest Journal: tracks active, completed, and failed quests
bound to a world session. Supports objectives, rewards, and progress
reporting that integrates with world state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

@dataclass
class QuestObjective:
    """A single quest objective."""

    id: str
    description: str
    required_count: int = 1
    current_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "required_count": self.required_count,
            "current_count": self.current_count,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> QuestObjective:
        return QuestObjective(
            id=data["id"],
            description=data.get("description", ""),
            required_count=data.get("required_count", 1),
            current_count=data.get("current_count", 0),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class QuestReward:
    """Reward granted on quest completion."""

    type: str
    amount: int = 0
    item_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "amount": self.amount,
            "item_id": self.item_id,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> QuestReward:
        return QuestReward(
            type=data["type"],
            amount=data.get("amount", 0),
            item_id=data.get("item_id"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class QuestDefinition:
    """Static definition of a quest."""

    id: str
    name: str
    description: str
    objectives: list[dict[str, Any]] = field(default_factory=list)
    rewards: list[dict[str, Any]] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "objectives": list(self.objectives),
            "rewards": list(self.rewards),
            "prerequisites": list(self.prerequisites),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> QuestDefinition:
        return QuestDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            objectives=list(data.get("objectives", [])),
            rewards=list(data.get("rewards", [])),
            prerequisites=list(data.get("prerequisites", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class QuestEntry:
    """Runtime state for one quest instance bound to a world."""

    quest_id: str
    name: str
    description: str
    status: str = "active"  # active | completed | failed
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    failed_at: str | None = None
    objectives: list[QuestObjective] = field(default_factory=list)
    rewards: list[QuestReward] = field(default_factory=list)
    world_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failed_at": self.failed_at,
            "objectives": [o.to_dict() for o in self.objectives],
            "rewards": [r.to_dict() for r in self.rewards],
            "world_id": self.world_id,
            "session_id": self.session_id,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> QuestEntry:
        return QuestEntry(
            quest_id=data["quest_id"],
            name=data["name"],
            description=data.get("description", ""),
            status=data.get("status", "active"),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            failed_at=data.get("failed_at"),
            objectives=[QuestObjective.from_dict(o) for o in data.get("objectives", [])],
            rewards=[QuestReward.from_dict(r) for r in data.get("rewards", [])],
            world_id=data.get("world_id"),
            session_id=data.get("session_id"),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class QuestJournalManager:
    """
    Manages quest instances across worlds/sessions.

    Integrates with world state by scoping quests to a world_id and
    session_id.
    """

    def __init__(self) -> None:
        self._quests: dict[str, QuestEntry] = {}
        self._definitions: dict[str, QuestDefinition] = {}
        self._session_quests: dict[str, set[str]] = {}
        self._world_quests: dict[str, set[str]] = {}

    def register_definition(self, definition: QuestDefinition) -> None:
        self._definitions[definition.id] = definition

    def register_quest(self, quest: QuestDefinition) -> None:
        """Alias for register_definition (test convenience)."""
        self.register_definition(quest)

    def load_definitions(self, definitions: list[QuestDefinition]) -> None:
        for d in definitions:
            self.register_definition(d)

    def start_quest(
        self,
        quest_id: str,
        world_id: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> QuestEntry | None:
        definition = self._definitions.get(quest_id)
        if definition is None:
            return None

        entry = QuestEntry(
            quest_id=definition.id,
            name=definition.name,
            description=definition.description,
            world_id=world_id,
            session_id=session_id,
            objectives=[
                QuestObjective(
                    id=obj["id"],
                    description=obj.get("description", ""),
                    required_count=obj.get("required_count", 1),
                    current_count=0,
                    metadata=dict(obj.get("metadata", {})),
                )
                for obj in definition.objectives
            ],
            rewards=[
                QuestReward(
                    type=rw["type"],
                    amount=rw.get("amount", 0),
                    item_id=rw.get("item_id"),
                    metadata=dict(rw.get("metadata", {})),
                )
                for rw in definition.rewards
            ],
            metadata=metadata or {},
        )
        self._quests[entry.quest_id] = entry
        if session_id:
            self._session_quests.setdefault(session_id, set()).add(entry.quest_id)
        self._world_quests.setdefault(world_id, set()).add(entry.quest_id)
        return entry

    def get_quest(self, quest_id: str) -> QuestEntry | None:
        return self._quests.get(quest_id)

    def list_quests(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        quests = list(self._quests.values())
        if world_id is not None:
            quests = [q for q in quests if q.world_id == world_id]
        if session_id is not None:
            quests = [q for q in quests if q.session_id == session_id]
        if status is not None:
            quests = [q for q in quests if q.status == status]
        return [q.to_dict() for q in sorted(quests, key=lambda q: q.started_at)]

    def update_objective(
        self,
        quest_id: str,
        objective_id: str,
        delta: int = 1,
    ) -> QuestEntry | None:
        quest = self._quests.get(quest_id)
        if quest is None or quest.status != "active":
            return None
        for obj in quest.objectives:
            if obj.id == objective_id:
                obj.current_count = max(0, obj.current_count + delta)
                break
        return quest

    def set_objective(
        self,
        quest_id: str,
        objective_id: str,
        count: int,
    ) -> QuestEntry | None:
        quest = self._quests.get(quest_id)
        if quest is None or quest.status != "active":
            return None
        for obj in quest.objectives:
            if obj.id == objective_id:
                obj.current_count = max(0, int(count))
                break
        return quest

    def complete_objectives(self, quest_id: str) -> QuestEntry | None:
        quest = self._quests.get(quest_id)
        if quest is None or quest.status != "active":
            return None
        for obj in quest.objectives:
            obj.current_count = obj.required_count
        return quest

    def complete_quest(self, quest_id: str) -> QuestEntry | None:
        quest = self._quests.get(quest_id)
        if quest is None or quest.status != "active":
            return None
        if all(o.current_count >= o.required_count for o in quest.objectives):
            quest.status = "completed"
            quest.completed_at = datetime.now(UTC).isoformat()
        return quest

    def fail_quest(self, quest_id: str, reason: str = "") -> QuestEntry | None:
        quest = self._quests.get(quest_id)
        if quest is None or quest.status != "active":
            return None
        quest.status = "failed"
        quest.failed_at = datetime.now(UTC).isoformat()
        if reason:
            quest.metadata.setdefault("failure_reasons", []).append(reason)
        return quest

    def get_progress(self, quest_id: str) -> dict[str, Any]:
        quest = self._quests.get(quest_id)
        if quest is None:
            return {}
        total = sum(o.required_count for o in quest.objectives)
        current = sum(o.current_count for o in quest.objectives)
        return {
            "quest_id": quest.quest_id,
            "status": quest.status,
            "objectives_total": total,
            "objectives_completed": current,
            "progress": current / total if total else 0.0,
            "objectives": [o.to_dict() for o in quest.objectives],
        }

    def get_rewards(self, quest_id: str) -> list[dict[str, Any]]:
        quest = self._quests.get(quest_id)
        if quest is None:
            return []
        return [r.to_dict() for r in quest.rewards]

    def abandon_quest(self, quest_id: str) -> QuestEntry | None:
        quest = self._quests.get(quest_id)
        if quest is None or quest.status != "active":
            return None
        del self._quests[quest_id]
        self._session_quests.get(quest.session_id, set()).discard(quest_id)
        self._world_quests.get(quest.world_id, set()).discard(quest_id)
        return quest

    def export_state(self) -> dict[str, Any]:
        return {
            "quests": {qid: q.to_dict() for qid, q in self._quests.items()},
            "session_quests": {sid: list(qids) for sid, qids in self._session_quests.items()},
            "world_quests": {wid: list(qids) for wid, qids in self._world_quests.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._quests.clear()
        self._session_quests.clear()
        self._world_quests.clear()
        for qid, qdata in state.get("quests", {}).items():
            self._quests[qid] = QuestEntry.from_dict(qdata)
        for sid, qids in state.get("session_quests", {}).items():
            self._session_quests[sid] = set(qids)
        for wid, qids in state.get("world_quests", {}).items():
            self._world_quests[wid] = set(qids)
