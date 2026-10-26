"""
RPG-12-08: Performance Optimization System

Provides asset streaming and memory management for the RPG engine.

Concepts
--------
AssetPriority        : loading priority buckets (critical, high, normal, low, background)
AssetType            : category of game asset (texture, model, audio, data, ui)
AssetState           : runtime state of a registered asset
AssetDefinition      : metadata describing an asset (path, type, size, dependencies)
StreamingZone        : a spatial or logical zone that governs which assets are active
MemoryBudget         : configurable memory limits with current usage tracking
PerformanceMetrics   : snapshot of system health (FPS, memory, asset counts)
AssetStreamingManager: loads/unloads assets based on active zones and priority
MemoryManager        : tracks allocations, enforces budgets, triggers garbage collection
PerformanceOptimizer : orchestrates streaming + memory + metrics
"""

from __future__ import annotations

import gc
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Constants / Enums
# ---------------------------------------------------------------------------

class AssetPriority:
    """Loading priority buckets. Critical assets are loaded first and evicted last."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class AssetType:
    """Broad categories for game assets."""
    TEXTURE = "texture"
    MODEL = "model"
    AUDIO = "audio"
    DATA = "data"
    UI = "ui"
    WORLD = "world"
    FONT = "font"
    SHADER = "shader"


class AssetLoadState:
    """Runtime load state of an asset."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    EVICTING = "evicting"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class AssetDefinition:
    """Metadata describing an asset the optimizer can track."""

    asset_id: str
    name: str
    asset_type: str
    file_path: str = ""
    size_bytes: int = 0
    priority: str = AssetPriority.NORMAL
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    max_lifetime_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "asset_type": self.asset_type,
            "file_path": self.file_path,
            "size_bytes": self.size_bytes,
            "priority": self.priority,
            "dependencies": list(self.dependencies),
            "tags": list(self.tags),
            "max_lifetime_seconds": self.max_lifetime_seconds,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AssetDefinition:
        return AssetDefinition(
            asset_id=data["asset_id"],
            name=data["name"],
            asset_type=data["asset_type"],
            file_path=data.get("file_path", ""),
            size_bytes=int(data.get("size_bytes", 0)),
            priority=data.get("priority", AssetPriority.NORMAL),
            dependencies=list(data.get("dependencies", [])),
            tags=list(data.get("tags", [])),
            max_lifetime_seconds=data.get("max_lifetime_seconds"),
        )


@dataclass
class AssetState:
    """Runtime record for an asset currently tracked by the optimizer."""

    asset_id: str
    state: str = AssetLoadState.UNLOADED
    loaded_at: str = ""
    last_accessed: str = ""
    access_count: int = 0
    reference_count: int = 0
    custom_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "state": self.state,
            "loaded_at": self.loaded_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "reference_count": self.reference_count,
            "custom_data": dict(self.custom_data),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AssetState:
        return AssetState(
            asset_id=data["asset_id"],
            state=data.get("state", AssetLoadState.UNLOADED),
            loaded_at=data.get("loaded_at", ""),
            last_accessed=data.get("last_accessed", ""),
            access_count=int(data.get("access_count", 0)),
            reference_count=int(data.get("reference_count", 0)),
            custom_data=dict(data.get("custom_data", {})),
        )


@dataclass
class StreamingZone:
    """A spatial or logical zone that governs asset loading."""

    zone_id: str
    name: str = ""
    asset_ids: list[str] = field(default_factory=list)
    priority_boost: str = ""
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "asset_ids": list(self.asset_ids),
            "priority_boost": self.priority_boost,
            "active": self.active,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StreamingZone:
        return StreamingZone(
            zone_id=data["zone_id"],
            name=data.get("name", ""),
            asset_ids=list(data.get("asset_ids", [])),
            priority_boost=data.get("priority_boost", ""),
            active=data.get("active", True),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class MemoryBudget:
    """Configurable memory limits with current usage tracking."""

    name: str
    max_bytes: int = 256 * 1024 * 1024  # 256 MB default
    warning_threshold: float = 0.8
    critical_threshold: float = 0.95
    current_bytes: int = 0
    category_budgets: dict[str, int] = field(default_factory=dict)

    def utilization(self) -> float:
        if self.max_bytes <= 0:
            return 0.0
        return self.current_bytes / self.max_bytes

    def is_warning(self) -> bool:
        return self.utilization() >= self.warning_threshold

    def is_critical(self) -> bool:
        return self.utilization() >= self.critical_threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "max_bytes": self.max_bytes,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "current_bytes": self.current_bytes,
            "category_budgets": dict(self.category_budgets),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MemoryBudget:
        return MemoryBudget(
            name=data["name"],
            max_bytes=int(data.get("max_bytes", 256 * 1024 * 1024)),
            warning_threshold=float(data.get("warning_threshold", 0.8)),
            critical_threshold=float(data.get("critical_threshold", 0.95)),
            current_bytes=int(data.get("current_bytes", 0)),
            category_budgets=dict(data.get("category_budgets", {})),
        )


@dataclass
class PerformanceMetrics:
    """Snapshot of system health."""

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    fps: float = 0.0
    frame_time_ms: float = 0.0
    memory_used_bytes: int = 0
    memory_budget_bytes: int = 0
    assets_loaded: int = 0
    assets_unloaded: int = 0
    streaming_queue_size: int = 0
    gc_collections: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "fps": self.fps,
            "frame_time_ms": self.frame_time_ms,
            "memory_used_bytes": self.memory_used_bytes,
            "memory_budget_bytes": self.memory_budget_bytes,
            "assets_loaded": self.assets_loaded,
            "assets_unloaded": self.assets_unloaded,
            "streaming_queue_size": self.streaming_queue_size,
            "gc_collections": self.gc_collections,
            "warnings": list(self.warnings),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PerformanceMetrics:
        return PerformanceMetrics(
            timestamp=data.get("timestamp", ""),
            fps=float(data.get("fps", 0.0)),
            frame_time_ms=float(data.get("frame_time_ms", 0.0)),
            memory_used_bytes=int(data.get("memory_used_bytes", 0)),
            memory_budget_bytes=int(data.get("memory_budget_bytes", 0)),
            assets_loaded=int(data.get("assets_loaded", 0)),
            assets_unloaded=int(data.get("assets_unloaded", 0)),
            streaming_queue_size=int(data.get("streaming_queue_size", 0)),
            gc_collections=int(data.get("gc_collections", 0)),
            warnings=list(data.get("warnings", [])),
        )


# ---------------------------------------------------------------------------
# Core Managers
# ---------------------------------------------------------------------------

class AssetStreamingManager:
    """
    Loads and unloads assets based on active streaming zones and priority.

    Call ``update`` once per tick (frame or logic tick) with the set of active
    zone ids. Assets inside active zones are queued for loading; assets no
    longer in any active zone are candidates for eviction.
    """

    def __init__(self, load_callback: Callable[[AssetDefinition], None] | None = None,
                 unload_callback: Callable[[str], None] | None = None) -> None:
        self._definitions: dict[str, AssetDefinition] = {}
        self._states: dict[str, AssetState] = {}
        self._zones: dict[str, StreamingZone] = {}
        self._active_zone_ids: set[str] = set()
        self._load_queue: list[AssetDefinition] = []
        self._evict_queue: list[str] = []
        self._load_callback = load_callback
        self._unload_callback = unload_callback

    # Registration ---------------------------------------------------------

    def register_asset(self, definition: AssetDefinition) -> None:
        self._definitions[definition.asset_id] = definition
        if definition.asset_id not in self._states:
            self._states[definition.asset_id] = AssetState(asset_id=definition.asset_id)

    def register_zone(self, zone: StreamingZone) -> None:
        self._zones[zone.zone_id] = zone

    def set_active_zones(self, zone_ids: list[str]) -> None:
        self._active_zone_ids = set(zone_ids)

    # Tick ----------------------------------------------------------------

    def update(self, dt: float = 0.0) -> dict[str, Any]:
        """
        Process the load and evict queues.

        Returns a summary of actions taken this tick.
        """
        self._rebuild_queues()
        loaded = self._process_load_queue()
        evicted = self._process_evict_queue()
        self._enforce_lifetimes()
        return {
            "loaded": loaded,
            "evicted": evicted,
            "queue_remaining": self._load_queue + self._evict_queue,
        }

    # Queries -------------------------------------------------------------

    def get_state(self, asset_id: str) -> AssetState | None:
        return self._states.get(asset_id)

    def is_loaded(self, asset_id: str) -> bool:
        state = self._states.get(asset_id)
        return bool(state and state.state == AssetLoadState.LOADED)

    def list_loaded(self) -> list[str]:
        return [aid for aid, s in self._states.items() if s.state == AssetLoadState.LOADED]

    def list_registered(self) -> list[str]:
        return list(self._definitions.keys())

    def mark_accessed(self, asset_id: str) -> None:
        state = self._states.get(asset_id)
        if state:
            state.last_accessed = datetime.now(UTC).isoformat()
            state.access_count += 1

    # Internal ------------------------------------------------------------

    def _rebuild_queues(self) -> None:
        self._load_queue.clear()
        self._evict_queue.clear()

        active_asset_ids: set[str] = set()
        for zone_id in self._active_zone_ids:
            zone = self._zones.get(zone_id)
            if zone and zone.active:
                for asset_id in zone.asset_ids:
                    active_asset_ids.add(asset_id)
                if zone.priority_boost:
                    for asset_id in zone.asset_ids:
                        defn = self._definitions.get(asset_id)
                        if defn:
                            defn.priority = zone.priority_boost

        for asset_id in active_asset_ids:
            if asset_id in self._definitions:
                state = self._states.get(asset_id)
                if not state or state.state in (AssetLoadState.UNLOADED, AssetLoadState.FAILED):
                    self._load_queue.append(self._definitions[asset_id])

        for asset_id, state in self._states.items():
            if state.state == AssetLoadState.LOADED and asset_id not in active_asset_ids:
                self._evict_queue.append(asset_id)

        self._sort_queues()

    def _sort_queues(self) -> None:
        priority_order = {
            AssetPriority.CRITICAL: 0,
            AssetPriority.HIGH: 1,
            AssetPriority.NORMAL: 2,
            AssetPriority.LOW: 3,
            AssetPriority.BACKGROUND: 4,
        }
        self._load_queue.sort(key=lambda d: priority_order.get(d.priority, 99))
        self._evict_queue.sort(key=lambda aid: priority_order.get(self._definitions.get(aid, AssetDefinition(asset_id="", name="", asset_type="")).priority, 99), reverse=True)

    def _process_load_queue(self) -> list[str]:
        loaded_ids: list[str] = []
        for defn in self._load_queue:
            state = self._states.get(defn.asset_id)
            if not state:
                continue
            state.state = AssetLoadState.LOADING
            state.loaded_at = datetime.now(UTC).isoformat()
            if self._load_callback:
                try:
                    self._load_callback(defn)
                    state.state = AssetLoadState.LOADED
                    loaded_ids.append(defn.asset_id)
                except Exception:
                    state.state = AssetLoadState.FAILED
            else:
                state.state = AssetLoadState.LOADED
                loaded_ids.append(defn.asset_id)
        self._load_queue.clear()
        return loaded_ids

    def _process_evict_queue(self) -> list[str]:
        evicted_ids: list[str] = []
        for asset_id in self._evict_queue:
            state = self._states.get(asset_id)
            if not state or state.reference_count > 0:
                continue
            state.state = AssetLoadState.EVICTING
            if self._unload_callback:
                try:
                    self._unload_callback(asset_id)
                except Exception:
                    pass
            state.state = AssetLoadState.UNLOADED
            evicted_ids.append(asset_id)
        self._evict_queue.clear()
        return evicted_ids

    def _enforce_lifetimes(self) -> None:
        now = datetime.now(UTC)
        for asset_id, defn in self._definitions.items():
            if defn.max_lifetime_seconds is None:
                continue
            state = self._states.get(asset_id)
            if not state or not state.loaded_at:
                continue
            loaded_time = datetime.fromisoformat(state.loaded_at)
            age = (now - loaded_time).total_seconds()
            if age >= defn.max_lifetime_seconds and state.state == AssetLoadState.LOADED:
                state.state = AssetLoadState.EVICTING
                if self._unload_callback:
                    try:
                        self._unload_callback(asset_id)
                    except Exception:
                        pass
                state.state = AssetLoadState.UNLOADED


class MemoryManager:
    """
    Tracks memory allocations per asset category and enforces budgets.

    If the budget is exceeded, the manager triggers eviction of the lowest-
    priority loaded assets until utilization drops below the warning threshold.
    """

    def __init__(self, streaming_manager: AssetStreamingManager | None = None) -> None:
        self.streaming = streaming_manager
        self._budget = MemoryBudget(name="default")
        self._category_usage: dict[str, int] = {}
        self._allocation_log: list[dict[str, Any]] = []

    def set_budget(self, budget: MemoryBudget) -> None:
        self._budget = budget

    def get_budget(self) -> MemoryBudget:
        return self._budget

    def record_allocation(self, asset_id: str, asset_type: str, size_bytes: int) -> None:
        self._budget.current_bytes += size_bytes
        self._category_usage[asset_type] = self._category_usage.get(asset_type, 0) + size_bytes
        self._allocation_log.append({
            "time": datetime.now(UTC).isoformat(),
            "asset_id": asset_id,
            "asset_type": asset_type,
            "size_bytes": size_bytes,
            "total": self._budget.current_bytes,
        })

    def record_deallocation(self, asset_id: str, asset_type: str, size_bytes: int) -> None:
        self._budget.current_bytes = max(0, self._budget.current_bytes - size_bytes)
        self._category_usage[asset_type] = max(0, self._category_usage.get(asset_type, 0) - size_bytes)

    def get_category_usage(self, asset_type: str) -> int:
        return self._category_usage.get(asset_type, 0)

    def get_utilization(self) -> float:
        return self._budget.utilization()

    def enforce_budget(self) -> dict[str, Any]:
        """
        If over budget, evict low-priority assets until under warning threshold.

        Returns a summary of evictions triggered.
        """
        evicted: list[str] = []
        if not self.streaming:
            return {"evicted": evicted, "reason": "no_streaming_manager"}

        while self._budget.is_critical() or self._budget.is_warning():
            candidates = [
                aid for aid in self.streaming.list_loaded()
                if self.streaming.get_state(aid) and self.streaming.get_state(aid).reference_count == 0
            ]
            if not candidates:
                break
            priority_order = {
                AssetPriority.BACKGROUND: 0,
                AssetPriority.LOW: 1,
                AssetPriority.NORMAL: 2,
                AssetPriority.HIGH: 3,
                AssetPriority.CRITICAL: 4,
            }
            candidates.sort(key=lambda aid: priority_order.get(
                self.streaming._definitions.get(aid, AssetDefinition(asset_id="", name="", asset_type="")).priority, 99
            ))
            target = candidates[0]
            defn = self.streaming._definitions.get(target)
            if defn:
                self.streaming._unload_callback(target) if self.streaming._unload_callback else None
                state = self.streaming._states.get(target)
                if state:
                    state.state = AssetLoadState.UNLOADED
                self.record_deallocation(target, defn.asset_type, defn.size_bytes)
                evicted.append(target)
            if not evicted:
                break

        return {"evicted": evicted, "reason": "budget_enforcement" if evicted else "within_budget"}

    def garbage_collect(self) -> dict[str, Any]:
        """Run Python GC and report collections performed."""
        before = len(gc.get_objects())
        gc.collect()
        after = len(gc.get_objects())
        return {"collected": max(0, before - after), "gc_count": gc.get_stats()[0]["collections"] if gc.get_stats() else 0}


class PerformanceOptimizer:
    """
    Top-level orchestrator: wires AssetStreamingManager + MemoryManager +
    PerformanceMetrics and exposes a simple API.
    """

    def __init__(self, max_memory_bytes: int = 256 * 1024 * 1024) -> None:
        self.streaming = AssetStreamingManager(
            load_callback=self._on_asset_load,
            unload_callback=self._on_asset_unload,
        )
        self.memory = MemoryManager(streaming_manager=self.streaming)
        self.memory.set_budget(MemoryBudget(name="global", max_bytes=max_memory_bytes))
        self._metrics = PerformanceMetrics()
        self._last_tick = time.time()
        self._frame_times: list[float] = []
        self._tick_count = 0

    # Public API ----------------------------------------------------------

    def register_asset(self, definition: AssetDefinition) -> None:
        self.streaming.register_asset(definition)

    def register_zone(self, zone: StreamingZone) -> None:
        self.streaming.register_zone(zone)

    def set_active_zones(self, zone_ids: list[str]) -> None:
        self.streaming.set_active_zones(zone_ids)

    def tick(self, dt: float = 0.0) -> dict[str, Any]:
        """Run one optimizer tick: update streaming, enforce memory, refresh metrics."""
        now = time.time()
        frame_time_ms = (now - self._last_tick) * 1000.0
        self._last_tick = now
        self._frame_times.append(frame_time_ms)
        if len(self._frame_times) > 120:
            self._frame_times.pop(0)

        streaming_result = self.streaming.update(dt)
        budget_result = self.memory.enforce_budget()
        gc_result = self.memory.garbage_collect()

        fps = 1000.0 / max(frame_time_ms, 0.001)
        warnings = []
        if self.memory.get_budget().is_warning():
            warnings.append("memory_usage_high")
        if self.memory.get_budget().is_critical():
            warnings.append("memory_usage_critical")

        self._metrics = PerformanceMetrics(
            fps=fps,
            frame_time_ms=frame_time_ms,
            memory_used_bytes=self.memory.get_budget().current_bytes,
            memory_budget_bytes=self.memory.get_budget().max_bytes,
            assets_loaded=len(self.streaming.list_loaded()),
            assets_unloaded=len([aid for aid, s in self.streaming._states.items() if s.state == AssetLoadState.UNLOADED]),
            streaming_queue_size=len(streaming_result.get("queue_remaining", [])),
            gc_collections=gc_result.get("gc_count", 0),
            warnings=warnings,
        )
        self._tick_count += 1

        return {
            "streaming": streaming_result,
            "budget": budget_result,
            "gc": gc_result,
            "metrics": self._metrics.to_dict(),
        }

    def get_metrics(self) -> PerformanceMetrics:
        return self._metrics

    def get_streaming_state(self) -> dict[str, Any]:
        return {
            "loaded": self.streaming.list_loaded(),
            "registered": self.streaming.list_registered(),
            "zones": {zid: z.to_dict() for zid, z in self.streaming._zones.items()},
            "active_zones": list(self.streaming._active_zone_ids),
        }

    def get_memory_state(self) -> dict[str, Any]:
        return self.memory.get_budget().to_dict()

    # Internal callbacks --------------------------------------------------

    def _on_asset_load(self, definition: AssetDefinition) -> None:
        self.memory.record_allocation(definition.asset_id, definition.asset_type, definition.size_bytes)

    def _on_asset_unload(self, asset_id: str) -> None:
        defn = self.streaming._definitions.get(asset_id)
        if defn:
            self.memory.record_deallocation(asset_id, defn.asset_type, defn.size_bytes)
