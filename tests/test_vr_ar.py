"""
RPG-13-08: VR/AR Support tests.
Run with: python -m pytest tests/ -v
or:       python tests/test_vr_ar.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vr_ar import (
    ARMode,
    ComfortLevel,
    ComfortSettings,
    MovementType,
    VRARManager,
    VRDeviceProfile,
    VRMode,
    VRSessionState,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager() -> VRARManager:
    return VRARManager()


def _make_device(device_id: str = "test_device") -> VRDeviceProfile:
    return VRDeviceProfile(
        device_id=device_id,
        display_name="Test Device",
        platform="test",
        supports_vr=True,
        supports_ar=True,
        supports_hand_tracking=True,
        supports_eye_tracking=False,
        recommended_comfort=ComfortLevel.MEDIUM,
        fov_degrees=100,
    )


# ---------------------------------------------------------------------------
# VRMode / ARMode / MovementType / ComfortLevel enum checks
# ---------------------------------------------------------------------------

class TestEnums:
    def test_vr_mode_values(self):
        assert VRMode.OFF == "off"
        assert VRMode.FULL_VR == "full_vr"
        assert VRMode.PASSTHROUGH == "passthrough"
        assert VRMode.SPATIAL_UI == "spatial_ui"

    def test_ar_mode_values(self):
        assert ARMode.OFF == "off"
        assert ARMode.OVERLAY == "overlay"
        assert ARMode.PASSTHROUGH == "passthrough"
        assert ARMode.SPATIAL_ANCHOR == "spatial_anchor"

    def test_movement_type_values(self):
        assert MovementType.TELEPORT == "teleport"
        assert MovementType.SMOOTH == "smooth"
        assert MovementType.SNAP_TURN == "snap_turn"
        assert MovementType.CONTINUOUS_TURN == "continuous_turn"

    def test_comfort_level_values(self):
        assert ComfortLevel.HIGH == "high"
        assert ComfortLevel.MEDIUM == "medium"
        assert ComfortLevel.LOW == "low"


# ---------------------------------------------------------------------------
# VRDeviceProfile tests
# ---------------------------------------------------------------------------

class TestVRDeviceProfile:
    def test_defaults(self):
        d = _make_device()
        assert d.display_name == "Test Device"
        assert d.supports_vr is True
        assert d.supports_ar is True
        assert d.supports_hand_tracking is True
        assert d.supports_eye_tracking is False
        assert d.recommended_comfort == ComfortLevel.MEDIUM
        assert d.fov_degrees == 100

    def test_roundtrip(self):
        d = _make_device("quest_3")
        restored = VRDeviceProfile.from_dict(d.to_dict())
        assert restored.device_id == "quest_3"
        assert restored.supports_hand_tracking is True
        assert restored.fov_degrees == 100


# ---------------------------------------------------------------------------
# ComfortSettings tests
# ---------------------------------------------------------------------------

class TestComfortSettings:
    def test_defaults(self):
        c = ComfortSettings()
        assert c.movement_type == MovementType.TELEPORT
        assert c.snap_turn_angle == 30
        assert c.vignette_enabled is True
        assert c.vignette_intensity == 0.5
        assert c.show_static_world is True
        assert c.reduce_flicker is True

    def test_roundtrip(self):
        c = ComfortSettings(
            movement_type=MovementType.SMOOTH,
            snap_turn_angle=45,
            vignette_enabled=False,
            vignette_intensity=0.8,
            show_static_world=False,
            reduce_flicker=False,
        )
        restored = ComfortSettings.from_dict(c.to_dict())
        assert restored.movement_type == MovementType.SMOOTH
        assert restored.snap_turn_angle == 45
        assert restored.vignette_intensity == 0.8


# ---------------------------------------------------------------------------
# VRSessionState tests
# ---------------------------------------------------------------------------

class TestVRSessionState:
    def test_defaults(self):
        s = VRSessionState(world_id="w1", device_id="d1")
        assert s.world_id == "w1"
        assert s.device_id == "d1"
        assert s.vr_mode == VRMode.OFF
        assert s.ar_mode == ARMode.OFF
        assert s.is_running is True
        assert s.session_end is None

    def test_roundtrip(self):
        s = VRSessionState(
            world_id="w1",
            device_id="d1",
            session_id="s1",
            vr_mode=VRMode.FULL_VR,
            ar_mode=ARMode.OVERLAY,
            comfort=ComfortSettings(movement_type=MovementType.SMOOTH),
            is_running=True,
            start_position={"x": 1.0, "y": 2.0, "z": 3.0},
        )
        restored = VRSessionState.from_dict(s.to_dict())
        assert restored.world_id == "w1"
        assert restored.device_id == "d1"
        assert restored.vr_mode == VRMode.FULL_VR
        assert restored.ar_mode == ARMode.OVERLAY
        assert restored.comfort.movement_type == MovementType.SMOOTH
        assert restored.start_position == {"x": 1.0, "y": 2.0, "z": 3.0}


# ---------------------------------------------------------------------------
# VRARManager tests
# ---------------------------------------------------------------------------

class TestVRARManager:
    def test_default_devices_loaded(self):
        mgr = _make_manager()
        assert "quest_3" in mgr.list_devices()
        assert "vision_pro" in mgr.list_devices()
        assert "index" in mgr.list_devices()
        assert "hololens" in mgr.list_devices()

    def test_register_and_query_device(self):
        mgr = _make_manager()
        dev = _make_device("custom")
        mgr.register_device(dev)
        assert mgr.get_device("custom") is not None
        assert mgr.get_device("unknown") is None

    def test_start_session(self):
        mgr = _make_manager()
        state = mgr.start_session(world_id="w1", device_id="quest_3", vr_mode=VRMode.FULL_VR)
        assert state.world_id == "w1"
        assert state.vr_mode == VRMode.FULL_VR
        assert state.is_running is True
        assert mgr.get_session("w1") is state
        assert mgr.get_active_session() is state

    def test_end_session(self):
        mgr = _make_manager()
        mgr.start_session(world_id="w1", device_id="quest_3")
        ended = mgr.end_session("w1")
        assert ended is not None
        assert ended.is_running is False
        assert ended.session_end is not None
        assert mgr.get_active_session() is None

    def test_set_vr_mode(self):
        mgr = _make_manager()
        mgr.start_session(world_id="w1", device_id="quest_3")
        state = mgr.set_vr_mode("w1", VRMode.SPATIAL_UI)
        assert state.vr_mode == VRMode.SPATIAL_UI

    def test_set_vr_mode_unsupported(self):
        mgr = _make_manager()
        mgr.start_session(world_id="w1", device_id="hololens")
        try:
            mgr.set_vr_mode("w1", VRMode.FULL_VR)
            raise AssertionError("Expected ValueError")
        except ValueError:
            pass

    def test_set_ar_mode(self):
        mgr = _make_manager()
        mgr.start_session(world_id="w1", device_id="vision_pro")
        state = mgr.set_ar_mode("w1", ARMode.SPATIAL_ANCHOR)
        assert state.ar_mode == ARMode.SPATIAL_ANCHOR

    def test_set_ar_mode_unsupported(self):
        mgr = _make_manager()
        mgr.start_session(world_id="w1", device_id="index")
        try:
            mgr.set_ar_mode("w1", ARMode.PASSTHROUGH)
            raise AssertionError("Expected ValueError")
        except ValueError:
            pass

    def test_update_comfort(self):
        mgr = _make_manager()
        mgr.start_session(world_id="w1", device_id="quest_3")
        new_comfort = ComfortSettings(
            movement_type=MovementType.SMOOTH,
            snap_turn_angle=45,
            vignette_enabled=False,
            vignette_intensity=0.7,
        )
        state = mgr.update_comfort("w1", new_comfort)
        assert state.comfort.movement_type == MovementType.SMOOTH
        assert state.comfort.snap_turn_angle == 45

    def test_comfort_auto_adjusted_for_low(self):
        mgr = _make_manager()
        mgr.start_session(world_id="w1", device_id="index")
        state = mgr.get_session("w1")
        assert state.comfort.movement_type == MovementType.SNAP_TURN
        assert state.comfort.vignette_intensity == 0.7

    def test_comfort_auto_adjusted_for_high(self):
        mgr = _make_manager()
        mgr.start_session(world_id="w1", device_id="vision_pro")
        state = mgr.get_session("w1")
        assert state.comfort.movement_type == MovementType.TELEPORT
        assert state.comfort.vignette_intensity == 0.3

    def test_persistence_roundtrip(self):
        mgr = _make_manager()
        mgr.start_session(world_id="w1", device_id="quest_3", vr_mode=VRMode.FULL_VR)
        restored = VRARManager.from_dict(mgr.to_dict())
        assert restored.get_session("w1").vr_mode == VRMode.FULL_VR
        assert "quest_3" in restored.list_devices()
