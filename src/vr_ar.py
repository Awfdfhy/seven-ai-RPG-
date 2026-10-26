"""
RPG-13-08: VR/AR Support

Provides VR and AR session management for the Seven RPG framework.

Concepts
--------
VRMode              : how the engine renders in VR headsets
ARMode              : how the engine renders in AR headsets / passthrough
MovementType        : supported locomotion schemes
ComfortLevel        : motion-sickness comfort buckets
VRDeviceProfile     : hardware capabilities for a VR/AR device
VRSessionState      : runtime record of an active VR/AR session
ComfortSettings     : user-tunable comfort options
VRARManager         : owns device profiles, session state, and mode transitions
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

__all__ = [
    "ARMode",
    "ComfortLevel",
    "ComfortSettings",
    "MovementType",
    "VRARManager",
    "VRDeviceProfile",
    "VRMode",
    "VRSessionState",
]

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VRMode(StrEnum):
    """Rendering mode for VR headsets."""
    OFF = "off"
    FULL_VR = "full_vr"
    PASSTHROUGH = "passthrough"
    SPATIAL_UI = "spatial_ui"


class ARMode(StrEnum):
    """Rendering mode for AR headsets and passthrough devices."""
    OFF = "off"
    OVERLAY = "overlay"
    PASSTHROUGH = "passthrough"
    SPATIAL_ANCHOR = "spatial_anchor"


class MovementType(StrEnum):
    """Supported locomotion / navigation schemes."""
    TELEPORT = "teleport"
    SMOOTH = "smooth"
    SNAP_TURN = "snap_turn"
    CONTINUOUS_TURN = "continuous_turn"


class ComfortLevel(StrEnum):
    """User comfort bucket for motion-sickness mitigation."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------------------------------------------------------------------------
# Default device registry
# ---------------------------------------------------------------------------

_DEFAULT_DEVICES: dict[str, dict[str, Any]] = {
    "quest_3": {
        "display_name": "Meta Quest 3",
        "platform": "android",
        "supports_vr": True,
        "supports_ar": True,
        "supports_hand_tracking": True,
        "supports_eye_tracking": False,
        "recommended_comfort": ComfortLevel.MEDIUM,
        "fov_degrees": 100,
    },
    "vision_pro": {
        "display_name": "Apple Vision Pro",
        "platform": "visionos",
        "supports_vr": True,
        "supports_ar": True,
        "supports_hand_tracking": True,
        "supports_eye_tracking": True,
        "recommended_comfort": ComfortLevel.HIGH,
        "fov_degrees": 120,
    },
    "index": {
        "display_name": "Valve Index",
        "platform": "steamvr",
        "supports_vr": True,
        "supports_ar": False,
        "supports_hand_tracking": False,
        "supports_eye_tracking": False,
        "recommended_comfort": ComfortLevel.LOW,
        "fov_degrees": 130,
    },
    "hololens": {
        "display_name": "Microsoft HoloLens 2",
        "platform": "uwp",
        "supports_vr": False,
        "supports_ar": True,
        "supports_hand_tracking": True,
        "supports_eye_tracking": True,
        "recommended_comfort": ComfortLevel.HIGH,
        "fov_degrees": 52,
    },
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class VRDeviceProfile:
    """
    Hardware capability profile for a VR/AR device.

    Attributes:
        device_id         : stable identifier (e.g. 'quest_3')
        display_name      : human-readable name
        platform          : runtime platform string
        supports_vr       : whether the device can render VR
        supports_ar       : whether the device can render AR
        supports_hand_tracking : whether hand tracking is available
        supports_eye_tracking : whether eye tracking is available
        recommended_comfort   : default comfort level for this device
        fov_degrees       : horizontal field of view
        metadata          : additional device-specific data
    """
    device_id: str
    display_name: str = ""
    platform: str = ""
    supports_vr: bool = False
    supports_ar: bool = False
    supports_hand_tracking: bool = False
    supports_eye_tracking: bool = False
    recommended_comfort: str = ComfortLevel.MEDIUM
    fov_degrees: int = 90
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "display_name": self.display_name,
            "platform": self.platform,
            "supports_vr": self.supports_vr,
            "supports_ar": self.supports_ar,
            "supports_hand_tracking": self.supports_hand_tracking,
            "supports_eye_tracking": self.supports_eye_tracking,
            "recommended_comfort": self.recommended_comfort,
            "fov_degrees": self.fov_degrees,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> VRDeviceProfile:
        return VRDeviceProfile(
            device_id=data["device_id"],
            display_name=data.get("display_name", ""),
            platform=data.get("platform", ""),
            supports_vr=bool(data.get("supports_vr", False)),
            supports_ar=bool(data.get("supports_ar", False)),
            supports_hand_tracking=bool(data.get("supports_hand_tracking", False)),
            supports_eye_tracking=bool(data.get("supports_eye_tracking", False)),
            recommended_comfort=data.get("recommended_comfort", ComfortLevel.MEDIUM),
            fov_degrees=int(data.get("fov_degrees", 90)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ComfortSettings:
    """
    User-tunable comfort options to reduce motion sickness.

    Attributes:
        movement_type     : primary locomotion scheme
        snap_turn_angle   : degrees per snap turn (15, 30, 45)
        vignette_enabled  : whether to show comfort vignette
        vignette_intensity: 0.0 to 1.0
        show_static_world : keep world static while UI is rendered
        reduce_flicker    : lower UI update rates in immersive mode
    """
    movement_type: str = MovementType.TELEPORT
    snap_turn_angle: int = 30
    vignette_enabled: bool = True
    vignette_intensity: float = 0.5
    show_static_world: bool = True
    reduce_flicker: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "movement_type": self.movement_type,
            "snap_turn_angle": self.snap_turn_angle,
            "vignette_enabled": self.vignette_enabled,
            "vignette_intensity": self.vignette_intensity,
            "show_static_world": self.show_static_world,
            "reduce_flicker": self.reduce_flicker,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ComfortSettings:
        return ComfortSettings(
            movement_type=data.get("movement_type", MovementType.TELEPORT),
            snap_turn_angle=int(data.get("snap_turn_angle", 30)),
            vignette_enabled=bool(data.get("vignette_enabled", True)),
            vignette_intensity=float(data.get("vignette_intensity", 0.5)),
            show_static_world=bool(data.get("show_static_world", True)),
            reduce_flicker=bool(data.get("reduce_flicker", True)),
        )


@dataclass
class VRSessionState:
    """
    Runtime record of an active VR/AR session.

    Attributes:
        state_id       : unique identifier
        world_id       : the world this session belongs to
        session_id     : optional active session binding
        device_id      : current device profile id
        vr_mode        : active VR rendering mode
        ar_mode        : active AR rendering mode
        comfort        : current comfort settings
        is_running     : whether the session is active
        start_position : initial headset position
        session_start  : ISO timestamp when session started
        session_end    : ISO timestamp when session ended, or None
    """
    world_id: str
    device_id: str
    session_id: str | None = None
    vr_mode: str = VRMode.OFF
    ar_mode: str = ARMode.OFF
    comfort: ComfortSettings = field(default_factory=ComfortSettings)
    is_running: bool = True
    start_position: dict[str, float] = field(default_factory=dict)
    session_start: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    session_end: str | None = None
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "world_id": self.world_id,
            "session_id": self.session_id,
            "device_id": self.device_id,
            "vr_mode": self.vr_mode,
            "ar_mode": self.ar_mode,
            "comfort": self.comfort.to_dict(),
            "is_running": self.is_running,
            "start_position": dict(self.start_position),
            "session_start": self.session_start,
            "session_end": self.session_end,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> VRSessionState:
        comfort_data = data.get("comfort", {})
        comfort = ComfortSettings.from_dict(comfort_data) if comfort_data else ComfortSettings()
        return VRSessionState(
            state_id=data.get("state_id", str(uuid.uuid4())),
            world_id=data["world_id"],
            session_id=data.get("session_id"),
            device_id=data["device_id"],
            vr_mode=data.get("vr_mode", VRMode.OFF),
            ar_mode=data.get("ar_mode", ARMode.OFF),
            comfort=comfort,
            is_running=bool(data.get("is_running", True)),
            start_position=dict(data.get("start_position", {})),
            session_start=data.get("session_start", datetime.now(UTC).isoformat()),
            session_end=data.get("session_end"),
        )


# ---------------------------------------------------------------------------
# Core Manager
# ---------------------------------------------------------------------------

class VRARManager:
    """
    Manages VR/AR device profiles, session state, and mode transitions.

    The manager:
    - maintains a registry of known device profiles
    - tracks active sessions per world
    - applies comfort defaults for each device
    - supports persistence via to_dict / from_dict
    """

    def __init__(self) -> None:
        self._devices: dict[str, VRDeviceProfile] = {}
        self._sessions: dict[str, VRSessionState] = {}
        self._active_world: str | None = None
        self._load_default_devices()

    # ------------------------------------------------------------------
    # Device registry
    # ------------------------------------------------------------------

    def _load_default_devices(self) -> None:
        for device_id, raw in _DEFAULT_DEVICES.items():
            self._devices[device_id] = VRDeviceProfile.from_dict(
                {"device_id": device_id, **raw}
            )

    def register_device(self, device: VRDeviceProfile) -> None:
        """Add or replace a device profile."""
        self._devices[device.device_id] = device

    def get_device(self, device_id: str) -> VRDeviceProfile | None:
        """Return a device profile by id, or None."""
        return self._devices.get(device_id)

    def remove_device(self, device_id: str) -> None:
        """Remove a device profile by id."""
        self._devices.pop(device_id, None)

    def list_devices(self) -> list[str]:
        """Return all registered device ids."""
        return list(self._devices.keys())

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(
        self,
        world_id: str,
        device_id: str,
        session_id: str | None = None,
        vr_mode: str = VRMode.OFF,
        ar_mode: str = ARMode.OFF,
        comfort: ComfortSettings | None = None,
    ) -> VRSessionState:
        """
        Start a new VR/AR session for a world.

        If a session for this world already exists, it is replaced.
        """
        if not world_id:
            raise ValueError("world_id must not be empty")
        if not device_id:
            raise ValueError("device_id must not be empty")
        if device_id not in self._devices:
            raise KeyError(f"Unknown device: {device_id}")

        device = self._devices[device_id]
        effective_comfort = comfort or ComfortSettings()

        # Apply device recommended comfort if session comfort is default
        if (
            effective_comfort.movement_type == MovementType.TELEPORT
            and device.recommended_comfort == ComfortLevel.LOW
        ):
            effective_comfort = ComfortSettings(
                movement_type=MovementType.SNAP_TURN,
                snap_turn_angle=45,
                vignette_enabled=True,
                vignette_intensity=0.7,
                show_static_world=True,
                reduce_flicker=True,
            )
        elif (
            effective_comfort.movement_type == MovementType.TELEPORT
            and device.recommended_comfort == ComfortLevel.HIGH
        ):
            effective_comfort = ComfortSettings(
                movement_type=MovementType.TELEPORT,
                snap_turn_angle=15,
                vignette_enabled=False,
                vignette_intensity=0.3,
                show_static_world=True,
                reduce_flicker=True,
            )

        state = VRSessionState(
            world_id=world_id,
            device_id=device_id,
            session_id=session_id,
            vr_mode=vr_mode,
            ar_mode=ar_mode,
            comfort=effective_comfort,
            is_running=True,
            start_position={},
        )
        self._sessions[world_id] = state
        self._active_world = world_id
        return state

    def end_session(self, world_id: str) -> VRSessionState | None:
        """End the active session for a world."""
        state = self._sessions.get(world_id)
        if state is None:
            return None
        state.is_running = False
        state.session_end = datetime.now(UTC).isoformat()
        if self._active_world == world_id:
            self._active_world = None
        return state

    def get_session(self, world_id: str) -> VRSessionState | None:
        """Return the session for a world, or None."""
        return self._sessions.get(world_id)

    def has_session(self, world_id: str) -> bool:
        """Return True if a session exists for the given world."""
        return world_id in self._sessions

    def list_sessions(self) -> list[str]:
        """Return all world ids with active or ended sessions."""
        return list(self._sessions.keys())

    def get_active_session(self) -> VRSessionState | None:
        """Return the session for the current active world, or None."""
        if self._active_world is None:
            return None
        return self._sessions.get(self._active_world)

    # ------------------------------------------------------------------
    # Mode transitions
    # ------------------------------------------------------------------

    def set_vr_mode(self, world_id: str, mode: str) -> VRSessionState:
        """
        Change the VR mode for a world's session.

        Raises ValueError if the device does not support VR.
        """
        state = self._sessions.get(world_id)
        if state is None:
            raise KeyError(f"No active session for world: {world_id}")
        device = self._devices.get(state.device_id)
        if device is None or not device.supports_vr:
            raise ValueError(f"Device {state.device_id} does not support VR")
        state.vr_mode = mode
        return state

    def set_ar_mode(self, world_id: str, mode: str) -> VRSessionState:
        """
        Change the AR mode for a world's session.

        Raises ValueError if the device does not support AR.
        """
        state = self._sessions.get(world_id)
        if state is None:
            raise KeyError(f"No active session for world: {world_id}")
        device = self._devices.get(state.device_id)
        if device is None or not device.supports_ar:
            raise ValueError(f"Device {state.device_id} does not support AR")
        state.ar_mode = mode
        return state

    def update_comfort(self, world_id: str, comfort: ComfortSettings) -> VRSessionState:
        """Replace comfort settings for a world's session."""
        state = self._sessions.get(world_id)
        if state is None:
            raise KeyError(f"No active session for world: {world_id}")
        state.comfort = comfort
        return state

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize manager state to a dict."""
        return {
            "devices": {did: d.to_dict() for did, d in self._devices.items()},
            "sessions": {wid: s.to_dict() for wid, s in self._sessions.items()},
            "active_world": self._active_world,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> VRARManager:
        manager = VRARManager()
        manager._devices = {}
        manager._sessions = {}
        for did, ddata in data.get("devices", {}).items():
            manager._devices[did] = VRDeviceProfile.from_dict(ddata)
        for wid, sdata in data.get("sessions", {}).items():
            manager._sessions[wid] = VRSessionState.from_dict(sdata)
        manager._active_world = data.get("active_world")
        return manager
