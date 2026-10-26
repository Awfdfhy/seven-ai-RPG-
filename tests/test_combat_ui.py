"""
Tests for RPG-12-04: Combat UI and Battle Interface
Run with: python -m pytest tests/test_combat_ui.py -v
or:       python tests/test_combat_ui.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ability import Ability, AbilityCategory, AbilityEffect, TargetType
from combat import (
    ActionResultType,
    Combatant,
    CombatantStats,
    CombatantTeam,
    CombatEncounter,
    CombatPosition,
)
from combat_ui import (
    _render_health_bar,
    _render_status_effects,
    render_ability_panel,
    render_action_result,
    render_battle_grid,
    render_battle_interface,
    render_combat_log,
    render_combatant_card,
    render_turn_order,
)
from status_conditions import StatusCondition, StatusConditionEffect, StatusConditionType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _make_encounter() -> CombatEncounter:
    p = _make_player()
    e = _make_enemy()
    enc = CombatEncounter(encounter_id="enc_test_ui")
    enc.combatants = [p, e]
    enc.turn_order = [p.combatant_id, e.combatant_id]
    enc.current_turn_index = 0
    enc.is_active = True
    enc.round_number = 1
    enc.encounter_log = ["Encounter started.", "Hero attacks Goblin."]
    return enc


def _make_burn_condition() -> StatusCondition:
    return StatusCondition(
        id="cond_burn",
        name="Burn",
        description="Taking fire damage over time.",
        condition_type=StatusConditionType.BURN,
        effects=[StatusConditionEffect(tick_value=3)],
        duration_seconds=5,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRenderHealthBar:
    def test_full_health(self):
        bar = _render_health_bar(100, 100, width=10)
        assert "100%" in bar
        assert "█" * 10 in bar

    def test_zero_health(self):
        bar = _render_health_bar(0, 100, width=10)
        assert "0%" in bar

    def test_partial_health(self):
        bar = _render_health_bar(50, 100, width=10)
        assert "50%" in bar

    def test_maximum_zero(self):
        bar = _render_health_bar(0, 0, width=10)
        assert "0%" in bar


class TestRenderStatusEffects:
    def test_no_status(self):
        p = _make_player()
        result = _render_status_effects(p)
        assert result.strip() == ""

    def test_with_burn(self):
        p = _make_player()
        burn = _make_burn_condition()
        p.status_manager.definitions[burn.id] = burn
        p.status_manager.active[(p.combatant_id, burn.id)] = burn
        result = _render_status_effects(p)
        assert "🔥" in result


class TestRenderCombatantCard:
    def test_player_card(self):
        p = _make_player()
        card = render_combatant_card(p)
        assert "Hero" in card
        assert "HP:" in card
        assert "POS:" in card
        assert "ATK:" in card
        assert "DEF:" in card

    def test_enemy_card(self):
        e = _make_enemy()
        card = render_combatant_card(e)
        assert "Goblin" in card

    def test_current_turn_marker(self):
        p = _make_player()
        card = render_combatant_card(p, is_current_turn=True)
        assert "TURN" in card


class TestRenderBattleGrid:
    def test_grid_size(self):
        enc = _make_encounter()
        grid = render_battle_grid(enc)
        lines = grid.split("\n")
        assert len(lines) == 8

    def test_combatant_placed(self):
        enc = _make_encounter()
        grid = render_battle_grid(enc)
        assert "H" in grid or "P" in grid or "E" in grid


class TestRenderTurnOrder:
    def test_turn_order_output(self):
        enc = _make_encounter()
        out = render_turn_order(enc)
        assert "Turn order:" in out
        assert "Hero" in out
        assert "Goblin" in out

    def test_current_turn_marker(self):
        enc = _make_encounter()
        out = render_turn_order(enc)
        assert "◀" in out


class TestRenderCombatLog:
    def test_log_output(self):
        enc = _make_encounter()
        out = render_combat_log(enc)
        assert "Combat log:" in out
        assert "Encounter started." in out

    def test_empty_log(self):
        enc = _make_encounter()
        enc.encounter_log = []
        out = render_combat_log(enc)
        assert "—" in out


class TestRenderAbilityPanel:
    def test_panel_with_abilities(self):
        p = _make_player()
        ability = Ability(
            id="melee.quick_strike",
            name="Quick Strike",
            description="A fast hit.",
            category=AbilityCategory.COMBAT,
            target_type=TargetType.SINGLE_TARGET,
            mana_cost=5,
            cooldown_seconds=2.0,
            effects=[AbilityEffect(effect_type="damage", value=12, chance=1.0)],
        )
        if p.ability_manager is None:
            from ability_manager import AbilityManager
            p.ability_manager = AbilityManager()
        p.ability_manager.register(ability)
        out = render_ability_panel(p)
        assert "Abilities:" in out
        assert "Quick Strike" in out

    def test_no_abilities(self):
        p = _make_player()
        p.ability_manager = None
        out = render_ability_panel(p)
        assert "None" in out


class TestRenderBattleInterface:
    def test_interface_output(self):
        enc = _make_encounter()
        out = render_battle_interface(enc, current_combatant=enc.get_combatant(enc.turn_order[0]))
        assert "Round 1" in out
        assert "Combat active" in out
        assert "Hero" in out
        assert "Goblin" in out
        assert "Abilities:" in out

    def test_ended_interface(self):
        enc = _make_encounter()
        enc.is_active = False
        enc.winner_team = CombatantTeam.PLAYER
        out = render_battle_interface(enc)
        assert "Combat ended" in out
        assert "Player wins!" in out


class TestRenderActionResult:
    def test_hit_result(self):
        class FakeResult:
            result_type = ActionResultType.HIT
            damage = 10.0
            healing = 0.0
            attacker_name = "Hero"
            target_name = "Goblin"
            narration = ""
            triggered_finisher = None

        msg = render_action_result(FakeResult())
        assert "Hero" in msg
        assert "Goblin" in msg
        assert "10.0 dmg" in msg

    def test_miss_result(self):
        class FakeResult:
            result_type = ActionResultType.MISS
            damage = 0.0
            healing = 0.0
            attacker_name = "Hero"
            target_name = "Goblin"
            narration = ""
            triggered_finisher = None

        msg = render_action_result(FakeResult())
        assert "MISSED" in msg

    def test_finisher_result(self):
        class FakeResult:
            result_type = ActionResultType.CRITICAL
            damage = 60.0
            healing = 0.0
            attacker_name = "Hero"
            target_name = "Goblin"
            narration = ""
            triggered_finisher = "melee.finishing_blow"

        msg = render_action_result(FakeResult())
        assert "FINISHER" in msg
        assert "melee.finishing_blow" in msg


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
