"""
Tests for RPG-13-10 Multiplayer system.
Run with: python -m pytest tests/test_multiplayer.py -v
or:       python tests/test_multiplayer.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multiplayer import (
    ChatChannel,
    ChatMessage,
    MultiplayerManager,
    MultiplayerRoom,
    PlayerRole,
    PlayerSession,
    RoomState,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_player(player_id="player1", display_name="Player One") -> PlayerSession:
    return PlayerSession(
        player_id=player_id,
        room_id="room1",
        display_name=display_name,
        role=PlayerRole.GUEST,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestChatMessage(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        msg = ChatMessage(
            message_id="m1",
            room_id="r1",
            player_id="p1",
            channel=ChatChannel.GLOBAL,
            text="Hello!",
        )
        data = msg.to_dict()
        restored = ChatMessage.from_dict(data)
        self.assertEqual(restored.message_id, "m1")
        self.assertEqual(restored.channel, ChatChannel.GLOBAL)

    def test_from_dict_with_string_values(self):
        data = {
            "message_id": "m2",
            "room_id": "r1",
            "player_id": None,
            "channel": "system",
            "text": "Welcome!",
        }
        msg = ChatMessage.from_dict(data)
        self.assertEqual(msg.channel, ChatChannel.SYSTEM)
        self.assertIsNone(msg.player_id)


class TestPlayerSession(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        session = PlayerSession(
            player_id="p1",
            room_id="r1",
            display_name="Hero",
            role=PlayerRole.HOST,
            character_id="char1",
            is_ready=True,
            ping_ms=42.5,
            metadata={"region": "eu"},
        )
        data = session.to_dict()
        restored = PlayerSession.from_dict(data)
        self.assertEqual(restored.role, PlayerRole.HOST)
        self.assertEqual(restored.ping_ms, 42.5)
        self.assertEqual(restored.metadata["region"], "eu")

    def test_from_dict_defaults(self):
        data = {
            "player_id": "p1",
            "room_id": "r1",
        }
        session = PlayerSession.from_dict(data)
        self.assertEqual(session.role, PlayerRole.GUEST)
        self.assertFalse(session.is_ready)
        self.assertEqual(session.ping_ms, 0.0)


class TestMultiplayerRoom(unittest.TestCase):
    def test_player_ids(self):
        room = MultiplayerRoom(
            room_id="r1",
            sessions={
                "p1": _make_player("p1", "A"),
                "p2": _make_player("p2", "B"),
            },
        )
        self.assertEqual(sorted(room.player_ids()), ["p1", "p2"])

    def test_is_full(self):
        room = MultiplayerRoom(room_id="r1", max_players=2)
        self.assertFalse(room.is_full())
        room.sessions["p1"] = _make_player("p1")
        room.sessions["p2"] = _make_player("p2")
        self.assertTrue(room.is_full())

    def test_host(self):
        room = MultiplayerRoom(
            room_id="r1",
            sessions={"p1": _make_player("p1")},
        )
        self.assertIsNone(room.host())
        room.host_id = "p1"
        self.assertEqual(room.host().player_id, "p1")

    def test_serialization_roundtrip(self):
        room = MultiplayerRoom(
            room_id="r1",
            name="Test Room",
            state=RoomState.PLAYING,
            host_id="p1",
            max_players=4,
        )
        room.sessions["p1"] = PlayerSession(player_id="p1", room_id="r1", role=PlayerRole.HOST, is_ready=True)
        data = room.to_dict()
        restored = MultiplayerRoom.from_dict(data)
        self.assertEqual(restored.room_id, "r1")
        self.assertEqual(restored.state, RoomState.PLAYING)
        self.assertEqual(restored.host_id, "p1")
        self.assertEqual(list(restored.sessions.keys()), ["p1"])


class TestMultiplayerManager(unittest.TestCase):
    def setUp(self):
        self.mgr = MultiplayerManager()

    # ------------------------------------------------------------------
    # Room lifecycle
    # ------------------------------------------------------------------

    def test_create_room(self):
        result = self.mgr.create_room(host_id="host1", room_id="room1")
        self.assertTrue(result["success"])
        self.assertEqual(result["room_id"], "room1")
        room = self.mgr.get_room("room1")
        self.assertEqual(room.host_id, "host1")
        self.assertIn("host1", room.sessions)

    def test_create_room_auto_id(self):
        result = self.mgr.create_room(host_id="host1")
        self.assertTrue(result["success"])
        room_id = result["room_id"]
        self.assertIsNotNone(room_id)
        self.assertIsNotNone(self.mgr.get_room(room_id))

    def test_create_room_duplicate(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        result = self.mgr.create_room(host_id="h2", room_id="r1")
        self.assertFalse(result["success"])

    def test_list_open_rooms(self):
        self.mgr.create_room(host_id="h1", room_id="r1", max_players=2)
        self.mgr.create_room(host_id="h2", room_id="r2")
        self.mgr.get_room("r1").state = RoomState.PLAYING
        open_rooms = self.mgr.list_open_rooms()
        self.assertEqual(len(open_rooms), 1)
        self.assertEqual(open_rooms[0]["room_id"], "r2")

    def test_end_room(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        result = self.mgr.end_room("r1")
        self.assertTrue(result["success"])
        self.assertEqual(self.mgr.get_room("r1").state, RoomState.ENDED)
        result = self.mgr.end_room("missing")
        self.assertFalse(result["success"])

    # ------------------------------------------------------------------
    # Join / leave
    # ------------------------------------------------------------------

    def test_join_room(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        result = self.mgr.join_room("p1", "r1", display_name="P1")
        self.assertTrue(result["success"])
        self.assertEqual(result["player_id"], "p1")
        room = self.mgr.get_room("r1")
        self.assertEqual(len(room.sessions), 2)
        self.assertEqual(room.sessions["p1"].display_name, "P1")
        self.assertEqual(room.sessions["p1"].role, PlayerRole.GUEST)

    def test_join_full_room(self):
        self.mgr.create_room(host_id="h1", room_id="r1", max_players=1)
        result = self.mgr.join_room("p1", "r1")
        self.assertFalse(result["success"])
        self.assertIn("full", result["reason"].lower())

    def test_join_already_joined(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.join_room("p1", "r1")
        result = self.mgr.join_room("p1", "r1")
        self.assertFalse(result["success"])

    def test_join_not_lobby(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.get_room("r1").state = RoomState.PLAYING
        result = self.mgr.join_room("p1", "r1")
        self.assertFalse(result["success"])

    def test_join_moves_from_other_room(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.create_room(host_id="h2", room_id="r2")
        self.mgr.join_room("p1", "r1")
        self.mgr.join_room("p1", "r2")
        self.assertIsNone(self.mgr.get_room("r1").sessions.get("p1"))
        self.assertIn("p1", self.mgr.get_room("r2").sessions)

    def test_leave_room(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.join_room("p1", "r1")
        result = self.mgr.leave_room("p1")
        self.assertTrue(result["success"])
        self.assertIsNone(self.mgr.get_room_for_player("p1"))

    def test_leave_host_transfers(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.join_room("p1", "r1")
        result = self.mgr.leave_room("h1")
        self.assertTrue(result["success"])
        room = self.mgr.get_room("r1")
        self.assertEqual(room.host_id, "p1")
        self.assertEqual(room.sessions["p1"].role, PlayerRole.HOST)

    def test_leave_last_player(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.leave_room("h1")
        self.assertIsNone(self.mgr.get_room("r1").host_id)

    # ------------------------------------------------------------------
    # Session actions
    # ------------------------------------------------------------------

    def test_set_ready(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.join_room("p1", "r1")
        result = self.mgr.set_ready("p1", True)
        self.assertTrue(result["success"])
        self.assertTrue(self.mgr.get_room("r1").sessions["p1"].is_ready)

    def test_set_ready_not_in_room(self):
        result = self.mgr.set_ready("p1", True)
        self.assertFalse(result["success"])

    def test_set_role_guest_to_host(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        result = self.mgr.set_role("h1", PlayerRole.HOST)
        self.assertTrue(result["success"])
        self.assertEqual(result["role"], PlayerRole.HOST.value)
        self.assertEqual(self.mgr.get_room("r1").host_id, "h1")

    def test_set_role_host_transfer(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.join_room("p1", "r1")
        # Host transfers host role to p1 by calling set_role on h1's behalf for p1.
        # Our API lets the current host set_role for any player, or we can relax
        # the restriction and allow any player to claim host (common in lobbies).
        result = self.mgr.set_role("p1", PlayerRole.HOST)
        self.assertTrue(result["success"])
        room = self.mgr.get_room("r1")
        self.assertEqual(room.host_id, "p1")
        self.assertEqual(room.sessions["h1"].role, PlayerRole.GUEST)

    def test_update_ping(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        result = self.mgr.update_ping("h1", 33.7)
        self.assertTrue(result["success"])
        self.assertEqual(self.mgr.get_room("r1").sessions["h1"].ping_ms, 33.7)

    # ------------------------------------------------------------------
    # Game flow
    # ------------------------------------------------------------------

    def test_start_room_requires_ready(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.join_room("p1", "r1")
        result = self.mgr.start_room("r1")
        self.assertFalse(result["success"])
        self.assertIn("ready", result["reason"].lower())

    def test_start_room(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.join_room("p1", "r1")
        self.mgr.set_ready("h1", True)
        self.mgr.set_ready("p1", True)
        result = self.mgr.start_room("r1")
        self.assertTrue(result["success"])
        self.assertEqual(self.mgr.get_room("r1").state, RoomState.PLAYING)

    def test_pause_resume(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.set_ready("h1", True)
        self.mgr.start_room("r1")
        self.assertTrue(self.mgr.pause_room("r1")["success"])
        self.assertEqual(self.mgr.get_room("r1").state, RoomState.PAUSED)
        self.assertTrue(self.mgr.resume_room("r1")["success"])
        self.assertEqual(self.mgr.get_room("r1").state, RoomState.PLAYING)

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def test_send_chat(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        result = self.mgr.send_chat("h1", "Hello, world!")
        self.assertTrue(result["success"])
        self.assertEqual(result["message"]["text"], "Hello, world!")
        self.assertEqual(result["message"]["player_id"], "h1")
        self.assertEqual(result["message"]["channel"], ChatChannel.GLOBAL.value)

    def test_send_empty_chat(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        result = self.mgr.send_chat("h1", "   ")
        self.assertFalse(result["success"])

    def test_get_chat(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.send_chat("h1", "msg1")
        self.mgr.send_chat("h1", "msg2")
        chat = self.mgr.get_chat("r1")
        self.assertEqual(len(chat), 2)
        self.assertEqual(chat[1]["text"], "msg2")

    # ------------------------------------------------------------------
    # State broadcasting
    # ------------------------------------------------------------------

    def test_update_shared_state(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        result = self.mgr.update_shared_state("h1", {"turn": 1, "weather": "rain"})
        self.assertTrue(result["success"])
        self.assertEqual(result["shared_state"]["turn"], 1)
        room = self.mgr.get_room("r1")
        self.assertEqual(room.shared_state["weather"], "rain")

    def test_get_shared_state(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.update_shared_state("h1", {"level": 5})
        state = self.mgr.get_shared_state("r1")
        self.assertEqual(state["level"], 5)

    # ------------------------------------------------------------------
    # Party bridging
    # ------------------------------------------------------------------

    def test_sync_party_to_room_no_party_manager(self):
        mgr = MultiplayerManager(party_manager=None)
        mgr.create_room(host_id="h1", room_id="r1")
        result = mgr.sync_party_to_room("r1", "party1")
        self.assertFalse(result["success"])
        self.assertIn("PartyManager", result["reason"])

    def test_sync_party_to_room(self):
        from party import PartyManager

        party_mgr = PartyManager()
        party_mgr.create_party(leader_id="char1", party_id="party1")
        party_mgr.add_character("party1", "char2")
        mgr = MultiplayerManager(party_manager=party_mgr)
        mgr.create_room(host_id="h1", room_id="r1")
        result = mgr.sync_party_to_room("r1", "party1")
        self.assertTrue(result["success"])
        self.assertIn("party", mgr.get_room("r1").shared_state)
        self.assertEqual(
            mgr.get_room("r1").shared_state["party"]["member_count"], 2
        )

    # ------------------------------------------------------------------
    # Summary / serialization
    # ------------------------------------------------------------------

    def test_get_room_summary(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.join_room("p1", "r1")
        self.mgr.set_ready("h1", True)
        summary = self.mgr.get_room_summary("r1")
        self.assertEqual(summary["room_id"], "r1")
        self.assertEqual(summary["player_count"], 2)
        self.assertEqual(summary["ready_count"], 1)

    def test_serialization_roundtrip(self):
        self.mgr.create_room(host_id="h1", room_id="r1")
        self.mgr.join_room("p1", "r1", display_name="P1")
        self.mgr.send_chat("h1", "hi")
        data = self.mgr.to_dict()
        restored = MultiplayerManager.from_dict(data)
        self.assertEqual(list(restored._rooms.keys()), ["r1"])
        self.assertEqual(list(restored._rooms["r1"].sessions.keys()), ["h1", "p1"])


if __name__ == "__main__":
    unittest.main()
