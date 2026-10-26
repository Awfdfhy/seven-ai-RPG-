"""
RPG-12-04: Procedural Content Generation

Provides random dungeon generation, encounter generation, and themed
loot table creation that integrates with the existing world map,
location directory, and loot systems.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from locations import LocationDirectory, LocationDirectoryEntry
from loot import LootEntry, LootTable
from world_map import Location, TravelRoute

# ---------------------------------------------------------------------------
# Dungeon Theme Definitions
# ---------------------------------------------------------------------------

DUNGEON_THEMES: dict[str, dict[str, Any]] = {
    "cave": {
        "adjectives": ["Dark", "Echoing", "Damp", "Crystal", "Fungal"],
        "nouns": ["Cavern", "Grotto", "Hollow", "Tunnel", "Chamber"],
        "room_types": ["cavern", "tunnel", "pool", "fungal_garden", "crystal_room"],
        "enemy_templates": {
            1: ["bat", "spider", "goblin_scout", "slime"],
            2: ["giant_bat", "cave_spider", "kobold", "giant_rat"],
            3: ["troll", "ogre", "dark_mage", "shadow"],
            4: ["vampire_spawn", "hell_hound", "wight"],
            5: ["giant", "chimera", "mummy"],
            6: ["frost_troll", "fire_elemental", "ettin"],
            7: ["young_dragon", "stone_golem", "medusa"],
            8: ["adult_dragon", "beholder", "naga"],
            9: ["pit_fiend", "lich"],
            10: ["ancient_dragon", "tarrasque"],
        },
        "trap_templates": ["rockslide", "poison_gas", "pit", "arrow_volley"],
    },
    "ruins": {
        "adjectives": ["Ancient", "Crumbling", "Forgotten", "Sunken", "Overgrown"],
        "nouns": ["Temple", "Spire", "Palace", "Sanctum", "Catacomb"],
        "room_types": ["shrine", "hall", "crypt", "library", "throne_room"],
        "enemy_templates": {
            1: ["skeleton", "zombie", "ghost", "spider"],
            2: ["skeleton_warrior", "ghoul", "wraith"],
            3: ["wraith", "dark_mage", "construct"],
            4: ["vampire_spawn", "shadow", "wight"],
            5: ["mummy", "specter", "drider"],
            6: ["fire_elemental", "archmage", "stone_golem"],
            7: ["young_dragon", "medusa", "harpy"],
            8: ["adult_dragon", "beholder", "naga"],
            9: ["pit_fiend", "lich", "kraken"],
            10: ["ancient_dragon", "tarrasque", "void_lord"],
        },
        "trap_templates": ["curse", "spike_trap", "collapse", "teleport"],
    },
    "mine": {
        "adjectives": ["Deep", "Smoldering", "Crystal", "Abandoned", "Collapsed"],
        "nouns": ["Shaft", "Vein", "Deposit", "Tunnel", "Chamber"],
        "room_types": ["shaft", "vein_room", "flooded_passage", "ore_chamber", "workshop"],
        "enemy_templates": {
            1: ["kobold", "giant_rat", "bat", "slime"],
            2: ["dwarf_ghost", "giant_spider", "fire_elemental"],
            3: ["golem", "dark_mage", "ogre"],
            4: ["hell_hound", "shadow", "wraith"],
            5: ["giant", "chimera", "mummy"],
            6: ["frost_troll", "ettin", "archmage"],
            7: ["young_dragon", "stone_golem", "medusa"],
            8: ["adult_dragon", "beholder", "naga"],
            9: ["pit_fiend", "lich"],
            10: ["ancient_dragon", "tarrasque"],
        },
        "trap_templates": ["gas_leak", "flood", "collapse", "lava_flow"],
    },
    "fortress": {
        "adjectives": ["Shadowed", "Haunted", "Iron", "Cursed", "Storm"],
        "nouns": ["Keep", "Bastion", "Citadel", "Fortress", "Watchtower"],
        "room_types": ["barracks", "armory", "torture_chamber", "throne_room", "dungeon_cell"],
        "enemy_templates": {
            1: ["guard", "kobold", "rat", "slime"],
            2: ["skeleton", "bandit", "wolf", "dark_mage"],
            3: ["ogre", "troll", "wraith", "construct"],
            4: ["vampire_spawn", "hell_hound", "wight", "shadow"],
            5: ["giant", "chimera", "mummy", "drider"],
            6: ["fire_elemental", "ettin", "archmage", "stone_golem"],
            7: ["young_dragon", "medusa", "harpy", "minotaur"],
            8: ["adult_dragon", "beholder", "naga", "salamander"],
            9: ["pit_fiend", "lich"],
            10: ["ancient_dragon", "tarrasque", "void_lord"],
        },
        "trap_templates": ["alarm", "portcullis", "fire_trap", "pitfall"],
    },
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class Room:
    """One room in a procedurally generated dungeon."""

    room_id: str
    name: str
    room_type: str
    x: int
    y: int
    width: int = 3
    height: int = 3
    danger_level: int = 1
    connections: list[dict[str, Any]] = field(default_factory=list)
    encounter: dict[str, Any] | None = None
    loot_table_id: str | None = None
    trap: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "name": self.name,
            "room_type": self.room_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "danger_level": self.danger_level,
            "connections": [dict(c) for c in self.connections],
            "encounter": dict(self.encounter) if self.encounter else None,
            "loot_table_id": self.loot_table_id,
            "trap": dict(self.trap) if self.trap else None,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Room:
        return Room(
            room_id=data["room_id"],
            name=data.get("name", ""),
            room_type=data.get("room_type", "room"),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            width=int(data.get("width", 3)),
            height=int(data.get("height", 3)),
            danger_level=int(data.get("danger_level", 1)),
            connections=[dict(c) for c in data.get("connections", [])],
            encounter=data.get("encounter"),
            loot_table_id=data.get("loot_table_id"),
            trap=data.get("trap"),
        )


@dataclass
class Dungeon:
    """A fully generated dungeon instance."""

    dungeon_id: str
    name: str
    description: str
    region_id: str
    theme: str
    difficulty: int
    seed: int
    rooms: list[Room] = field(default_factory=list)
    x: int = 0
    y: int = 0
    danger_level: int = 1
    exit_location_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dungeon_id": self.dungeon_id,
            "name": self.name,
            "description": self.description,
            "region_id": self.region_id,
            "theme": self.theme,
            "difficulty": self.difficulty,
            "seed": self.seed,
            "rooms": [r.to_dict() for r in self.rooms],
            "x": self.x,
            "y": self.y,
            "danger_level": self.danger_level,
            "exit_location_id": self.exit_location_id,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Dungeon:
        return Dungeon(
            dungeon_id=data["dungeon_id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            region_id=data.get("region_id", ""),
            theme=data.get("theme", "generic"),
            difficulty=int(data.get("difficulty", 1)),
            seed=int(data.get("seed", 0)),
            rooms=[Room.from_dict(r) for r in data.get("rooms", [])],
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            danger_level=int(data.get("danger_level", 1)),
            exit_location_id=data.get("exit_location_id", ""),
            metadata=dict(data.get("metadata", {})),
        )

    def to_location_entry(self) -> LocationDirectoryEntry:
        """Convert this dungeon into a LocationDirectoryEntry for the world map."""
        return LocationDirectoryEntry(
            id=self.dungeon_id,
            name=self.name,
            region_id=self.region_id,
            description=self.description,
            location_type="dungeon",
            x=self.x,
            y=self.y,
            danger_level=self.danger_level,
            connections=[{"to": self.exit_location_id, "distance": 1, "travel_time_hours": 1}]
            if self.exit_location_id
            else [],
        )

    def to_world_location(self) -> Location:
        """Convert this dungeon into a world_map.Location."""
        return Location(
            id=self.dungeon_id,
            name=self.name,
            region_id=self.region_id,
            description=self.description,
            location_type="dungeon",
            x=self.x,
            y=self.y,
            danger_level=self.danger_level,
            connections=[{"to": self.exit_location_id, "distance": 1, "travel_time_hours": 1}]
            if self.exit_location_id
            else [],
        )


@dataclass
class Encounter:
    """A procedurally generated encounter."""

    encounter_id: str
    encounter_type: str
    title: str
    description: str
    difficulty: int
    enemies: list[str] = field(default_factory=list)
    npc_id: str | None = None
    skill_checks: list[dict[str, Any]] = field(default_factory=list)
    rewards: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "encounter_id": self.encounter_id,
            "encounter_type": self.encounter_type,
            "title": self.title,
            "description": self.description,
            "difficulty": self.difficulty,
            "enemies": list(self.enemies),
            "npc_id": self.npc_id,
            "skill_checks": [dict(s) for s in self.skill_checks],
            "rewards": dict(self.rewards),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Encounter:
        return Encounter(
            encounter_id=data["encounter_id"],
            encounter_type=data.get("encounter_type", "combat"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            difficulty=int(data.get("difficulty", 1)),
            enemies=list(data.get("enemies", [])),
            npc_id=data.get("npc_id"),
            skill_checks=[dict(s) for s in data.get("skill_checks", [])],
            rewards=dict(data.get("rewards", {})),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Encounter & Loot Templates
# ---------------------------------------------------------------------------

ENCOUNTER_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "combat": [
        {
            "title": "Ambush!",
            "description": "Hostile creatures emerge from the shadows.",
            "skill_checks": [],
        },
        {
            "title": "Standing Guard",
            "description": "Enemy guards block the path forward.",
            "skill_checks": [],
        },
        {
            "title": "Pack Hunters",
            "description": "A hungry pack of beasts circles the party.",
            "skill_checks": [],
        },
    ],
    "social": [
        {
            "title": "Wandering Merchant",
            "description": "A traveling merchant offers goods and information.",
            "skill_checks": [{"type": "persuasion", "dc": 12}],
        },
        {
            "title": "Lost Traveler",
            "description": "A frightened traveler begs for help.",
            "skill_checks": [{"type": "insight", "dc": 10}],
        },
    ],
    "trap": [
        {
            "title": "Hidden Trap",
            "description": "The floor gives way to reveal a spike pit.",
            "skill_checks": [{"type": "perception", "dc": 14}],
        },
        {
            "title": "Poison Dart",
            "description": "A pressure plate triggers a volley of poisoned darts.",
            "skill_checks": [{"type": "reflex", "dc": 13}],
        },
    ],
    "puzzle": [
        {
            "title": "Ancient Runes",
            "description": "Mysterious runes on the wall need to be deciphered.",
            "skill_checks": [{"type": "arcana", "dc": 15}],
        },
        {
            "title": "Locked Door",
            "description": "A heavy door blocks the way, requiring a clever solution.",
            "skill_checks": [{"type": "thievery", "dc": 14}],
        },
    ],
    "treasure": [
        {
            "title": "Hidden Cache",
            "description": "A hidden compartment contains forgotten treasure.",
            "skill_checks": [{"type": "perception", "dc": 11}],
        },
        {
            "title": "Ancient Urn",
            "description": "An ornate urn sits in the corner, potentially valuable.",
            "skill_checks": [{"type": "history", "dc": 12}],
        },
    ],
}

ENEMY_TEMPLATES: dict[str, list[str]] = {
    "level_1": ["rat", "bat", "spider", "goblin_scout", "slime"],
    "level_2": ["wolf", "kobold", "skeleton", "zombie", "giant_rat"],
    "level_3": ["ogre", "troll", "wraith", "dark_mage", "bandit_captain"],
    "level_4": ["vampire_spawn", "hell_hound", "shadow", "wight", "drider"],
    "level_5": ["giant", "chimera", "mummy", "specter", "troll_brute"],
    "level_6": ["frost_troll", "fire_elemental", "ettin", "black_dragon_wyrmling", "archmage"],
    "level_7": ["young_dragon", "stone_golem", "medusa", "harpy", "minotaur"],
    "level_8": ["adult_dragon", "beholder", "naga", "salamander", "unicorn_corrupted"],
    "level_9": ["pit_fiend", "lich", "kraken", "elder_evil", "demigod"],
    "level_10": ["ancient_dragon", "tarrasque", "god_touched", "void_lord", "celestial_tyrant"],
}


# ---------------------------------------------------------------------------
# Procedural Generation Engine
# ---------------------------------------------------------------------------

class ProceduralGenerator:
    """
    Generates random dungeons, encounters, and themed loot tables.

    All generation is seeded for reproducibility when needed.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    # ------------------------------------------------------------------
    # Dungeon Generation
    # ------------------------------------------------------------------

    def generate_dungeon(
        self,
        difficulty: int = 1,
        region_id: str = "",
        theme: str = "cave",
        seed: int | None = None,
        room_count: int = 8,
        connect_to: str = "",
    ) -> Dungeon:
        """
        Generate a random dungeon with interconnected rooms.

        Args:
            difficulty: Overall threat level (1-10).
            region_id: Parent region identifier.
            theme: Dungeon theme (cave, ruins, mine, fortress).
            seed: Optional RNG seed for reproducibility.
            room_count: Number of rooms to generate.
            connect_to: Optional existing location_id to connect the dungeon exit to.

        Returns:
            A fully populated Dungeon instance.
        """
        if seed is not None:
            self.rng = random.Random(seed)
        else:
            self.rng = random.Random()

        theme_data = DUNGEON_THEMES.get(theme, DUNGEON_THEMES["cave"])
        dungeon_id = f"proc_dungeon_{self.rng.randint(0, 0xffffffff):08x}"

        # Pick name
        adj = self.rng.choice(theme_data["adjectives"])
        noun = self.rng.choice(theme_data["nouns"])
        name = f"The {adj} {noun}"

        # Generate rooms
        rooms = self._generate_rooms(room_count, difficulty, theme_data)

        # Pick exit room (the one closest to the entrance / lowest index)
        exit_room = rooms[0]
        exit_room.connections.append({"to": connect_to, "type": "exit"})

        return Dungeon(
            dungeon_id=dungeon_id,
            name=name,
            description=f"A procedurally generated {theme} dungeon of difficulty {difficulty}.",
            region_id=region_id,
            theme=theme,
            difficulty=difficulty,
            seed=seed if seed is not None else 0,
            rooms=rooms,
            x=exit_room.x,
            y=exit_room.y,
            danger_level=difficulty,
            exit_location_id=connect_to,
        )

    def _generate_rooms(self, count: int, difficulty: int, theme_data: dict) -> list[Room]:
        """Generate a set of non-overlapping rooms on a grid."""
        rooms: list[Room] = []

        for i in range(count):
            rx, ry, rw, rh = 0, 0, 3, 3
            for _ in range(50):
                rx = self.rng.randint(0, 40)
                ry = self.rng.randint(0, 40)
                rw = self.rng.randint(2, 5)
                rh = self.rng.randint(2, 5)

                overlaps = False
                for other in rooms:
                    if not (
                        rx + rw < other.x
                        or rx > other.x + other.width
                        or ry + rh < other.y
                        or ry > other.y + other.height
                    ):
                        overlaps = True
                        break

                if not overlaps:
                    break

            room_type = self.rng.choice(theme_data["room_types"])
            room = Room(
                room_id=f"room_{i}",
                name=f"{room_type.replace('_', ' ').title()}",
                room_type=room_type,
                x=rx,
                y=ry,
                width=rw,
                height=rh,
                danger_level=max(1, difficulty + self.rng.randint(-1, 1)),
            )
            rooms.append(room)

        self._connect_rooms(rooms)
        return rooms

    def _connect_rooms(self, rooms: list[Room]) -> None:
        """Ensure all rooms are reachable by connecting nearby rooms."""
        if len(rooms) < 2:
            return

        for i, room in enumerate(rooms):
            nearest = None
            nearest_dist = float("inf")
            for j, other in enumerate(rooms):
                if i == j:
                    continue
                dist = abs(room.x - other.x) + abs(room.y - other.y)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = other

            if nearest:
                room.connections.append(
                    {
                        "to": nearest.room_id,
                        "type": "corridor",
                        "distance": max(1, nearest_dist),
                    }
                )

    # ------------------------------------------------------------------
    # Encounter Generation
    # ------------------------------------------------------------------

    def generate_encounter(
        self,
        danger_level: int = 1,
        encounter_type: str | None = None,
        seed: int | None = None,
    ) -> Encounter:
        """
        Generate a random encounter appropriate for the given danger level.

        Args:
            danger_level: Threat rating (1-10).
            encounter_type: Optional specific type (combat, social, trap, puzzle, treasure).
            seed: Optional RNG seed.

        Returns:
            A populated Encounter instance.
        """
        if seed is not None:
            self.rng = random.Random(seed)
        else:
            self.rng = random.Random()

        if encounter_type is None:
            types = ["combat", "combat", "combat", "social", "trap", "puzzle", "treasure"]
            encounter_type = self.rng.choice(types)

        encounter_id = f"enc_{self.rng.randint(0, 0xffffffff):08x}"
        templates = ENCOUNTER_TEMPLATES.get(encounter_type, ENCOUNTER_TEMPLATES["combat"])
        template = self.rng.choice(templates)

        scaled_difficulty = max(1, danger_level + self.rng.randint(-1, 1))
        enemies: list[str] = []

        if encounter_type == "combat":
            num_enemies = self.rng.randint(1, min(4, 1 + danger_level // 2))
            level_key = f"level_{min(10, scaled_difficulty)}"
            pool = ENEMY_TEMPLATES.get(level_key, ENEMY_TEMPLATES["level_1"])
            for _ in range(num_enemies):
                enemies.append(self.rng.choice(pool))

        return Encounter(
            encounter_id=encounter_id,
            encounter_type=encounter_type,
            title=template["title"],
            description=template["description"],
            difficulty=scaled_difficulty,
            enemies=enemies,
            skill_checks=[dict(s) for s in template.get("skill_checks", [])],
            rewards=self._generate_encounter_rewards(scaled_difficulty),
        )

    def _generate_encounter_rewards(self, difficulty: int) -> dict[str, Any]:
        """Generate rewards for an encounter."""
        return {
            "xp": difficulty * 50 + self.rng.randint(0, 50),
            "gold": difficulty * 10 + self.rng.randint(0, 10),
        }

    # ------------------------------------------------------------------
    # Loot Table Generation
    # ------------------------------------------------------------------

    def generate_loot_table(
        self,
        difficulty: int = 1,
        theme: str = "generic",
        seed: int | None = None,
    ) -> LootTable:
        """
        Generate a procedurally themed loot table.

        Args:
            difficulty: Threat level (1-10).
            theme: Theme key (cave, ruins, mine, fortress, generic).
            seed: Optional RNG seed.

        Returns:
            A LootTable instance ready to register with LootManager.
        """
        if seed is not None:
            self.rng = random.Random(seed)
        else:
            self.rng = random.Random()

        table_id = f"proc_loot_{self.rng.randint(0, 0xffffffff):08x}"

        entries: list[LootEntry] = []

        # Common base items
        common_items = [
            ("gold_coin", "common", 60, 1, max(1, difficulty * 3)),
            ("healing_potion", "common", 30, 1, 2),
        ]

        # Themed items
        themed_items = {
            "cave": [
                ("bat_wing", "common", 40, 1, 3),
                ("crystal_shard", "uncommon", 20, 1, 1),
                ("mushroom_spores", "common", 30, 1, 2),
            ],
            "ruins": [
                ("ancient_coin", "uncommon", 25, 1, 2),
                ("dusty_scroll", "rare", 10, 1, 1),
                ("bone_fragment", "common", 35, 1, 3),
            ],
            "mine": [
                ("iron_ore", "common", 45, 1, 4),
                ("ember_crystal", "uncommon", 20, 1, 1),
                ("pickaxe_head", "common", 25, 1, 1),
            ],
            "fortress": [
                ("iron_ingot", "common", 35, 1, 2),
                ("knight_insignia", "rare", 12, 1, 1),
                ("trophy_sword", "uncommon", 20, 1, 1),
            ],
        }

        items = common_items + themed_items.get(theme, [])

        # Higher difficulty adds rare/epic/legendary entries
        if difficulty >= 5:
            items.append((f"{theme}_gem", "rare", 15, 1, 1))
        if difficulty >= 8:
            items.append((f"{theme}_relic", "epic", 8, 1, 1))
        if difficulty >= 10:
            items.append((f"{theme}_artifact", "legendary", 3, 1, 1))

        for item_id, rarity, weight, min_q, max_q in items:
            entries.append(
                LootEntry(
                    item_id=item_id,
                    rarity=rarity,
                    weight=weight,
                    min_quantity=min_q,
                    max_quantity=max_q,
                )
            )

        min_drops = max(1, difficulty // 2)
        max_drops = max(2, difficulty)

        return LootTable(
            id=table_id,
            name=f"{theme.title()} Loot Table (Lvl {difficulty})",
            description=f"Procedurally generated loot for {theme} content.",
            entries=[e.to_dict() for e in entries],
            min_drops=min_drops,
            max_drops=max_drops,
            allow_duplicates=self.rng.random() > 0.5,
            metadata={"theme": theme, "difficulty": difficulty, "seed": seed if seed is not None else 0},
        )

    # ------------------------------------------------------------------
    # World Integration Helpers
    # ------------------------------------------------------------------

    def integrate_dungeon(
        self,
        dungeon: Dungeon,
        location_directory: LocationDirectory,
        world_map: Any,
        connect_to: str = "",
    ) -> dict[str, Any]:
        """
        Add a generated dungeon to the world map and location directory.

        Args:
            dungeon: The generated dungeon.
            location_directory: The LocationDirectory to update.
            world_map: The WorldMap to update.
            connect_to: Existing location to connect the dungeon exit to.

        Returns:
            Summary dict of what was added.
        """
        # Add to location directory
        location_directory.add_location(dungeon.to_location_entry())

        # Add to world map
        world_map._locations[dungeon.dungeon_id] = dungeon.to_world_location()

        # Add exit route
        if connect_to:
            world_map._routes.append(
                TravelRoute(
                    from_location_id=dungeon.dungeon_id,
                    to_location_id=connect_to,
                    distance=1,
                    travel_time_hours=1,
                )
            )
            world_map._routes.append(
                TravelRoute(
                    from_location_id=connect_to,
                    to_location_id=dungeon.dungeon_id,
                    distance=1,
                    travel_time_hours=1,
                )
            )

        return {
            "dungeon_id": dungeon.dungeon_id,
            "name": dungeon.name,
            "rooms": len(dungeon.rooms),
            "integrated": True,
        }
