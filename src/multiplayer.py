"""
RPG-13-10: Multiplayer

Provides multiplayer session management including room creation, player
synchronization, party formation across networked clients, chat, and
state broadcasting.  Designed to integrate with the existing PartyManager,
WorldSessionManager, and combat systems.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RoomState(Enum):
    """Lifecycle state of a multiplayer room."""

    LOBBY = "lobby"
    PLAYING = "playing"
    PAUSED = "paused"
    ENDED = "ended"


class PlayerRole(Enum):
    """Role a player occupies within a multiplayer room."""

    HOST = "host"
    GUEST = "guest"
    SPECTATOR = "spectator"


class ChatChannel(Enum):
    """Target audience for a chat message."""

    GLOBAL = "global"
    PARTY = "party"
    ROOM = "room"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@dataclass
class ChatMessage:
    """Single chat message broadcast inside a multiplayer room."""

    message_id: str
    room_id: str
    player_id: str | None
    channel: ChatChannel
    text: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if isinstance(self.channel, str):
            self.channel = ChatChannel(self.channel)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "room_id": self.room_id,
            "player_id": self.player_id,
            "channel": self.channel.value,
            "text": self.text,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ChatMessage:
        channel = data.get("channel", "global")
        if not isinstance(channel, ChatChannel):
            channel = ChatChannel(channel)
        return ChatMessage(
            message_id=data["message_id"],
            room_id=data["room_id"],
            player_id=data.get("player_id"),
            channel=channel,
            text=data["text"],
            timestamp=data.get("timestamp", ""),
        )


# ---------------------------------------------------------------------------
# Player session
# ---------------------------------------------------------------------------

@dataclass
class PlayerSession:
    """
    Network session for one connected multiplayer player.
    """

    player_id: str
    room_id: str
    display_name: str = ""
    role: PlayerRole = PlayerRole.GUEST
    character_id: str | None = None
    is_ready: bool = False
    ping_ms: float = 0.0
    last_seen: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.role, str):
            self.role = PlayerRole(self.role)

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "room_id": self.room_id,
            "display_name": self.display_name,
            "role": self.role.value,
            "character_id": self.character_id,
            "is_ready": self.is_ready,
            "ping_ms": self.ping_ms,
            "last_seen": self.last_seen,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PlayerSession:
        role = data.get("role", "guest")
        if not isinstance(role, PlayerRole):
            role = PlayerRole(role)
        return PlayerSession(
            player_id=data["player_id"],
            room_id=data["room_id"],
            display_name=data.get("display_name", ""),
            role=role,
            character_id=data.get("character_id"),
            is_ready=data.get("is_ready", False),
            ping_ms=data.get("ping_ms", 0.0),
            last_seen=data.get("last_seen", ""),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

@dataclass
class MultiplayerRoom:
    """
    A multiplayer game room containing sessions, chat history, and
    shared state that gets broadcast to participants.
    """

    room_id: str
    name: str = ""
    state: RoomState = RoomState.LOBBY
    host_id: str | None = None
    max_players: int = 4
    sessions: dict[str, PlayerSession] = field(default_factory=dict)
    chat: list[ChatMessage] = field(default_factory=list)
    shared_state: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    ended_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.state, str):
            self.state = RoomState(self.state)

    def player_ids(self) -> list[str]:
        return list(self.sessions.keys())

    def is_full(self) -> bool:
        return len(self.sessions) >= self.max_players

    def host(self) -> PlayerSession | None:
        if self.host_id and self.host_id in self.sessions:
            return self.sessions[self.host_id]
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "name": self.name,
            "state": self.state.value,
            "host_id": self.host_id,
            "max_players": self.max_players,
            "sessions": {pid: s.to_dict() for pid, s in self.sessions.items()},
            "chat": [m.to_dict() for m in self.chat],
            "shared_state": dict(self.shared_state),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MultiplayerRoom:
        state = data.get("state", "lobby")
        if not isinstance(state, RoomState):
            state = RoomState(state)
        sessions = {pid: PlayerSession.from_dict(s) for pid, s in data.get("sessions", {}).items()}
        chat = [ChatMessage.from_dict(m) for m in data.get("chat", [])]
        room = MultiplayerRoom(
            room_id=data["room_id"],
            name=data.get("name", ""),
            state=state,
            host_id=data.get("host_id"),
            max_players=data.get("max_players", 4),
            sessions=sessions,
            chat=chat,
            shared_state=dict(data.get("shared_state", {})),
            created_at=data.get("created_at", ""),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            metadata=dict(data.get("metadata", {})),
        )
        return room


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class MultiplayerManager:
    """
    Creates and tracks multiplayer rooms and player sessions.

    Also exposes party bridging so remote players can form parties that
    mirror the local PartyManager state.
    """

    def __init__(self, party_manager: Any | None = None) -> None:
        self._rooms: dict[str, MultiplayerRoom] = {}
        self._player_to_room: dict[str, str] = {}
        self._party_manager = party_manager

    # ------------------------------------------------------------------
    # Room lifecycle
    # ------------------------------------------------------------------

    def create_room(
        self,
        host_id: str,
        room_id: str | None = None,
        name: str = "",
        max_players: int = 4,
    ) -> dict[str, Any]:
        room_id = room_id or str(uuid.uuid4())
        if room_id in self._rooms:
            return {"success": False, "reason": f"Room '{room_id}' already exists."}
        room = MultiplayerRoom(
            room_id=room_id,
            name=name or room_id,
            host_id=host_id,
            max_players=max_players,
        )
        # Auto-join host
        host = PlayerSession(
            player_id=host_id,
            room_id=room_id,
            display_name=host_id,
            role=PlayerRole.HOST,
        )
        room.sessions[host_id] = host
        self._rooms[room_id] = room
        self._player_to_room[host_id] = room_id
        return {"success": True, "room_id": room_id}

    def get_room(self, room_id: str) -> MultiplayerRoom | None:
        return self._rooms.get(room_id)

    def get_room_for_player(self, player_id: str) -> MultiplayerRoom | None:
        rid = self._player_to_room.get(player_id)
        return self._rooms.get(rid) if rid else None

    def list_rooms(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._rooms.values()]

    def list_open_rooms(self) -> list[dict[str, Any]]:
        return [
            r.to_dict()
            for r in self._rooms.values()
            if r.state == RoomState.LOBBY and not r.is_full()
        ]

    def end_room(self, room_id: str) -> dict[str, Any]:
        room = self._rooms.get(room_id)
        if room is None:
            return {"success": False, "reason": "Room not found."}
        room.state = RoomState.ENDED
        room.ended_at = datetime.now(UTC).isoformat()
        return {"success": True, "room_id": room_id}

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def join_room(self, player_id: str, room_id: str, display_name: str = "") -> dict[str, Any]:
        room = self._rooms.get(room_id)
        if room is None:
            return {"success": False, "reason": "Room not found."}
        if room.state != RoomState.LOBBY:
            return {"success": False, "reason": "Room is not accepting new players."}
        if player_id in room.sessions:
            return {"success": False, "reason": "Player already in room."}
        if room.is_full():
            return {"success": False, "reason": "Room is full."}
        existing = self._player_to_room.get(player_id)
        if existing and existing != room_id:
            self.leave_room(player_id)
        session = PlayerSession(
            player_id=player_id,
            room_id=room_id,
            display_name=display_name or player_id,
            role=PlayerRole.GUEST,
        )
        room.sessions[player_id] = session
        self._player_to_room[player_id] = room_id
        self._broadcast_system(room_id, f"{display_name or player_id} joined the room.")
        return {"success": True, "room_id": room_id, "player_id": player_id}

    def leave_room(self, player_id: str) -> dict[str, Any]:
        room = self.get_room_for_player(player_id)
        if room is None:
            return {"success": False, "reason": "Player not in any room."}
        display = room.sessions.get(player_id, PlayerSession(player_id=player_id, room_id=room.room_id)).display_name
        room.sessions.pop(player_id, None)
        self._player_to_room.pop(player_id, None)
        if room.host_id == player_id:
            remaining = list(room.sessions.keys())
            if remaining:
                new_host = remaining[0]
                room.host_id = new_host
                room.sessions[new_host].role = PlayerRole.HOST
                self._broadcast_system(room.room_id, f"{display} left. Host transferred to {new_host}.")
            else:
                room.host_id = None
                self._broadcast_system(room.room_id, f"{display} left. Room is empty.")
        else:
            self._broadcast_system(room.room_id, f"{display} left.")
        return {"success": True}

    def set_ready(self, player_id: str, is_ready: bool) -> dict[str, Any]:
        room = self.get_room_for_player(player_id)
        if room is None:
            return {"success": False, "reason": "Player not in any room."}
        session = room.sessions.get(player_id)
        if session is None:
            return {"success": False, "reason": "Session not found."}
        session.is_ready = is_ready
        return {"success": True, "player_id": player_id, "is_ready": is_ready}

    def set_role(self, player_id: str, role: PlayerRole) -> dict[str, Any]:
        room = self.get_room_for_player(player_id)
        if room is None:
            return {"success": False, "reason": "Player not in any room."}
        session = room.sessions.get(player_id)
        if session is None:
            return {"success": False, "reason": "Session not found."}
        if role == PlayerRole.HOST and room.host_id:
            room.sessions[room.host_id].role = PlayerRole.GUEST
        session.role = role
        if role == PlayerRole.HOST:
            room.host_id = player_id
        return {"success": True, "player_id": player_id, "role": role.value}

    def update_ping(self, player_id: str, ping_ms: float) -> dict[str, Any]:
        room = self.get_room_for_player(player_id)
        if room is None:
            return {"success": False}
        session = room.sessions.get(player_id)
        if session is None:
            return {"success": False}
        session.ping_ms = ping_ms
        session.last_seen = datetime.now(UTC).isoformat()
        return {"success": True}

    # ------------------------------------------------------------------
    # Game flow
    # ------------------------------------------------------------------

    def start_room(self, room_id: str) -> dict[str, Any]:
        room = self._rooms.get(room_id)
        if room is None:
            return {"success": False, "reason": "Room not found."}
        if room.state != RoomState.LOBBY:
            return {"success": False, "reason": "Room is not in lobby state."}
        if not all(s.is_ready for s in room.sessions.values()):
            return {"success": False, "reason": "Not all players are ready."}
        room.state = RoomState.PLAYING
        room.started_at = datetime.now(UTC).isoformat()
        self._broadcast_system(room_id, "Game started!")
        return {"success": True, "room_id": room_id}

    def pause_room(self, room_id: str) -> dict[str, Any]:
        room = self._rooms.get(room_id)
        if room is None:
            return {"success": False, "reason": "Room not found."}
        if room.state != RoomState.PLAYING:
            return {"success": False, "reason": "Room is not playing."}
        room.state = RoomState.PAUSED
        self._broadcast_system(room_id, "Game paused.")
        return {"success": True}

    def resume_room(self, room_id: str) -> dict[str, Any]:
        room = self._rooms.get(room_id)
        if room is None:
            return {"success": False, "reason": "Room not found."}
        if room.state != RoomState.PAUSED:
            return {"success": False, "reason": "Room is not paused."}
        room.state = RoomState.PLAYING
        self._broadcast_system(room_id, "Game resumed.")
        return {"success": True}

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def send_chat(
        self,
        player_id: str,
        text: str,
        channel: ChatChannel = ChatChannel.GLOBAL,
    ) -> dict[str, Any]:
        room = self.get_room_for_player(player_id)
        if room is None:
            return {"success": False, "reason": "Player not in any room."}
        if not text.strip():
            return {"success": False, "reason": "Empty message."}
        message = ChatMessage(
            message_id=str(uuid.uuid4()),
            room_id=room.room_id,
            player_id=player_id,
            channel=channel,
            text=text.strip(),
        )
        room.chat.append(message)
        return {"success": True, "message": message.to_dict()}

    def get_chat(self, room_id: str, limit: int = 50) -> list[dict[str, Any]]:
        room = self._rooms.get(room_id)
        if room is None:
            return []
        return [m.to_dict() for m in room.chat[-limit:]]

    # ------------------------------------------------------------------
    # State broadcasting
    # ------------------------------------------------------------------

    def update_shared_state(self, player_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        room = self.get_room_for_player(player_id)
        if room is None:
            return {"success": False, "reason": "Player not in any room."}
        room.shared_state.update(patch)
        return {"success": True, "shared_state": dict(room.shared_state)}

    def get_shared_state(self, room_id: str) -> dict[str, Any]:
        room = self._rooms.get(room_id)
        if room is None:
            return {}
        return dict(room.shared_state)

    # ------------------------------------------------------------------
    # Party bridging
    # ------------------------------------------------------------------

    def sync_party_to_room(self, room_id: str, party_id: str) -> dict[str, Any]:
        """
        Reflect a PartyManager party into the room shared_state so all
        clients see the same party composition.
        """
        if self._party_manager is None:
            return {"success": False, "reason": "No PartyManager configured."}
        party = self._party_manager.get_party(party_id)
        if party is None:
            return {"success": False, "reason": "Party not found."}
        room = self._rooms.get(room_id)
        if room is None:
            return {"success": False, "reason": "Room not found."}
        summary = self._party_manager.get_party_summary(party_id)
        room.shared_state["party"] = summary
        return {"success": True, "party": summary}

    # ------------------------------------------------------------------
    # Summary / serialization
    # ------------------------------------------------------------------

    def get_room_summary(self, room_id: str) -> dict[str, Any]:
        room = self._rooms.get(room_id)
        if room is None:
            return {"success": False, "reason": "Room not found."}
        player_count = len(room.sessions)
        ready_count = sum(1 for s in room.sessions.values() if s.is_ready)
        return {
            "room_id": room.room_id,
            "name": room.name,
            "state": room.state.value,
            "host_id": room.host_id,
            "max_players": room.max_players,
            "player_count": player_count,
            "ready_count": ready_count,
            "players": [
                {
                    "player_id": pid,
                    "display_name": s.display_name,
                    "role": s.role.value,
                    "is_ready": s.is_ready,
                    "ping_ms": s.ping_ms,
                    "character_id": s.character_id,
                }
                for pid, s in room.sessions.items()
            ],
            "chat_count": len(room.chat),
            "shared_state_keys": list(room.shared_state.keys()),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "rooms": {rid: r.to_dict() for rid, r in self._rooms.items()},
            "player_to_room": dict(self._player_to_room),
        }

    @staticmethod
    def from_dict(data: dict[str, Any], party_manager: Any | None = None) -> MultiplayerManager:
        mgr = MultiplayerManager(party_manager=party_manager)
        for rid, rdata in data.get("rooms", {}).items():
            mgr._rooms[rid] = MultiplayerRoom.from_dict(rdata)
        for pid, rid in data.get("player_to_room", {}).items():
            if rid in mgr._rooms:
                mgr._player_to_room[pid] = rid
        return mgr

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _broadcast_system(self, room_id: str, text: str) -> None:
        room = self._rooms.get(room_id)
        if room is None:
            return
        message = ChatMessage(
            message_id=str(uuid.uuid4()),
            room_id=room_id,
            player_id=None,
            channel=ChatChannel.SYSTEM,
            text=text,
        )
        room.chat.append(message)
