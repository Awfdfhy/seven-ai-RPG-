"""
RPG-10-12: Onboarding System
High-level onboarding flow that automatically starts tutorial sequences
for new players and tracks completion per world and session.

Integrates with TutorialManager to drive tutorial instances and provides
convenience methods for common onboarding operations.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from tutorial import TutorialDefinition, TutorialInstance, TutorialManager, TutorialStepDefinition


@dataclass
class OnboardingState:
    """
    Tracks onboarding completion for a world.

    Attributes:
        world_id          : the world this state belongs to
        session_id        : the session that triggered onboarding (if any)
        started           : whether onboarding has been started
        completed         : whether onboarding is fully completed
        skipped           : whether onboarding was skipped
        active_instance_id: the currently active tutorial instance id
        metadata          : arbitrary extra data
    """

    world_id: str
    session_id: str | None = None
    started: bool = False
    completed: bool = False
    skipped: bool = False
    active_instance_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "session_id": self.session_id,
            "started": self.started,
            "completed": self.completed,
            "skipped": self.skipped,
            "active_instance_id": self.active_instance_id,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> OnboardingState:
        return OnboardingState(
            world_id=data["world_id"],
            session_id=data.get("session_id"),
            started=data.get("started", False),
            completed=data.get("completed", False),
            skipped=data.get("skipped", False),
            active_instance_id=data.get("active_instance_id"),
            metadata=dict(data.get("metadata", {})),
        )


class OnboardingManager:
    """
    Manages the onboarding flow for new players.

    Typical usage:
        mgr = OnboardingManager(tutorial_manager)
        mgr.load_definitions([...])

        # When a new world is opened
        state = mgr.start_onboarding("new_world", session_id="s1")

        # Check if onboarding is needed
        if mgr.is_onboarded("new_world"):
            ...

        # Advance onboarding via the tutorial manager
        mgr.complete_current_step(state.active_instance_id)
    """

    def __init__(self, tutorial_manager: TutorialManager | None = None, data_directory: str | None = None) -> None:
        self.tutorial_manager = tutorial_manager or TutorialManager()
        self._world_states: dict[str, OnboardingState] = {}
        self._onboarding_tutorial_id: str = "onboarding_basics"

        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self._load_onboarding_definitions(data_directory)

    def _load_onboarding_definitions(self, directory: str) -> None:
        path = os.path.join(directory, "onboarding.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
            definitions = [TutorialDefinition.from_dict(d) for d in raw]
            self.tutorial_manager.load_definitions(definitions)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Definition loading (delegates to TutorialManager)
    # ------------------------------------------------------------------

    def load_definitions(self, definitions: list[TutorialDefinition]) -> None:
        self.tutorial_manager.load_definitions(definitions)

    def set_onboarding_tutorial(self, tutorial_id: str) -> None:
        self._onboarding_tutorial_id = tutorial_id

    # ------------------------------------------------------------------
    # Onboarding lifecycle
    # ------------------------------------------------------------------

    def start_onboarding(
        self,
        world_id: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OnboardingState | None:
        """
        Start the onboarding tutorial for a world if not already started.
        Returns the OnboardingState or None if onboarding is already done.
        """
        if self.is_onboarded(world_id):
            return None

        state = self._world_states.get(world_id)
        if state is None:
            state = OnboardingState(world_id=world_id, session_id=session_id)

        instance = self.tutorial_manager.start_tutorial(
            self._onboarding_tutorial_id,
            world_id=world_id,
            session_id=session_id,
            metadata=metadata or {},
        )

        if instance is None:
            return None

        state.started = True
        state.active_instance_id = instance.instance_id
        state.metadata.update(metadata or {})
        self._world_states[world_id] = state
        return state

    def complete_current_step(self, instance_id: str) -> TutorialInstance | None:
        """
        Advance the current tutorial step.
        If the tutorial completes, mark onboarding as complete.
        """
        instance = self.tutorial_manager.complete_step(instance_id)
        if instance is None:
            return None

        if instance.status == "completed":
            self._mark_completed(instance.world_id)
        return instance

    def skip_current_step(self, instance_id: str) -> TutorialInstance | None:
        """
        Skip the current tutorial step.
        If the tutorial is fully skipped, mark onboarding as skipped.
        """
        instance = self.tutorial_manager.skip_step(instance_id)
        if instance is None:
            return None

        if instance.status == "skipped":
            self._mark_skipped(instance.world_id)
        return instance

    def skip_onboarding(self, world_id: str) -> OnboardingState | None:
        """
        Skip the entire onboarding tutorial for a world.
        """
        state = self._world_states.get(world_id)
        if state is None or not state.started or state.active_instance_id is None:
            return None

        instance = self.tutorial_manager.skip_tutorial(state.active_instance_id)
        if instance is None:
            return None

        self._mark_skipped(world_id)
        return self._world_states.get(world_id)

    def complete_onboarding(self, world_id: str) -> OnboardingState | None:
        """
        Force-complete onboarding for a world.
        """
        state = self._world_states.get(world_id)
        if state is None or not state.started or state.active_instance_id is None:
            return None

        instance = self.tutorial_manager.complete_tutorial(state.active_instance_id)
        if instance is None:
            return None

        self._mark_completed(world_id)
        return self._world_states.get(world_id)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_onboarded(self, world_id: str) -> bool:
        state = self._world_states.get(world_id)
        if state is None:
            return False
        return state.completed or state.skipped

    def get_state(self, world_id: str) -> OnboardingState | None:
        return self._world_states.get(world_id)

    def get_current_tutorial_instance(
        self, world_id: str
    ) -> tuple[TutorialInstance, TutorialStepDefinition] | tuple[None, None]:
        state = self._world_states.get(world_id)
        if state is None or state.active_instance_id is None:
            return None, None
        return self.tutorial_manager.get_current_step(state.active_instance_id)

    def get_hint(self, world_id: str) -> str | None:
        state = self._world_states.get(world_id)
        if state is None or state.active_instance_id is None:
            return None
        return self.tutorial_manager.get_hint(state.active_instance_id)

    def match_action(self, world_id: str, action_type: str, target: str) -> bool:
        state = self._world_states.get(world_id)
        if state is None or state.active_instance_id is None:
            return False
        return self.tutorial_manager.match_action(
            state.active_instance_id, action_type, target
        )

    def list_worlds_pending_onboarding(self) -> list[str]:
        return [
            wid
            for wid, state in self._world_states.items()
            if state.started and not state.completed and not state.skipped
        ]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "world_states": {wid: s.to_dict() for wid, s in self._world_states.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._world_states.clear()
        for wid, sdata in state.get("world_states", {}).items():
            self._world_states[wid] = OnboardingState.from_dict(sdata)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _mark_completed(self, world_id: str) -> None:
        state = self._world_states.get(world_id)
        if state is None:
            return
        state.completed = True
        state.skipped = False
        state.active_instance_id = None

    def _mark_skipped(self, world_id: str) -> None:
        state = self._world_states.get(world_id)
        if state is None:
            return
        state.skipped = True
        state.completed = False
        state.active_instance_id = None
