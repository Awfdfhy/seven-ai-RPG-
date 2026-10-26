"""
RPG World Bridge: connects WorldSession and WorldLibrary so that
session-level operations can mutate the underlying world library.
Milestone operations are also exposed through this facade.
"""

from __future__ import annotations

from typing import Any

from milestone import MilestoneManager
from world_events import WorldEventManager
from world_library import WorldLibrary
from world_session import WorldSessionManager


class WorldBridge:
    """
    Facade that couples a WorldLibrary with a WorldSessionManager and
    optional MilestoneManager and WorldEventManager.

    Exposes high-level actions:
      - open_world            -> create session + ensure world exists
      - close_session         -> end a session
      - rename_world          -> rename underlying world via library
      - archive_world         -> archive underlying world via library
      - list_world_library    -> list library worlds
      - list_active_sessions  -> list active sessions
      - trigger_milestone     -> trigger a milestone in a world
      - get_world_milestones  -> list achieved milestones for a world
      - get_milestone_effects -> aggregate world effects from milestones
      - trigger_world_event   -> trigger a dynamic world event
      - get_active_world_events -> list active world events
      - check_world_event_triggers -> evaluate and fire event triggers
    """

    def __init__(self, library: WorldLibrary | None = None, sessions: WorldSessionManager | None = None,
                 milestones: MilestoneManager | None = None, world_events: WorldEventManager | None = None) -> None:
        self.library = library or WorldLibrary()
        self.sessions = sessions or WorldSessionManager()
        self.milestones = milestones or MilestoneManager()
        self.world_events = world_events or WorldEventManager()

    # ------------------------------------------------------------------
    # World lifecycle
    # ------------------------------------------------------------------

    def open_world(self, world_id: str | None = None, name: str = "Untitled World", description: str = "",
                   metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Open a world. If `world_id` is provided and exists in the library,
        bind to it; otherwise create a new world entry.
        Returns a session dict.
        """
        if world_id is not None:
            entry = self.library.get_world(world_id)
            if entry is None:
                entry = self.library.create_world(name=name, description=description, metadata=metadata)
        else:
            entry = self.library.create_world(name=name, description=description, metadata=metadata)

        session = self.sessions.create_session(world_id=entry.world_id, metadata={"world_name": entry.name})
        return {"session": session.to_dict(), "world": entry.to_dict()}

    def close_session(self, session_id: str) -> dict[str, Any]:
        ok = self.sessions.end_session(session_id)
        session = self.sessions.get_session(session_id)
        return {
            "success": ok,
            "session_id": session_id,
            "world_id": session.world_id if session else None,
        }

    # ------------------------------------------------------------------
    # World mutation (rename / archive)
    # ------------------------------------------------------------------

    def rename_world(self, world_id: str, new_name: str) -> dict[str, Any]:
        """
        Rename a world in the library and update any active session metadata
        that caches the world name.
        """
        ok = self.library.rename_world(world_id, new_name)
        if not ok:
            return {"success": False, "reason": f"World '{world_id}' not found."}

        entry = self.library.get_world(world_id)
        # Keep active sessions' cached name in sync
        for session in self.sessions._sessions.values():
            if session.world_id == world_id and session.status == "active":
                session.metadata["world_name"] = new_name

        return {"success": True, "world_id": world_id, "new_name": new_name}

    def archive_world(self, world_id: str) -> dict[str, Any]:
        ok = self.library.archive_world(world_id)
        if not ok:
            return {"success": False, "reason": f"World '{world_id}' not found or already archived."}

        # End any active sessions for this world
        ended_sessions = []
        for session in self.sessions._sessions.values():
            if session.world_id == world_id and session.status == "active":
                self.sessions.end_session(session.session_id)
                ended_sessions.append(session.session_id)

        return {"success": True, "world_id": world_id, "ended_sessions": ended_sessions}

    def unarchive_world(self, world_id: str) -> dict[str, Any]:
        ok = self.library.unarchive_world(world_id)
        if not ok:
            return {"success": False, "reason": f"World '{world_id}' not found or already active."}
        return {"success": True, "world_id": world_id}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_world_library(self, include_archived: bool = False) -> list[dict[str, Any]]:
        return self.library.list_worlds(include_archived=include_archived)

    def list_active_sessions(self) -> list[dict[str, Any]]:
        return self.sessions.list_active_sessions()

    def get_world(self, world_id: str) -> dict[str, Any] | None:
        entry = self.library.get_world(world_id)
        return entry.to_dict() if entry else None

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.sessions.get_session(session_id)
        return session.to_dict() if session else None

    # ------------------------------------------------------------------
    # Milestones
    # ------------------------------------------------------------------

    def trigger_milestone(
        self,
        milestone_id: str,
        world_id: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        event = self.milestones.trigger_milestone(
            milestone_id, world_id, session_id=session_id, metadata=metadata
        )
        return event.to_dict() if event else None

    def get_world_milestones(self, world_id: str, status: str = "achieved") -> list[dict[str, Any]]:
        return self.milestones.list_events(world_id=world_id, status=status)

    def get_milestone_effects(self, world_id: str) -> list[dict[str, Any]]:
        return self.milestones.get_world_effects(world_id)

    def get_available_milestones(self, world_id: str) -> list[dict[str, Any]]:
        return self.milestones.get_available_milestones(world_id)

    def get_milestone_narration(self, world_id: str, scope: str | None = None) -> list[dict[str, Any]]:
        return self.milestones.get_narration_hooks(world_id, scope=scope)

    # ------------------------------------------------------------------
    # World Events
    # ------------------------------------------------------------------

    def trigger_world_event(
        self,
        event_id: str,
        world_id: str,
        session_id: str | None = None,
        trigger_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Manually trigger a world event definition in a world.

        Returns the created instance dict or None if the definition
        does not exist.
        """
        if not hasattr(self, "world_events"):
            return None
        instance = self.world_events.trigger_event(
            event_id, world_id, session_id=session_id,
            trigger_context=trigger_context,
        )
        return self.world_events._serialize_instance(instance) if instance else None

    def get_active_world_events(self, world_id: str) -> list[dict[str, Any]]:
        if not hasattr(self, "world_events"):
            return []
        return self.world_events.get_active_events(world_id)

    def get_world_event_narration(self, world_id: str, scope: str | None = None) -> list[dict[str, Any]]:
        if not hasattr(self, "world_events"):
            return []
        return self.world_events.get_narration_hooks(world_id, scope=scope)

    def resolve_world_event(self, instance_id: str, status: str = "resolved") -> dict[str, Any] | None:
        if not hasattr(self, "world_events"):
            return None
        instance = self.world_events.resolve_event(instance_id, status=status)
        return self.world_events._serialize_instance(instance) if instance else None

    def check_world_event_triggers(
        self,
        world_id: str,
        context: dict[str, Any],
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Evaluate all event definitions against `context` and trigger any
        whose conditions are met. Returns list of created instance dicts.
        """
        if not hasattr(self, "world_events"):
            return []
        instances = self.world_events.check_and_trigger(world_id, context, session_id=session_id)
        return [self.world_events._serialize_instance(i) for i in instances]

