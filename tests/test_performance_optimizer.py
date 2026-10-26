"""
Tests for RPG-12-08: Performance Optimization System.

Run with: python -m pytest tests/ -v
or:       python tests/test_performance_optimizer.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from performance_optimizer import (
    AssetDefinition,
    AssetLoadState,
    AssetPriority,
    AssetState,
    AssetStreamingManager,
    AssetType,
    MemoryBudget,
    MemoryManager,
    PerformanceMetrics,
    PerformanceOptimizer,
    StreamingZone,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_optimizer(max_memory: int = 10 * 1024 * 1024) -> PerformanceOptimizer:
    return PerformanceOptimizer(max_memory_bytes=max_memory)


def _make_asset(asset_id: str, size: int = 1024) -> AssetDefinition:
    return AssetDefinition(
        asset_id=asset_id,
        name=asset_id,
        asset_type=AssetType.TEXTURE,
        file_path=f"assets/{asset_id}.png",
        size_bytes=size,
        priority=AssetPriority.NORMAL,
    )


# ---------------------------------------------------------------------------
# AssetDefinition tests
# ---------------------------------------------------------------------------

class TestAssetDefinition:
    def test_roundtrip(self):
        a = _make_asset("a1", 2048)
        restored = AssetDefinition.from_dict(a.to_dict())
        assert restored.asset_id == "a1"
        assert restored.size_bytes == 2048
        assert restored.priority == AssetPriority.NORMAL

    def test_defaults(self):
        a = AssetDefinition(asset_id="x", name="X", asset_type=AssetType.MODEL)
        assert a.file_path == ""
        assert a.size_bytes == 0
        assert a.dependencies == []
        assert a.tags == []
        assert a.max_lifetime_seconds is None


# ---------------------------------------------------------------------------
# AssetState tests
# ---------------------------------------------------------------------------

class TestAssetState:
    def test_roundtrip(self):
        s = AssetState(asset_id="a1", state=AssetLoadState.LOADED, access_count=5)
        restored = AssetState.from_dict(s.to_dict())
        assert restored.asset_id == "a1"
        assert restored.state == AssetLoadState.LOADED
        assert restored.access_count == 5


# ---------------------------------------------------------------------------
# StreamingZone tests
# ---------------------------------------------------------------------------

class TestStreamingZone:
    def test_roundtrip(self):
        z = StreamingZone(zone_id="z1", name="Forest", asset_ids=["a1", "a2"], active=True)
        restored = StreamingZone.from_dict(z.to_dict())
        assert restored.zone_id == "z1"
        assert restored.asset_ids == ["a1", "a2"]
        assert restored.active is True


# ---------------------------------------------------------------------------
# MemoryBudget tests
# ---------------------------------------------------------------------------

class TestMemoryBudget:
    def test_utilization(self):
        b = MemoryBudget(name="test", max_bytes=1000, current_bytes=500)
        assert b.utilization() == 0.5

    def test_warning_and_critical(self):
        b = MemoryBudget(name="test", max_bytes=1000, warning_threshold=0.8, critical_threshold=0.95, current_bytes=850)
        assert b.is_warning() is True
        assert b.is_critical() is False
        b.current_bytes = 980
        assert b.is_critical() is True

    def test_roundtrip(self):
        b = MemoryBudget(name="r", max_bytes=2048, current_bytes=512, category_budgets={"texture": 1024})
        restored = MemoryBudget.from_dict(b.to_dict())
        assert restored.max_bytes == 2048
        assert restored.category_budgets["texture"] == 1024


# ---------------------------------------------------------------------------
# PerformanceMetrics tests
# ---------------------------------------------------------------------------

class TestPerformanceMetrics:
    def test_roundtrip(self):
        m = PerformanceMetrics(fps=60.0, frame_time_ms=16.6, warnings=["memory_high"])
        restored = PerformanceMetrics.from_dict(m.to_dict())
        assert restored.fps == 60.0
        assert restored.warnings == ["memory_high"]


# ---------------------------------------------------------------------------
# AssetStreamingManager tests
# ---------------------------------------------------------------------------

class TestAssetStreamingManager:
    def test_register_and_query(self):
        mgr = AssetStreamingManager()
        a = _make_asset("a1")
        mgr.register_asset(a)
        assert mgr.is_loaded("a1") is False
        assert "a1" in mgr.list_registered()

    def test_load_with_callback(self):
        loaded: list[str] = []
        def cb(defn):
            loaded.append(defn.asset_id)

        mgr = AssetStreamingManager(load_callback=cb)
        mgr.register_asset(_make_asset("a1"))
        zone = StreamingZone(zone_id="z1", asset_ids=["a1"])
        mgr.register_zone(zone)
        mgr.set_active_zones(["z1"])
        result = mgr.update()
        assert "a1" in loaded
        assert mgr.is_loaded("a1") is True

    def test_unload_with_callback(self):
        unloaded: list[str] = []
        def cb(aid):
            unloaded.append(aid)

        mgr = AssetStreamingManager(unload_callback=cb)
        mgr.register_asset(_make_asset("a1"))
        zone = StreamingZone(zone_id="z1", asset_ids=["a1"])
        mgr.register_zone(zone)
        mgr.set_active_zones(["z1"])
        mgr.update()
        mgr.set_active_zones([])
        mgr.update()
        assert "a1" in unloaded
        assert mgr.is_loaded("a1") is False

    def test_priority_ordering(self):
        order: list[str] = []
        def cb(defn):
            order.append(defn.asset_id)

        mgr = AssetStreamingManager(load_callback=cb)
        mgr.register_asset(AssetDefinition(asset_id="low", name="Low", asset_type=AssetType.TEXTURE, priority=AssetPriority.LOW, size_bytes=1))
        mgr.register_asset(AssetDefinition(asset_id="high", name="High", asset_type=AssetType.TEXTURE, priority=AssetPriority.HIGH, size_bytes=1))
        mgr.register_asset(AssetDefinition(asset_id="critical", name="Critical", asset_type=AssetType.TEXTURE, priority=AssetPriority.CRITICAL, size_bytes=1))
        zone = StreamingZone(zone_id="z1", asset_ids=["low", "high", "critical"])
        mgr.register_zone(zone)
        mgr.set_active_zones(["z1"])
        mgr.update()
        assert order == ["critical", "high", "low"]

    def test_access_count(self):
        mgr = AssetStreamingManager()
        mgr.register_asset(_make_asset("a1"))
        zone = StreamingZone(zone_id="z1", asset_ids=["a1"])
        mgr.register_zone(zone)
        mgr.set_active_zones(["z1"])
        mgr.update()
        assert mgr.get_state("a1").access_count == 0
        mgr.mark_accessed("a1")
        mgr.mark_accessed("a1")
        assert mgr.get_state("a1").access_count == 2


# ---------------------------------------------------------------------------
# MemoryManager tests
# ---------------------------------------------------------------------------

class TestMemoryManager:
    def test_record_allocation_and_deallocation(self):
        mgr = MemoryManager()
        mgr.set_budget(MemoryBudget(name="g", max_bytes=5000))
        mgr.record_allocation("a1", AssetType.TEXTURE, 1000)
        assert mgr.get_budget().current_bytes == 1000
        assert mgr.get_category_usage(AssetType.TEXTURE) == 1000
        mgr.record_deallocation("a1", AssetType.TEXTURE, 500)
        assert mgr.get_budget().current_bytes == 500
        assert mgr.get_category_usage(AssetType.TEXTURE) == 500

    def test_enforce_budget_evicts(self):
        loaded: list[str] = []
        def load_cb(defn):
            loaded.append(defn.asset_id)
        def unload_cb(aid):
            pass

        streaming = AssetStreamingManager(load_callback=load_cb, unload_callback=unload_cb)
        streaming.register_asset(_make_asset("bg", 100))
        streaming.register_asset(_make_asset("low", 100))
        streaming.register_asset(_make_asset("high", 100))
        zone = StreamingZone(zone_id="z1", asset_ids=["bg", "low", "high"])
        streaming.register_zone(zone)
        streaming.set_active_zones(["z1"])
        streaming.update()

        memory = MemoryManager(streaming_manager=streaming)
        memory.set_budget(MemoryBudget(name="g", max_bytes=150))
        memory.record_allocation("bg", AssetType.TEXTURE, 100)
        memory.record_allocation("low", AssetType.TEXTURE, 100)
        memory.record_allocation("high", AssetType.TEXTURE, 100)

        result = memory.enforce_budget()
        assert len(result["evicted"]) >= 1


# ---------------------------------------------------------------------------
# PerformanceOptimizer tests
# ---------------------------------------------------------------------------

class TestPerformanceOptimizer:
    def test_tick_processes_streaming_and_metrics(self):
        opt = _make_optimizer(max_memory=10 * 1024 * 1024)
        opt.register_asset(_make_asset("a1", 1024))
        zone = StreamingZone(zone_id="z1", asset_ids=["a1"])
        opt.register_zone(zone)
        opt.set_active_zones(["z1"])
        result = opt.tick(0.016)
        assert result["streaming"]["loaded"] == ["a1"]
        assert opt.streaming.is_loaded("a1") is True
        assert "fps" in result["metrics"]

    def test_memory_tracking_through_tick(self):
        opt = _make_optimizer(max_memory=10 * 1024 * 1024)
        opt.register_asset(_make_asset("a1", 5000))
        zone = StreamingZone(zone_id="z1", asset_ids=["a1"])
        opt.register_zone(zone)
        opt.set_active_zones(["z1"])
        opt.tick(0.016)
        assert opt.memory.get_budget().current_bytes == 5000

    def test_active_zones_switch(self):
        opt = _make_optimizer()
        opt.register_asset(_make_asset("a1"))
        opt.register_asset(_make_asset("a2"))
        z1 = StreamingZone(zone_id="z1", asset_ids=["a1"])
        z2 = StreamingZone(zone_id="z2", asset_ids=["a2"])
        opt.register_zone(z1)
        opt.register_zone(z2)
        opt.set_active_zones(["z1"])
        opt.tick()
        assert opt.streaming.is_loaded("a1") is True
        opt.set_active_zones(["z2"])
        opt.tick()
        assert opt.streaming.is_loaded("a2") is True

    def test_get_streaming_state(self):
        opt = _make_optimizer()
        opt.register_asset(_make_asset("a1"))
        opt.register_zone(StreamingZone(zone_id="z1", asset_ids=["a1"], name="TestZone"))
        opt.set_active_zones(["z1"])
        opt.tick()
        state = opt.get_streaming_state()
        assert "a1" in state["loaded"]
        assert "z1" in state["zones"]

    def test_get_memory_state(self):
        opt = _make_optimizer(max_memory=1024)
        mem = opt.get_memory_state()
        assert mem["max_bytes"] == 1024
        assert mem["name"] == "global"


if __name__ == "__main__":
    suites = [
        TestAssetDefinition,
        TestAssetState,
        TestStreamingZone,
        TestMemoryBudget,
        TestPerformanceMetrics,
        TestAssetStreamingManager,
        TestMemoryManager,
        TestPerformanceOptimizer,
    ]
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
