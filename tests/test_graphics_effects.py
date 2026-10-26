"""
Tests for RPG-13-07 Graphics Effects System.
Run with: python -m pytest tests/test_graphics_effects.py -v
or:       python tests/test_graphics_effects.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graphics_effects import (
    BlendMode,
    BloomEffectDefinition,
    ColorGradingEffectDefinition,
    DepthOfFieldEffectDefinition,
    EmitterShape,
    GraphicsEffectsManager,
    MotionBlurEffectDefinition,
    Particle,
    ParticleEmitter,
    ParticleSystem,
    PostProcessEffect,
    PostProcessLayer,
    QualityLevel,
    ShaderDefinition,
    ShaderParameter,
    ShaderParameterType,
    ShaderProgram,
    VignetteEffectDefinition,
    create_fire_burst_emitter,
    create_heal_sparkle_emitter,
    create_ice_ring_emitter,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_emitter() -> ParticleEmitter:
    return ParticleEmitter(
        id="test_spark",
        shape=EmitterShape.POINT,
        position=(1.0, 2.0, 3.0),
        direction=(0.0, 1.0, 0.0),
        spread_degrees=45.0,
        rate_per_second=10.0,
        particle_lifetime=1.0,
        particle_size=(0.5, 1.0),
        start_color=(1.0, 0.5, 0.0, 1.0),
        end_color=(1.0, 0.0, 0.0, 0.0),
        start_velocity=2.0,
        end_velocity=0.5,
        blend_mode=BlendMode.ADDITIVE,
        duration_seconds=0.5,
        max_particles=50,
    )


def _sample_shader() -> ShaderDefinition:
    return ShaderDefinition(
        id="test_shader",
        name="Test Shader",
        category="test",
        vertex_source="void main() {}",
        fragment_source="void main() {}",
        parameters=[
            ShaderParameter(name="u_time", param_type=ShaderParameterType.FLOAT, default_value=0.0),
        ],
        tags=["test"],
        min_quality=QualityLevel.LOW,
    )


# ---------------------------------------------------------------------------
# ParticleEmitter tests
# ---------------------------------------------------------------------------

class TestParticleEmitter:
    def test_defaults(self):
        emitter = ParticleEmitter()
        assert emitter.shape == EmitterShape.POINT
        assert emitter.position == (0.0, 0.0, 0.0)
        assert emitter.rate_per_second == 10.0
        assert emitter.blend_mode == BlendMode.ADDITIVE
        assert emitter.max_particles == 100

    def test_spawn_particle_returns_particle(self):
        emitter = _sample_emitter()
        p = emitter.spawn_particle()
        assert isinstance(p, Particle)
        assert p.active is True
        assert p.max_life > 0.0

    def test_spawn_position_point(self):
        emitter = _sample_emitter()
        assert emitter.get_spawn_position() == (1.0, 2.0, 3.0)

    def test_spawn_position_sphere(self):
        emitter = ParticleEmitter(
            shape=EmitterShape.SPHERE,
            position=(0.0, 0.0, 0.0),
            extra={"radius": 2.0},
        )
        for _ in range(50):
            pos = emitter.get_spawn_position()
            dist = (pos[0]**2 + pos[1]**2 + pos[2]**2) ** 0.5
            assert dist <= 2.0 + 1e-6

    def test_spawn_position_box(self):
        emitter = ParticleEmitter(
            shape=EmitterShape.BOX,
            position=(0.0, 0.0, 0.0),
            extra={"half_extents": (1.0, 2.0, 3.0)},
        )
        for _ in range(50):
            pos = emitter.get_spawn_position()
            assert -1.0 <= pos[0] <= 1.0
            assert -2.0 <= pos[1] <= 2.0
            assert -3.0 <= pos[2] <= 3.0

    def test_to_dict_roundtrip(self):
        emitter = _sample_emitter()
        data = emitter.to_dict()
        restored = ParticleEmitter.from_dict(data)
        assert restored.id == emitter.id
        assert restored.shape == emitter.shape
        assert restored.rate_per_second == emitter.rate_per_second


# ---------------------------------------------------------------------------
# Particle tests
# ---------------------------------------------------------------------------

class TestParticle:
    def test_age_decreases_life(self):
        p = Particle(life=1.0, max_life=1.0)
        p.age(0.1)
        assert abs(p.life - 0.9) < 1e-6

    def test_age_kills_particle(self):
        p = Particle(life=0.05, max_life=0.05)
        p.age(0.1)
        assert p.active is False

    def test_inactive_not_aged(self):
        p = Particle(life=1.0, active=False)
        p.age(0.5)
        assert p.life == 1.0

    def test_normalized_life(self):
        p = Particle(life=0.5, max_life=1.0)
        assert abs(p.normalized_life() - 0.5) < 1e-6

    def test_roundtrip(self):
        p = Particle(position=(1.0, 2.0, 3.0), life=0.5, max_life=1.0)
        data = p.to_dict()
        restored = Particle.from_dict(data)
        assert restored.position == (1.0, 2.0, 3.0)
        assert abs(restored.life - 0.5) < 1e-6


# ---------------------------------------------------------------------------
# ParticleSystem tests
# ---------------------------------------------------------------------------

class TestParticleSystem:
    def test_spawns_particles(self):
        emitter = ParticleEmitter(
            rate_per_second=100.0,
            particle_lifetime=1.0,
            duration_seconds=0.1,
            max_particles=10,
        )
        ps = ParticleSystem("test", emitter)
        ps.update(0.1)
        assert ps.get_alive_count() > 0

    def test_expires(self):
        emitter = ParticleEmitter(
            rate_per_second=10.0,
            particle_lifetime=0.1,
            duration_seconds=0.05,
            max_particles=10,
        )
        ps = ParticleSystem("test", emitter)
        ps.update(0.1)
        assert ps.active is False

    def test_update_ages_particles(self):
        emitter = _sample_emitter()
        ps = ParticleSystem("test", emitter)
        # Use a fixed particle with deterministic values to verify aging
        ps.particles = [Particle(life=1.0, max_life=1.0, velocity=(0.0, 0.0, 0.0))]
        ps.update(0.2)
        for p in ps.particles:
            assert p.life < p.max_life

    def test_roundtrip(self):
        emitter = _sample_emitter()
        ps = ParticleSystem("test", emitter)
        ps.update(0.1)
        data = ps.to_dict()
        restored = ParticleSystem.from_dict(data)
        assert restored.effect_id == "test"
        assert len(restored.particles) == len(ps.particles)


# ---------------------------------------------------------------------------
# Shader tests
# ---------------------------------------------------------------------------

class TestShader:
    def test_parameter_set_get(self):
        shader = _sample_shader()
        prog = ShaderProgram(shader)
        prog.set_parameter("u_time", 3.14)
        assert abs(prog.get_parameter("u_time") - 3.14) < 1e-6

    def test_unknown_parameter_returns_none(self):
        shader = _sample_shader()
        prog = ShaderProgram(shader)
        assert prog.get_parameter("does_not_exist") is None

    def test_roundtrip_definition(self):
        shader = _sample_shader()
        data = shader.to_dict()
        restored = ShaderDefinition.from_dict(data)
        assert restored.id == shader.id
        assert restored.parameters[0].name == "u_time"


# ---------------------------------------------------------------------------
# Post-process tests
# ---------------------------------------------------------------------------

class TestPostProcess:
    def test_update_duration(self):
        pp = PostProcessEffect(definition_id="test", duration_seconds=0.1)
        assert pp.active is True
        pp.update(0.15)
        assert pp.active is False

    def test_no_duration_stays_active(self):
        pp = PostProcessEffect(definition_id="test", duration_seconds=0.0)
        pp.update(1.0)
        assert pp.active is True

    def test_roundtrip(self):
        pp = PostProcessEffect(
            definition_id="bloom",
            layer=PostProcessLayer.PRE_TONEMAP,
            intensity=0.8,
            duration_seconds=0.5,
            parameters={"threshold": 1.2},
        )
        data = pp.to_dict()
        restored = PostProcessEffect.from_dict(data)
        assert restored.definition_id == "bloom"
        assert restored.layer == PostProcessLayer.PRE_TONEMAP
        assert restored.parameters["threshold"] == 1.2


# ---------------------------------------------------------------------------
# Post-process definition helpers
# ---------------------------------------------------------------------------

class TestPostProcessDefinitions:
    def test_bloom_roundtrip(self):
        b = BloomEffectDefinition(threshold=1.2, intensity=0.7, radius=5.0, tint=(1.0, 0.9, 0.8))
        data = b.to_dict()
        restored = BloomEffectDefinition.from_dict(data)
        assert restored.threshold == 1.2
        assert restored.tint == (1.0, 0.9, 0.8)

    def test_motion_blur_roundtrip(self):
        mb = MotionBlurEffectDefinition(velocity_scale=1.5, max_blur=10.0, samples=32)
        data = mb.to_dict()
        restored = MotionBlurEffectDefinition.from_dict(data)
        assert restored.samples == 32

    def test_color_grading_roundtrip(self):
        cg = ColorGradingEffectDefinition(saturation=1.2, contrast=0.9, tint=(1.1, 0.9, 0.8))
        data = cg.to_dict()
        restored = ColorGradingEffectDefinition.from_dict(data)
        assert restored.saturation == 1.2

    def test_vignette_roundtrip(self):
        v = VignetteEffectDefinition(intensity=0.4, radius=0.6, color=(0.1, 0.0, 0.0))
        data = v.to_dict()
        restored = VignetteEffectDefinition.from_dict(data)
        assert restored.color == (0.1, 0.0, 0.0)

    def test_dof_roundtrip(self):
        dof = DepthOfFieldEffectDefinition(focal_distance=15.0, max_blur=12.0)
        data = dof.to_dict()
        restored = DepthOfFieldEffectDefinition.from_dict(data)
        assert restored.focal_distance == 15.0


# ---------------------------------------------------------------------------
# GraphicsEffectsManager tests
# ---------------------------------------------------------------------------

class TestGraphicsEffectsManager:
    def test_loads_from_json(self):
        mgr = GraphicsEffectsManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        assert "fire_burst" in mgr.particle_definitions
        assert "fire_distortion" in mgr.shader_definitions
        assert "bloom" in mgr.postprocess_definitions

    def test_spawn_particle_system(self):
        mgr = GraphicsEffectsManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        ps = mgr.spawn_particle_system("fire_burst", position=(0.0, 1.0, 0.0))
        assert ps is not None
        assert ps.emitter.position == (0.0, 1.0, 0.0)
        assert len(mgr.active_particle_systems) == 1

    def test_spawn_unknown_returns_none(self):
        mgr = GraphicsEffectsManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        assert mgr.spawn_particle_system("no_such_effect") is None

    def test_trigger_postprocess(self):
        mgr = GraphicsEffectsManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        pp = mgr.trigger_postprocess("bloom", duration_seconds=0.5)
        assert pp is not None
        assert pp.layer == PostProcessLayer.PRE_TONEMAP
        assert len(mgr.active_postprocess) == 1

    def test_update_cleans_up(self):
        mgr = GraphicsEffectsManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        ps = mgr.spawn_particle_system("fire_burst")
        mgr.update(5.0)
        assert len(mgr.active_particle_systems) == 0

    def test_quality_level_filters_shaders(self):
        mgr = GraphicsEffectsManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        mgr.set_quality_level(QualityLevel.LOW)
        # chromatic_aberation requires medium
        prog = mgr.create_shader_program("chromatic_aberration")
        assert prog is None
        # hit_flash is low
        prog = mgr.create_shader_program("hit_flash")
        assert prog is not None

    def test_clear_all(self):
        mgr = GraphicsEffectsManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        mgr.spawn_particle_system("fire_burst")
        mgr.trigger_postprocess("bloom")
        mgr.clear_all()
        assert len(mgr.active_particle_systems) == 0
        assert len(mgr.active_postprocess) == 0

    def test_runtime_summary(self):
        mgr = GraphicsEffectsManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        mgr.spawn_particle_system("fire_burst")
        mgr.trigger_postprocess("bloom")
        summary = mgr.get_runtime_summary()
        assert summary["particle_systems"] == 1
        assert summary["post_process_effects"] == 1

    def test_load_from_dicts(self):
        mgr = GraphicsEffectsManager.__new__(GraphicsEffectsManager)
        mgr.particle_definitions = {}
        mgr.shader_definitions = {}
        mgr.postprocess_definitions = {}
        mgr.active_particle_systems = {}
        mgr.active_shader_programs = {}
        mgr.active_postprocess = {}
        mgr.quality_level = QualityLevel.HIGH

        data = {
            "particle_emitters": [
                {
                    "id": "custom_fire",
                    "shape": "point",
                    "rate_per_second": 5.0,
                    "particle_lifetime": 1.0,
                    "start_color": [1.0, 0.0, 0.0, 1.0],
                    "end_color": [0.5, 0.0, 0.0, 0.0],
                }
            ],
            "shaders": [],
            "post_process": {},
        }
        mgr.load_from_dicts(data)
        assert "custom_fire" in mgr.particle_definitions


# ---------------------------------------------------------------------------
# Preset helpers
# ---------------------------------------------------------------------------

class TestPresets:
    def test_fire_burst(self):
        e = create_fire_burst_emitter((0.0, 0.0, 0.0))
        assert e.shape == EmitterShape.SPHERE
        assert e.blend_mode == BlendMode.ADDITIVE
        assert e.start_color[0] == 1.0

    def test_ice_ring(self):
        e = create_ice_ring_emitter((1.0, 0.0, 1.0))
        assert e.shape == EmitterShape.DISC
        assert e.position == (1.0, 0.0, 1.0)

    def test_heal_sparkle(self):
        e = create_heal_sparkle_emitter((0.0, 5.0, 0.0))
        assert e.spread_degrees == 360.0
        assert e.position == (0.0, 5.0, 0.0)


# ---------------------------------------------------------------------------
# Integration: full manager with data
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_combat_effect_sequence(self):
        mgr = GraphicsEffectsManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        mgr.set_quality_level(QualityLevel.HIGH)
        # spawn fire burst
        fire = mgr.spawn_particle_system("fire_burst", position=(0.0, 0.0, 0.0))
        # trigger bloom
        bloom = mgr.trigger_postprocess("bloom", duration_seconds=0.5)
        # trigger hit flash
        flash = mgr.trigger_postprocess("flash_white", duration_seconds=0.15)
        # tick
        for _ in range(3):
            mgr.update(0.05)
        summary = mgr.get_runtime_summary()
        assert summary["particle_systems"] >= 1
        # after enough time, particle system should expire
        mgr.update(2.0)
        assert len(mgr.active_particle_systems) == 0

    def test_mixed_quality_levels(self):
        mgr = GraphicsEffectsManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        for level in (QualityLevel.LOW, QualityLevel.MEDIUM, QualityLevel.HIGH, QualityLevel.ULTRA):
            mgr.set_quality_level(level)
            fire = mgr.spawn_particle_system("fire_burst")
            assert fire is not None
            prog = mgr.create_shader_program("hit_flash")
            assert prog is not None


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
