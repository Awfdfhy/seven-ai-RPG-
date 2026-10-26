"""
RPG-10-02: AI Narration System tests.
Run with: python -m pytest tests/ -v
or:       python tests/test_ai_narration.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ai_narration import (
    NarrationContext,
    NarrationEvent,
    NarrationManager,
    NarrationScope,
    NarrationTemplate,
)

# ---------------------------------------------------------------------------
# NarrationTemplate tests
# ---------------------------------------------------------------------------

class TestNarrationTemplate:
    def test_default_values(self):
        tmpl = NarrationTemplate(
            template_id="t1",
            scope=NarrationScope.GLOBAL,
            text="Hello {name}",
            variables=["name"],
        )
        assert tmpl.template_id == "t1"
        assert tmpl.scope == NarrationScope.GLOBAL
        assert tmpl.text == "Hello {name}"
        assert tmpl.variables == ["name"]
        assert tmpl.weight == 1.0
        assert tmpl.tags == []

    def test_to_dict_roundtrip(self):
        tmpl = NarrationTemplate(
            template_id="t2",
            scope=NarrationScope.LOCATION,
            text="Welcome to {location}",
            variables=["location"],
            weight=2.5,
            tags=["location", "welcome"],
            metadata={"author": "system"},
        )
        restored = NarrationTemplate.from_dict(tmpl.to_dict())
        assert restored.template_id == "t2"
        assert restored.scope == NarrationScope.LOCATION
        assert restored.text == "Welcome to {location}"
        assert restored.variables == ["location"]
        assert restored.weight == 2.5
        assert restored.tags == ["location", "welcome"]
        assert restored.metadata == {"author": "system"}


# ---------------------------------------------------------------------------
# NarrationContext tests
# ---------------------------------------------------------------------------

class TestNarrationContext:
    def test_default_values(self):
        ctx = NarrationContext()
        assert ctx.world_id == ""
        assert ctx.character_name == ""
        assert ctx.location_id == ""

    def test_as_fill_dict_defaults(self):
        ctx = NarrationContext()
        d = ctx.as_fill_dict()
        assert d["character_name"] == "the traveler"
        assert d["location_name"] == "the road"
        assert d["region_name"] == "the wilds"
        assert d["weather_condition"] == "clear"
        assert d["party_size"] == 0

    def test_as_fill_dict_with_values(self):
        ctx = NarrationContext(
            character_name="Aria",
            location_name="Oakhaven",
            region_name="Green Valley",
            weather_condition="rain",
            weather_intensity="heavy",
            party_members=["Aria", "Borin"],
        )
        d = ctx.as_fill_dict()
        assert d["character_name"] == "Aria"
        assert d["location_name"] == "Oakhaven"
        assert d["region_name"] == "Green Valley"
        assert d["weather_condition"] == "rain"
        assert d["weather_intensity"] == "heavy"
        assert d["party_size"] == 2

    def test_as_fill_dict_extra(self):
        ctx = NarrationContext(extra={"custom_var": "value"})
        d = ctx.as_fill_dict()
        assert d["custom_var"] == "value"

    def test_to_dict_roundtrip(self):
        ctx = NarrationContext(
            world_id="w1",
            character_name="Aria",
            location_name="Oakhaven",
            character_stats={"strength": 14},
            recent_events=[{"type": "quest_complete"}],
        )
        restored = NarrationContext.from_dict(ctx.to_dict())
        assert restored.world_id == "w1"
        assert restored.character_name == "Aria"
        assert restored.location_name == "Oakhaven"
        assert restored.character_stats == {"strength": 14}
        assert restored.recent_events == [{"type": "quest_complete"}]


# ---------------------------------------------------------------------------
# NarrationEvent tests
# ---------------------------------------------------------------------------

class TestNarrationEvent:
    def test_default_values(self):
        ev = NarrationEvent()
        assert ev.world_id == ""
        assert ev.scope == NarrationScope.GLOBAL
        assert ev.text == ""
        assert ev.priority == 0
        assert ev.tags == []
        assert ev.event_id != ""

    def test_to_dict_roundtrip(self):
        ev = NarrationEvent(
            world_id="w1",
            session_id="s1",
            scope=NarrationScope.WEATHER,
            text="Rain falls.",
            source="weather",
            priority=5,
            tags=["weather"],
        )
        restored = NarrationEvent.from_dict(ev.to_dict())
        assert restored.world_id == "w1"
        assert restored.session_id == "s1"
        assert restored.scope == NarrationScope.WEATHER
        assert restored.text == "Rain falls."
        assert restored.source == "weather"
        assert restored.priority == 5
        assert restored.tags == ["weather"]


# ---------------------------------------------------------------------------
# NarrationManager tests
# ---------------------------------------------------------------------------

class TestNarrationManager:
    def test_builtin_templates_loaded(self):
        mgr = NarrationManager()
        tmpls = mgr.list_templates()
        assert len(tmpls) > 0
        # Should have at least weather templates
        weather_tmpls = mgr.list_templates(scope=NarrationScope.WEATHER)
        assert len(weather_tmpls) > 0

    def test_register_and_get_template(self):
        mgr = NarrationManager()
        tmpl = NarrationTemplate(
            template_id="custom_1",
            scope=NarrationScope.CUSTOM,
            text="Custom: {name}",
            variables=["name"],
        )
        mgr.register_template(tmpl)
        assert mgr.get_template("custom_1") is tmpl
        assert mgr.get_template("missing") is None

    def test_list_templates_filter_by_scope(self):
        mgr = NarrationManager()
        weather = mgr.list_templates(scope=NarrationScope.WEATHER)
        combat = mgr.list_templates(scope=NarrationScope.COMBAT)
        for t in weather:
            assert t.scope == NarrationScope.WEATHER
        for t in combat:
            assert t.scope == NarrationScope.COMBAT

    def test_list_templates_filter_by_tags(self):
        mgr = NarrationManager()
        results = mgr.list_templates(tags=["weather"])
        assert len(results) > 0
        for t in results:
            assert "weather" in t.tags

    def test_render_template_basic(self):
        mgr = NarrationManager()
        ctx = NarrationContext(
            character_name="Aria",
            location_name="Oakhaven",
            weather_condition="rain",
            weather_intensity="heavy",
        )
        text = mgr.render_template("weather_arrival_moderate", ctx)
        assert "Aria" in text or "rain" in text.lower() or "snow" in text.lower() or "fog" in text.lower()
        assert text != ""

    def test_render_template_missing_returns_raw(self):
        mgr = NarrationManager()
        ctx = NarrationContext()
        text = mgr.render_template("does_not_exist", ctx)
        assert text == ""

    def test_render_custom(self):
        mgr = NarrationManager()
        ctx = NarrationContext(character_name="Borin")
        text = mgr.render_custom("Greetings, {character_name}!", ctx)
        assert text == "Greetings, Borin!"

    def test_compose_narration_template_mode(self):
        mgr = NarrationManager()
        ctx = NarrationContext(
            character_name="Aria",
            location_name="Oakhaven",
            weather_condition="rain",
            weather_intensity="heavy",
        )
        text = mgr.compose_narration("w1", NarrationScope.WEATHER, ctx, mode="template")
        assert text != ""
        assert isinstance(text, str)

    def test_compose_narration_system_mode(self):
        mgr = NarrationManager()
        ctx = NarrationContext(location_name="Oakhaven")
        text = mgr.compose_narration("w1", NarrationScope.LOCATION, ctx, mode="system")
        # May or may not have system sources depending on integrations,
        # but should return a string
        assert isinstance(text, str)

    def test_compose_narration_auto_mode(self):
        mgr = NarrationManager()
        ctx = NarrationContext(character_name="Aria")
        text = mgr.compose_narration("w1", NarrationScope.GLOBAL, ctx, mode="auto")
        assert isinstance(text, str)

    def test_queue_and_get_world_events(self):
        mgr = NarrationManager()
        ev = mgr.queue_narration(
            world_id="w1",
            scope=NarrationScope.GLOBAL,
            text="Hello world",
            source="test",
        )
        events = mgr.get_world_events("w1")
        assert len(events) == 1
        assert events[0].event_id == ev.event_id
        assert events[0].text == "Hello world"

    def test_queue_and_get_session_events(self):
        mgr = NarrationManager()
        ev = mgr.queue_narration(
            world_id="w1",
            session_id="s1",
            scope=NarrationScope.COMBAT,
            text="Combat begins",
            source="test",
        )
        events = mgr.get_session_events("s1")
        assert len(events) == 1
        assert events[0].scope == NarrationScope.COMBAT

    def test_get_world_events_filter_by_scope(self):
        mgr = NarrationManager()
        mgr.queue_narration("w1", NarrationScope.GLOBAL, "g")
        mgr.queue_narration("w1", NarrationScope.LOCATION, "l")
        events = mgr.get_world_events("w1", scope=NarrationScope.LOCATION)
        assert len(events) == 1
        assert events[0].text == "l"

    def test_get_events_limit(self):
        mgr = NarrationManager()
        for i in range(10):
            mgr.queue_narration("w1", NarrationScope.GLOBAL, f"msg{i}")
        events = mgr.get_world_events("w1", limit=3)
        assert len(events) == 3

    def test_export_import_roundtrip(self):
        mgr = NarrationManager()
        mgr.register_template(
            NarrationTemplate(
                template_id="custom_export",
                scope=NarrationScope.CUSTOM,
                text="Exported {name}",
                variables=["name"],
            )
        )
        mgr.queue_narration("w1", NarrationScope.GLOBAL, "keep this")
        state = mgr.export_state()

        mgr2 = NarrationManager()
        mgr2.import_state(state)
        assert mgr2.get_template("custom_export") is not None
        events = mgr2.get_world_events("w1")
        assert len(events) == 1
        assert events[0].text == "keep this"

    def test_register_and_get_source(self):
        mgr = NarrationManager()
        fake = {"name": "test"}
        mgr.register_source("fake_source", fake)
        assert mgr.get_source("fake_source") is fake
        assert mgr.get_source("missing") is None

    def test_compose_narration_returns_string_for_empty_scope(self):
        mgr = NarrationManager()
        ctx = NarrationContext()
        # A scope with no templates should still return a string (empty)
        text = mgr.compose_narration("w1", "nonexistent_scope", ctx, mode="template")
        assert isinstance(text, str)


if __name__ == "__main__":
    import traceback

    suites = [
        TestNarrationTemplate,
        TestNarrationContext,
        TestNarrationEvent,
        TestNarrationManager,
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
                    traceback.print_exc()
                    failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
