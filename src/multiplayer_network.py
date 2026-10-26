"""
RPG-13-20: Multiplayer Networking

WebSocket-based multiplayer server and client that bridge the existing
in-memory MultiplayerManager to real networked sessions.

Protocol (JSON):
  Client -> Server:
    {"type": "command", "request_id": "...", "action": "...", "payload": {...}}
  Server -> Client:
    {"type": "result", "request_id": "...", "success": bool, "data": {...}}
    {"type": "event", "event": "...", "payload": {...}}
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection
from websockets.asyncio.server import ServerConnection

from multiplayer import (
    ChatChannel,
    MultiplayerManager,
    PlayerRole,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Protocol helpers
# ---------------------------------------------------------------------------

class NetworkMessage:
    """Wire message wrapper."""

    def __init__(
        self,
        msg_type: str,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        self.type = msg_type
        self.payload = payload or {}
        self.request_id = request_id or str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "request_id": self.request_id,
            "payload": self.payload,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @staticmethod
    def from_dict(data: dict[str, Any]) -> NetworkMessage:
        return NetworkMessage(
            msg_type=data.get("type", ""),
            payload=data.get("payload", {}),
            request_id=data.get("request_id"),
        )

    @staticmethod
    def from_json(text: str) -> NetworkMessage:
        return NetworkMessage.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class MultiplayerServer:
    """
    Async WebSocket server that exposes multiplayer room operations.

    Usage:
        mgr = MultiplayerManager()
        server = MultiplayerServer(mgr, host="0.0.0.0", port=8765)
        await server.start()
    """

    def __init__(
        self,
        manager: MultiplayerManager,
        host: str = "0.0.0.0",
        port: int = 8765,
        auth_token: str | None = None,
    ) -> None:
        self.manager = manager
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self._sessions: dict[str, ServerConnection] = {}
        self._player_ws: dict[str, str] = {}       # player_id -> ws_id
        self._ws_players: dict[str, str] = {}      # ws_id -> player_id
        self._stop_event: asyncio.Event | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._stop_event = asyncio.Event()
        async with websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=20,
        ):
            logger.info("Multiplayer server listening on ws://%s:%d", self.host, self.port)
            await self._stop_event.wait()

    async def stop(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        for ws in list(self._sessions.values()):
            try:
                await ws.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Connection handler
    # ------------------------------------------------------------------

    async def _handle_connection(self, websocket: ServerConnection) -> None:
        ws_id = str(uuid.uuid4())
        self._sessions[ws_id] = websocket
        player_id: str | None = None
        try:
            async for raw in websocket:
                try:
                    msg = NetworkMessage.from_dict(json.loads(raw))
                except (json.JSONDecodeError, KeyError):
                    await self._send(websocket, NetworkMessage("error", {"reason": "Invalid message format."}))
                    continue

                response = await self._dispatch(msg, ws_id)
                if msg.type == "command":
                    await self._send(websocket, NetworkMessage("result", response, msg.request_id))
        except websockets.ConnectionClosed:
            pass
        finally:
            if player_id:
                self._player_ws.pop(player_id, None)
                self._ws_players.pop(ws_id, None)
                self._unregister_player(player_id)
            self._sessions.pop(ws_id, None)

    async def _send(self, websocket: ServerConnection, msg: NetworkMessage) -> None:
        try:
            await websocket.send(msg.to_json())
        except Exception:
            pass

    async def _broadcast_to_room(self, room_id: str, event: str, payload: dict[str, Any]) -> None:
        room = self.manager.get_room(room_id)
        if not room:
            return
        for pid in room.sessions:
            ws_id = self._player_ws.get(pid)
            if ws_id and ws_id in self._sessions:
                await self._send(self._sessions[ws_id], NetworkMessage("event", {"event": event, **payload}))

    def _unregister_player(self, player_id: str) -> None:
        self.manager.leave_room(player_id)

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, msg: NetworkMessage, ws_id: str) -> dict[str, Any]:
        action = msg.payload.get("action")
        if action == "hello":
            player_id = self._handle_hello(msg.payload)
            self._player_ws[player_id] = ws_id
            self._ws_players[ws_id] = player_id
            return {"player_id": player_id}
        if action == "create_room":
            return await self._handle_create_room(msg.payload, ws_id)
        if action == "join_room":
            return await self._handle_join_room(msg.payload, ws_id)
        if action == "leave_room":
            return self.manager.leave_room(msg.payload.get("player_id", ""))
        if action == "set_ready":
            return self.manager.set_ready(msg.payload.get("player_id", ""), msg.payload.get("is_ready", False))
        if action == "start_room":
            return self.manager.start_room(msg.payload.get("room_id", ""))
        if action == "pause_room":
            return self.manager.pause_room(msg.payload.get("room_id", ""))
        if action == "resume_room":
            return self.manager.resume_room(msg.payload.get("room_id", ""))
        if action == "end_room":
            return self.manager.end_room(msg.payload.get("room_id", ""))
        if action == "send_chat":
            return self.manager.send_chat(
                msg.payload.get("player_id", ""),
                msg.payload.get("text", ""),
                ChatChannel(msg.payload.get("channel", "global")),
            )
        if action == "get_chat":
            return {"messages": self.manager.get_chat(msg.payload.get("room_id", ""), msg.payload.get("limit", 50))}
        if action == "update_shared_state":
            return self.manager.update_shared_state(msg.payload.get("player_id", ""), msg.payload.get("patch", {}))
        if action == "get_shared_state":
            return self.manager.get_shared_state(msg.payload.get("room_id", ""))
        if action == "get_room_summary":
            return self.manager.get_room_summary(msg.payload.get("room_id", ""))
        if action == "list_open_rooms":
            return {"rooms": self.manager.list_open_rooms()}
        if action == "update_ping":
            return self.manager.update_ping(msg.payload.get("player_id", ""), msg.payload.get("ping_ms", 0.0))
        if action == "set_role":
            return self.manager.set_role(msg.payload.get("player_id", ""), PlayerRole(msg.payload.get("role", "guest")))
        return {"success": False, "reason": f"Unknown action '{action}'."}

    def _handle_hello(self, payload: dict[str, Any]) -> str:
        player_id = payload.get("player_id") or str(uuid.uuid4())
        return player_id

    async def _handle_create_room(self, payload: dict[str, Any], ws_id: str) -> dict[str, Any]:
        host_id = payload.get("host_id") or self._ws_players.get(ws_id) or str(uuid.uuid4())
        result = self.manager.create_room(
            host_id=host_id,
            room_id=payload.get("room_id"),
            name=payload.get("name", ""),
            max_players=payload.get("max_players", 4),
        )
        if result.get("success"):
            self._player_ws[host_id] = ws_id
            self._ws_players[ws_id] = host_id
        return result

    async def _handle_join_room(self, payload: dict[str, Any], ws_id: str) -> dict[str, Any]:
        player_id = payload.get("player_id") or self._ws_players.get(ws_id) or str(uuid.uuid4())
        result = self.manager.join_room(
            player_id=player_id,
            room_id=payload.get("room_id", ""),
            display_name=payload.get("display_name", ""),
        )
        if result.get("success"):
            self._player_ws[player_id] = ws_id
            self._ws_players[ws_id] = player_id
            room = self.manager.get_room(payload.get("room_id", ""))
            if room:
                asyncio.create_task(
                    self._broadcast_to_room(room.room_id, "player_joined", {
                        "player_id": player_id,
                        "display_name": payload.get("display_name", player_id),
                    })
                )
        return result


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class MultiplayerClient:
    """
    Async WebSocket client for the multiplayer server.

    Usage:
        client = MultiplayerClient("ws://localhost:8765")
        await client.connect()
        await client.send_command("create_room", {"name": "My Room"})
    """

    def __init__(self, server_url: str, player_id: str | None = None) -> None:
        self.server_url = server_url
        self.player_id = player_id or str(uuid.uuid4())
        self._ws: ClientConnection | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._listeners: dict[str, list[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]]] = {}
        self._connected = False

    async def connect(self, timeout: float = 10.0) -> bool:
        try:
            self._ws = await websockets.connect(self.server_url, ping_interval=20)
            self._connected = True
            asyncio.get_event_loop().create_task(self._receive_loop())
            # Register identity
            await self.send_command("hello", {"player_id": self.player_id})
            return True
        except Exception as exc:
            logger.error("Connection failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass

    @property
    def connected(self) -> bool:
        return self._connected and self._ws is not None

    async def send_command(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._ws:
            return {"success": False, "reason": "Not connected."}
        request_id = str(uuid.uuid4())
        msg = NetworkMessage("command", {"action": action, **payload}, request_id)
        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future
        try:
            await self._ws.send(msg.to_json())
            return await asyncio.wait_for(future, timeout=15.0)
        except TimeoutError:
            return {"success": False, "reason": "Command timed out."}
        finally:
            self._pending.pop(request_id, None)

    def on_event(self, event_name: str, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        self._listeners.setdefault(event_name, []).append(callback)

    async def _receive_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                msg_type = data.get("type")
                if msg_type == "result":
                    req_id = data.get("request_id")
                    if req_id and req_id in self._pending:
                        self._pending[req_id].set_result(data.get("payload", {}))
                elif msg_type == "event":
                    payload = data.get("payload", {})
                    event = payload.pop("event", None)
                    if event:
                        for cb in self._listeners.get(event, []):
                            try:
                                await cb(payload)
                            except Exception as exc:
                                logger.error("Event listener error: %s", exc)
                elif msg_type == "error":
                    req_id = data.get("request_id")
                    if req_id and req_id in self._pending:
                        self._pending[req_id].set_result(data.get("payload", {"success": False}))
        except websockets.ConnectionClosed:
            pass
        finally:
            self._connected = False
            for future in self._pending.values():
                if not future.done():
                    future.cancel()
            self._pending.clear()
