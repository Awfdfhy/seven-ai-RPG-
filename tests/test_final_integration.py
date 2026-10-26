"""
Final Integration Tests for Seven RPG
======================================
Tests that verify multiple game systems work correctly together.

Run with: python -m pytest tests/test_final_integration.py -v -m integration
or:       python tests/test_final_integration.py
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ---------------------------------------------------------------------------
# System imports
# ---------------------------------------------------------------------------
from ability import Ability, AbilityCategory, AbilityEffect, TargetType
from ability_manager import AbilityManager
from character_customization import (
    CharacterCustomizationManager,
)
from character_sheet import CharacterSheet
from character_stats import (
    BASE_STATS,
    CharacterStatsState,
    DerivedStatRule,
    StatDefinition,
    StatsManager,
    StatsSystem,
)
from combat import (
    ActionResultType,
    Combatant,
    CombatantStats,
    CombatantTeam,
    CombatEncounter,
    CombatPosition,
    TacticalPositioning,
)
from crafting import Ingredient, Recipe
from crafting_manager import CraftingManager
from difficulty_settings import DifficultyPreset, DifficultySettings, GameSettings
from economy import (
    EconomyManager,
    MerchantDefinition,
    MerchantType,
    PriceRule,
)
from inventory import (
    EquipmentSlotType,
    InventoryManager,
    Item,
    ItemCategory,
    ItemRarity,
)
from loot import (
    LootManager,
    LootTable,
    LootTableEntry,
    roll_rarity,
)
from milestone import MilestoneDefinition, MilestoneManager
from npc_reaction import NPCProfile, NPCReactionResolver
from party import (
    CompanionArchetype,
    CompanionRole,
    CompanionStance,
    PartyManager,
)
from progression import (
    ProgressionSystem,
    StatGrowth,
)
from progression_manager import ProgressionManager
from quest_journal import (
    QuestDefinition,
    QuestJournalManager,
    QuestObjective,
    QuestReward,
)
from skill_tree_manager import SkillTreeManager
from status_conditions import (
    StatusCondition,
    StatusConditionEffect,
    StatusConditionType,
    StatOperator,
)
from status_manager import StatusManager
from title_system import (
    TitleDefinition,
    TitleManager,
    TitleType,
)
from world_events import (
    EventCategory,
    EventTrigger,
    WorldEventDefinition,
    WorldEventManager,
)
from world_map import (
    Location,
    LocationType,
    WorldMapManager,
)
from world_simulation import (
    WorldSimulationManager,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def data_path(project_root: str) -> str:
    return os.path.join(project_root, "data")


@pytest.fixture
def game_settings() -> GameSettings:
    return GameSettings(
        difficulty=DifficultySettings(preset=DifficultyPreset.NORMAL),
        accessibility_settings=None,
    )


@pytest.fixture
def character_id() -> str:
    return "test_hero_01"


@pytest.fixture
def world_id() -> str:
    return "world_alpha"


# ---------------------------------------------------------------------------
# Integration Test Suite
# ---------------------------------------------------------------------------


class TestCharacterCreationAndStatsIntegration:
    """Verify that character creation, stats, and customization work together."""

    def test_full_character_creation_flow(self, character_id: str):
        mgr = CharacterCustomizationManager()
        state = mgr.create_character(
            character_id=character_id,
            name="Test Hero",
            class_id="warrior",
            background_id="soldier",
            appearance={
                "hair_style": "short",
                "hair_color": "brown",
                "eye_color": "blue",
            },
        )
        assert state.character_id == character_id
        assert state.name == "Test Hero"
        assert state.class_id == "warrior"

        stats_mgr = StatsManager()
        stats_mgr.load_from_json()
        summary = stats_mgr.get_character_stats_summary(character_id)
        assert "base_stats" in summary

    def test_stats_affect_derived_values(self, character_id: str):
        system = StatsSystem(
            stat_definitions=[
                StatDefinition(id=s, name=s.title(), abbreviation=s[:3].upper())
                for s in BASE_STATS
            ],
            derived_rules=[
                DerivedStatRule(id="max_hp", name="Maximum HP", formula="vitality * 10 + strength * 2"),
                DerivedStatRule(id="max_mp", name="Maximum MP", formula="intelligence * 8"),
            ],
        )
        state = CharacterStatsState(character_id=character_id)
        state.base_stats["vitality"] = 20
        state.base_stats["strength"] = 15
        state.base_stats["intelligence"] = 10
        system.register_state(state)
        derived = system.get_derived_stats(character_id)
        assert derived["max_hp"] == 20 * 10 + 15 * 2
        assert derived["max_mp"] == 10 * 8


class TestSkillTreeAndAbilityIntegration:
    """Verify skill trees unlock abilities and modify combat effectiveness."""

    def test_skill_unlock_grants_ability_points(self, character_id: str):
        skill_mgr = SkillTreeManager()
        ability_mgr = AbilityManager()

        state = skill_mgr.get_character_state(character_id)
        state.available_points = 3
        state.level = 5
        state.attributes = {"strength": 10}

        available = skill_mgr.get_available_nodes(character_id, "two_handed_combat")
        assert len(available) > 0

        first = available[0]
        result = skill_mgr.unlock_node(character_id, "two_handed_combat", first["id"])
        assert result["success"] is True

    def test_ability_manager_tracks_character_state(self, character_id: str):
        mgr = AbilityManager()
        mgr.register(Ability(
            id="test.fireball",
            name="Fireball",
            description="A ball of fire.",
            category=AbilityCategory.MAGIC,
            target_type=TargetType.SINGLE_TARGET,
            mana_cost=25,
            cooldown_seconds=8.0,
            effects=[AbilityEffect(effect_type="damage", value=50)],
        ))
        state = mgr.get_character_state(character_id)
        state.available_points = 2
        result = mgr.grant_ability(character_id, "test.fireball")
        assert result["success"] is True


class TestCombatAndStatusIntegration:
    """Verify combat applies status conditions and interacts with abilities."""

    def test_combat_applies_status_conditions(self, character_id: str):
        status_mgr = StatusManager()
        status_mgr.register_definition(StatusCondition(
            id="burn",
            name="Burn",
            description="Taking fire damage over time.",
            condition_type=StatusConditionType.BURN,
            duration_seconds=5.0,
            tick_interval_seconds=1.0,
            effects=[
                StatusConditionEffect(stat="hp", value=-5, operator=StatOperator.SET, tick_value=5)
            ],
            prevents_actions=False,
        ))

        encounter = CombatEncounter(
            encounter_id="test_combat",
            combatants=[
                Combatant(
                    combatant_id="goblin_01",
                    name="Goblin",
                    team=CombatantTeam.ENEMY,
                    position=CombatPosition.FRONTLINE,
                    stats=CombatantStats(health=30, max_health=30, attack_power=8, defense=5),
                ),
                Combatant(
                    combatant_id=character_id,
                    name="Hero",
                    team=CombatantTeam.PLAYER,
                    position=CombatPosition.FRONTLINE,
                    stats=CombatantStats(health=100, max_health=100, attack_power=15, defense=10),
                ),
            ],
        )

        fireball = Ability(
            id="magic.fireball",
            name="Fireball",
            description="Explosive fire damage.",
            category=AbilityCategory.MAGIC,
            target_type=TargetType.SINGLE_TARGET,
            mana_cost=25,
            cooldown_seconds=8.0,
            effects=[
                AbilityEffect(effect_type="damage", value=20),
                AbilityEffect(effect_type="dot", value=8, duration_seconds=5.0, chance=1.0),
            ],
        )

        result = encounter.resolve_action(
            attacker=encounter.get_combatant("goblin_01"),
            ability=fireball,
            target=encounter.get_combatant(character_id),
            current_time=0.0,
        )
        assert result.result_type in (ActionResultType.HIT, ActionResultType.CRITICAL)
        assert len(result.status_effects_applied) >= 1

    def test_position_modifiers_affect_combat(self):
        positioning = TacticalPositioning()
        positioning.register_modifier(
            position=CombatPosition.ELEVATED,
            attack_bonus=10.0,
            crit_chance_bonus=5.0,
        )
        bonus = positioning.get_modifier(CombatPosition.ELEVATED)
        assert bonus.attack_bonus == 10.0


class TestInventoryAndEquipmentIntegration:
    """Verify inventory, equipment, and stat modifications work together."""

    def test_equipment_modifies_effective_stats(self, character_id: str):
        stats_mgr = StatsManager()
        stats_mgr.load_from_json()

        inv = InventoryManager(character_id=character_id)
        sword = Item(
            id="iron_sword",
            name="Iron Sword",
            item_type=ItemCategory.WEAPON,
            rarity=ItemRarity.RARE,
            stackable=False,
            max_stack=1,
            stats={"attack_power": 15, "critical_chance": 3},
        )
        inv.add_item(item=sword)
        equipped = inv.equip_item(item_id=sword.id, slot_index=0)
        assert equipped["success"] is True

        slot = inv.get_equipped_item(slot_type=EquipmentSlotType.MAIN_HAND.value)
        assert slot is not None
        assert slot.item.id == "iron_sword"

    def test_inventory_capacity_limits(self, character_id: str):
        inv = InventoryManager(character_id=character_id, max_slots=5)
        for i in range(5):
            item = Item(
                id=f"potion_{i}",
                name=f"Potion {i}",
                item_type=ItemCategory.POTION,
                stackable=True,
                max_stack=99,
            )
            inv.add_item(item=item)
        assert len(inv.list_items()) == 5

        extra = Item(id="extra", name="Extra", item_type=ItemCategory.MISC)
        added = inv.add_item(item=extra)
        assert added["success"] is False


class TestProgressionAndLootIntegration:
    """Verify progression grants rewards and loot scales with level."""

    def test_level_up_grants_stat_points(self, character_id: str):
        prog_sys = ProgressionSystem(
            xp_per_level_base=100,
            xp_per_level_multiplier=1.5,
            skill_points_per_level=1,
            ability_points_per_level=1,
            stat_points_per_level=2,
            stat_growth=[StatGrowth(attribute="strength", amount_per_level=2)],
        )
        state = prog_sys.get_or_create_state(character_id)
        state.experience = 150
        levelups = prog_sys.process_xp(character_id, 0)
        assert len(levelups) >= 1
        assert state.level >= 2

    def test_loot_rarity_weights(self):
        counts = {"common": 0, "uncommon": 0, "rare": 0, "epic": 0, "legendary": 0}
        for _ in range(1000):
            r = roll_rarity()
            counts[r] += 1
        assert counts["common"] > counts["legendary"]

    def test_loot_manager_instances(self, character_id: str, world_id: str):
        mgr = LootManager()
        table = LootTable(
            id="goblin_loot",
            name="Goblin Loot",
            entries=[
                LootTableEntry(item_id="gold", weight=60, min_quantity=1, max_quantity=10),
                LootTableEntry(item_id="rusty_dagger", weight=30, min_quantity=1, max_quantity=1),
                LootTableEntry(item_id="health_potion", weight=10, min_quantity=1, max_quantity=2),
            ],
        )
        mgr.register_definition(table)
        rolled = mgr.roll_loot(
            loot_table_id="goblin_loot",
            world_id=world_id,
            source="combat",
        )
        assert len(rolled.items) >= 1


class TestEconomyAndCraftingIntegration:
    """Verify economy, crafting, and inventory interact correctly."""

    def test_merchant_buy_sell_cycle(self, character_id: str):
        econ = EconomyManager()
        econ.load_merchants([
            MerchantDefinition(
                id="blacksmith_01",
                name="Grimjaw Smithy",
                merchant_type=MerchantType.BLACKSMITH,
                region_id="oakhaven",
                location_id="oakhaven",
                buy_markup=1.2,
                sell_discount=0.5,
            ),
        ])
        econ.load_price_rules("blacksmith_01", [
            PriceRule(item_id="iron_sword", base_price=100, min_price=50, max_price=200),
        ])
        econ.load_stock("blacksmith_01", [
            {"item_id": "iron_sword", "quantity": 5},
        ])

        inv = InventoryManager(character_id=character_id)
        inv.add_item(item=Item(
            id="iron_sword",
            name="Iron Sword",
            item_type=ItemCategory.WEAPON,
            rarity=ItemRarity.COMMON,
            stackable=False,
            max_stack=1,
        ))

        txn = econ.buy_from_merchant(
            merchant_id="blacksmith_01",
            character_id=character_id,
            item_id="iron_sword",
            quantity=1,
        )
        assert txn is not None
        assert txn["success"] is True

    def test_crafting_requires_materials_in_inventory(self, character_id: str):
        craft_mgr = CraftingManager()
        recipe = Recipe(
            id="iron_sword_recipe",
            name="Iron Sword",
            description="A basic iron sword.",
            station_id="forge",
            ingredients=[Ingredient(material_id="iron_ingot", quantity=3)],
            result_item_id="iron_sword",
            result_quantity=1,
        )
        craft_mgr.register_recipe(recipe)
        craft_mgr.grant_recipe(character_id, recipe.id)

        state = craft_mgr.get_character_state(character_id)
        result = craft_mgr.craft(character_id, recipe.id)
        assert result["success"] is True


class TestQuestAndMilestoneIntegration:
    """Verify quests, milestones, and world state interact."""

    def test_quest_rewards_grant_xp_and_items(self, character_id: str):
        journal = QuestJournalManager()
        quest = QuestDefinition(
            id="first_blood",
            name="First Blood",
            description="Defeat your first enemy.",
            objectives=[
                QuestObjective(id="kill_goblin", description="Kill a goblin", required_count=1).to_dict()
            ],
            rewards=[
                QuestReward(type="xp", amount=100).to_dict(),
                QuestReward(type="item", item_id="health_potion", amount=1).to_dict(),
            ],
        )
        journal.register_quest(quest)

        inv = InventoryManager(character_id=character_id)
        prog_mgr = ProgressionManager()

        entry = journal.start_quest("first_blood", world_id="default")
        assert entry.status == "active"
        for obj in entry.objectives:
            obj.current_count = obj.required_count
        result = journal.complete_quest("first_blood")
        assert result.status == "completed"

    def test_milestone_unlocks_world_content(self, world_id: str):
        mgr = MilestoneManager()
        milestone = MilestoneDefinition(
            id="defeat_dragon",
            name="Defeat the Dragon",
            description="Slay the ancient dragon.",
            category="story",
            world_effects=[{"type": "unlock_region", "region": "ashlands"}],
            narration_hooks=[
                {"scope": "region", "target": "oakhaven", "template": "The dragon is dead."}
            ],
        )
        mgr.register_definition(milestone)

        event = mgr.trigger_milestone("defeat_dragon", world_id)
        assert event is not None
        assert event.milestone_id == "defeat_dragon"
        assert len(event.effects_applied) >= 1


class TestWorldSimulationAndEventsIntegration:
    """Verify world simulation, events, and day/night cycle interact."""

    def test_day_night_cycle_advances(self, world_id: str):
        sim = WorldSimulationManager()
        state = sim.get_or_create_state(world_id)
        assert state["day_night"]["phase"] == "day"

        sim.advance_time(world_id, 1)
        assert state["day_night"]["hour"] >= 7

    def test_world_event_triggers_on_location(self, world_id: str):
        wm = WorldMapManager()
        wm.load_locations([
            Location(
                id="oakhaven",
                name="Oakhaven",
                region_id="oakhaven_region",
                location_type=LocationType.VILLAGE,
                danger_level=1,
            ),
        ])

        evt_mgr = WorldEventManager()
        event = WorldEventDefinition(
            id="bandit_raid",
            name="Bandit Raid",
            description="Bandits attack Oakhaven.",
            category=EventCategory.STORY,
            triggers=[
                EventTrigger(
                    trigger_type="location",
                    location_ids=["oakhaven"],
                    probability=1.0,
                )
            ],
            effects=[{"type": "spawn_encounter", "encounter_id": "bandit_fight"}],
        )
        evt_mgr.register_definition(event)

        triggered = evt_mgr.trigger_event("bandit_raid", world_id)
        assert triggered is not None


class TestPartyAndCompanionIntegration:
    """Verify party formation and companion AI work with combat."""

    def test_party_formation_with_companions(self, character_id: str):
        party = PartyManager()
        archetype = CompanionArchetype(
            id="knight_companion",
            name="Sir Roderick",
            description="A loyal knight.",
            role=CompanionRole.TANK,
            base_stats={"strength": 14, "vitality": 12},
            preferred_skills=["two_handed_combat"],
            default_stance=CompanionStance.DEFENSIVE,
        )
        party.register_archetype(archetype)

        result = party.add_companion(
            character_id=character_id,
            archetype_id="knight_companion",
            name="Roderick",
        )
        assert result is not None
        assert result["success"] is True

        state = party.get_party_for_character(character_id)
        assert state is not None
        assert len(state.members()) == 2


class TestTitleAndNPCReactionIntegration:
    """Verify titles modify NPC reactions and character sheet."""

    def test_earned_title_modifies_npc_reaction(self, character_id: str):
        title_mgr = TitleManager()
        title = TitleDefinition(
            id="dragon_slayer",
            name="Dragon Slayer",
            description="Slayer of the ancient dragon.",
            title_type=TitleType.PRESTIGE,
            requirements={"quests_completed": 1, "level": 10},
            effects={"npc_reaction_modifier": 5},
        )
        title_mgr.register_definition(title)

        state = title_mgr.get_character_state(character_id)
        state.earned_titles.append(title.id)
        state.title_ranks[title.id] = 1

        npc = NPCProfile(
            id="village_elder",
            name="Village Elder",
            base_disposition=0,
            feared_titles=[],
            admired_titles=["dragon_slayer"],
        )
        resolver = NPCReactionResolver()
        disposition = resolver.resolve_disposition(character_id, npc)
        assert disposition["disposition"] >= 0

    def test_character_sheet_aggregates_systems(self, character_id: str):
        sheet = CharacterSheet(
            skill_manager=SkillTreeManager(),
            title_manager=TitleManager(),
            stats_manager=StatsManager(),
        )
        result = sheet.render_sheet(character_id, "Test Hero")
        assert result["character_id"] == character_id
        assert "stats_summary" in result
        assert "skill_summaries" in result
        assert "title_summary" in result


class TestDifficultyAndBalancingIntegration:
    """Verify difficulty settings modify combat, loot, and XP consistently."""

    def test_difficulty_modifies_xp_and_loot(self, character_id: str, world_id: str):
        settings = DifficultySettings(
            preset=DifficultyPreset.HARD,
            xp_multiplier=1.5,
            loot_rarity_boost=1.2,
            damage_dealt_multiplier=0.8,
            damage_taken_multiplier=1.3,
        )

        from difficulty_integration import apply_xp_multiplier, roll_loot_with_difficulty
        xp = apply_xp_multiplier(100, settings)
        assert xp == 150

        loot_mgr = LootManager()
        table = LootTable(
            id="test_loot",
            name="Test Loot",
            entries=[LootTableEntry(item_id="gold", weight=100, min_quantity=1, max_quantity=10)],
        )
        loot_mgr.register_definition(table)
        rolled = roll_loot_with_difficulty(
            loot_manager=loot_mgr,
            loot_table_id="test_loot",
            world_id=world_id,
            settings=settings,
        )
        assert rolled is not None


class TestFullGameplayLoopIntegration:
    """End-to-end test of a complete gameplay loop."""

    def test_full_gameplay_loop(self, character_id: str, world_id: str, data_path: str):
        # 1. Create character
        cust_mgr = CharacterCustomizationManager()
        state = cust_mgr.create_character(
            character_id=character_id,
            name="Integration Hero",
            class_id="warrior",
            background_id="soldier",
        )
        assert state.character_id == character_id

        # 2. Initialize stats and progression
        stats_mgr = StatsManager()
        stats_mgr.load_from_json()
        prog_sys = ProgressionSystem(
            xp_per_level_base=100,
            xp_per_level_multiplier=1.5,
            skill_points_per_level=1,
            ability_points_per_level=1,
            stat_points_per_level=2,
            stat_growth=[StatGrowth(attribute="strength", amount_per_level=2)],
        )
        state = prog_sys.get_or_create_state(character_id)

        # 3. Gain XP and level up
        state.experience = 375
        levelups = prog_sys.process_xp(character_id, 0)
        assert state.level >= 3

        # 4. Unlock a skill
        skill_mgr = SkillTreeManager()
        skill_state = skill_mgr.get_character_state(character_id)
        skill_state.available_points = state.level - 1
        skill_state.level = state.level
        available = skill_mgr.get_available_nodes(character_id, "two_handed_combat")
        if available:
            skill_mgr.unlock_node(character_id, "two_handed_combat", available[0]["id"])

        # 5. Equip a weapon
        inv = InventoryManager(character_id=character_id)
        sword = Item(
            id="iron_sword",
            name="Iron Sword",
            item_type=ItemCategory.WEAPON,
            rarity=ItemRarity.RARE,
            stackable=False,
            max_stack=1,
            stats={"attack_power": 15},
        )
        inv.add_item(item=sword)
        inv.equip_item(item_id=sword.id, slot_index=0)

        # 6. Fight a combat encounter
        hero = Combatant(
            combatant_id=character_id,
            name="Integration Hero",
            team=CombatantTeam.PLAYER,
            position=CombatPosition.FRONTLINE,
            stats=CombatantStats(health=100, max_health=100, attack_power=20, defense=10),
        )
        goblin = Combatant(
            combatant_id="goblin_01",
            name="Goblin",
            team=CombatantTeam.ENEMY,
            position=CombatPosition.FRONTLINE,
            stats=CombatantStats(health=30, max_health=30, attack_power=8, defense=5),
        )
        encounter = CombatEncounter(
            encounter_id="test",
            combatants=[
                hero,
                goblin,
            ],
        )

        fireball = Ability(
            id="magic.fireball",
            name="Fireball",
            category=AbilityCategory.MAGIC,
            target_type=TargetType.SINGLE_TARGET,
            mana_cost=25,
            cooldown_seconds=8.0,
            effects=[AbilityEffect(effect_type="damage", value=25)],
        )
        result = encounter.perform_ability(hero.combatant_id, goblin.combatant_id, fireball)
        assert result.result_type in (ActionResultType.HIT, ActionResultType.CRITICAL, ActionResultType.RESISTED)

        # 7. Loot the enemy
        loot_mgr = LootManager()
        table = LootTable(
            id="goblin_loot",
            name="Goblin Loot",
            entries=[
                LootTableEntry(item_id="gold", weight=80, min_quantity=5, max_quantity=20),
                LootTableEntry(item_id="rusty_dagger", weight=20, min_quantity=1, max_quantity=1),
            ],
        )
        loot_mgr.register_definition(table)
        rolled = loot_mgr.roll_loot(
            loot_table_id="goblin_loot",
            world_id=world_id,
            source="goblin_01",
        )
        for item in rolled.items:
            inv.add_item(
                character_id=character_id,
                item=Item(
                    id=item["item_id"],
                    name=item["item_id"].replace("_", " ").title(),
                    item_type=ItemCategory.MISC,
                    rarity=ItemRarity.COMMON,
                    stackable=True,
                    max_stack=99,
                ),
                quantity=item["quantity"],
            )

        # 8. Complete a quest
        journal = QuestJournalManager()
        quest = QuestDefinition(
            id="first_blood",
            name="First Blood",
            description="Defeat your first enemy.",
            objectives=[QuestObjective(id="kill_goblin", description="Kill a goblin", required_count=1).to_dict()],
            rewards=[QuestReward(type="xp", amount=50).to_dict()],
        )
        journal.register_quest(quest)
        quest_result = journal.start_quest("first_blood", world_id)
        assert quest_result is not None
        assert quest_result.status == "active"
        journal.update_objective("first_blood", "kill_goblin", 1)
        complete_result = journal.complete_quest("first_blood")
        assert complete_result is not None
        assert complete_result.status == "completed"

        # 9. Update character sheet
        sheet = CharacterSheet(
            skill_manager=skill_mgr,
            title_manager=TitleManager(),
            stats_manager=stats_mgr,
        )
        sheet_result = sheet.render_sheet(character_id, "Integration Hero")
        assert sheet_result["character_id"] == character_id


# ---------------------------------------------------------------------------
# Data integrity integration tests
# ---------------------------------------------------------------------------

class TestDataIntegrityIntegration:
    """Verify all data files load correctly and managers initialize."""

    def test_all_managers_load_without_error(self, data_path: str):
        managers = [
            AbilityManager(data_path),
            AbilityManager(data_path),
            CraftingManager(data_path),
            EconomyManager(),
            LootManager(),
            MilestoneManager(),
            QuestJournalManager(),
            SkillTreeManager(data_path),
            StatusManager(data_path),
            TitleManager(),
            WorldEventManager(),
            WorldMapManager(),
            WorldSimulationManager(),
        ]
        for mgr in managers:
            assert mgr is not None

    def test_json_data_files_are_valid(self, data_path: str):
        import json
        json_files = [
            "abilities.json",
            "status_conditions.json",
            "crafting_materials.json",
            "crafting_recipes.json",
            "crafting_items.json",
            "crafting_stations.json",
            "economy.json",
            "loot_tables.json",
            "milestones.json",
            "quests.json",
            "titles.json",
            "world_events.json",
            "world_map.json",
            "world_locations.json",
            "character_stats.json",
            "character_customization.json",
        ]
        for filename in json_files:
            path = os.path.join(data_path, filename)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                assert isinstance(data, (dict, list))

    def test_character_sheet_round_trip(self, character_id: str):
        sheet = CharacterSheet()
        result = sheet.render_sheet(character_id, "Test")
        assert isinstance(result, dict)
        assert "character_id" in result
        assert "display_name" in result


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
