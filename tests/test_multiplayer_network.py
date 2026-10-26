"""
Tests for RPG-13-20 Multiplayer Networking.
Run with: python -m pytest tests/test_multiplayer_network.py -v
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from typing import Any

from multiplayer import MultiplayerManager
from multiplayer_network import MultiplayerClient, MultiplayerServer, NetworkMessage

HOST = "127.0.0.1"
PORT = 9876  # non-standard to avoid conflicts


class TestNetworkMessage(unittest.TestCase):
    def test_roundtrip(self):
        msg = NetworkMessage("command", {"action": "ping"}, "req-1")
        data = msg.to_dict()
        restored = NetworkMessage.from_dict(data)
        self.assertEqual(restored.type, "command")
        self.assertEqual(restored.payload["action"], "ping")
        self.assertEqual(restored.request_id, "req-1")

    def test_json_roundtrip(self):
        msg = NetworkMessage("event", {"event": "chat", "text": "hi"})
        text = msg.to_json()
        restored = NetworkMessage.from_json(text)
        self.assertEqual(restored.type, "event")
        self.assertEqual(restored.payload["event"], "chat")


class TestMultiplayerServerClientIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.manager = MultiplayerManager()
        self.server = MultiplayerServer(self.manager, host=HOST, port=PORT)
        self.server_task = asyncio.ensure_future(self.server.start())
        # Give server time to bind
        await asyncio.sleep(0.2)

    async def asyncTearDown(self):
        await self.server.stop()
        self.server_task.cancel()
        try:
            await self.server_task
        except asyncio.CancelledError:
            pass

    async def test_client_connect_and_hello(self):
        client = MultiplayerClient(f"ws://{HOST}:{PORT}")
        ok = await client.connect()
        self.assertTrue(ok)
        self.assertTrue(client.connected)
        result = await client.send_command("hello", {"player_id": "p1"})
        self.assertIn("player_id", result)
        self.assertEqual(result["player_id"], "p1")
        await client.disconnect()

    async def test_create_and_list_rooms(self):
        client = MultiplayerClient(f"ws://{HOST}:{PORT}")
        await client.connect()

        create = await client.send_command("create_room", {"room_id": "r1", "name": "Room One"})
        self.assertTrue(create.get("success"))

        rooms = await client.send_command("list_open_rooms", {})
        self.assertEqual(len(rooms["rooms"]), 1)
        self.assertEqual(rooms["rooms"][0]["room_id"], "r1")

        await client.disconnect()

    async def test_join_leave_and_chat(self):
        client1 = MultiplayerClient(f"ws://{HOST}:{PORT}", player_id="host1")
        client2 = MultiplayerClient(f"ws://{HOST}:{PORT}", player_id="guest1")
        await client1.connect()
        await client2.connect()

        await client1.send_command("create_room", {"room_id": "r1", "name": "Chat Room"})
        join_result = await client2.send_command("join_room", {"room_id": "r1", "display_name": "Guest"})
        self.assertTrue(join_result.get("success"))

        chat = await client1.send_command("send_chat", {"player_id": "host1", "text": "Hello"})
        self.assertTrue(chat.get("success"))
        self.assertEqual(chat["message"]["text"], "Hello")

        history = await client1.send_command("get_chat", {"room_id": "r1"})
        # join generates a system message + the user chat message
        self.assertEqual(len(history["messages"]), 2)

        await client2.disconnect()
        await client1.disconnect()

    async def test_start_pause_resume_end(self):
        client = MultiplayerClient(f"ws://{HOST}:{PORT}", player_id="host1")
        await client.connect()

        await client.send_command("create_room", {"room_id": "r1", "name": "Flow"})
        await client.send_command("join_room", {"room_id": "r1", "player_id": "p1", "display_name": "P1"})
        await client.send_command("set_ready", {"player_id": "host1", "is_ready": True})
        await client.send_command("set_ready", {"player_id": "p1", "is_ready": True})

        started = await client.send_command("start_room", {"room_id": "r1"})
        self.assertTrue(started.get("success"))

        paused = await client.send_command("pause_room", {"room_id": "r1"})
        self.assertTrue(paused.get("success"))

        resumed = await client.send_command("resume_room", {"room_id": "r1"})
        self.assertTrue(resumed.get("success"))

        ended = await client.send_command("end_room", {"room_id": "r1"})
        self.assertTrue(ended.get("success"))

        await client.disconnect()

    async def test_shared_state_sync(self):
        client = MultiplayerClient(f"ws://{HOST}:{PORT}", player_id="p1")
        await client.connect()

        await client.send_command("create_room", {"room_id": "r1"})
        patch = await client.send_command("update_shared_state", {
            "player_id": "p1",
            "patch": {"turn": 1, "weather": "rain"},
        })
        self.assertTrue(patch.get("success"))

        state = await client.send_command("get_shared_state", {"room_id": "r1"})
        self.assertEqual(state["turn"], 1)
        self.assertEqual(state["weather"], "rain")

        await client.disconnect()

    async def test_event_broadcast(self):
        received: dict[str, Any] = {}

        async def on_join(payload):
            received["join"] = payload

        client = MultiplayerClient(f"ws://{HOST}:{PORT}", player_id="p1")
        await client.connect()
        client.on_event("player_joined", on_join)

        await client.send_command("create_room", {"room_id": "r1"})
        await client.send_command("join_room", {"room_id": "r1", "player_id": "p2", "display_name": "P2"})
        # Give server time to broadcast
        await asyncio.sleep(1.0)

        self.assertIn("join", received)
        self.assertEqual(received["join"]["player_id"], "p2")

        await client.disconnect()

    async def test_invalid_action_returns_error(self):
        client = MultiplayerClient(f"ws://{HOST}:{PORT}")
        await client.connect()
        result = await client.send_command("unknown_action", {})
        self.assertFalse(result.get("success"))
        await client.disconnect()


if __name__ == "__main__":
    unittest.main()
