"""
Tests for RPG-12-04 Procedural Content Generation.
Run with: python tests/test_procedural_generation.py
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from locations import LocationDirectory
from procedural_generation import (
    DUNGEON_THEMES,
    ENCOUNTER_TEMPLATES,
    ENEMY_TEMPLATES,
    Dungeon,
    Encounter,
    ProceduralGenerator,
    Room,
)
from world_map import Location, Region, WorldMap

# ---------------------------------------------------------------------------
# Room tests
# ---------------------------------------------------------------------------

class TestRoom:
    def test_roundtrip(self):
        r = Room(
            room_id="r1",
            name="Cavern",
            room_type="cavern",
            x=5,
            y=10,
            width=3,
            height=4,
            danger_level=3,
            connections=[{"to": "r2", "type": "corridor", "distance": 2}],
            encounter={"title": "Ambush", "encounter_type": "combat"},
            loot_table_id="lt1",
            trap={"type": "spike_pit", "dc": 14},
        )
        restored = Room.from_dict(r.to_dict())
        assert restored.room_id == "r1"
        assert restored.name == "Cavern"
        assert restored.room_type == "cavern"
        assert restored.x == 5
        assert restored.y == 10
        assert restored.width == 3
        assert restored.height == 4
        assert restored.danger_level == 3
        assert len(restored.connections) == 1
        assert restored.connections[0]["to"] == "r2"
        assert restored.encounter["title"] == "Ambush"
        assert restored.loot_table_id == "lt1"
        assert restored.trap["type"] == "spike_pit"

    def test_defaults(self):
        r = Room(room_id="r1", name="Room", room_type="room", x=0, y=0)
        assert r.width == 3
        assert r.height == 3
        assert r.danger_level == 1
        assert r.connections == []
        assert r.encounter is None
        assert r.loot_table_id is None
        assert r.trap is None


# ---------------------------------------------------------------------------
# Dungeon tests
# ---------------------------------------------------------------------------

class TestDungeon:
    def test_roundtrip(self):
        rooms = [
            Room(room_id="r0", name="Entrance", room_type="hall", x=0, y=0),
            Room(room_id="r1", name="Chamber", room_type="cavern", x=5, y=5),
        ]
        d = Dungeon(
            dungeon_id="d1",
            name="The Dark Cavern",
            description="A dark cave.",
            region_id="r_valley",
            theme="cave",
            difficulty=3,
            seed=42,
            rooms=rooms,
            x=0,
            y=0,
            danger_level=3,
            exit_location_id="oakhaven",
            metadata={"secret": True},
        )
        restored = Dungeon.from_dict(d.to_dict())
        assert restored.dungeon_id == "d1"
        assert restored.name == "The Dark Cavern"
        assert restored.theme == "cave"
        assert restored.difficulty == 3
        assert restored.seed == 42
        assert len(restored.rooms) == 2
        assert restored.exit_location_id == "oakhaven"
        assert restored.metadata["secret"] is True

    def test_to_location_entry(self):
        d = Dungeon(
            dungeon_id="d1",
            name="Test Dungeon",
            description="desc",
            region_id="r1",
            theme="cave",
            difficulty=2,
            seed=1,
            danger_level=2,
            exit_location_id="town",
        )
        entry = d.to_location_entry()
        assert entry.id == "d1"
        assert entry.location_type == "dungeon"
        assert entry.danger_level == 2
        assert len(entry.connections) == 1
        assert entry.connections[0]["to"] == "town"

    def test_to_world_location(self):
        d = Dungeon(
            dungeon_id="d1",
            name="Test Dungeon",
            description="desc",
            region_id="r1",
            theme="cave",
            difficulty=2,
            seed=1,
        )
        loc = d.to_world_location()
        assert isinstance(loc, Location)
        assert loc.id == "d1"
        assert loc.location_type == "dungeon"


# ---------------------------------------------------------------------------
# Encounter tests
# ---------------------------------------------------------------------------

class TestEncounter:
    def test_roundtrip(self):
        e = Encounter(
            encounter_id="e1",
            encounter_type="combat",
            title="Ambush!",
            description="Enemies appear.",
            difficulty=3,
            enemies=["goblin", "wolf"],
            npc_id="npc1",
            skill_checks=[{"type": "perception", "dc": 12}],
            rewards={"xp": 150, "gold": 30},
            metadata={"ambush": True},
        )
        restored = Encounter.from_dict(e.to_dict())
        assert restored.encounter_id == "e1"
        assert restored.encounter_type == "combat"
        assert restored.title == "Ambush!"
        assert restored.difficulty == 3
        assert restored.enemies == ["goblin", "wolf"]
        assert restored.npc_id == "npc1"
        assert restored.rewards["xp"] == 150
        assert restored.metadata["ambush"] is True


# ---------------------------------------------------------------------------
# ProceduralGenerator tests
# ---------------------------------------------------------------------------

class TestProceduralGenerator:
    def test_generate_dungeon_defaults(self):
        gen = ProceduralGenerator(rng=random.Random(42))
        dungeon = gen.generate_dungeon(difficulty=3, region_id="r_valley", theme="cave")
        assert dungeon.theme == "cave"
        assert dungeon.difficulty == 3
        assert dungeon.region_id == "r_valley"
        assert len(dungeon.rooms) > 0
        assert dungeon.dungeon_id.startswith("proc_dungeon_")
        # Each room should have connections
        for room in dungeon.rooms:
            assert "room_" in room.room_id

    def test_generate_dungeon_seed_reproducible(self):
        gen1 = ProceduralGenerator(rng=random.Random(99))
        gen2 = ProceduralGenerator(rng=random.Random(99))
        d1 = gen1.generate_dungeon(difficulty=5, region_id="r1", theme="ruins", seed=123)
        d2 = gen2.generate_dungeon(difficulty=5, region_id="r1", theme="ruins", seed=123)
        assert d1.name == d2.name
        assert len(d1.rooms) == len(d2.rooms)
        assert d1.rooms[0].x == d2.rooms[0].x

    def test_generate_dungeon_with_connect_to(self):
        gen = ProceduralGenerator(rng=random.Random(1))
        dungeon = gen.generate_dungeon(
            difficulty=4,
            region_id="r1",
            theme="mine",
            connect_to="oakhaven",
        )
        assert dungeon.exit_location_id == "oakhaven"
        # The exit room should have a connection to oakhaven
        for room in dungeon.rooms:
            for conn in room.connections:
                if conn.get("type") == "exit":
                    assert conn["to"] == "oakhaven"

    def test_generate_dungeon_themes(self):
        for theme in ["cave", "ruins", "mine", "fortress"]:
            gen = ProceduralGenerator(rng=random.Random(0))
            dungeon = gen.generate_dungeon(difficulty=2, theme=theme)
            assert dungeon.theme == theme
            assert dungeon.name.startswith("The ")

    def test_generate_encounter_combat(self):
        gen = ProceduralGenerator(rng=random.Random(7))
        enc = gen.generate_encounter(danger_level=3, encounter_type="combat")
        assert enc.encounter_type == "combat"
        assert enc.difficulty >= 1
        assert len(enc.enemies) >= 1

    def test_generate_encounter_social(self):
        gen = ProceduralGenerator(rng=random.Random(7))
        enc = gen.generate_encounter(danger_level=2, encounter_type="social")
        assert enc.encounter_type == "social"
        assert len(enc.skill_checks) >= 1

    def test_generate_encounter_trap(self):
        gen = ProceduralGenerator(rng=random.Random(7))
        enc = gen.generate_encounter(danger_level=4, encounter_type="trap")
        assert enc.encounter_type == "trap"
        assert len(enc.skill_checks) >= 1

    def test_generate_encounter_treasure(self):
        gen = ProceduralGenerator(rng=random.Random(7))
        enc = gen.generate_encounter(danger_level=2, encounter_type="treasure")
        assert enc.encounter_type == "treasure"
        assert enc.rewards["xp"] > 0

    def test_generate_encounter_random_type(self):
        gen = ProceduralGenerator(rng=random.Random(7))
        enc = gen.generate_encounter(danger_level=1)
        assert enc.encounter_type in ENCOUNTER_TEMPLATES

    def test_generate_encounter_seed_reproducible(self):
        gen1 = ProceduralGenerator(rng=random.Random(11))
        gen2 = ProceduralGenerator(rng=random.Random(11))
        e1 = gen1.generate_encounter(danger_level=3, seed=55)
        e2 = gen2.generate_encounter(danger_level=3, seed=55)
        assert e1.title == e2.title
        assert e1.description == e2.description

    def test_generate_loot_table_cave(self):
        gen = ProceduralGenerator(rng=random.Random(3))
        table = gen.generate_loot_table(difficulty=4, theme="cave")
        assert table.id.startswith("proc_loot_")
        assert table.metadata["theme"] == "cave"
        assert table.metadata["difficulty"] == 4
        assert len(table.entries) > 0
        assert table.min_drops >= 1
        assert table.max_drops >= table.min_drops

    def test_generate_loot_table_ruins(self):
        gen = ProceduralGenerator(rng=random.Random(3))
        table = gen.generate_loot_table(difficulty=8, theme="ruins")
        assert table.metadata["theme"] == "ruins"
        assert table.metadata["difficulty"] == 8
        # Should have epic entry at difficulty 8
        rarities = [e.rarity for e in table._entry_objects()]
        assert "epic" in rarities

    def test_generate_loot_table_fortress(self):
        gen = ProceduralGenerator(rng=random.Random(3))
        table = gen.generate_loot_table(difficulty=10, theme="fortress")
        rarities = [e.rarity for e in table._entry_objects()]
        assert "legendary" in rarities

    def test_generate_loot_table_generic(self):
        gen = ProceduralGenerator(rng=random.Random(3))
        table = gen.generate_loot_table(difficulty=1, theme="generic")
        assert table.metadata["theme"] == "generic"
        assert len(table.entries) > 0

    def test_generate_loot_table_seed_reproducible(self):
        gen1 = ProceduralGenerator(rng=random.Random(5))
        gen2 = ProceduralGenerator(rng=random.Random(5))
        t1 = gen1.generate_loot_table(difficulty=3, theme="cave", seed=77)
        t2 = gen2.generate_loot_table(difficulty=3, theme="cave", seed=77)
        assert t1.id == t2.id
        assert t1.entries == t2.entries

    def test_integrate_dungeon(self):
        gen = ProceduralGenerator(rng=random.Random(9))
        dungeon = gen.generate_dungeon(difficulty=2, region_id="r1", theme="cave", connect_to="town")

        loc_dir = LocationDirectory()
        world_map = WorldMap(
            regions=[Region(id="r1", name="Region")],
            locations=[Location(id="town", name="Town", region_id="r1")],
        )

        result = gen.integrate_dungeon(dungeon, loc_dir, world_map, connect_to="town")
        assert result["integrated"] is True
        assert result["name"] == dungeon.name
        assert loc_dir.get_location(dungeon.dungeon_id) is not None
        assert world_map.get_location(dungeon.dungeon_id) is not None

        # Check routes were added
        routes_from_dungeon = world_map.get_routes_from(dungeon.dungeon_id)
        assert len(routes_from_dungeon) >= 1

    def test_enemy_templates_by_level(self):
        for level in range(1, 11):
            key = f"level_{level}"
            assert key in ENEMY_TEMPLATES
            assert len(ENEMY_TEMPLATES[key]) > 0

    def test_dungeon_themes_exist(self):
        assert "cave" in DUNGEON_THEMES
        assert "ruins" in DUNGEON_THEMES
        assert "mine" in DUNGEON_THEMES
        assert "fortress" in DUNGEON_THEMES


if __name__ == "__main__":
    import random

    suites = [
        TestRoom,
        TestDungeon,
        TestEncounter,
        TestProceduralGenerator,
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
