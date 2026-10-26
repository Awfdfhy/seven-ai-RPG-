"""
RPG-10-09: Soundtrack System tests.
Run with: python -m pytest tests/ -v
or:       python tests/test_soundtrack.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from soundtrack import (
    SoundtrackCategory,
    SoundtrackLayer,
    SoundtrackManager,
    SoundtrackState,
    SoundtrackTrack,
    TrackIntensity,
)

# ---------------------------------------------------------------------------
# SoundtrackTrack tests
# ---------------------------------------------------------------------------

class TestSoundtrackTrack:
    def test_default_values(self):
        track = SoundtrackTrack(
            track_id="t1",
            name="Test Track",
            category=SoundtrackCategory.AMBIENT,
        )
        assert track.track_id == "t1"
        assert track.name == "Test Track"
        assert track.category == SoundtrackCategory.AMBIENT
        assert track.file_path == ""
        assert track.default_volume == 0.7
        assert track.loop is True
        assert track.tags == []

    def test_to_dict_roundtrip(self):
        track = SoundtrackTrack(
            track_id="t1",
            name="Test Track",
            category=SoundtrackCategory.BATTLE,
            file_path="audio/battle/test.ogg",
            default_volume=0.9,
            loop=False,
            tags=["boss", "high"],
        )
        restored = SoundtrackTrack.from_dict(track.to_dict())
        assert restored.track_id == "t1"
        assert restored.name == "Test Track"
        assert restored.category == SoundtrackCategory.BATTLE
        assert restored.file_path == "audio/battle/test.ogg"
        assert restored.default_volume == 0.9
        assert restored.loop is False
        assert restored.tags == ["boss", "high"]


# ---------------------------------------------------------------------------
# SoundtrackLayer tests
# ---------------------------------------------------------------------------

class TestSoundtrackLayer:
    def test_default_values(self):
        layer = SoundtrackLayer(
            layer_id="l1",
            category=SoundtrackCategory.BATTLE,
            track_id="t1",
        )
        assert layer.layer_id == "l1"
        assert layer.category == SoundtrackCategory.BATTLE
        assert layer.track_id == "t1"
        assert layer.intensity == TrackIntensity.LOW
        assert layer.volume == 0.7
        assert layer.fade_ms == 2000

    def test_to_dict_roundtrip(self):
        layer = SoundtrackLayer(
            layer_id="l1",
            category=SoundtrackCategory.DUNGEON,
            track_id="t2",
            intensity=TrackIntensity.HIGH,
            volume=0.8,
            fade_ms=500,
        )
        restored = SoundtrackLayer.from_dict(layer.to_dict())
        assert restored.layer_id == "l1"
        assert restored.category == SoundtrackCategory.DUNGEON
        assert restored.track_id == "t2"
        assert restored.intensity == TrackIntensity.HIGH
        assert restored.volume == 0.8
        assert restored.fade_ms == 500


# ---------------------------------------------------------------------------
# SoundtrackState tests
# ---------------------------------------------------------------------------

class TestSoundtrackState:
    def test_default_values(self):
        state = SoundtrackState(
            world_id="w1",
            category=SoundtrackCategory.TOWN,
            track_id="t1",
        )
        assert state.world_id == "w1"
        assert state.category == SoundtrackCategory.TOWN
        assert state.track_id == "t1"
        assert state.session_id is None
        assert state.intensity == TrackIntensity.LOW
        assert state.volume == 0.7
        assert state.is_playing is True
        assert state.layers == []
        assert state.ended_at is None
        assert state.state_id is not None

    def test_to_dict_roundtrip(self):
        state = SoundtrackState(
            world_id="w1",
            category=SoundtrackCategory.BATTLE,
            track_id="t1",
            session_id="s1",
            intensity=TrackIntensity.HIGH,
            volume=0.9,
            is_playing=True,
            layers=["l1", "l2"],
            state_id="sid-1",
            started_at="2024-01-01T00:00:00+00:00",
        )
        restored = SoundtrackState.from_dict(state.to_dict())
        assert restored.world_id == "w1"
        assert restored.category == SoundtrackCategory.BATTLE
        assert restored.track_id == "t1"
        assert restored.session_id == "s1"
        assert restored.intensity == TrackIntensity.HIGH
        assert restored.volume == 0.9
        assert restored.is_playing is True
        assert restored.layers == ["l1", "l2"]
        assert restored.state_id == "sid-1"


# ---------------------------------------------------------------------------
# SoundtrackManager tests
# ---------------------------------------------------------------------------

class TestSoundtrackManager:
    def test_register_defaults_creates_tracks(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        assert any(t.category == SoundtrackCategory.BATTLE for t in mgr._tracks.values())
        assert any(t.category == SoundtrackCategory.TOWN for t in mgr._tracks.values())

    def test_register_track_and_get_track(self):
        mgr = SoundtrackManager()
        track = SoundtrackTrack(
            track_id="custom.ambient.forest",
            name="Forest",
            category=SoundtrackCategory.AMBIENT,
        )
        mgr.register_track(track)
        assert mgr.get_track("custom.ambient.forest") is track
        assert mgr.get_track("missing") is None

    def test_register_layer_and_get_layers(self):
        mgr = SoundtrackManager()
        layer = SoundtrackLayer(
            layer_id="battle.layer.high",
            category=SoundtrackCategory.BATTLE,
            track_id="t1",
            intensity=TrackIntensity.HIGH,
        )
        mgr.register_layer(layer)
        layers = mgr.get_layers(SoundtrackCategory.BATTLE)
        assert len(layers) == 1
        assert layers[0].intensity == TrackIntensity.HIGH

    def test_play_creates_state(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        state = mgr.play("w1", SoundtrackCategory.TOWN)
        assert state is not None
        assert state.world_id == "w1"
        assert state.category == SoundtrackCategory.TOWN
        assert state.is_playing is True

    def test_play_without_track_id_picks_default(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        state = mgr.play("w1", SoundtrackCategory.EXPLORATION)
        assert state.track_id != ""

    def test_play_with_explicit_track_id(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        state = mgr.play("w1", SoundtrackCategory.AMBIENT, track_id="ambient.default.Forest_day")
        assert state.track_id == "ambient.default.Forest_day"

    def test_play_ends_previous(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        mgr.play("w1", SoundtrackCategory.TOWN)
        mgr.play("w1", SoundtrackCategory.TOWN)
        current = mgr.get_current("w1", SoundtrackCategory.TOWN)
        assert current is not None
        assert current.is_playing is True
        history = mgr.get_history("w1")
        assert len(history) == 1
        assert history[0]["ended_at"] is not None

    def test_stop_marks_inactive(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        mgr.play("w1", SoundtrackCategory.TOWN)
        ok = mgr.stop("w1", SoundtrackCategory.TOWN)
        assert ok is True
        assert mgr.get_current("w1", SoundtrackCategory.TOWN) is None
        history = mgr.get_history("w1")
        assert len(history) == 1
        assert history[0]["is_playing"] is False

    def test_stop_returns_false_when_no_playing(self):
        mgr = SoundtrackManager()
        assert mgr.stop("w1", SoundtrackCategory.TOWN) is False

    def test_set_intensity_changes_state(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        mgr.play("w1", SoundtrackCategory.BATTLE, intensity=TrackIntensity.LOW)
        mgr.set_intensity("w1", SoundtrackCategory.BATTLE, TrackIntensity.HIGH)
        state = mgr.get_current("w1", SoundtrackCategory.BATTLE)
        assert state is not None
        assert state.intensity == TrackIntensity.HIGH

    def test_set_intensity_switches_track_when_layer_exists(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        mgr.play("w1", SoundtrackCategory.BATTLE, intensity=TrackIntensity.LOW)
        state = mgr.set_intensity("w1", SoundtrackCategory.BATTLE, TrackIntensity.HIGH)
        assert state is not None
        assert state.intensity == TrackIntensity.HIGH

    def test_get_current_returns_none_for_unknown(self):
        mgr = SoundtrackManager()
        assert mgr.get_current("missing", SoundtrackCategory.TOWN) is None

    def test_get_all_current(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        mgr.play("w1", SoundtrackCategory.TOWN)
        mgr.play("w1", SoundtrackCategory.EXPLORATION)
        all_current = mgr.get_all_current("w1")
        assert len(all_current) == 2
        assert SoundtrackCategory.TOWN in all_current
        assert SoundtrackCategory.EXPLORATION in all_current

    def test_adapt_to_context_in_combat(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        changes = mgr.adapt_to_context("w1", in_combat=True, danger_level=4)
        assert SoundtrackCategory.BATTLE in changes
        assert changes[SoundtrackCategory.BATTLE].intensity == TrackIntensity.MEDIUM

    def test_adapt_to_context_town(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        changes = mgr.adapt_to_context("w1", location_type="town")
        assert SoundtrackCategory.TOWN in changes
        assert changes[SoundtrackCategory.TOWN].is_playing is True

    def test_adapt_to_context_dungeon(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        changes = mgr.adapt_to_context("w1", location_type="dungeon")
        assert SoundtrackCategory.DUNGEON in changes

    def test_adapt_to_context_wilderness(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        changes = mgr.adapt_to_context("w1", location_type="wilderness")
        assert SoundtrackCategory.EXPLORATION in changes

    def test_adapt_to_context_rain_adds_ambient(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        changes = mgr.adapt_to_context("w1", location_type="town", weather="rain")
        assert SoundtrackCategory.AMBIENT in changes
        assert "rain" in changes[SoundtrackCategory.AMBIENT].track_id

    def test_adapt_to_context_snow_adds_ambient(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        changes = mgr.adapt_to_context("w1", location_type="wilderness", weather="snow")
        assert SoundtrackCategory.AMBIENT in changes
        assert "wind" in changes[SoundtrackCategory.AMBIENT].track_id

    def test_export_import_roundtrip(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        mgr.play("w1", SoundtrackCategory.TOWN)
        mgr.play("w2", SoundtrackCategory.BATTLE, intensity=TrackIntensity.HIGH)
        mgr.stop("w2", SoundtrackCategory.BATTLE)

        state = mgr.export_state()
        mgr2 = SoundtrackManager()
        mgr2.import_state(state)

        assert mgr2.get_current("w1", SoundtrackCategory.TOWN) is not None
        assert mgr2.get_current("w2", SoundtrackCategory.BATTLE) is None
        hist = mgr2.get_history("w2")
        assert len(hist) == 1
        assert hist[0]["is_playing"] is False

    def test_resolve_layers(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        # After register_defaults, battle should have low/medium/high layers
        layers = mgr._resolve_layers(SoundtrackCategory.BATTLE, TrackIntensity.MEDIUM)
        assert len(layers) >= 1

    def test_history_scoped_by_world(self):
        mgr = SoundtrackManager()
        mgr.register_defaults()
        mgr.play("w1", SoundtrackCategory.TOWN)
        mgr.stop("w1", SoundtrackCategory.TOWN)
        mgr.play("w2", SoundtrackCategory.TOWN)
        h1 = mgr.get_history("w1")
        h2 = mgr.get_history("w2")
        assert len(h1) == 1
        assert len(h2) == 0  # w2 still active
