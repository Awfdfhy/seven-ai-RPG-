"""
Session branching system: alternate timeline branches from checkpoints.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class SessionBranch:
    """
    An alternate timeline branch spawned from a session checkpoint.

    Attributes:
        branch_id       : unique identifier for the branch
        session_id      : the world session this branch belongs to
        parent_branch_id: parent branch id (None for root branch)
        name            : human-readable branch name
        checkpoint_snapshot: game-state snapshot at branch creation
        created_at      : ISO timestamp of branch creation
        status          : active | ended
        metadata        : arbitrary branch metadata
    """

    branch_id: str
    session_id: str
    parent_branch_id: str | None
    name: str
    checkpoint_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "session_id": self.session_id,
            "parent_branch_id": self.parent_branch_id,
            "name": self.name,
            "checkpoint_snapshot": dict(self.checkpoint_snapshot),
            "created_at": self.created_at,
            "status": self.status,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SessionBranch:
        return SessionBranch(
            branch_id=data["branch_id"],
            session_id=data["session_id"],
            parent_branch_id=data.get("parent_branch_id"),
            name=data["name"],
            checkpoint_snapshot=dict(data.get("checkpoint_snapshot", {})),
            created_at=data.get("created_at", ""),
            status=data.get("status", "active"),
            metadata=dict(data.get("metadata", {})),
        )


class SessionBranchManager:
    """
    Creates and tracks alternate timeline branches for a play session.
    """

    def __init__(self) -> None:
        self._branches: dict[str, SessionBranch] = {}
        self._active_branch: dict[str, str] = {}  # session_id -> branch_id

    def create_branch(
        self,
        session_id: str,
        name: str,
        parent_branch_id: str | None = None,
        snapshot: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionBranch:
        """
        Spawn a new branch from an existing branch or checkpoint snapshot.

        If parent_branch_id is provided, the new branch inherits from that branch.
        Otherwise, it is treated as a root branch for the session.
        """
        if parent_branch_id is not None:
            parent = self._branches.get(parent_branch_id)
            if parent is None:
                raise ValueError(f"Parent branch {parent_branch_id} does not exist.")
            if parent.status != "active":
                raise ValueError(f"Parent branch {parent_branch_id} is not active.")
            if parent.session_id != session_id:
                raise ValueError("Parent branch does not belong to the given session.")
            checkpoint_snapshot = dict(parent.checkpoint_snapshot)
        else:
            checkpoint_snapshot = dict(snapshot or {})

        branch_id = str(uuid.uuid4())
        branch = SessionBranch(
            branch_id=branch_id,
            session_id=session_id,
            parent_branch_id=parent_branch_id,
            name=name,
            checkpoint_snapshot=checkpoint_snapshot,
            metadata=metadata or {},
        )
        self._branches[branch_id] = branch
        self._active_branch[session_id] = branch_id
        return branch

    def get_branch(self, branch_id: str) -> SessionBranch | None:
        return self._branches.get(branch_id)

    def get_branches_for_session(self, session_id: str) -> list[dict[str, Any]]:
        return [b.to_dict() for b in self._branches.values() if b.session_id == session_id]

    def get_active_branch(self, session_id: str) -> SessionBranch | None:
        branch_id = self._active_branch.get(session_id)
        if branch_id is None:
            return None
        return self._branches.get(branch_id)

    def get_branch_history(self, branch_id: str) -> list[dict[str, Any]]:
        """
        Return the ancestry chain for the given branch, oldest first.
        """
        history: list[dict[str, Any]] = []
        current_id = branch_id
        visited: set[str] = set()
        while current_id is not None:
            if current_id in visited:
                break
            visited.add(current_id)
            branch = self._branches.get(current_id)
            if branch is None:
                break
            history.append(branch.to_dict())
            current_id = branch.parent_branch_id
        history.reverse()
        return history

    def switch_branch(self, session_id: str, branch_id: str) -> SessionBranch | None:
        """
        Switch the active branch for a session to the specified branch.
        """
        branch = self._branches.get(branch_id)
        if branch is None or branch.session_id != session_id or branch.status != "active":
            return None
        self._active_branch[session_id] = branch_id
        return branch

    def end_branch(self, branch_id: str) -> bool:
        branch = self._branches.get(branch_id)
        if branch is None or branch.status == "ended":
            return False
        branch.status = "ended"
        return True

    def update_checkpoint(self, branch_id: str, snapshot: dict[str, Any]) -> bool:
        branch = self._branches.get(branch_id)
        if branch is None or branch.status != "active":
            return False
        branch.checkpoint_snapshot = dict(snapshot)
        return True
