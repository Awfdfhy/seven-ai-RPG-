"""
RPG World Persistence: file-based save / load for the world library,
active play sessions, milestone events, and world simulation state.
"""

from __future__ import annotations

import json
import os
from typing import Any

from milestone import MilestoneManager
from tutorial import TutorialManager
from world_events import WorldEventManager
from world_library import WorldLibrary
from world_session import WorldSession, WorldSessionManager
from world_simulation import WorldSimulationManager


class WorldPersistence:
    """
    Handles reading and writing the complete world state (library + sessions
    + milestones + tutorials + world events + world simulation) to a JSON file on disk.
    """

    def __init__(self, library: WorldLibrary | None = None,
                 sessions: WorldSessionManager | None = None,
                 milestones: MilestoneManager | None = None,
                 tutorials: TutorialManager | None = None,
                 world_events: WorldEventManager | None = None,
                 world_simulation: WorldSimulationManager | None = None) -> None:
        self.library = library or WorldLibrary()
        self.sessions = sessions or WorldSessionManager()
        self.milestones = milestones or MilestoneManager()
        self.tutorials = tutorials or TutorialManager()
        self.world_events = world_events or WorldEventManager()
        self.world_simulation = world_simulation or WorldSimulationManager()

    def save(self, path: str) -> dict[str, Any]:
        """
        Serialize the current library, session, milestone, tutorial, world
        event, and world simulation state to `path`.

        Returns:
            {"success": True, "path": str, "worlds": int, "sessions": int,
             "milestone_events": int, "tutorial_instances": int, "world_events": int,
             "world_simulation_worlds": int}
        """
        payload = {
            "version": 1,
            "worlds": self.library.export_state(),
            "sessions": [s.to_dict() for s in self.sessions._sessions.values()],
            "milestones": self.milestones.export_state(),
            "tutorials": self.tutorials.export_state(),
            "world_events": self.world_events.export_state(),
            "world_simulation": self.world_simulation.export_state(),
        }
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return {
            "success": True,
            "path": path,
            "worlds": len(self.library._worlds),
            "sessions": len(self.sessions._sessions),
            "milestone_events": len(self.milestones._events),
            "tutorial_instances": len(self.tutorials._instances),
            "world_events": len(self.world_events._events),
            "world_simulation_worlds": len(self.world_simulation._day_night),
        }

    def load(self, path: str) -> dict[str, Any]:
        """
        Replace current state with data loaded from `path`.

        Returns:
            {"success": True, "path": str, ...}
        """
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)

        self.library.import_state(payload.get("worlds", {}))
        self.sessions._sessions.clear()
        for sdata in payload.get("sessions", []):
            session = WorldSession.from_dict(sdata)
            self.sessions._sessions[session.session_id] = session

        self.milestones.import_state(payload.get("milestones", {}))
        self.tutorials.import_state(payload.get("tutorials", {}))
        self.world_events.import_state(payload.get("world_events", {}))
        self.world_simulation.import_state(payload.get("world_simulation", {}))

        return {
            "success": True,
            "path": path,
            "worlds": len(self.library._worlds),
            "sessions": len(self.sessions._sessions),
            "milestone_events": len(self.milestones._events),
            "tutorial_instances": len(self.tutorials._instances),
            "world_events": len(self.world_events._events),
            "world_simulation_worlds": len(self.world_simulation._day_night),
        }

    def save_library(self, path: str) -> dict[str, Any]:
        """
        Convenience: persist only the library state (no sessions or milestones).
        """
        payload = {
            "version": 1,
            "worlds": self.library.export_state(),
        }
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return {"success": True, "path": path, "worlds": len(self.library._worlds)}

    def load_library(self, path: str) -> dict[str, Any]:
        """
        Convenience: load only the library state from `path`.
        """
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        self.library.import_state(payload.get("worlds", {}))
        return {"success": True, "path": path, "worlds": len(self.library._worlds)}
