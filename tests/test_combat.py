"""
Tests for RPG-12-03: Advanced Combat System
Run with: python -m pytest tests/test_combat.py -v
or:       python tests/test_combat.py
"""

from __future__ import annotations

import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ability import Ability, AbilityCategory, AbilityEffect, TargetType
from combat import (
    ActionResultType,
    CombatActionResult,
    Combatant,
    CombatantStats,
    CombatantTeam,
    CombatComboState,
    CombatEncounter,
    CombatPosition,
    ComboNode,
    ComboSystem,
    FinisherDefinition,
    FinisherTrigger,
    PositionModifier,
    TacticalPositioning,
)
from status_conditions import StatusCondition, StatusConditionType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fireball() -> Ability:
    return Ability(
        id="fire.fireball",
        name="Fireball",
        description="A searing explosion.",
        category=AbilityCategory.COMBAT,
        target_type=TargetType.SINGLE_TARGET,
        mana_cost=25,
        cooldown_seconds=8.0,
        effects=[
            AbilityEffect(effect_type="damage", value=35, chance=1.0),
            AbilityEffect(effect_type="dot", value=8, duration_seconds=5.0, chance=0.75),
        ],
    )


def _make_quick_strike() -> Ability:
    return Ability(
        id="melee.quick_strike",
        name="Quick Strike",
        description="A fast melee hit.",
        category=AbilityCategory.COMBAT,
        target_type=TargetType.SINGLE_TARGET,
        mana_cost=5,
        cooldown_seconds=2.0,
        effects=[
            AbilityEffect(effect_type="damage", value=12, chance=1.0),
            AbilityEffect(effect_type="dot", value=3, duration_seconds=3.0, chance=0.5),
        ],
    )


def _make_power_strike() -> Ability:
    return Ability(
        id="melee.power_strike",
        name="Power Strike",
        description="A heavy blow.",
        category=AbilityCategory.COMBAT,
        target_type=TargetType.SINGLE_TARGET,
        mana_cost=10,
        cooldown_seconds=5.0,
        effects=[
            AbilityEffect(effect_type="damage", value=30, chance=1.0),
        ],
    )


def _make_finishing_blow() -> Ability:
    return Ability(
        id="melee.finishing_blow",
        name="Finishing Blow",
        description="Execute a weakened foe.",
        category=AbilityCategory.COMBAT,
        target_type=TargetType.SINGLE_TARGET,
        mana_cost=15,
        cooldown_seconds=10.0,
        effects=[
            AbilityEffect(effect_type="damage", value=60, chance=1.0),
        ],
    )


def _make_player(name: str = "Hero") -> Combatant:
    return Combatant(
        combatant_id=f"char_{name.lower().replace(' ', '_')}",
        name=name,
        team=CombatantTeam.PLAYER,
        position=CombatPosition.FRONTLINE,
        stats=CombatantStats(health=100, max_health=100, attack_power=20, defense=8),
    )


def _make_enemy(name: str = "Goblin") -> Combatant:
    return Combatant(
        combatant_id=f"enemy_{name.lower().replace(' ', '_')}",
        name=name,
        team=CombatantTeam.ENEMY,
        position=CombatPosition.FRONTLINE,
        stats=CombatantStats(health=80, max_health=80, attack_power=12, defense=4),
    )


def _make_encounter(player: Combatant, enemy: Combatant) -> CombatEncounter:
    encounter = CombatEncounter(encounter_id="enc_test_1")
    encounter.combatants = [player, enemy]
    return encounter


# ---------------------------------------------------------------------------
# TacticalPositioning tests
# ---------------------------------------------------------------------------


class TestTacticalPositioning:
    def test_default_modifiers_exist(self):
        tp = TacticalPositioning()
        for pos in CombatPosition:
            mod = tp.get_modifier(pos)
            assert mod.position == pos

    def test_frontline_defense_bonus(self):
        tp = TacticalPositioning()
        mod = tp.get_modifier(CombatPosition.FRONTLINE)
        assert mod.defense_bonus > 0

    def test_backline_dodge_bonus(self):
        tp = TacticalPositioning()
        mod = tp.get_modifier(CombatPosition.BACKLINE)
        assert mod.dodge_chance_bonus > 0

    def test_elevated_attack_bonus(self):
        tp = TacticalPositioning()
        mod = tp.get_modifier(CombatPosition.ELEVATED)
        assert mod.attack_bonus > 0

    def test_flank_attack_bonus_vs_frontline(self):
        tp = TacticalPositioning()
        attacker = _make_player()
        attacker.position = CombatPosition.FLANK
        defender = _make_enemy()
        defender.position = CombatPosition.FRONTLINE
        bonus = tp.calculate_attack_bonus(attacker, defender)
        assert bonus > 0

    def test_backline_vs_frontline_penalty(self):
        tp = TacticalPositioning()
        attacker = _make_player()
        attacker.position = CombatPosition.BACKLINE
        defender = _make_enemy()
        defender.position = CombatPosition.FRONTLINE
        bonus = tp.calculate_attack_bonus(attacker, defender)
        assert bonus < 0

    def test_positional_advantage_elevated_vs_grounded(self):
        tp = TacticalPositioning()
        attacker = _make_player()
        attacker.position = CombatPosition.ELEVATED
        defender = _make_enemy()
        defender.position = CombatPosition.GROUNDED
        assert tp.has_positional_advantage(attacker, defender) is True

    def test_no_advantage_same_position(self):
        tp = TacticalPositioning()
        attacker = _make_player()
        attacker.position = CombatPosition.FRONTLINE
        defender = _make_enemy()
        defender.position = CombatPosition.FRONTLINE
        assert tp.has_positional_advantage(attacker, defender) is False

    def test_can_strike_from_behind(self):
        tp = TacticalPositioning()
        attacker = _make_player()
        attacker.position = CombatPosition.FLANK
        defender = _make_enemy()
        defender.position = CombatPosition.BACKLINE
        assert tp.can_strike_from_behind(attacker, defender) is True

    def test_cannot_strike_from_behind_frontline(self):
        tp = TacticalPositioning()
        attacker = _make_player()
        attacker.position = CombatPosition.FRONTLINE
        defender = _make_enemy()
        defender.position = CombatPosition.BACKLINE
        assert tp.can_strike_from_behind(attacker, defender) is False


# ---------------------------------------------------------------------------
# PositionModifier tests
# ---------------------------------------------------------------------------


class TestPositionModifier:
    def test_roundtrip(self):
        mod = PositionModifier(
            position=CombatPosition.FLANK,
            attack_bonus=0.15,
            defense_bonus=0.05,
        )
        data = mod.to_dict()
        restored = PositionModifier.from_dict(data)
        assert restored.position == CombatPosition.FLANK
        assert restored.attack_bonus == 0.15
        assert restored.defense_bonus == 0.05

    def test_default_values(self):
        mod = PositionModifier(position=CombatPosition.COVER)
        assert mod.attack_bonus == 0.0
        assert mod.damage_taken_multiplier == 1.0
        assert mod.extra == {}


# ---------------------------------------------------------------------------
# Combatant tests
# ---------------------------------------------------------------------------


class TestCombatant:
    def test_alive_by_default(self):
        c = _make_player()
        assert c.is_alive() is True

    def test_dead_when_zero_health(self):
        c = _make_player()
        c.stats.health = 0
        assert c.is_alive() is False

    def test_effective_position_cover_unchanged(self):
        c = _make_player()
        c.position = CombatPosition.COVER
        assert c.effective_position() == CombatPosition.COVER

    def test_effective_position_root_grounds(self):
        c = _make_player()
        c.position = CombatPosition.ELEVATED
        stun_cond = StatusCondition(
            id="root",
            name="Rooted",
            condition_type=StatusConditionType.ROOT,
            duration_seconds=5.0,
        )
        c.status_manager.register_definition(stun_cond)
        c.status_manager.apply_condition(
            c.combatant_id,
            "root",
            current_time=time.time(),
        )
        assert c.effective_position() == CombatPosition.GROUNDED

    def test_to_from_dict_roundtrip(self):
        c = _make_player("Alice")
        data = c.to_dict()
        restored = Combatant.from_dict(data)
        assert restored.combatant_id == c.combatant_id
        assert restored.name == "Alice"
        assert restored.team == CombatantTeam.PLAYER
        assert restored.position == CombatPosition.FRONTLINE
        assert restored.stats.health == 100


# ---------------------------------------------------------------------------
# CombatComboState tests
# ---------------------------------------------------------------------------


class TestCombatComboState:
    def test_not_in_combo_initially(self):
        state = CombatComboState(combatant_id="p1")
        assert state.is_in_combo() is False

    def test_is_in_combo_when_active(self):
        state = CombatComboState(combatant_id="p1")
        state.active_combo_id = "combo_1"
        state.current_step_index = 0
        assert state.is_in_combo() is True

    def test_combo_window_expired(self):
        state = CombatComboState(combatant_id="p1")
        state.active_combo_id = "combo_1"
        state.current_step_index = 0
        state.last_combo_time = time.time() - 5.0
        assert state.is_combo_window_expired(time.time()) is True

    def test_combo_window_not_expired(self):
        state = CombatComboState(combatant_id="p1")
        state.active_combo_id = "combo_1"
        state.current_step_index = 0
        state.last_combo_time = time.time()
        assert state.is_combo_window_expired(time.time()) is False

    def test_reset_clears_state(self):
        state = CombatComboState(combatant_id="p1")
        state.active_combo_id = "combo_1"
        state.current_step_index = 1
        state.reset()
        assert state.is_in_combo() is False
        assert state.current_step_index == -1

    def test_roundtrip(self):
        state = CombatComboState(combatant_id="p1", active_combo_id="c1", combo_points=3)
        data = state.to_dict()
        restored = CombatComboState.from_dict(data)
        assert restored.active_combo_id == "c1"
        assert restored.combo_points == 3


# ---------------------------------------------------------------------------
# ComboNode / ComboSystem tests
# ---------------------------------------------------------------------------


class TestComboNode:
    def test_roundtrip(self):
        node = ComboNode(
            combo_id="strike_combo",
            sequence_index=0,
            ability_id="melee.quick_strike",
            next_combo_ability_id="melee.power_strike",
            combo_point_gain=2,
        )
        data = node.to_dict()
        restored = ComboNode.from_dict(data)
        assert restored.combo_id == "strike_combo"
        assert restored.sequence_index == 0
        assert restored.next_combo_ability_id == "melee.power_strike"
        assert restored.combo_point_gain == 2


class TestComboSystem:
    def test_start_combo(self):
        cs = ComboSystem()
        nodes = [
            ComboNode("combo_1", 0, "melee.quick_strike", "melee.power_strike"),
            ComboNode("combo_1", 1, "melee.power_strike"),
        ]
        cs.register_combo(nodes)
        state = CombatComboState(combatant_id="p1")
        ok = cs.start_combo(state, "combo_1", time.time())
        assert ok is True
        assert state.is_in_combo() is True
        assert state.current_step_index == 0

    def test_advance_combo_success(self):
        cs = ComboSystem()
        nodes = [
            ComboNode("combo_1", 0, "melee.quick_strike", "melee.power_strike"),
            ComboNode("combo_1", 1, "melee.power_strike"),
        ]
        cs.register_combo(nodes)
        state = CombatComboState(combatant_id="p1")
        cs.start_combo(state, "combo_1", time.time())
        ok, node, points = cs.advance_combo(state, "melee.quick_strike", time.time())
        assert ok is True
        assert points == 1
        assert state.current_step_index == 1

    def test_advance_combo_wrong_ability_resets(self):
        cs = ComboSystem()
        nodes = [
            ComboNode("combo_1", 0, "melee.quick_strike", "melee.power_strike"),
            ComboNode("combo_1", 1, "melee.power_strike"),
        ]
        cs.register_combo(nodes)
        state = CombatComboState(combatant_id="p1")
        cs.start_combo(state, "combo_1", time.time())
        ok, _, points = cs.advance_combo(state, "fire.fireball", time.time())
        assert ok is False
        assert state.is_in_combo() is False

    def test_combo_completion_marks_completed(self):
        cs = ComboSystem()
        nodes = [
            ComboNode("combo_1", 0, "melee.quick_strike"),
        ]
        cs.register_combo(nodes)
        state = CombatComboState(combatant_id="p1")
        cs.start_combo(state, "combo_1", time.time())
        ok, _, points = cs.advance_combo(state, "melee.quick_strike", time.time())
        assert ok is True
        assert "combo_1" in state.completed_combos

    def test_available_finishers_combo_points(self):
        cs = ComboSystem()
        finisher = FinisherDefinition(
            ability_id="melee.execute",
            name="Execute",
            combo_points_required=5,
            triggers=[],
        )
        state = CombatComboState(combatant_id="p1", combo_points=3)
        available = cs.get_available_finishers(state, [finisher], _make_player(), _make_enemy())
        assert len(available) == 0
        state.combo_points = 6
        available = cs.get_available_finishers(state, [finisher], _make_player(), _make_enemy())
        assert len(available) == 1

    def test_available_finishers_trigger_check(self):
        cs = ComboSystem()
        finisher = FinisherDefinition(
            ability_id="melee.execute",
            name="Execute",
            combo_points_required=0,
            triggers=[FinisherTrigger.TARGET_STUNNED],
        )
        attacker = _make_player()
        defender = _make_enemy()
        stun_def = StatusCondition(
            id="stun",
            name="Stunned",
            condition_type=StatusConditionType.STUN,
            duration_seconds=2.0,
            prevents_actions=True,
        )
        defender.status_manager.register_definition(stun_def)
        defender.status_manager.apply_condition(
            defender.combatant_id,
            "stun",
            current_time=time.time(),
        )
        available = cs.get_available_finishers(
            CombatComboState(combatant_id=attacker.combatant_id),
            [finisher],
            attacker,
            defender,
        )
        assert len(available) == 1


# ---------------------------------------------------------------------------
# FinisherDefinition tests
# ---------------------------------------------------------------------------


class TestFinisherDefinition:
    def test_roundtrip(self):
        finisher = FinisherDefinition(
            ability_id="melee.execute",
            name="Execute",
            description="Finish them.",
            triggers=[FinisherTrigger.LOW_HEALTH, FinisherTrigger.HIGH_COMBO],
            combo_points_required=5,
            positional_requirements=[CombatPosition.FLANK],
            target_health_max_percent=25.0,
            target_health_min_percent=0.0,
            effects=[AbilityEffect(effect_type="damage", value=80)],
        )
        data = finisher.to_dict()
        restored = FinisherDefinition.from_dict(data)
        assert restored.ability_id == "melee.execute"
        assert restored.combo_points_required == 5
        assert FinisherTrigger.LOW_HEALTH in restored.triggers
        assert CombatPosition.FLANK in restored.positional_requirements
        assert restored.target_health_max_percent == 25.0
        assert len(restored.effects) == 1

    def test_default_values(self):
        finisher = FinisherDefinition(ability_id="x", name="X")
        assert finisher.triggers == []
        assert finisher.combo_points_required == 0
        assert finisher.positional_requirements == []
        assert finisher.target_health_max_percent == 100.0
        assert finisher.effects == []


# ---------------------------------------------------------------------------
# CombatEncounter tests
# ---------------------------------------------------------------------------


class TestCombatEncounter:
    def test_start_encounter_builds_turn_order(self):
        player = _make_player("Hero")
        enemy = _make_enemy("Orc")
        player.stats.speed = 10
        enemy.stats.speed = 5
        encounter = _make_encounter(player, enemy)
        encounter.start_encounter()
        assert encounter.turn_order[0] == player.combatant_id
        assert encounter.is_active is True
        assert encounter.round_number == 1

    def test_next_turn_returns_current(self):
        player = _make_player()
        enemy = _make_enemy()
        encounter = _make_encounter(player, enemy)
        encounter.start_encounter()
        turn = encounter.next_turn(time.time())
        assert turn is not None
        assert turn.combatant_id in [player.combatant_id, enemy.combatant_id]

    def test_end_encounter_sets_winner(self):
        player = _make_player()
        enemy = _make_enemy()
        enemy.stats.health = 0
        encounter = _make_encounter(player, enemy)
        encounter.start_encounter()
        encounter.end_encounter()
        assert encounter.winner_team == CombatantTeam.PLAYER

    def test_resolve_action_deals_damage(self):
        random.seed(42)
        player = _make_player()
        enemy = _make_enemy()
        encounter = _make_encounter(player, enemy)
        encounter.start_encounter()
        result = encounter.resolve_action(player, _make_quick_strike(), enemy, time.time())
        assert result.result_type in (ActionResultType.HIT, ActionResultType.CRITICAL, ActionResultType.MISS, ActionResultType.DODGED)
        if result.result_type in (ActionResultType.HIT, ActionResultType.CRITICAL):
            assert enemy.stats.health < 80

    def test_resolve_action_heals_on_hot(self):
        player = _make_player()
        player.stats.health = 50
        heal_ability = Ability(
            id="holy.light",
            name="Holy Light",
            category=AbilityCategory.MAGIC,
            target_type=TargetType.SELF,
            effects=[
                AbilityEffect(effect_type="hot", value=10, duration_seconds=3.0, chance=1.0),
            ],
        )
        enemy = _make_enemy()
        encounter = _make_encounter(player, enemy)
        encounter.start_encounter()
        result = encounter.resolve_action(player, heal_ability, player, time.time())
        assert len(result.status_effects_applied) == 1
        assert result.status_effects_applied[0].condition_id == "hot_holy.light"

    def test_get_team_filters_alive(self):
        player1 = _make_player("Hero")
        player2 = _make_player("Ally")
        enemy = _make_enemy()
        player2.stats.health = 0
        encounter = CombatEncounter(encounter_id="e1", combatants=[player1, player2, enemy])
        players = encounter.get_team(CombatantTeam.PLAYER)
        assert len(players) == 1
        assert players[0].combatant_id == player1.combatant_id

    def test_to_from_dict_roundtrip(self):
        player = _make_player("Hero")
        enemy = _make_enemy("Orc")
        encounter = _make_encounter(player, enemy)
        encounter.start_encounter()
        encounter.resolve_action(player, _make_quick_strike(), enemy, time.time())
        data = encounter.to_dict()
        restored = CombatEncounter.from_dict(data)
        assert restored.encounter_id == encounter.encounter_id
        assert len(restored.combatants) == 2
        assert restored.round_number == 1
        assert len(restored.action_history) >= 1

    def test_finisher_execution(self):
        cs = ComboSystem()
        finisher = FinisherDefinition(
            ability_id="melee.execute",
            name="Execute",
            combo_points_required=5,
            triggers=[FinisherTrigger.LOW_HEALTH],
            effects=[AbilityEffect(effect_type="damage", value=50)],
        )
        player = _make_player()
        enemy = _make_enemy()
        enemy.stats.health = 15
        encounter = _make_encounter(player, enemy)
        encounter.finishers = [finisher]
        encounter.combo_system = cs
        encounter.start_encounter()
        player.combo_state.combo_points = 6
        result = encounter.resolve_action(player, _make_quick_strike(), enemy, time.time())
        assert result.triggered_finisher == "melee.execute"


# ---------------------------------------------------------------------------
# Action result tests
# ---------------------------------------------------------------------------


class TestCombatActionResult:
    def test_roundtrip(self):
        result = CombatActionResult(
            action_id="act_1",
            attacker_id="a1",
            target_id="t1",
            result_type=ActionResultType.CRITICAL,
            damage=50.0,
            combo_points_gained=2,
        )
        data = result.to_dict()
        restored = CombatActionResult.from_dict(data)
        assert restored.action_id == "act_1"
        assert restored.result_type == ActionResultType.CRITICAL
        assert restored.damage == 50.0
        assert restored.combo_points_gained == 2
