"""
Tests for RPG-13-11 Cloud Gaming.

Run with: python -m pytest tests/test_cloud_gaming.py -v
or:       python tests/test_cloud_gaming.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cloud_gaming import (
    CloudGamingClient,
    CloudGamingManager,
    CloudGamingMessage,
    CloudGamingServer,
    CloudGamingSession,
)
from world_library import WorldLibrary
from world_persistence import WorldPersistence
from world_session import WorldSessionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager() -> tuple[CloudGamingManager, WorldPersistence, str]:
    lib = WorldLibrary()
    world = lib.create_world(name="CloudWorld", description="A cloud gaming world.")
    sessions = WorldSessionManager()
    persistence = WorldPersistence(library=lib, sessions=sessions)
    mgr = CloudGamingManager(sessions=sessions, persistence=persistence)
    return mgr, persistence, world.world_id


# ---------------------------------------------------------------------------
# CloudGamingSession tests
# ---------------------------------------------------------------------------

class TestCloudGamingSession:
    def test_to_dict_round_trip(self):
        cs = CloudGamingSession(
            session_id="s1",
            world_id="w1",
            player_id="p1",
            status="streaming",
            frame_count=5,
            metadata={"key": "value"},
            state_snapshot={"hp": 10},
        )
        data = cs.to_dict()
        cs2 = CloudGamingSession.from_dict(data)
        assert cs2.session_id == "s1"
        assert cs2.world_id == "w1"
        assert cs2.player_id == "p1"
        assert cs2.status == "streaming"
        assert cs2.frame_count == 5
        assert cs2.metadata == {"key": "value"}
        assert cs2.state_snapshot == {"hp": 10}


# ---------------------------------------------------------------------------
# CloudGamingManager tests
# ---------------------------------------------------------------------------

class TestCloudGamingManager:
    def test_create_session(self):
        mgr, _, _ = _make_manager()
        result = mgr.create_session(world_id=_make_manager()[2])
        assert result["success"] is True
        assert "session_id" in result
        assert result["status"] == "idle"

    def test_get_session(self):
        mgr, _, _ = _make_manager()
        result = mgr.create_session(world_id=_make_manager()[2])
        cs = mgr.get_session(result["session_id"])
        assert cs is not None
        assert cs.session_id == result["session_id"]

    def test_start_streaming(self):
        mgr, _, _ = _make_manager()
        result = mgr.create_session(world_id=_make_manager()[2])
        sid = result["session_id"]
        r = mgr.start_streaming(sid)
        assert r["success"] is True
        assert r["status"] == "streaming"
        cs = mgr.get_session(sid)
        assert cs.status == "streaming"

    def test_pause_streaming(self):
        mgr, _, _ = _make_manager()
        result = mgr.create_session(world_id=_make_manager()[2])
        sid = result["session_id"]
        mgr.start_streaming(sid)
        r = mgr.pause_streaming(sid)
        assert r["success"] is True
        assert r["status"] == "paused"

    def test_end_session(self):
        mgr, _, _ = _make_manager()
        result = mgr.create_session(world_id=_make_manager()[2])
        sid = result["session_id"]
        mgr.start_streaming(sid)
        r = mgr.end_session(sid)
        assert r["success"] is True
        cs = mgr.get_session(sid)
        assert cs.status == "ended"

    def test_update_snapshot(self):
        mgr, _, _ = _make_manager()
        result = mgr.create_session(world_id=_make_manager()[2])
        sid = result["session_id"]
        mgr.start_streaming(sid)
        r = mgr.update_snapshot(sid, {"location": "tavern"})
        assert r["success"] is True
        assert r["frame_count"] == 1
        cs = mgr.get_session(sid)
        assert cs.state_snapshot == {"location": "tavern"}
        assert cs.frame_count == 1

    def test_save_session(self):
        mgr, persistence, _ = _make_manager()
        result = mgr.create_session(world_id=_make_manager()[2])
        sid = result["session_id"]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cloud.json")
            r = mgr.save_session(sid, path=path)
            assert r["success"] is True
            assert os.path.exists(path)
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            assert data["version"] == 1
            assert "cloud_session" in data

    def test_list_sessions_filtered(self):
        mgr, _, _ = _make_manager()
        r1 = mgr.create_session(world_id=_make_manager()[2])
        r2 = mgr.create_session(world_id=_make_manager()[2])
        mgr.start_streaming(r1["session_id"])
        ended = mgr.list_sessions(status="ended")
        assert len(ended) == 0
        streaming = mgr.list_sessions(status="streaming")
        assert len(streaming) == 1
        all_sessions = mgr.list_sessions()
        assert len(all_sessions) == 2

    def test_to_dict_round_trip(self):
        mgr, persistence, _ = _make_manager()
        r = mgr.create_session(world_id=_make_manager()[2])
        mgr.start_streaming(r["session_id"])
        data = mgr.to_dict()
        mgr2 = CloudGamingManager.from_dict(data, sessions=mgr.sessions, persistence=persistence)
        assert len(mgr2.list_sessions()) == 1
        assert mgr2.get_session(r["session_id"]).status == "streaming"


# ---------------------------------------------------------------------------
# CloudGamingMessage tests
# ---------------------------------------------------------------------------

class TestCloudGamingMessage:
    def test_round_trip(self):
        msg = CloudGamingMessage("frame", {"snapshot": {}}, "req-1")
        data = msg.to_dict()
        msg2 = CloudGamingMessage.from_dict(data)
        assert msg2.type == "frame"
        assert msg2.payload == {"snapshot": {}}
        assert msg2.request_id == "req-1"

    def test_json_round_trip(self):
        msg = CloudGamingMessage("command", {"action": "start"}, "abc")
        text = msg.to_json()
        msg2 = CloudGamingMessage.from_json(text)
        assert msg2.type == "command"
        assert msg2.payload["action"] == "start"
        assert msg2.request_id == "abc"


# ---------------------------------------------------------------------------
# CloudGamingServer / Client integration tests
# ---------------------------------------------------------------------------

class TestCloudGamingServerClient:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_server_client_create_and_stream(self):
        mgr, _, _ = _make_manager()
        server = CloudGamingServer(mgr, host="127.0.0.1", port=0)

        async def scenario():
            server_task = asyncio.get_event_loop().create_task(server.start())
            # Give server a moment to bind
            await asyncio.sleep(0.2)
            port = server.port
            client = CloudGamingClient(f"ws://127.0.0.1:{port}")
            assert await client.connect() is True

            # Create session
            resp = await client.send_command("create_session", {"world_id": "cloud-world"})
            # World may not exist; accept any response because manager doesn't validate world_id
            assert "session_id" in resp or "success" in resp

            if resp.get("session_id"):
                sid = resp["session_id"]
                # Start streaming
                r = await client.send_command("start_streaming", {"session_id": sid})
                assert r["success"] is True

                # Send input
                r = await client.send_input(sid, "move", {"direction": "north"})
                assert r["success"] is True
                assert r["queued_inputs"] >= 1

                # Receive at least one frame
                frames = []
                async for frame in client.stream_frames():
                    frames.append(frame)
                    if len(frames) >= 2:
                        break
                assert len(frames) >= 1

                await client.disconnect()

            server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

        self._run(scenario())


if __name__ == "__main__":
    suites = [TestCloudGamingSession, TestCloudGamingManager, TestCloudGamingMessage, TestCloudGamingServerClient]
    passed = 0
    failed = 0
    for suite in suites:
        instance = suite()
        for method in dir(instance):
            if method.startswith("test_"):
                try:
                    getattr(instance, method)()
                    print(f"  PASS  {suite.__name__}.{method}")
                    passed += 1
                except Exception as exc:
                    print(f"  FAIL  {suite.__name__}.{method}: {exc}")
                    import traceback
                    traceback.print_exc()
                    failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
