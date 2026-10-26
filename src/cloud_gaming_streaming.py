"""
RPG-12-12: Cloud Gaming and Streaming Support

Provides remote game execution with video/audio streaming, input relay,
and adaptive bitrate control. Sessions integrate with CloudSyncManager
for save-state portability and MultiplayerServer for transport.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums / Constants
# ---------------------------------------------------------------------------

class StreamQuality(Enum):
    """Target streaming quality presets."""
    DRAFT = "draft"          # 480p, low bitrate, low latency
    BALANCED = "balanced"    # 720p, medium bitrate
    HIGH = "high"            # 1080p, high bitrate
    ULTRA = "ultra"          # 1440p, very high bitrate


class StreamCodec(Enum):
    """Supported video/audio codecs."""
    H264 = "h264"
    H265 = "h265"
    VP9 = "vp9"
    AV1 = "av1"
    OPUS = "opus"


class StreamState(Enum):
    """Lifecycle state of a streaming session."""
    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    PAUSED = "paused"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    ERROR = "error"


class InputEventType(Enum):
    """Client input event categories."""
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    MOUSE_MOVE = "mouse_move"
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    GAMEPAD = "gamepad"
    TOUCH = "touch"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class InputEvent:
    """A client-side input captured for relay to the remote session."""
    event_type: str
    timestamp: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    client_id: str = ""
    sequence: int = 0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": dict(self.data),
            "session_id": self.session_id,
            "client_id": self.client_id,
            "sequence": self.sequence,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> InputEvent:
        return InputEvent(
            event_type=data.get("event_type", ""),
            timestamp=data.get("timestamp", ""),
            data=dict(data.get("data", {})),
            session_id=data.get("session_id", ""),
            client_id=data.get("client_id", ""),
            sequence=int(data.get("sequence", 0)),
        )


@dataclass
class StreamMetrics:
    """Runtime metrics for a streaming session."""
    session_id: str = ""
    state: str = StreamState.IDLE.value
    started_at: str = ""
    rtt_ms: float = 0.0
    packets_sent: int = 0
    packets_lost: int = 0
    frames_encoded: int = 0
    frames_dropped: int = 0
    bitrate_kbps: int = 0
    current_quality: str = StreamQuality.BALANCED.value
    input_latency_ms: float = 0.0
    video_latency_ms: float = 0.0
    audio_latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state,
            "started_at": self.started_at,
            "rtt_ms": self.rtt_ms,
            "packets_sent": self.packets_sent,
            "packets_lost": self.packets_lost,
            "frames_encoded": self.frames_encoded,
            "frames_dropped": self.frames_dropped,
            "bitrate_kbps": self.bitrate_kbps,
            "current_quality": self.current_quality,
            "input_latency_ms": self.input_latency_ms,
            "video_latency_ms": self.video_latency_ms,
            "audio_latency_ms": self.audio_latency_ms,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StreamMetrics:
        return StreamMetrics(
            session_id=data.get("session_id", ""),
            state=data.get("state", StreamState.IDLE.value),
            started_at=data.get("started_at", ""),
            rtt_ms=float(data.get("rtt_ms", 0.0)),
            packets_sent=int(data.get("packets_sent", 0)),
            packets_lost=int(data.get("packets_lost", 0)),
            frames_encoded=int(data.get("frames_encoded", 0)),
            frames_dropped=int(data.get("frames_dropped", 0)),
            bitrate_kbps=int(data.get("bitrate_kbps", 0)),
            current_quality=data.get("current_quality", StreamQuality.BALANCED.value),
            input_latency_ms=float(data.get("input_latency_ms", 0.0)),
            video_latency_ms=float(data.get("video_latency_ms", 0.0)),
            audio_latency_ms=float(data.get("audio_latency_ms", 0.0)),
        )


@dataclass
class StreamingSession:
    """State for one cloud-gaming streaming session."""
    session_id: str
    client_id: str
    quality: str = StreamQuality.BALANCED.value
    state: str = StreamState.IDLE.value
    started_at: str = ""
    ended_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "quality": self.quality,
            "state": self.state,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StreamingSession:
        return StreamingSession(
            session_id=data.get("session_id", ""),
            client_id=data.get("client_id", ""),
            quality=data.get("quality", StreamQuality.BALANCED.value),
            state=data.get("state", StreamState.IDLE.value),
            started_at=data.get("started_at", ""),
            ended_at=data.get("ended_at", ""),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CloudStreamingError(Exception):
    """Raised when a cloud streaming operation fails."""


# ---------------------------------------------------------------------------
# CloudStreamingManager
# ---------------------------------------------------------------------------

class CloudStreamingManager:
    """
    Manages cloud gaming streaming sessions.

    Sessions are transport-agnostic; the caller is responsible for wiring
    video/audio frames and input events to and from the remote client
    (e.g. via WebSocket in multiplayer_network.MultiplayerServer).
    """

    def __init__(self) -> None:
        self._sessions: dict[str, StreamingSession] = {}
        self._metrics: dict[str, StreamMetrics] = {}
        self._input_queues: dict[str, list[InputEvent]] = {}
        self._listeners: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        client_id: str,
        quality: str = StreamQuality.BALANCED.value,
        metadata: dict[str, Any] | None = None,
    ) -> StreamingSession:
        """Create a new streaming session in the CONNECTING state."""
        session_id = str(uuid.uuid4())
        session = StreamingSession(
            session_id=session_id,
            client_id=client_id,
            quality=quality,
            state=StreamState.CONNECTING.value,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        self._metrics[session_id] = StreamMetrics(session_id=session_id)
        self._input_queues[session_id] = []
        self._emit(session_id, {"event": "session_created", "session": session.to_dict()})
        return session

    def start_session(self, session_id: str) -> dict[str, Any]:
        """Start streaming for an existing session."""
        session = self._get_session(session_id)
        if session.state == StreamState.STREAMING.value:
            return {"success": False, "reason": "Session already streaming."}
        session.state = StreamState.STREAMING.value
        session.started_at = self._now_iso()
        self._metrics[session_id].state = StreamState.STREAMING.value
        self._metrics[session_id].started_at = session.started_at
        self._emit(session_id, {"event": "session_started", "session": session.to_dict()})
        return {"success": True, "session": session.to_dict()}

    def pause_session(self, session_id: str) -> dict[str, Any]:
        session = self._get_session(session_id)
        session.state = StreamState.PAUSED.value
        self._metrics[session_id].state = StreamState.PAUSED.value
        self._emit(session_id, {"event": "session_paused", "session": session.to_dict()})
        return {"success": True, "session": session.to_dict()}

    def resume_session(self, session_id: str) -> dict[str, Any]:
        session = self._get_session(session_id)
        if session.state != StreamState.PAUSED.value:
            return {"success": False, "reason": "Session is not paused."}
        session.state = StreamState.STREAMING.value
        self._metrics[session_id].state = StreamState.STREAMING.value
        self._emit(session_id, {"event": "session_resumed", "session": session.to_dict()})
        return {"success": True, "session": session.to_dict()}

    def stop_session(self, session_id: str) -> dict[str, Any]:
        session = self._get_session(session_id)
        session.state = StreamState.STOPPED.value
        session.ended_at = self._now_iso()
        self._metrics[session_id].state = StreamState.STOPPED.value
        self._emit(session_id, {"event": "session_stopped", "session": session.to_dict()})
        return {"success": True, "session": session.to_dict()}

    def end_session(self, session_id: str) -> dict[str, Any]:
        result = self.stop_session(session_id)
        self._sessions.pop(session_id, None)
        self._metrics.pop(session_id, None)
        self._input_queues.pop(session_id, None)
        self._listeners.pop(session_id, None)
        return result

    # ------------------------------------------------------------------
    # Input relay
    # ------------------------------------------------------------------

    def enqueue_input(self, session_id: str, event: InputEvent) -> dict[str, Any]:
        """Queue a client input event for delivery to the remote game."""
        session = self._get_session(session_id)
        if session.state != StreamState.STREAMING.value:
            raise CloudStreamingError(
                f"Cannot enqueue input for session {session_id} in state {session.state}."
            )
        event.session_id = session_id
        self._input_queues[session_id].append(event)
        self._metrics[session_id].packets_sent += 1
        return {"success": True, "queued": event.to_dict()}

    def drain_input(self, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Return and clear pending input events for the session."""
        queue = self._input_queues.get(session_id, [])
        batch = [e.to_dict() for e in queue[:limit]]
        self._input_queues[session_id] = queue[len(batch):]
        return batch

    # ------------------------------------------------------------------
    # Metrics / telemetry
    # ------------------------------------------------------------------

    def record_frame(self, session_id: str, dropped: bool = False) -> None:
        self._get_session(session_id)
        m = self._metrics[session_id]
        m.frames_encoded += 1
        if dropped:
            m.frames_dropped += 1

    def update_network_metrics(
        self,
        session_id: str,
        rtt_ms: float,
        packets_lost: int,
        bitrate_kbps: int,
    ) -> None:
        m = self._metrics[session_id]
        m.rtt_ms = rtt_ms
        m.packets_lost += packets_lost
        m.bitrate_kbps = bitrate_kbps
        degraded = rtt_ms > 200 or (m.packets_lost > 0 and m.bitrate_kbps < 500)
        if degraded and self._sessions[session_id].state == StreamState.STREAMING.value:
            self._sessions[session_id].state = StreamState.DEGRADED.value
            m.state = StreamState.DEGRADED.value
            self._emit(session_id, {"event": "session_degraded", "metrics": m.to_dict()})

    def set_quality(self, session_id: str, quality: str) -> dict[str, Any]:
        session = self._get_session(session_id)
        session.quality = quality
        self._metrics[session_id].current_quality = quality
        self._emit(session_id, {"event": "quality_changed", "quality": quality})
        return {"success": True, "quality": quality}

    def get_metrics(self, session_id: str) -> StreamMetrics:
        return self._metrics[session_id]

    def get_session(self, session_id: str) -> StreamingSession:
        return self._get_session(session_id)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def on_event(
        self,
        session_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        self._listeners.setdefault(session_id, []).append(callback)

    def list_sessions(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._sessions.values()]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_session(self, session_id: str) -> StreamingSession:
        if session_id not in self._sessions:
            raise CloudStreamingError(f"Session not found: {session_id}")
        return self._sessions[session_id]

    def _emit(self, session_id: str, payload: dict[str, Any]) -> None:
        for cb in self._listeners.get(session_id, []):
            try:
                cb(payload)
            except Exception as exc:
                logger.error("Stream listener error: %s", exc)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Async transport helpers
# ---------------------------------------------------------------------------

class CloudStreamingTransport:
    """
    Minimal async helper that integrates CloudStreamingManager with
    websockets-based transport (compatible with MultiplayerServer).
    """

    def __init__(self, manager: CloudStreamingManager) -> None:
        self.manager = manager

    async def handle_client(
        self,
        websocket: Any,
        session_id: str,
    ) -> None:
        """
        Pump messages between a WebSocket client and the streaming manager.

        Incoming JSON commands (client -> server):
            {"action": "input", "payload": InputEvent.to_dict()}
            {"action": "update_metrics", "payload": {...}}
            {"action": "set_quality", "payload": {"quality": "..."}}
            {"action": "drain_input", "payload": {"limit": N}}

        Outgoing JSON events (server -> client):
            {"event": "session_state", "session": ...}
            {"event": "metrics_update", "metrics": ...}
            {"event": "input_batch", "inputs": [...]}
        """
        try:
            await websocket.send(json.dumps({
                "event": "hello",
                "session_id": session_id,
            }))
            while True:
                raw = await websocket.recv()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                action = data.get("action")
                payload = data.get("payload", {})
                if action == "input":
                    evt = InputEvent.from_dict(payload)
                    self.manager.enqueue_input(session_id, evt)
                elif action == "update_metrics":
                    self.manager.update_network_metrics(
                        session_id,
                        float(payload.get("rtt_ms", 0.0)),
                        int(payload.get("packets_lost", 0)),
                        int(payload.get("bitrate_kbps", 0)),
                    )
                elif action == "set_quality":
                    res = self.manager.set_quality(session_id, payload.get("quality", "balanced"))
                    await websocket.send(json.dumps({"event": "quality_ack", **res}))
                elif action == "drain_input":
                    batch = self.manager.drain_input(session_id, int(payload.get("limit", 100)))
                    await websocket.send(json.dumps({"event": "input_batch", "inputs": batch}))
        except Exception:
            pass
