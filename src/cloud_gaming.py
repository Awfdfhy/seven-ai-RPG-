"""
RPG-13-11: Cloud Gaming

Provides cloud gaming support: a remote server hosts the authoritative game
session and streams state updates to thin clients over WebSocket. Clients
send input commands; the server processes ticks, updates world state, and
broadcasts deltas or full snapshots.

Designed to integrate with WorldSessionManager, WorldPersistence, and the
existing multiplayer networking layer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection
from websockets.asyncio.server import ServerConnection

from world_persistence import WorldPersistence
from world_session import WorldSessionManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CloudGamingSession:
    """
    One hosted cloud gaming instance bound to a world session.

    Attributes:
        session_id   : unique cloud session identifier
        world_id     : the world being played
        player_id    : the connected player (if any)
        status       : idle | streaming | paused | ended
        started_at   : ISO timestamp of when streaming began
        frame_count  : number of state snapshots sent
        last_frame   : ISO timestamp of last snapshot
        metadata     : arbitrary session metadata
        state_snapshot: latest full game state dict
    """

    session_id: str
    world_id: str
    player_id: str | None = None
    status: str = "idle"
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    frame_count: int = 0
    last_frame: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    state_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "world_id": self.world_id,
            "player_id": self.player_id,
            "status": self.status,
            "started_at": self.started_at,
            "frame_count": self.frame_count,
            "last_frame": self.last_frame,
            "metadata": dict(self.metadata),
            "state_snapshot": dict(self.state_snapshot),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CloudGamingSession:
        return CloudGamingSession(
            session_id=data["session_id"],
            world_id=data["world_id"],
            player_id=data.get("player_id"),
            status=data.get("status", "idle"),
            started_at=data.get("started_at", ""),
            frame_count=data.get("frame_count", 0),
            last_frame=data.get("last_frame"),
            metadata=dict(data.get("metadata", {})),
            state_snapshot=dict(data.get("state_snapshot", {})),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class CloudGamingManager:
    """
    Creates and tracks cloud gaming sessions.

    Sessions are backed by WorldSessionManager and can optionally persist
    their state via WorldPersistence.
    """

    def __init__(
        self,
        sessions: WorldSessionManager | None = None,
        persistence: WorldPersistence | None = None,
    ) -> None:
        self.sessions = sessions or WorldSessionManager()
        self.persistence = persistence
        self._cloud_sessions: dict[str, CloudGamingSession] = {}

    def create_session(
        self,
        world_id: str,
        player_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Start a new cloud gaming session bound to a world.

        Returns a session dict.
        """
        # Ensure there is an active world session
        world_session = self.sessions.create_session(
            world_id=world_id,
            metadata={"cloud_gaming": True, **(metadata or {})},
        )
        cloud_id = str(uuid.uuid4())
        cloud_session = CloudGamingSession(
            session_id=cloud_id,
            world_id=world_id,
            player_id=player_id,
            metadata={"world_session_id": world_session.session_id},
        )
        self._cloud_sessions[cloud_id] = cloud_session
        logger.info("Created cloud gaming session %s for world %s", cloud_id, world_id)
        return {"success": True, **cloud_session.to_dict()}

    def get_session(self, cloud_session_id: str) -> CloudGamingSession | None:
        return self._cloud_sessions.get(cloud_session_id)

    def list_sessions(self, status: str | None = None) -> list[dict[str, Any]]:
        result = []
        for cs in self._cloud_sessions.values():
            if status is None or cs.status == status:
                result.append(cs.to_dict())
        return result

    def start_streaming(self, cloud_session_id: str) -> dict[str, Any]:
        cs = self._cloud_sessions.get(cloud_session_id)
        if cs is None:
            return {"success": False, "reason": "Cloud session not found."}
        if cs.status in ("streaming", "paused"):
            return {"success": False, "reason": f"Session already {cs.status}."}
        cs.status = "streaming"
        cs.started_at = datetime.now(UTC).isoformat()
        return {"success": True, "session_id": cloud_session_id, "status": cs.status}

    def pause_streaming(self, cloud_session_id: str) -> dict[str, Any]:
        cs = self._cloud_sessions.get(cloud_session_id)
        if cs is None:
            return {"success": False, "reason": "Cloud session not found."}
        if cs.status != "streaming":
            return {"success": False, "reason": "Session is not streaming."}
        cs.status = "paused"
        return {"success": True, "session_id": cloud_session_id, "status": cs.status}

    def end_session(self, cloud_session_id: str) -> dict[str, Any]:
        cs = self._cloud_sessions.get(cloud_session_id)
        if cs is None:
            return {"success": False, "reason": "Cloud session not found."}
        cs.status = "ended"
        # End the underlying world session too
        wsid = cs.metadata.get("world_session_id")
        if wsid:
            self.sessions.end_session(wsid)
        return {"success": True, "session_id": cloud_session_id}

    def update_snapshot(
        self, cloud_session_id: str, snapshot: dict[str, Any]
    ) -> dict[str, Any]:
        cs = self._cloud_sessions.get(cloud_session_id)
        if cs is None:
            return {"success": False, "reason": "Cloud session not found."}
        cs.state_snapshot = dict(snapshot)
        cs.frame_count += 1
        cs.last_frame = datetime.now(UTC).isoformat()
        return {"success": True, "frame_count": cs.frame_count}

    def save_session(self, cloud_session_id: str, path: str | None = None) -> dict[str, Any]:
        if self.persistence is None:
            return {"success": False, "reason": "No persistence configured."}
        cs = self._cloud_sessions.get(cloud_session_id)
        if cs is None:
            return {"success": False, "reason": "Cloud session not found."}
        target = path or f"cloud_gaming_{cloud_session_id}.json"
        payload = {
            "version": 1,
            "cloud_session": cs.to_dict(),
            "worlds": self.persistence.library.export_state(),
            "sessions": [
                s.to_dict()
                for s in self.persistence.sessions._sessions.values()
            ],
        }
        import os
        os.makedirs(os.path.dirname(target) if os.path.dirname(target) else ".", exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return {"success": True, "path": target}

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessions": {sid: cs.to_dict() for sid, cs in self._cloud_sessions.items()}
        }

    @staticmethod
    def from_dict(
        data: dict[str, Any],
        sessions: WorldSessionManager | None = None,
        persistence: WorldPersistence | None = None,
    ) -> CloudGamingManager:
        mgr = CloudGamingManager(sessions=sessions, persistence=persistence)
        for sid, sdata in data.get("sessions", {}).items():
            mgr._cloud_sessions[sid] = CloudGamingSession.from_dict(sdata)
        return mgr


# ---------------------------------------------------------------------------
# Network protocol helpers
# ---------------------------------------------------------------------------

class CloudGamingMessage:
    """Wire message wrapper for cloud gaming."""

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
    def from_dict(data: dict[str, Any]) -> CloudGamingMessage:
        return CloudGamingMessage(
            msg_type=data.get("type", ""),
            payload=data.get("payload", {}),
            request_id=data.get("request_id"),
        )

    @staticmethod
    def from_json(text: str) -> CloudGamingMessage:
        return CloudGamingMessage.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class CloudGamingServer:
    """
    Async WebSocket server that hosts cloud gaming sessions.

    Usage:
        mgr = CloudGamingManager()
        server = CloudGamingServer(mgr, host="0.0.0.0", port=8766)
        await server.start()
    """

    def __init__(
        self,
        manager: CloudGamingManager,
        host: str = "0.0.0.0",
        port: int = 8766,
        frame_rate: float = 30.0,
    ) -> None:
        self.manager = manager
        self.host = host
        self.port = port
        self.frame_rate = frame_rate
        self._sessions: dict[str, ServerConnection] = {}
        self._cloud_to_ws: dict[str, str] = {}
        self._ws_to_cloud: dict[str, str] = {}
        self._stop_event: asyncio.Event | None = None
        self._tick_task: asyncio.Task | None = None

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
        ) as server:
            # Capture the actual bound port if port was 0 (auto-assign)
            if self.port == 0 and server.sockets:
                sock = next(iter(server.sockets))
                self.port = sock.getsockname()[1]
            logger.info(
                "Cloud gaming server listening on ws://%s:%d", self.host, self.port
            )
            self._tick_task = asyncio.get_event_loop().create_task(self._tick_loop())
            await self._stop_event.wait()

    async def stop(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
        for ws in list(self._sessions.values()):
            try:
                await ws.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Tick loop: broadcast state at frame_rate
    # ------------------------------------------------------------------

    async def _tick_loop(self) -> None:
        interval = 1.0 / self.frame_rate if self.frame_rate > 0 else 0.0
        while not self._stop_event or not self._stop_event.is_set():
            if interval > 0:
                await asyncio.sleep(interval)
            for cloud_id, cs in self.manager._cloud_sessions.items():
                if cs.status != "streaming":
                    continue
                ws_id = self._cloud_to_ws.get(cloud_id)
                if not ws_id:
                    continue
                ws = self._sessions.get(ws_id)
                if not ws:
                    continue
                msg = CloudGamingMessage(
                    "frame",
                    {
                        "session_id": cloud_id,
                        "snapshot": cs.state_snapshot,
                        "frame": cs.frame_count,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
                try:
                    await ws.send(msg.to_json())
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Connection handler
    # ------------------------------------------------------------------

    async def _handle_connection(self, websocket: ServerConnection) -> None:
        ws_id = str(uuid.uuid4())
        self._sessions[ws_id] = websocket
        cloud_id: str | None = None
        try:
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await self._send(websocket, CloudGamingMessage("error", {"reason": "Invalid JSON."}))
                    continue

                msg = CloudGamingMessage.from_dict(data)
                response = await self._dispatch(msg, ws_id)

                if msg.type == "command":
                    await self._send(websocket, CloudGamingMessage("result", response, msg.request_id))
        except websockets.ConnectionClosed:
            pass
        finally:
            if cloud_id:
                self._cloud_to_ws.pop(cloud_id, None)
                self._ws_to_cloud.pop(ws_id, None)
                cs = self.manager.get_session(cloud_id)
                if cs and cs.status == "streaming":
                    self.manager.pause_streaming(cloud_id)
            self._sessions.pop(ws_id, None)

    async def _send(self, websocket: ServerConnection, msg: CloudGamingMessage) -> None:
        try:
            await websocket.send(msg.to_json())
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, msg: CloudGamingMessage, ws_id: str) -> dict[str, Any]:
        action = msg.payload.get("action")
        if action == "hello":
            return await self._handle_hello(msg.payload, ws_id)
        if action == "create_session":
            return self._handle_create_session(msg.payload, ws_id)
        if action == "start_streaming":
            return self.manager.start_streaming(msg.payload.get("session_id", ""))
        if action == "pause_streaming":
            return self.manager.pause_streaming(msg.payload.get("session_id", ""))
        if action == "end_session":
            return self.manager.end_session(msg.payload.get("session_id", ""))
        if action == "input":
            return self._handle_input(msg.payload, ws_id)
        if action == "update_snapshot":
            return self.manager.update_snapshot(
                msg.payload.get("session_id", ""), msg.payload.get("snapshot", {})
            )
        if action == "list_sessions":
            return {"sessions": self.manager.list_sessions()}
        if action == "get_session":
            cs = self.manager.get_session(msg.payload.get("session_id", ""))
            return cs.to_dict() if cs else {"success": False, "reason": "Not found."}
        return {"success": False, "reason": f"Unknown action '{action}'."}

    async def _handle_hello(self, payload: dict[str, Any], ws_id: str) -> dict[str, Any]:
        player_id = payload.get("player_id") or str(uuid.uuid4())
        return {"player_id": player_id}

    def _handle_create_session(self, payload: dict[str, Any], ws_id: str) -> dict[str, Any]:
        world_id = payload.get("world_id", "")
        player_id = payload.get("player_id") or str(uuid.uuid4())
        result = self.manager.create_session(
            world_id=world_id,
            player_id=player_id,
            metadata=payload.get("metadata"),
        )
        if result.get("session_id"):
            cloud_id = result["session_id"]
            self._cloud_to_ws[cloud_id] = ws_id
            self._ws_to_cloud[ws_id] = cloud_id
        return result

    def _handle_input(self, payload: dict[str, Any], ws_id: str) -> dict[str, Any]:
        cloud_id = payload.get("session_id")
        if not cloud_id:
            return {"success": False, "reason": "Missing session_id."}
        cs = self.manager.get_session(cloud_id)
        if cs is None:
            return {"success": False, "reason": "Session not found."}
        # Record the input in the cloud session metadata for the host engine
        # to consume. The actual game logic execution is intentionally left
        # to the integrator; this layer only transports input.
        inputs = cs.metadata.setdefault("inputs", [])
        inputs.append({
            "type": payload.get("input_type", "generic"),
            "data": payload.get("data", {}),
            "timestamp": datetime.now(UTC).isoformat(),
        })
        # Keep input buffer bounded
        if len(inputs) > 200:
            cs.metadata["inputs"] = inputs[-200:]
        return {"success": True, "queued_inputs": len(inputs)}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class CloudGamingClient:
    """
    Async WebSocket client for a cloud gaming server.

    Usage:
        client = CloudGamingClient("ws://localhost:8766")
        await client.connect()
        await client.create_session(world_id="...")
        await client.start_streaming(session_id="...")
        async for frame in client.stream_frames():
            render(frame)
    """

    def __init__(self, server_url: str, player_id: str | None = None) -> None:
        self.server_url = server_url
        self.player_id = player_id or str(uuid.uuid4())
        self._ws: ClientConnection | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._frame_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._connected = False

    async def connect(self, timeout: float = 10.0) -> bool:
        try:
            self._ws = await websockets.connect(self.server_url, ping_interval=20)
            self._connected = True
            asyncio.get_event_loop().create_task(self._receive_loop())
            await self.send_command("hello", {"player_id": self.player_id})
            return True
        except Exception as exc:
            logger.error("Cloud gaming connection failed: %s", exc)
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
        msg = CloudGamingMessage("command", {"action": action, **payload}, request_id)
        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future
        try:
            await self._ws.send(msg.to_json())
            return await asyncio.wait_for(future, timeout=15.0)
        except TimeoutError:
            return {"success": False, "reason": "Command timed out."}
        finally:
            self._pending.pop(request_id, None)

    async def send_input(
        self, session_id: str, input_type: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self.send_command(
            "input",
            {
                "session_id": session_id,
                "input_type": input_type,
                "data": data,
            },
        )

    async def stream_frames(self):
        """
        Async generator that yields frame snapshots as they arrive.

        Usage:
            async for frame in client.stream_frames():
                render(frame)
        """
        while self.connected:
            try:
                frame = await asyncio.wait_for(self._frame_queue.get(), timeout=1.0)
                yield frame
            except TimeoutError:
                continue

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
                elif msg_type == "frame":
                    payload = data.get("payload", {})
                    await self._frame_queue.put(payload)
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
