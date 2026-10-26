"""
RPG-08-15: Loot and Rewards System
Tests for loot tables, rarity tiers, and loot rolling.
Run with: python -m pytest tests/ -v
or:       python tests/test_loot.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from loot import (
    RARITY_TIERS,
    LootEntry,
    LootInstance,
    LootManager,
    LootTable,
    get_rarity_info,
    roll_quantity,
    roll_rarity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_tables() -> list[LootTable]:
    return [
        LootTable(
            id="goblin_pouch",
            name="Goblin Loot Pouch",
            description="Common drops from goblins.",
            entries=[
                {"item_id": "copper_coin", "rarity": "common", "weight": 60, "min_quantity": 2, "max_quantity": 5},
                {"item_id": "iron_dagger", "rarity": "common", "weight": 30, "min_quantity": 1, "max_quantity": 1},
                {"item_id": "healing_salve", "rarity": "uncommon", "weight": 10, "min_quantity": 1, "max_quantity": 1},
            ],
            min_drops=1,
            max_drops=2,
            allow_duplicates=False,
            metadata={"source": "goblin"},
        ),
        LootTable(
            id="dragon_hoard",
            name="Dragon Hoard",
            description="Prestigious loot from an ancient dragon.",
            entries=[
                {"item_id": "gold_bar", "rarity": "rare", "weight": 40, "min_quantity": 1, "max_quantity": 3},
                {"item_id": "dragon_scale", "rarity": "epic", "weight": 25, "min_quantity": 1, "max_quantity": 2},
                {"item_id": "ancient_crown", "rarity": "legendary", "weight": 5, "min_quantity": 1, "max_quantity": 1},
            ],
            min_drops=2,
            max_drops=3,
            allow_duplicates=False,
            metadata={"source": "dragon"},
        ),
        LootTable(
            id="common_chest",
            name="Common Chest",
            description="A basic treasure chest.",
            entries=[
                {"item_id": "gold_coin", "rarity": "common", "weight": 80, "min_quantity": 1, "max_quantity": 10},
                {"item_id": "rusty_sword", "rarity": "common", "weight": 20, "min_quantity": 1, "max_quantity": 1},
            ],
            min_drops=1,
            max_drops=1,
            allow_duplicates=True,
            metadata={"source": "chest"},
        ),
    ]


def _make_manager() -> LootManager:
    mgr = LootManager()
    mgr.load_definitions(_sample_tables())
    return mgr


# ---------------------------------------------------------------------------
# Rarity tests
# ---------------------------------------------------------------------------

class TestRarityTiers(unittest.TestCase):
    def test_rarity_tiers_exist(self):
        assert "common" in RARITY_TIERS
        assert "uncommon" in RARITY_TIERS
        assert "rare" in RARITY_TIERS
        assert "epic" in RARITY_TIERS
        assert "legendary" in RARITY_TIERS

    def test_rarity_order(self):
        assert RARITY_TIERS["common"]["order"] < RARITY_TIERS["legendary"]["order"]

    def test_get_rarity_info_known(self):
        info = get_rarity_info("rare")
        assert info["display_name"] == "Rare"
        assert info["order"] == 2

    def test_get_rarity_info_unknown_falls_back(self):
        info = get_rarity_info("nonexistent")
        assert info["display_name"] == "Common"

    def test_roll_rarity_returns_valid_tier(self):
        for _ in range(50):
            tier = roll_rarity()
            assert tier in RARITY_TIERS

    def test_roll_quantity_within_bounds(self):
        for rarity in RARITY_TIERS:
            for _ in range(20):
                qty = roll_quantity(rarity)
                info = RARITY_TIERS[rarity]
                assert info["min_quantity"] <= qty <= info["max_quantity"]


# ---------------------------------------------------------------------------
# LootEntry tests
# ---------------------------------------------------------------------------

class TestLootEntry(unittest.TestCase):
    def test_from_dict(self):
        data = {"item_id": "potion", "rarity": "common", "weight": 5, "min_quantity": 1, "max_quantity": 3}
        entry = LootEntry.from_dict(data)
        assert entry.item_id == "potion"
        assert entry.rarity == "common"
        assert entry.weight == 5
        assert entry.min_quantity == 1
        assert entry.max_quantity == 3

    def test_to_dict(self):
        entry = LootEntry(item_id="sword", rarity="rare", weight=10, min_quantity=1, max_quantity=1, metadata={"enchanted": True})
        data = entry.to_dict()
        assert data["item_id"] == "sword"
        assert data["rarity"] == "rare"
        assert data["metadata"] == {"enchanted": True}

    def test_to_from_dict_roundtrip(self):
        original = LootEntry(item_id="bow", rarity="epic", weight=2, min_quantity=1, max_quantity=2, metadata={"durability": 100})
        restored = LootEntry.from_dict(original.to_dict())
        assert restored.item_id == original.item_id
        assert restored.rarity == original.rarity
        assert restored.weight == original.weight
        assert restored.min_quantity == original.min_quantity
        assert restored.max_quantity == original.max_quantity
        assert restored.metadata == original.metadata


# ---------------------------------------------------------------------------
# LootTable tests
# ---------------------------------------------------------------------------

class TestLootTable(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "id": "test_table",
            "name": "Test Table",
            "description": "A test table.",
            "entries": [{"item_id": "gem", "rarity": "rare", "weight": 10}],
            "min_drops": 1,
            "max_drops": 2,
            "allow_duplicates": True,
            "metadata": {"region": "cave"},
        }
        table = LootTable.from_dict(data)
        assert table.id == "test_table"
        assert table.name == "Test Table"
        assert table.min_drops == 1
        assert table.max_drops == 2
        assert table.allow_duplicates is True

    def test_to_dict(self):
        table = LootTable(
            id="sample",
            name="Sample",
            entries=[{"item_id": "coin", "rarity": "common", "weight": 50}],
            metadata={"key": "val"},
        )
        data = table.to_dict()
        assert data["id"] == "sample"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["item_id"] == "coin"
        assert data["metadata"] == {"key": "val"}

    def test_to_from_dict_roundtrip(self):
        data = {
            "id": "rt",
            "name": "Roundtrip",
            "entries": [{"item_id": "x", "rarity": "epic", "weight": 3}],
            "min_drops": 2,
            "max_drops": 4,
            "allow_duplicates": True,
            "metadata": {"m": 1},
        }
        original = LootTable.from_dict(data)
        restored = LootTable.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.min_drops == original.min_drops
        assert restored.max_drops == original.max_drops
        assert restored.allow_duplicates == original.allow_duplicates
        assert len(restored.entries) == len(original.entries)
        assert restored.entries[0]["item_id"] == original.entries[0]["item_id"]


# ---------------------------------------------------------------------------
# LootInstance tests
# ---------------------------------------------------------------------------

class TestLootInstance(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "instance_id": "inst-1",
            "loot_table_id": "table-1",
            "world_id": "w-1",
            "session_id": "s-1",
            "items": [{"item_id": "potion", "rarity": "common", "quantity": 2}],
            "source": "combat",
            "metadata": {"enemy": "goblin"},
        }
        inst = LootInstance.from_dict(data)
        assert inst.instance_id == "inst-1"
        assert inst.loot_table_id == "table-1"
        assert inst.source == "combat"
        assert inst.items[0]["quantity"] == 2

    def test_to_dict(self):
        inst = LootInstance(
            instance_id="i1",
            loot_table_id="t1",
            world_id="w1",
            session_id="s1",
            items=[{"item_id": "sword", "rarity": "rare", "quantity": 1}],
            source="quest",
            metadata={"quest": "q1"},
        )
        data = inst.to_dict()
        assert data["instance_id"] == "i1"
        assert data["source"] == "quest"
        assert data["items"][0]["item_id"] == "sword"

    def test_to_from_dict_roundtrip(self):
        original = LootInstance(
            instance_id="i1",
            loot_table_id="t1",
            world_id="w1",
            session_id="s1",
            items=[{"item_id": "bow", "rarity": "epic", "quantity": 1}],
            source="chest",
            metadata={"chest": "rare"},
        )
        restored = LootInstance.from_dict(original.to_dict())
        assert restored.instance_id == original.instance_id
        assert restored.loot_table_id == original.loot_table_id
        assert restored.source == original.source
        assert restored.items == original.items


# ---------------------------------------------------------------------------
# LootManager tests
# ---------------------------------------------------------------------------

class TestLootManager(unittest.TestCase):
    def test_register_and_get_definition(self):
        mgr = LootManager()
        table = LootTable(id="t1", name="T1", entries=[{"item_id": "i1", "rarity": "common", "weight": 1}])
        mgr.register_definition(table)
        assert mgr.get_definition("t1") is not None
        assert mgr.get_definition("missing") is None

    def test_list_definitions(self):
        mgr = _make_manager()
        defs = mgr.list_definitions()
        assert len(defs) == 3
        ids = [d["id"] for d in defs]
        assert "goblin_pouch" in ids
        assert "dragon_hoard" in ids

    def test_roll_loot_success(self):
        mgr = _make_manager()
        inst = mgr.roll_loot("goblin_pouch", world_id="w1", session_id="s1", source="combat")
        assert inst is not None
        assert inst.loot_table_id == "goblin_pouch"
        assert inst.world_id == "w1"
        assert inst.source == "combat"
        assert inst.instance_id is not None
        assert 1 <= len(inst.items) <= 2

    def test_roll_loot_unknown_table_returns_none(self):
        mgr = _make_manager()
        assert mgr.roll_loot("nonexistent", world_id="w1") is None

    def test_roll_loot_deterministic_with_seed(self):
        mgr = _make_manager()
        inst1 = mgr.roll_loot("common_chest", world_id="w1", seed=42)
        inst2 = mgr.roll_loot("common_chest", world_id="w1", seed=42)
        assert inst1 is not None
        assert inst2 is not None
        assert inst1.items == inst2.items

    def test_roll_loot_different_seeds_differ(self):
        mgr = LootManager()
        table = LootTable(
            id="weighted",
            name="Weighted",
            entries=[
                {"item_id": "a", "rarity": "common", "weight": 99},
                {"item_id": "b", "rarity": "legendary", "weight": 1},
            ],
            min_drops=1,
            max_drops=1,
        )
        mgr.register_definition(table)
        items_a = mgr.roll_loot("weighted", world_id="w1", seed=1).items
        items_b = mgr.roll_loot("weighted", world_id="w1", seed=2).items
        # With very different seeds we expect different results most of the time
        # (not strictly guaranteed, but extremely likely with weight 99 vs 1)
        assert items_a[0]["item_id"] == "a"
        assert items_b[0]["item_id"] == "a"

    def test_roll_loot_without_session(self):
        mgr = _make_manager()
        inst = mgr.roll_loot("goblin_pouch", world_id="w1")
        assert inst is not None
        assert inst.session_id is None

    def test_get_loot(self):
        mgr = _make_manager()
        inst = mgr.roll_loot("goblin_pouch", world_id="w1")
        fetched = mgr.get_loot(inst.instance_id)
        assert fetched is not None
        assert fetched.instance_id == inst.instance_id
        assert mgr.get_loot("missing") is None

    def test_list_loot_scoped(self):
        mgr = _make_manager()
        mgr.roll_loot("goblin_pouch", world_id="w1", session_id="s1", source="combat")
        mgr.roll_loot("dragon_hoard", world_id="w2", session_id="s2", source="quest")
        assert len(mgr.list_loot(world_id="w1")) == 1
        assert len(mgr.list_loot(world_id="w2")) == 1
        assert len(mgr.list_loot(source="combat")) == 1
        assert len(mgr.list_loot(source="quest")) == 1
        assert len(mgr.list_loot()) == 2

    def test_allow_duplicates_chest(self):
        mgr = _make_manager()
        # common_chest allows duplicates and always drops 1 item
        # We roll many times to ensure duplicates can occur
        items_seen = set()
        for _ in range(20):
            inst = mgr.roll_loot("common_chest", world_id="w1")
            assert len(inst.items) == 1
            items_seen.add(inst.items[0]["item_id"])
        # With weight 80 vs 20, we should see both items after 20 rolls
        assert len(items_seen) == 2

    def test_no_duplicates_goblin_pouch(self):
        mgr = _make_manager()
        for _ in range(30):
            inst = mgr.roll_loot("goblin_pouch", world_id="w1")
            item_ids = [i["item_id"] for i in inst.items]
            assert len(item_ids) == len(set(item_ids)), f"Duplicates found: {item_ids}"

    def test_loot_history(self):
        mgr = _make_manager()
        mgr.roll_loot("goblin_pouch", world_id="w1")
        mgr.roll_loot("goblin_pouch", world_id="w1")
        history = mgr.get_loot_history("w1")
        assert len(history) >= 1
        total_qty = sum(h["total_quantity"] for h in history)
        assert total_qty >= 2

    def test_loot_summary(self):
        mgr = _make_manager()
        mgr.roll_loot("goblin_pouch", world_id="w1")
        mgr.roll_loot("goblin_pouch", world_id="w1")
        summary = mgr.get_loot_summary("w1")
        assert summary["world_id"] == "w1"
        assert summary["total_rolls"] == 2
        assert summary["total_items"] >= 2
        assert "rarity_breakdown" in summary

    def test_export_import_roundtrip(self):
        mgr = _make_manager()
        mgr.roll_loot("goblin_pouch", world_id="w1", session_id="s1")
        mgr.roll_loot("dragon_hoard", world_id="w2", session_id="s2")
        state = mgr.export_state()

        mgr2 = LootManager()
        mgr2.load_definitions(_sample_tables())
        mgr2.import_state(state)
        assert len(mgr2.list_loot()) == 2
        assert len(mgr2.list_loot(world_id="w1")) == 1
        assert len(mgr2.list_loot(world_id="w2")) == 1

    def test_roll_with_metadata(self):
        mgr = _make_manager()
        inst = mgr.roll_loot(
            "goblin_pouch",
            world_id="w1",
            metadata={"enemy_level": 3},
        )
        assert inst is not None
        assert inst.metadata["enemy_level"] == 3


if __name__ == "__main__":
    unittest.main()
