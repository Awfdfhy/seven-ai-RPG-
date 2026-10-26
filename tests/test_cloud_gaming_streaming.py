"""
Tests for RPG-12-12 Cloud Gaming and Streaming Support.

Run with: python -m pytest tests/test_cloud_gaming_streaming.py -v
or:       python tests/test_cloud_gaming_streaming.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from typing import Any

from cloud_gaming_streaming import (
    CloudStreamingError,
    CloudStreamingManager,
    CloudStreamingTransport,
    InputEvent,
    StreamingSession,
    StreamMetrics,
    StreamQuality,
    StreamState,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager() -> CloudStreamingManager:
    return CloudStreamingManager()


def _make_session(manager: CloudStreamingManager) -> StreamingSession:
    return manager.create_session(client_id="client-1", quality=StreamQuality.BALANCED.value)


# ---------------------------------------------------------------------------
# CloudStreamingManager tests
# ---------------------------------------------------------------------------

class TestCloudStreamingManager:
    def test_create_session_returns_session(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        assert session.session_id
        assert session.client_id == "c1"
        assert session.state == StreamState.CONNECTING.value

    def test_create_session_default_quality(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        assert session.quality == StreamQuality.BALANCED.value

    def test_create_session_custom_quality(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1", quality=StreamQuality.ULTRA.value)
        assert session.quality == StreamQuality.ULTRA.value

    def test_create_session_with_metadata(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1", metadata={"game": "test"})
        assert session.metadata == {"game": "test"}

    def test_start_session_transitions_to_streaming(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        result = mgr.start_session(session.session_id)
        assert result["success"] is True
        assert session.state == StreamState.STREAMING.value
        assert session.started_at

    def test_start_session_twice_fails(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        result = mgr.start_session(session.session_id)
        assert result["success"] is False
        assert "already" in result["reason"].lower()

    def test_pause_and_resume(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        mgr.pause_session(session.session_id)
        assert session.state == StreamState.PAUSED.value
        mgr.resume_session(session.session_id)
        assert session.state == StreamState.STREAMING.value

    def test_resume_without_pause_fails(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        result = mgr.resume_session(session.session_id)
        assert result["success"] is False

    def test_stop_session(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        result = mgr.stop_session(session.session_id)
        assert result["success"] is True
        assert session.state == StreamState.STOPPED.value
        assert session.ended_at

    def test_end_session_removes_state(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        mgr.end_session(session.session_id)
        assert session.session_id not in mgr._sessions
        assert session.session_id not in mgr._metrics

    def test_list_sessions_returns_all(self):
        mgr = _make_manager()
        s1 = mgr.create_session(client_id="c1")
        s2 = mgr.create_session(client_id="c2")
        listing = mgr.list_sessions()
        assert len(listing) == 2
        ids = {s["session_id"] for s in listing}
        assert s1.session_id in ids
        assert s2.session_id in ids

    def test_get_session_not_found_raises(self):
        mgr = _make_manager()
        try:
            mgr.get_session("missing")
        except CloudStreamingError:
            pass
        else:
            raise AssertionError("Expected CloudStreamingError")

    # Input relay

    def test_enqueue_input_queues_event(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        evt = InputEvent(event_type="key_down", data={"key": "W"})
        result = mgr.enqueue_input(session.session_id, evt)
        assert result["success"] is True
        assert result["queued"]["data"] == {"key": "W"}

    def test_enqueue_input_when_not_streaming_raises(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        evt = InputEvent(event_type="key_down")
        try:
            mgr.enqueue_input(session.session_id, evt)
        except CloudStreamingError:
            pass
        else:
            raise AssertionError("Expected CloudStreamingError")

    def test_drain_input_returns_and_clears_queue(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        mgr.enqueue_input(session.session_id, InputEvent(event_type="key_down"))
        mgr.enqueue_input(session.session_id, InputEvent(event_type="mouse_move"))
        batch = mgr.drain_input(session.session_id)
        assert len(batch) == 2
        assert batch[0]["event_type"] == "key_down"
        assert mgr.drain_input(session.session_id) == []

    def test_drain_input_respects_limit(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        for _ in range(5):
            mgr.enqueue_input(session.session_id, InputEvent(event_type="key_down"))
        batch = mgr.drain_input(session.session_id, limit=2)
        assert len(batch) == 2
        assert len(mgr.drain_input(session.session_id)) == 3

    # Metrics

    def test_record_frame_increments_counters(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        mgr.record_frame(session.session_id)
        m = mgr.get_metrics(session.session_id)
        assert m.frames_encoded == 1

    def test_record_frame_tracks_dropped(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        mgr.record_frame(session.session_id, dropped=True)
        m = mgr.get_metrics(session.session_id)
        assert m.frames_dropped == 1

    def test_update_network_metrics_degrades_when_rtt_high(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        mgr.update_network_metrics(session.session_id, rtt_ms=300, packets_lost=5, bitrate_kbps=400)
        assert session.state == StreamState.DEGRADED.value
        m = mgr.get_metrics(session.session_id)
        assert m.rtt_ms == 300
        assert m.packets_lost == 5

    def test_set_quality_updates_session_and_metrics(self):
        mgr = _make_manager()
        session = mgr.create_session(client_id="c1")
        mgr.start_session(session.session_id)
        result = mgr.set_quality(session.session_id, StreamQuality.HIGH.value)
        assert result["success"] is True
        assert session.quality == StreamQuality.HIGH.value
        assert mgr.get_metrics(session.session_id).current_quality == StreamQuality.HIGH.value

    # Observability

    def test_on_event_receives_events(self):
        mgr = _make_manager()
        received: list[dict[str, Any]] = []

        def _cb(payload: dict[str, Any]) -> None:
            received.append(payload)

        session = mgr.create_session(client_id="c1")
        mgr.on_event(session.session_id, _cb)
        mgr.start_session(session.session_id)
        assert len(received) == 1
        assert received[0]["event"] == "session_started"


# ---------------------------------------------------------------------------
# Data model serialization tests
# ---------------------------------------------------------------------------

class TestDataModels:
    def test_input_event_roundtrip(self):
        evt = InputEvent(
            event_type="mouse_down",
            data={"button": 0, "x": 10, "y": 20},
            session_id="s1",
            client_id="c1",
            sequence=3,
        )
        data = evt.to_dict()
        assert data["sequence"] == 3
        restored = InputEvent.from_dict(data)
        assert restored.event_type == "mouse_down"
        assert restored.sequence == 3
        assert restored.data == {"button": 0, "x": 10, "y": 20}

    def test_stream_metrics_roundtrip(self):
        m = StreamMetrics(session_id="s1", rtt_ms=12.5, frames_encoded=10)
        data = m.to_dict()
        restored = StreamMetrics.from_dict(data)
        assert restored.session_id == "s1"
        assert restored.rtt_ms == 12.5
        assert restored.frames_encoded == 10

    def test_streaming_session_roundtrip(self):
        s = StreamingSession(
            session_id="s1",
            client_id="c1",
            quality=StreamQuality.ULTRA.value,
            state=StreamState.STREAMING.value,
            metadata={"game": "rpg"},
        )
        data = s.to_dict()
        restored = StreamingSession.from_dict(data)
        assert restored.session_id == "s1"
        assert restored.quality == StreamQuality.ULTRA.value
        assert restored.metadata == {"game": "rpg"}


# ---------------------------------------------------------------------------
# CloudStreamingTransport tests
# ---------------------------------------------------------------------------

class TestCloudStreamingTransport:
    def test_transport_instantiation(self):
        mgr = _make_manager()
        transport = CloudStreamingTransport(mgr)
        assert transport.manager is mgr

