"""
RPG-13-07: Graphics Effects System

Provides particle effects, shader definitions, and post-processing
for combat, environment, and UI visual feedback.

Concepts
--------
ParticleSystem      : a container of active particles
ParticleEmitter     : spawns particles at a rate/location
Particle            : single particle with position, velocity, life, appearance
ShaderDefinition    : blueprint for a GPU shader program (vertex + fragment)
ShaderProgram       : runtime compiled shader program
PostProcessEffect   : base class for screen-space effects
BloomEffect         : glow / HDR bloom
MotionBlurEffect    : velocity-based motion blur
ColorGradingEffect  : LUT-based color grading / tinting
VignetteEffect      : darken screen edges
DepthOfFieldEffect  : focus-based blur
GraphicsEffectsManager : orchestrates all active effects per session
"""

from __future__ import annotations

import json
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BlendMode(Enum):
    """How particles are composited onto the screen."""
    ADDITIVE = "additive"
    ALPHA = "alpha"
    MULTIPLY = "multiply"
    SCREEN = "screen"


class EmitterShape(Enum):
    """Spawn volume geometry for a particle emitter."""
    POINT = "point"
    SPHERE = "sphere"
    BOX = "box"
    CONE = "cone"
    DISC = "disc"


class ParticleProperty(Enum):
    """Properties that can be animated over a particle's lifetime."""
    OPACITY = "opacity"
    SIZE = "size"
    COLOR = "color"
    VELOCITY = "velocity"
    ANGULAR_VELOCITY = "angular_velocity"


class ShaderType(Enum):
    """Shader program stages."""
    VERTEX = "vertex"
    FRAGMENT = "fragment"
    GEOMETRY = "geometry"
    COMPUTE = "compute"


class ShaderParameterType(Enum):
    """GLSL-style uniform types."""
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    VEC2 = "vec2"
    VEC3 = "vec3"
    VEC4 = "vec4"
    MAT3 = "mat3"
    MAT4 = "mat4"
    SAMPLER2D = "sampler2D"
    SAMPLERCUBE = "samplerCube"


class PostProcessLayer(Enum):
    """Rendering order for post-process effects."""
    PRE_TONEMAP = "pre_tonemap"
    POST_TONEMAP = "post_tonemap"
    OVERLAY = "overlay"


class QualityLevel(Enum):
    """Graphics quality presets that gate effect complexity."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


# ---------------------------------------------------------------------------
# Particle System
# ---------------------------------------------------------------------------


@dataclass
class Particle:
    """A single particle in a particle system."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    acceleration: tuple[float, float, float] = (0.0, 0.0, 0.0)
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    size: float = 1.0
    rotation: float = 0.0
    angular_velocity: float = 0.0
    life: float = 1.0
    max_life: float = 1.0
    active: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def age(self, dt: float) -> None:
        """Advance particle by dt seconds."""
        if not self.active:
            return
        self.life -= dt
        if self.life <= 0.0:
            self.active = False
            return
        # Position integration
        ax, ay, az = self.acceleration
        vx, vy, vz = self.velocity
        px, py, pz = self.position
        vx += ax * dt
        vy += ay * dt
        vz += az * dt
        px += vx * dt
        py += vy * dt
        pz += vz * dt
        self.velocity = (vx, vy, vz)
        self.position = (px, py, pz)
        self.rotation += self.angular_velocity * dt

    def normalized_life(self) -> float:
        """0 at birth, 1 at death."""
        if self.max_life <= 0.0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - self.life / self.max_life))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position,
            "velocity": self.velocity,
            "acceleration": self.acceleration,
            "color": self.color,
            "size": self.size,
            "rotation": self.rotation,
            "angular_velocity": self.angular_velocity,
            "life": self.life,
            "max_life": self.max_life,
            "active": self.active,
            "extra": self.extra,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Particle:
        return Particle(
            id=data.get("id", uuid.uuid4().hex),
            position=tuple(data.get("position", (0.0, 0.0, 0.0))),
            velocity=tuple(data.get("velocity", (0.0, 0.0, 0.0))),
            acceleration=tuple(data.get("acceleration", (0.0, 0.0, 0.0))),
            color=tuple(data.get("color", (1.0, 1.0, 1.0, 1.0))),
            size=data.get("size", 1.0),
            rotation=data.get("rotation", 0.0),
            angular_velocity=data.get("angular_velocity", 0.0),
            life=data.get("life", 1.0),
            max_life=data.get("max_life", 1.0),
            active=data.get("active", True),
            extra=data.get("extra", {}),
        )


@dataclass
class ParticleEmitter:
    """Spawns particles according to a rate and volume."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    shape: EmitterShape = EmitterShape.POINT
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: tuple[float, float, float] = (0.0, 1.0, 0.0)
    spread_degrees: float = 30.0
    rate_per_second: float = 10.0
    particle_lifetime: float = 1.0
    particle_size: tuple[float, float] = (1.0, 1.0)
    start_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    end_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 0.0)
    start_velocity: float = 1.0
    end_velocity: float = 0.5
    blend_mode: BlendMode = BlendMode.ADDITIVE
    duration_seconds: float = 0.0
    max_particles: int = 100
    extra: dict[str, Any] = field(default_factory=dict)

    def get_spawn_position(self) -> tuple[float, float, float]:
        """Return a randomized spawn position within the emitter volume."""
        x, y, z = self.position
        if self.shape == EmitterShape.POINT:
            return (x, y, z)
        if self.shape == EmitterShape.SPHERE:
            r = (random.random() ** (1.0 / 3.0)) * self.extra.get("radius", 1.0)
            theta = random.uniform(0.0, 2.0 * 3.141592653589793)
            phi = random.uniform(0.0, 3.141592653589793)
            return (
                x + r * __import__("math").sin(phi) * __import__("math").cos(theta),
                y + r * __import__("math").sin(phi) * __import__("math").sin(theta),
                z + r * __import__("math").cos(phi),
            )
        if self.shape == EmitterShape.BOX:
            hx = self.extra.get("half_extents", (1.0, 1.0, 1.0))
            return (
                x + random.uniform(-hx[0], hx[0]),
                y + random.uniform(-hx[1], hx[1]),
                z + random.uniform(-hx[2], hx[2]),
            )
        if self.shape == EmitterShape.CONE:
            r = random.uniform(0.0, self.extra.get("radius", 1.0))
            theta = random.uniform(0.0, 2.0 * 3.141592653589793)
            return (x + r * __import__("math").cos(theta), y, z + r * __import__("math").sin(theta))
        if self.shape == EmitterShape.DISC:
            r = (random.random() ** 0.5) * self.extra.get("radius", 1.0)
            theta = random.uniform(0.0, 2.0 * 3.141592653589793)
            return (x + r * __import__("math").cos(theta), y, z + r * __import__("math").sin(theta))
        return (x, y, z)

    def spawn_particle(self) -> Particle:
        """Create a single particle at the current emitter state."""
        pos = self.get_spawn_position()
        dx, dy, dz = self.direction
        angle = self.spread_degrees * (__import__("math").pi / 180.0)
        theta = random.uniform(-angle, angle)
        phi = random.uniform(0.0, 2.0 * 3.141592653589793)
        speed = self.start_velocity * random.uniform(0.8, 1.2)
        vx = speed * (dx * __import__("math").cos(theta) + __import__("math").cos(phi) * __import__("math").sin(theta))
        vy = speed * (dy * __import__("math").cos(theta) + __import__("math").sin(phi) * __import__("math").sin(theta))
        vz = speed * (dz * __import__("math").cos(theta) + __import__("math").sin(theta))
        particle_life = self.particle_lifetime * random.uniform(0.8, 1.2)
        return Particle(
            position=pos,
            velocity=(vx, vy, vz),
            acceleration=self.extra.get("acceleration", (0.0, 0.0, 0.0)),
            color=self.start_color,
            size=random.uniform(self.particle_size[0], self.particle_size[1]),
            max_life=particle_life,
            life=particle_life,
            extra=self.extra.get("particle_extra", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "shape": self.shape.value,
            "position": self.position,
            "direction": self.direction,
            "spread_degrees": self.spread_degrees,
            "rate_per_second": self.rate_per_second,
            "particle_lifetime": self.particle_lifetime,
            "particle_size": self.particle_size,
            "start_color": self.start_color,
            "end_color": self.end_color,
            "start_velocity": self.start_velocity,
            "end_velocity": self.end_velocity,
            "blend_mode": self.blend_mode.value,
            "duration_seconds": self.duration_seconds,
            "max_particles": self.max_particles,
            "extra": self.extra,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ParticleEmitter:
        return ParticleEmitter(
            id=data.get("id", uuid.uuid4().hex),
            shape=EmitterShape(data.get("shape", EmitterShape.POINT.value)),
            position=tuple(data.get("position", (0.0, 0.0, 0.0))),
            direction=tuple(data.get("direction", (0.0, 1.0, 0.0))),
            spread_degrees=data.get("spread_degrees", 30.0),
            rate_per_second=data.get("rate_per_second", 10.0),
            particle_lifetime=data.get("particle_lifetime", 1.0),
            particle_size=tuple(data.get("particle_size", (1.0, 1.0))),
            start_color=tuple(data.get("start_color", (1.0, 1.0, 1.0, 1.0))),
            end_color=tuple(data.get("end_color", (1.0, 1.0, 1.0, 0.0))),
            start_velocity=data.get("start_velocity", 1.0),
            end_velocity=data.get("end_velocity", 0.5),
            blend_mode=BlendMode(data.get("blend_mode", BlendMode.ADDITIVE.value)),
            duration_seconds=data.get("duration_seconds", 0.0),
            max_particles=data.get("max_particles", 100),
            extra=data.get("extra", {}),
        )


class ParticleSystem:
    """Active particle system tied to an entity or world position."""

    def __init__(self, effect_id: str, emitter: ParticleEmitter) -> None:
        self.id = uuid.uuid4().hex
        self.effect_id = effect_id
        self.emitter = emitter
        self.particles: list[Particle] = []
        self.elapsed: float = 0.0
        self.active: bool = True

    def update(self, dt: float) -> None:
        """Update all particles and emit new ones if active."""
        if not self.active:
            return
        self.elapsed += dt
        # Spawn
        if self.active:
            count = int(self.emitter.rate_per_second * dt)
            remainder = self.emitter.rate_per_second * dt - count
            if random.random() < remainder:
                count += 1
            for _ in range(count):
                if len(self.particles) < self.emitter.max_particles:
                    self.particles.append(self.emitter.spawn_particle())
        # Age existing
        for p in self.particles:
            p.age(dt)
        self.particles = [p for p in self.particles if p.active]
        # Check duration after spawning so the final frame still emits
        if self.emitter.duration_seconds > 0 and self.elapsed >= self.emitter.duration_seconds:
            self.active = False

    def get_alive_count(self) -> int:
        return sum(1 for p in self.particles if p.active)

    def get_blended_color(self, particle: Particle) -> tuple[float, float, float, float]:
        """Interpolate between start and end color based on normalized life."""
        t = particle.normalized_life()
        r = self.emitter.start_color[0] * (1.0 - t) + self.emitter.end_color[0] * t
        g = self.emitter.start_color[1] * (1.0 - t) + self.emitter.end_color[1] * t
        b = self.emitter.start_color[2] * (1.0 - t) + self.emitter.end_color[2] * t
        a = self.emitter.start_color[3] * (1.0 - t) + self.emitter.end_color[3] * t
        return (r, g, b, a)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "effect_id": self.effect_id,
            "emitter": self.emitter.to_dict(),
            "particles": [p.to_dict() for p in self.particles],
            "elapsed": self.elapsed,
            "active": self.active,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ParticleSystem:
        ps = ParticleSystem(
            effect_id=data["effect_id"],
            emitter=ParticleEmitter.from_dict(data["emitter"]),
        )
        ps.id = data.get("id", ps.id)
        ps.particles = [Particle.from_dict(p) for p in data.get("particles", [])]
        ps.elapsed = data.get("elapsed", 0.0)
        ps.active = data.get("active", True)
        return ps


# ---------------------------------------------------------------------------
# Shader System
# ---------------------------------------------------------------------------


@dataclass
class ShaderParameter:
    """A uniform / attribute definition for a shader program."""

    name: str
    param_type: ShaderParameterType
    default_value: Any = None
    min_value: float | None = None
    max_value: float | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.param_type.value,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "description": self.description,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ShaderParameter:
        return ShaderParameter(
            name=data["name"],
            param_type=ShaderParameterType(data["type"]),
            default_value=data.get("default_value"),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            description=data.get("description", ""),
        )


@dataclass
class ShaderDefinition:
    """Blueprint for a shader program: vertex + fragment source + uniforms."""

    id: str
    name: str
    category: str = "general"
    vertex_source: str = ""
    fragment_source: str = ""
    parameters: list[ShaderParameter] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    min_quality: QualityLevel = QualityLevel.MEDIUM
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "vertex_source": self.vertex_source,
            "fragment_source": self.fragment_source,
            "parameters": [p.to_dict() for p in self.parameters],
            "tags": self.tags,
            "min_quality": self.min_quality.value,
            "extra": self.extra,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ShaderDefinition:
        return ShaderDefinition(
            id=data["id"],
            name=data["name"],
            category=data.get("category", "general"),
            vertex_source=data.get("vertex_source", ""),
            fragment_source=data.get("fragment_source", ""),
            parameters=[ShaderParameter.from_dict(p) for p in data.get("parameters", [])],
            tags=data.get("tags", []),
            min_quality=QualityLevel(data.get("min_quality", QualityLevel.MEDIUM.value)),
            extra=data.get("extra", {}),
        )


class ShaderProgram:
    """Runtime compiled shader program with bound parameter values."""

    def __init__(self, definition: ShaderDefinition) -> None:
        self.definition = definition
        self.values: dict[str, Any] = {}
        self.compiled: bool = True
        self.last_use: float = time.time()
        # Initialize defaults
        for param in definition.parameters:
            self.values[param.name] = param.default_value

    def set_parameter(self, name: str, value: Any) -> None:
        self.values[name] = value
        self.last_use = time.time()

    def get_parameter(self, name: str) -> Any:
        return self.values.get(name)

    def age(self) -> float:
        return time.time() - self.last_use

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition_id": self.definition.id,
            "values": self.values,
            "compiled": self.compiled,
            "last_use": self.last_use,
        }


# ---------------------------------------------------------------------------
# Post-Processing Effects
# ---------------------------------------------------------------------------


@dataclass
class PostProcessEffect:
    """Base runtime record for an active post-process effect."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    definition_id: str = ""
    layer: PostProcessLayer = PostProcessLayer.POST_TONEMAP
    intensity: float = 1.0
    duration_seconds: float = 0.0
    elapsed: float = 0.0
    active: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)

    def update(self, dt: float) -> None:
        if not self.active:
            return
        self.elapsed += dt
        if 0.0 < self.duration_seconds <= self.elapsed:
            self.active = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "definition_id": self.definition_id,
            "layer": self.layer.value,
            "intensity": self.intensity,
            "duration_seconds": self.duration_seconds,
            "elapsed": self.elapsed,
            "active": self.active,
            "parameters": self.parameters,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PostProcessEffect:
        return PostProcessEffect(
            id=data.get("id", uuid.uuid4().hex),
            definition_id=data.get("definition_id", ""),
            layer=PostProcessLayer(data.get("layer", PostProcessLayer.POST_TONEMAP.value)),
            intensity=data.get("intensity", 1.0),
            duration_seconds=data.get("duration_seconds", 0.0),
            elapsed=data.get("elapsed", 0.0),
            active=data.get("active", True),
            parameters=data.get("parameters", {}),
        )


@dataclass
class BloomEffectDefinition:
    """Bloom / glow configuration."""
    threshold: float = 1.0
    intensity: float = 0.5
    radius: float = 4.0
    tint: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "intensity": self.intensity,
            "radius": self.radius,
            "tint": self.tint,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> BloomEffectDefinition:
        return BloomEffectDefinition(
            threshold=data.get("threshold", 1.0),
            intensity=data.get("intensity", 0.5),
            radius=data.get("radius", 4.0),
            tint=tuple(data.get("tint", (1.0, 1.0, 1.0))),
        )


@dataclass
class MotionBlurEffectDefinition:
    """Motion blur configuration."""
    velocity_scale: float = 1.0
    max_blur: float = 8.0
    samples: int = 16

    def to_dict(self) -> dict[str, Any]:
        return {
            "velocity_scale": self.velocity_scale,
            "max_blur": self.max_blur,
            "samples": self.samples,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MotionBlurEffectDefinition:
        return MotionBlurEffectDefinition(
            velocity_scale=data.get("velocity_scale", 1.0),
            max_blur=data.get("max_blur", 8.0),
            samples=data.get("samples", 16),
        )


@dataclass
class ColorGradingEffectDefinition:
    """Color grading / LUT configuration."""
    lut_texture: str = ""
    saturation: float = 1.0
    contrast: float = 1.0
    brightness: float = 0.0
    tint: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lut_texture": self.lut_texture,
            "saturation": self.saturation,
            "contrast": self.contrast,
            "brightness": self.brightness,
            "tint": self.tint,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ColorGradingEffectDefinition:
        return ColorGradingEffectDefinition(
            lut_texture=data.get("lut_texture", ""),
            saturation=data.get("saturation", 1.0),
            contrast=data.get("contrast", 1.0),
            brightness=data.get("brightness", 0.0),
            tint=tuple(data.get("tint", (1.0, 1.0, 1.0))),
        )


@dataclass
class VignetteEffectDefinition:
    """Vignette (edge darkening) configuration."""
    intensity: float = 0.3
    radius: float = 0.5
    softness: float = 0.3
    color: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intensity": self.intensity,
            "radius": self.radius,
            "softness": self.softness,
            "color": self.color,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> VignetteEffectDefinition:
        return VignetteEffectDefinition(
            intensity=data.get("intensity", 0.3),
            radius=data.get("radius", 0.5),
            softness=data.get("softness", 0.3),
            color=tuple(data.get("color", (0.0, 0.0, 0.0))),
        )


@dataclass
class DepthOfFieldEffectDefinition:
    """Depth-of-field configuration."""
    focal_distance: float = 10.0
    focal_range: float = 5.0
    blur_near: float = 2.0
    blur_far: float = 4.0
    max_blur: float = 8.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "focal_distance": self.focal_distance,
            "focal_range": self.focal_range,
            "blur_near": self.blur_near,
            "blur_far": self.blur_far,
            "max_blur": self.max_blur,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DepthOfFieldEffectDefinition:
        return DepthOfFieldEffectDefinition(
            focal_distance=data.get("focal_distance", 10.0),
            focal_range=data.get("focal_range", 5.0),
            blur_near=data.get("blur_near", 2.0),
            blur_far=data.get("blur_far", 4.0),
            max_blur=data.get("max_blur", 8.0),
        )


# ---------------------------------------------------------------------------
# Graphics Effects Manager
# ---------------------------------------------------------------------------


class GraphicsEffectsManager:
    """
    Orchestrates particle systems, shader programs, and post-process effects.

    Loads definitions from JSON, manages runtime active effects, and
    supports per-session or per-entity effect presets.
    """

    def __init__(self, data_directory: str | None = None) -> None:
        if data_directory is None:
            data_directory = os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_directory = data_directory
        self.particle_definitions: dict[str, ParticleEmitter] = {}
        self.shader_definitions: dict[str, ShaderDefinition] = {}
        self.postprocess_definitions: dict[str, dict[str, Any]] = {}
        self.active_particle_systems: dict[str, ParticleSystem] = {}
        self.active_shader_programs: dict[str, ShaderProgram] = {}
        self.active_postprocess: dict[str, PostProcessEffect] = {}
        self.quality_level: QualityLevel = QualityLevel.HIGH
        self._load_definitions()

    # --- definition loading -------------------------------------------------

    def _load_definitions(self) -> None:
        path = os.path.join(self.data_directory, "graphics_effects.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for item in data.get("particle_emitters", []):
            emitter = ParticleEmitter.from_dict(item)
            self.particle_definitions[emitter.id] = emitter
        for item in data.get("shaders", []):
            shader = ShaderDefinition.from_dict(item)
            self.shader_definitions[shader.id] = shader
        for ppid, item in data.get("post_process", {}).items():
            self.postprocess_definitions[ppid] = item

    def register_particle_emitter(self, emitter: ParticleEmitter) -> None:
        self.particle_definitions[emitter.id] = emitter

    def register_shader(self, shader: ShaderDefinition) -> None:
        self.shader_definitions[shader.id] = shader

    def register_postprocess(self, effect_id: str, definition: dict[str, Any]) -> None:
        self.postprocess_definitions[effect_id] = definition

    def load_from_dicts(self, data: dict[str, Any]) -> None:
        for item in data.get("particle_emitters", []):
            self.register_particle_emitter(ParticleEmitter.from_dict(item))
        for item in data.get("shaders", []):
            self.register_shader(ShaderDefinition.from_dict(item))
        for ppid, item in data.get("post_process", {}).items():
            self.register_postprocess(ppid, item)

    # --- particle systems --------------------------------------------------

    def spawn_particle_system(self, effect_id: str, position: tuple[float, float, float] | None = None) -> ParticleSystem | None:
        emitter = self.particle_definitions.get(effect_id)
        if emitter is None:
            return None
        if position is not None:
            emitter = ParticleEmitter(
                id=emitter.id,
                shape=emitter.shape,
                position=position,
                direction=emitter.direction,
                spread_degrees=emitter.spread_degrees,
                rate_per_second=emitter.rate_per_second,
                particle_lifetime=emitter.particle_lifetime,
                particle_size=emitter.particle_size,
                start_color=emitter.start_color,
                end_color=emitter.end_color,
                start_velocity=emitter.start_velocity,
                end_velocity=emitter.end_velocity,
                blend_mode=emitter.blend_mode,
                duration_seconds=emitter.duration_seconds,
                max_particles=emitter.max_particles,
                extra=emitter.extra,
            )
        ps = ParticleSystem(effect_id=effect_id, emitter=emitter)
        self.active_particle_systems[ps.id] = ps
        return ps

    def update_particle_system(self, ps_id: str, dt: float) -> None:
        ps = self.active_particle_systems.get(ps_id)
        if ps:
            ps.update(dt)
            if not ps.active and ps.get_alive_count() == 0:
                self.active_particle_systems.pop(ps_id, None)

    def remove_particle_system(self, ps_id: str) -> None:
        self.active_particle_systems.pop(ps_id, None)

    def get_active_particle_systems(self) -> list[ParticleSystem]:
        return list(self.active_particle_systems.values())

    # --- shaders -----------------------------------------------------------

    def get_shader_definition(self, shader_id: str) -> ShaderDefinition | None:
        return self.shader_definitions.get(shader_id)

    def create_shader_program(self, shader_id: str) -> ShaderProgram | None:
        definition = self.shader_definitions.get(shader_id)
        if definition is None:
            return None
        if definition.min_quality.value_index() > self.quality_level.value_index():
            return None
        prog = ShaderProgram(definition=definition)
        self.active_shader_programs[shader_id] = prog
        return prog

    def get_shader_program(self, shader_id: str) -> ShaderProgram | None:
        return self.active_shader_programs.get(shader_id)

    # --- post-process ------------------------------------------------------

    def trigger_postprocess(self, effect_id: str, duration_seconds: float = 0.0, parameters: dict[str, Any] | None = None) -> PostProcessEffect | None:
        definition = self.postprocess_definitions.get(effect_id)
        if definition is None:
            return None
        layer = PostProcessLayer(definition.get("layer", PostProcessLayer.POST_TONEMAP.value))
        intensity = definition.get("intensity", 1.0)
        pp = PostProcessEffect(
            definition_id=effect_id,
            layer=layer,
            intensity=intensity,
            duration_seconds=duration_seconds,
            parameters=parameters or definition.get("default_parameters", {}),
        )
        self.active_postprocess[pp.id] = pp
        return pp

    def get_active_postprocess(self, layer: PostProcessLayer | None = None) -> list[PostProcessEffect]:
        effects = [pp for pp in self.active_postprocess.values() if pp.active]
        if layer is not None:
            effects = [pp for pp in effects if pp.layer == layer]
        return effects

    # --- global update -----------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance all active systems by dt seconds."""
        # Particle systems
        dead = []
        for ps_id, ps in self.active_particle_systems.items():
            ps.update(dt)
            if not ps.active and ps.get_alive_count() == 0:
                dead.append(ps_id)
        for ps_id in dead:
            self.active_particle_systems.pop(ps_id, None)
        # Post-process
        dead_pp = []
        for pp_id, pp in self.active_postprocess.items():
            pp.update(dt)
            if not pp.active:
                dead_pp.append(pp_id)
        for pp_id in dead_pp:
            self.active_postprocess.pop(pp_id, None)

    def set_quality_level(self, level: QualityLevel) -> None:
        self.quality_level = level

    def clear_all(self) -> None:
        self.active_particle_systems.clear()
        self.active_shader_programs.clear()
        self.active_postprocess.clear()

    def get_runtime_summary(self) -> dict[str, Any]:
        return {
            "quality_level": self.quality_level.value,
            "particle_systems": len(self.active_particle_systems),
            "particles_alive": sum(ps.get_alive_count() for ps in self.active_particle_systems.values()),
            "shader_programs": len(self.active_shader_programs),
            "post_process_effects": len(self.active_postprocess),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "quality_level": self.quality_level.value,
            "particle_definitions": {k: v.to_dict() for k, v in self.particle_definitions.items()},
            "shader_definitions": {k: v.to_dict() for k, v in self.shader_definitions.items()},
            "postprocess_definitions": self.postprocess_definitions,
            "active_particle_systems": {k: v.to_dict() for k, v in self.active_particle_systems.items()},
            "active_postprocess": {k: v.to_dict() for k, v in self.active_postprocess.items()},
        }


# ---------------------------------------------------------------------------
# Quality level helpers
# ---------------------------------------------------------------------------


def _quality_index(level: QualityLevel) -> int:
    return ["low", "medium", "high", "ultra"].index(level.value)


QualityLevel.value_index = _quality_index


# ---------------------------------------------------------------------------
# Preset helpers
# ---------------------------------------------------------------------------


def create_fire_burst_emitter(position: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> ParticleEmitter:
    return ParticleEmitter(
        id="fire_burst",
        shape=EmitterShape.SPHERE,
        position=position,
        direction=(0.0, 1.0, 0.0),
        spread_degrees=20.0,
        rate_per_second=40.0,
        particle_lifetime=0.6,
        particle_size=(0.3, 0.8),
        start_color=(1.0, 0.6, 0.1, 1.0),
        end_color=(1.0, 0.1, 0.0, 0.0),
        start_velocity=3.0,
        end_velocity=0.5,
        blend_mode=BlendMode.ADDITIVE,
        duration_seconds=1.5,
        max_particles=80,
        extra={"radius": 0.5, "acceleration": (0.0, 1.5, 0.0)},
    )


def create_ice_ring_emitter(position: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> ParticleEmitter:
    return ParticleEmitter(
        id="ice_ring",
        shape=EmitterShape.DISC,
        position=position,
        direction=(0.0, 1.0, 0.0),
        spread_degrees=5.0,
        rate_per_second=30.0,
        particle_lifetime=1.2,
        particle_size=(0.2, 0.5),
        start_color=(0.7, 0.9, 1.0, 0.9),
        end_color=(0.3, 0.6, 1.0, 0.0),
        start_velocity=2.0,
        end_velocity=0.2,
        blend_mode=BlendMode.ADDITIVE,
        duration_seconds=1.0,
        max_particles=60,
        extra={"radius": 1.5, "acceleration": (0.0, 0.5, 0.0)},
    )


def create_heal_sparkle_emitter(position: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> ParticleEmitter:
    return ParticleEmitter(
        id="heal_sparkle",
        shape=EmitterShape.POINT,
        position=position,
        direction=(0.0, 1.0, 0.0),
        spread_degrees=360.0,
        rate_per_second=20.0,
        particle_lifetime=0.8,
        particle_size=(0.1, 0.3),
        start_color=(1.0, 1.0, 0.8, 1.0),
        end_color=(1.0, 1.0, 1.0, 0.0),
        start_velocity=1.5,
        end_velocity=0.0,
        blend_mode=BlendMode.ADDITIVE,
        duration_seconds=1.2,
        max_particles=40,
        extra={},
    )
