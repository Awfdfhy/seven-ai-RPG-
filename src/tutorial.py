"""
RPG-10-12: Tutorial System
Provides structured onboarding guidance for new players. Tutorials are
composed of ordered steps, each with a hint, an optional narration snippet,
and actions the player should perform. Progress is tracked per world session
and can integrate with quests, milestones, and progression events.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Definition dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TutorialActionHint:
    """
    Describes one expected player action within a tutorial step.

    Attributes:
        action_type : broad category e.g. "travel", "open_inventory",
                      "use_ability", "talk_to_npc", "equip_item"
        target      : the specific target e.g. a location id, npc id,
                      ability id
        description : human-readable text shown to the player
    """

    action_type: str
    target: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "target": self.target,
            "description": self.description,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TutorialActionHint:
        return TutorialActionHint(
            action_type=data["action_type"],
            target=data["target"],
            description=data.get("description", ""),
        )


@dataclass
class TutorialStepDefinition:
    """
    Static definition for one step inside a tutorial.

    Attributes:
        id            : unique step identifier (unique within the tutorial)
        name          : short display name
        description   : longer text explaining what the player should do
        hint          : optional hint text shown when the player is stuck
        actions       : list of expected player actions for this step
        prerequisites : ids of other tutorial steps that must be completed
                        before this one becomes active
        metadata      : opaque extra data
    """

    id: str
    name: str
    description: str
    hint: str = ""
    actions: list[dict[str, Any]] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_expected_actions(self) -> list[TutorialActionHint]:
        return [TutorialActionHint.from_dict(a) for a in self.actions]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "hint": self.hint,
            "actions": [copy.deepcopy(a) for a in self.actions],
            "prerequisites": list(self.prerequisites),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TutorialStepDefinition:
        return TutorialStepDefinition(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            hint=data.get("hint", ""),
            actions=[copy.deepcopy(a) for a in data.get("actions", [])],
            prerequisites=list(data.get("prerequisites", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class TutorialDefinition:
    """
    Static definition for a full tutorial sequence.

    Attributes:
        id          : unique tutorial identifier
        name        : display name
        description : overview text
        steps       : ordered list of tutorial steps
        prerequisites : ids of other tutorials that must be completed
                        before this tutorial is offered
        metadata    : opaque extra data
    """

    id: str
    name: str
    description: str
    steps: list[TutorialStepDefinition] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_step(self, step_id: str) -> TutorialStepDefinition | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "prerequisites": list(self.prerequisites),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TutorialDefinition:
        return TutorialDefinition(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=[TutorialStepDefinition.from_dict(s) for s in data.get("steps", [])],
            prerequisites=list(data.get("prerequisites", [])),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Runtime state dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TutorialInstance:
    """
    Runtime record for one active or completed tutorial bound to a world.

    Attributes:
        instance_id       : unique identifier
        tutorial_id       : references the TutorialDefinition
        world_id          : the world this tutorial belongs to
        session_id        : optional session that started it
        status            : active | completed | skipped
        current_step_index: index into the definition's steps list
        completed_steps   : list of step ids the player finished
        skipped_steps     : list of step ids the player skipped
        started_at        : ISO timestamp
        completed_at      : ISO timestamp or None
        skipped_at        : ISO timestamp or None
        metadata          : opaque extra data
    """

    instance_id: str
    tutorial_id: str
    world_id: str
    session_id: str | None = None
    status: str = "active"
    current_step_index: int = 0
    completed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    skipped_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "tutorial_id": self.tutorial_id,
            "world_id": self.world_id,
            "session_id": self.session_id,
            "status": self.status,
            "current_step_index": self.current_step_index,
            "completed_steps": list(self.completed_steps),
            "skipped_steps": list(self.skipped_steps),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "skipped_at": self.skipped_at,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TutorialInstance:
        return TutorialInstance(
            instance_id=data["instance_id"],
            tutorial_id=data["tutorial_id"],
            world_id=data["world_id"],
            session_id=data.get("session_id"),
            status=data.get("status", "active"),
            current_step_index=data.get("current_step_index", 0),
            completed_steps=list(data.get("completed_steps", [])),
            skipped_steps=list(data.get("skipped_steps", [])),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            skipped_at=data.get("skipped_at"),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class TutorialManager:
    """
    Manages tutorial definitions and runtime instances across worlds/sessions.

    Typical usage:
        mgr = TutorialManager()
        mgr.load_definitions([...])

        # Start a tutorial for a new player
        instance = mgr.start_tutorial("onboarding_basics", world_id="w1")

        # Advance through steps
        mgr.advance_step(instance.instance_id)

        # Check if an action matches the current step
        match = mgr.match_action(instance.instance_id, "travel", "oakhaven")
        if match:
            mgr.complete_step(instance.instance_id)
    """

    def __init__(self) -> None:
        self._instances: dict[str, TutorialInstance] = {}
        self._definitions: dict[str, TutorialDefinition] = {}
        self._session_tutorials: dict[str, set[str]] = {}
        self._world_tutorials: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Definition loading
    # ------------------------------------------------------------------

    def register_definition(self, definition: TutorialDefinition) -> None:
        self._definitions[definition.id] = definition

    def load_definitions(self, definitions: list[TutorialDefinition]) -> None:
        for d in definitions:
            self.register_definition(d)

    def get_definition(self, tutorial_id: str) -> TutorialDefinition | None:
        return self._definitions.get(tutorial_id)

    def list_definitions(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._definitions.values()]

    # ------------------------------------------------------------------
    # Tutorial lifecycle
    # ------------------------------------------------------------------

    def start_tutorial(
        self,
        tutorial_id: str,
        world_id: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TutorialInstance | None:
        """
        Start a tutorial for a world/session. Returns None if the definition
        does not exist or if prerequisites are not met.
        """
        definition = self._definitions.get(tutorial_id)
        if definition is None:
            return None

        if not self._prerequisites_met(tutorial_id, world_id):
            return None

        instance = TutorialInstance(
            instance_id=str(uuid.uuid4()),
            tutorial_id=tutorial_id,
            world_id=world_id,
            session_id=session_id,
            status="active",
            current_step_index=0,
            metadata=metadata or {},
        )
        self._instances[instance.instance_id] = instance
        self._world_tutorials.setdefault(world_id, set()).add(tutorial_id)
        if session_id:
            self._session_tutorials.setdefault(session_id, set()).add(tutorial_id)
        return instance

    def complete_step(self, instance_id: str) -> TutorialInstance | None:
        """
        Mark the current step of the tutorial as completed and advance to
        the next step. If all steps are completed, marks the tutorial as
        completed.
        """
        instance = self._get_active_instance(instance_id)
        if instance is None:
            return None

        definition = self._definitions.get(instance.tutorial_id)
        if definition is None:
            return None

        current_step = definition.steps[instance.current_step_index]
        instance.completed_steps.append(current_step.id)

        # Advance to next step
        next_index = instance.current_step_index + 1
        if next_index >= len(definition.steps):
            instance.status = "completed"
            instance.current_step_index = len(definition.steps) - 1
            instance.completed_at = datetime.now(UTC).isoformat()
        else:
            instance.current_step_index = next_index

        return instance

    def skip_step(self, instance_id: str) -> TutorialInstance | None:
        """
        Skip the current step. Advances to the next step without requiring
        the player to perform any actions.
        """
        instance = self._get_active_instance(instance_id)
        if instance is None:
            return None

        definition = self._definitions.get(instance.tutorial_id)
        if definition is None:
            return None

        current_step = definition.steps[instance.current_step_index]
        instance.skipped_steps.append(current_step.id)

        next_index = instance.current_step_index + 1
        if next_index >= len(definition.steps):
            instance.status = "skipped"
            instance.current_step_index = len(definition.steps) - 1
            instance.skipped_at = datetime.now(UTC).isoformat()
        else:
            instance.current_step_index = next_index

        return instance

    def skip_tutorial(self, instance_id: str) -> TutorialInstance | None:
        """
        Skip the entire tutorial. Marks it as skipped.
        """
        instance = self._get_active_instance(instance_id)
        if instance is None:
            return None

        instance.status = "skipped"
        instance.skipped_at = datetime.now(UTC).isoformat()
        return instance

    def complete_tutorial(self, instance_id: str) -> TutorialInstance | None:
        """
        Immediately complete the tutorial, marking all remaining steps as
        completed.
        """
        instance = self._get_active_instance(instance_id)
        if instance is None:
            return None

        definition = self._definitions.get(instance.tutorial_id)
        if definition is None:
            return None

        # Mark all remaining steps as completed
        for step in definition.steps[instance.current_step_index:]:
            if step.id not in instance.completed_steps:
                instance.completed_steps.append(step.id)

        instance.current_step_index = len(definition.steps) - 1
        instance.status = "completed"
        instance.completed_at = datetime.now(UTC).isoformat()
        return instance

    # ------------------------------------------------------------------
    # Step queries
    # ------------------------------------------------------------------

    def get_current_step(
        self, instance_id: str
    ) -> tuple[TutorialInstance, TutorialStepDefinition] | tuple[None, None]:
        """
        Return the current tutorial instance and its active step definition.
        Returns (None, None) if the instance is not active or has no steps.
        """
        instance = self._get_active_instance(instance_id)
        if instance is None:
            return None, None

        definition = self._definitions.get(instance.tutorial_id)
        if definition is None or not definition.steps:
            return None, None

        return instance, definition.steps[instance.current_step_index]

    def get_hint(self, instance_id: str) -> str | None:
        """
        Return the hint text for the current step, or None if unavailable.
        """
        _, step = self.get_current_step(instance_id)
        if step is None:
            return None
        return step.hint or None

    def match_action(
        self, instance_id: str, action_type: str, target: str
    ) -> bool:
        """
        Check whether the given player action matches any expected action
        for the current step. Returns True if the action matches.
        """
        _, step = self.get_current_step(instance_id)
        if step is None:
            return False

        for expected in step.get_expected_actions():
            if (
                expected.action_type == action_type
                and expected.target == target
            ):
                return True
        return False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_instance(self, instance_id: str) -> TutorialInstance | None:
        return self._instances.get(instance_id)

    def list_instances(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        instances = list(self._instances.values())
        if world_id is not None:
            instances = [i for i in instances if i.world_id == world_id]
        if session_id is not None:
            instances = [i for i in instances if i.session_id == session_id]
        if status is not None:
            instances = [i for i in instances if i.status == status]
        return [i.to_dict() for i in sorted(instances, key=lambda i: i.started_at)]

    def list_active(self, world_id: str | None = None) -> list[dict[str, Any]]:
        return self.list_instances(world_id=world_id, status="active")

    def get_available_tutorials(self, world_id: str) -> list[dict[str, Any]]:
        """
        Return tutorial definitions whose prerequisites are met in the
        given world and that have not been completed or skipped.
        """
        available = []
        for tid, definition in self._definitions.items():
            if self._is_completed_or_skipped(tid, world_id):
                continue
            if self._prerequisites_met(tid, world_id):
                available.append(definition.to_dict())
        return available

    # ------------------------------------------------------------------
    # World state integration
    # ------------------------------------------------------------------

    def get_completed_tutorials(self, world_id: str) -> list[str]:
        return [
            i.tutorial_id
            for i in self._instances.values()
            if i.world_id == world_id and i.status == "completed"
        ]

    def get_skipped_tutorials(self, world_id: str) -> list[str]:
        return [
            i.tutorial_id
            for i in self._instances.values()
            if i.world_id == world_id and i.status == "skipped"
        ]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "instances": {iid: i.to_dict() for iid, i in self._instances.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._instances.clear()
        self._session_tutorials.clear()
        self._world_tutorials.clear()
        for iid, idata in state.get("instances", {}).items():
            instance = TutorialInstance.from_dict(idata)
            self._instances[iid] = instance
            self._world_tutorials.setdefault(instance.world_id, set()).add(
                instance.tutorial_id
            )
            if instance.session_id:
                self._session_tutorials.setdefault(instance.session_id, set()).add(
                    instance.tutorial_id
                )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_active_instance(self, instance_id: str) -> TutorialInstance | None:
        instance = self._instances.get(instance_id)
        if instance is None or instance.status != "active":
            return None
        return instance

    def _prerequisites_met(self, tutorial_id: str, world_id: str) -> bool:
        definition = self._definitions.get(tutorial_id)
        if definition is None:
            return False
        for prereq_id in definition.prerequisites:
            found = any(
                i.tutorial_id == prereq_id
                and i.world_id == world_id
                and i.status == "completed"
                for i in self._instances.values()
            )
            if not found:
                return False
        return True

    def _is_completed_or_skipped(self, tutorial_id: str, world_id: str) -> bool:
        return any(
            i.tutorial_id == tutorial_id
            and i.world_id == world_id
            and i.status in ("completed", "skipped")
            for i in self._instances.values()
        )
