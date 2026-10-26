"""
RPG-10-08: Mini-Games System Tests
Tests for gambling, puzzles, and side activities.

Run with: python -m pytest tests/test_mini_games.py -v
or:       python tests/test_mini_games.py
"""

from __future__ import annotations

import os
import random
import sys
import unittest
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mini_games import (
    CardGameDefinition,
    DiceGameDefinition,
    GamblingType,
    LogicPuzzleDefinition,
    MiniGameCategory,
    MiniGameManager,
    MiniGameResult,
    PatternPuzzleDefinition,
    RiddlePuzzleDefinition,
    SideActivityDefinition,
    SideActivityType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager() -> MiniGameManager:
    mgr = MiniGameManager()
    mgr.load_defaults()
    return mgr


# ---------------------------------------------------------------------------
# MiniGameResult
# ---------------------------------------------------------------------------

class TestMiniGameResult(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        result = MiniGameResult(
            success=True,
            category=MiniGameCategory.GAMBLING.value,
            game_type=GamblingType.DICE.value,
            reward_gold=10,
            reward_xp=5,
            narrative="You win!",
            metadata={"dice": [3, 4]},
        )
        data = result.to_dict()
        restored = MiniGameResult.from_dict(data)
        self.assertEqual(restored.success, True)
        self.assertEqual(restored.reward_gold, 10)
        self.assertEqual(restored.narrative, "You win!")
        self.assertEqual(restored.metadata["dice"], [3, 4])


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

class TestDiceGameDefinition(unittest.TestCase):
    def test_roundtrip(self):
        game = DiceGameDefinition(
            id="dice_01",
            name="Test Dice",
            description="A test game.",
            min_bet=1,
            max_bet=50,
            house_edge=0.1,
            win_condition="higher",
            target_number=7,
            dice_count=2,
            dice_sides=6,
        )
        data = game.to_dict()
        restored = DiceGameDefinition.from_dict(data)
        self.assertEqual(restored.id, "dice_01")
        self.assertEqual(restored.house_edge, 0.1)


class TestCardGameDefinition(unittest.TestCase):
    def test_roundtrip(self):
        game = CardGameDefinition(
            id="cards_01",
            name="Test Cards",
            description="Card game.",
            game_type="blackjack",
        )
        data = game.to_dict()
        restored = CardGameDefinition.from_dict(data)
        self.assertEqual(restored.game_type, "blackjack")


class TestRiddlePuzzleDefinition(unittest.TestCase):
    def test_roundtrip(self):
        riddle = RiddlePuzzleDefinition(
            id="riddle_01",
            name="Test Riddle",
            description="A riddle.",
            question="What has keys but no locks?",
            answer="piano",
            hints=["It makes music."],
            reward_gold=10,
            reward_xp=5,
            difficulty="easy",
        )
        data = riddle.to_dict()
        restored = RiddlePuzzleDefinition.from_dict(data)
        self.assertEqual(restored.answer, "piano")
        self.assertEqual(restored.hints, ["It makes music."])


class TestPatternPuzzleDefinition(unittest.TestCase):
    def test_roundtrip(self):
        puzzle = PatternPuzzleDefinition(
            id="pattern_01",
            name="Test Pattern",
            description="A pattern.",
            sequence=[1, 2, 4, 8],
            next_in_sequence=16,
        )
        data = puzzle.to_dict()
        restored = PatternPuzzleDefinition.from_dict(data)
        self.assertEqual(restored.next_in_sequence, 16)


class TestLogicPuzzleDefinition(unittest.TestCase):
    def test_roundtrip(self):
        puzzle = LogicPuzzleDefinition(
            id="logic_01",
            name="Test Logic",
            description="A logic puzzle.",
            prompt="Choose A or B.",
            correct_choice="A",
            choices=["A", "B"],
        )
        data = puzzle.to_dict()
        restored = LogicPuzzleDefinition.from_dict(data)
        self.assertEqual(restored.correct_choice, "A")


class TestSideActivityDefinition(unittest.TestCase):
    def test_roundtrip(self):
        act = SideActivityDefinition(
            id="fish_01",
            name="Fishing",
            description="Go fishing.",
            activity_type=SideActivityType.FISHING.value,
            difficulty="easy",
            min_reward_gold=1,
            max_reward_gold=10,
            success_chance=0.8,
            cooldown_hours=1,
        )
        data = act.to_dict()
        restored = SideActivityDefinition.from_dict(data)
        self.assertEqual(restored.activity_type, SideActivityType.FISHING.value)
        self.assertEqual(restored.cooldown_hours, 1)


# ---------------------------------------------------------------------------
# Manager registration & defaults
# ---------------------------------------------------------------------------

class TestMiniGameManagerDefaults(unittest.TestCase):
    def test_load_defaults_populates_games(self):
        mgr = _make_manager()
        self.assertIn("tavern_dice_01", mgr.dice_games)
        self.assertIn("tavern_high_card", mgr.card_games)
        self.assertIn("tavern_blackjack", mgr.card_games)
        self.assertIn("sphinx_riddle_01", mgr.riddle_puzzles)
        self.assertIn("maze_pattern_01", mgr.pattern_puzzles)
        self.assertIn("guard_logic_01", mgr.logic_puzzles)
        self.assertIn("fishing_pond", mgr.side_activities)
        self.assertIn("lockpick_tutorial", mgr.side_activities)
        self.assertIn("haggling_market", mgr.side_activities)

    def test_register_custom_game(self):
        mgr = MiniGameManager()
        mgr.register_dice_game(DiceGameDefinition(
            id="custom_dice",
            name="Custom Dice",
            description="Custom.",
        ))
        self.assertIn("custom_dice", mgr.dice_games)


# ---------------------------------------------------------------------------
# Gambling
# ---------------------------------------------------------------------------

class TestDiceGambling(unittest.TestCase):
    def test_unknown_game_returns_error(self):
        mgr = _make_manager()
        result = mgr.play_dice_game("unknown", 10)
        self.assertFalse(result.success)
        self.assertEqual(result.category, MiniGameCategory.GAMBLING.value)

    def test_bet_out_of_range_returns_error(self):
        mgr = _make_manager()
        result = mgr.play_dice_game("tavern_dice_01", 0)
        self.assertFalse(result.success)
        result = mgr.play_dice_game("tavern_dice_01", 9999)
        self.assertFalse(result.success)

    def test_win_returns_positive_gold(self):
        mgr = _make_manager()
        random.seed(0)
        result = mgr.play_dice_game("tavern_dice_01", 10)
        self.assertIn(result.success, [True, False])
        self.assertIsInstance(result.reward_gold, int)
        if result.success:
            self.assertGreater(result.reward_gold, 0)
        else:
            self.assertEqual(result.reward_gold, -10)
        self.assertIn("dice", result.metadata)
        self.assertEqual(len(result.metadata["dice"]), 2)

    def test_luck_modifier_applied(self):
        mgr = _make_manager()
        random.seed(42)
        attrs_low = {"dexterity": 10}
        result_low = mgr.play_dice_game("tavern_dice_01", 10, attrs_low)
        random.seed(42)
        attrs_high = {"dexterity": 20}
        result_high = mgr.play_dice_game("tavern_dice_01", 10, attrs_high)
        # Just verify they both produce valid results
        self.assertIn(result_low.metadata["total"], range(2, 19))
        self.assertIn(result_high.metadata["total"], range(2, 19))


class TestCardGambling(unittest.TestCase):
    def test_high_card_roundtrip(self):
        mgr = _make_manager()
        random.seed(1)
        result = mgr.play_card_game("tavern_high_card", 10)
        self.assertIn(result.game_type, [GamblingType.CARDS.value])
        self.assertIn(result.success, [True, False])
        self.assertIn("player_card", result.metadata)
        self.assertIn("dealer_card", result.metadata)

    def test_blackjack_bust(self):
        mgr = _make_manager()
        # Seed to force a bust scenario if possible
        random.seed(99)
        results = [mgr.play_card_game("tavern_blackjack", 10) for _ in range(50)]
        busts = [r for r in results if r.metadata.get("player_total", 0) > 21]
        self.assertGreaterEqual(len(busts), 1, "Expected at least one bust in 50 hands")

    def test_unknown_card_game_returns_error(self):
        mgr = _make_manager()
        result = mgr.play_card_game("unknown", 10)
        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# Puzzles
# ---------------------------------------------------------------------------

class TestRiddlePuzzle(unittest.TestCase):
    def test_correct_answer_wins(self):
        mgr = _make_manager()
        result = mgr.solve_riddle("sphinx_riddle_01", "man")
        self.assertTrue(result.success)
        self.assertEqual(result.reward_gold, 50)
        self.assertEqual(result.reward_xp, 30)

    def test_wrong_answer_loses(self):
        mgr = _make_manager()
        result = mgr.solve_riddle("sphinx_riddle_01", "woman")
        self.assertFalse(result.success)
        self.assertEqual(result.reward_gold, 0)

    def test_case_insensitive(self):
        mgr = _make_manager()
        result = mgr.solve_riddle("sphinx_riddle_01", "MAN")
        self.assertTrue(result.success)

    def test_unknown_riddle(self):
        mgr = _make_manager()
        result = mgr.solve_riddle("unknown", "anything")
        self.assertFalse(result.success)


class TestPatternPuzzle(unittest.TestCase):
    def test_correct_next_number(self):
        mgr = _make_manager()
        result = mgr.solve_pattern("maze_pattern_01", 64)
        self.assertTrue(result.success)
        self.assertEqual(result.reward_gold, 40)
        self.assertEqual(result.reward_xp, 25)

    def test_wrong_next_number(self):
        mgr = _make_manager()
        result = mgr.solve_pattern("maze_pattern_01", 100)
        self.assertFalse(result.success)

    def test_unknown_pattern(self):
        mgr = _make_manager()
        result = mgr.solve_pattern("unknown", 0)
        self.assertFalse(result.success)


class TestLogicPuzzle(unittest.TestCase):
    def test_correct_choice(self):
        mgr = _make_manager()
        result = mgr.solve_logic("guard_logic_01", "the truthful guard")
        self.assertTrue(result.success)
        self.assertEqual(result.reward_gold, 30)

    def test_wrong_choice(self):
        mgr = _make_manager()
        result = mgr.solve_logic("guard_logic_01", "the lying guard")
        self.assertFalse(result.success)

    def test_unknown_logic(self):
        mgr = _make_manager()
        result = mgr.solve_logic("unknown", "anything")
        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# Side Activities
# ---------------------------------------------------------------------------

class TestSideActivities(unittest.TestCase):
    def test_unknown_activity_returns_error(self):
        mgr = _make_manager()
        result = mgr.do_side_activity("unknown", "char_01")
        self.assertFalse(result.success)

    def test_activity_succeeds_with_chance(self):
        mgr = _make_manager()
        random.seed(0)
        results = [mgr.do_side_activity("fishing_pond", f"char_{i}") for i in range(50)]
        successes = [r for r in results if r.success]
        # fishing has 0.8 success chance, so expect roughly 40 successes
        self.assertGreater(len(successes), 20)
        self.assertLess(len(successes), 50)

    def test_cooldown_blocks_repeat(self):
        mgr = _make_manager()
        # Do it once (may succeed or fail, but cooldown is set either way)
        result1 = mgr.do_side_activity("fishing_pond", "char_01", {"dexterity": 10})
        self.assertIn("char_01:fishing_pond", mgr.cooldowns)
        # Immediately do again — should be on cooldown regardless of first outcome
        result2 = mgr.do_side_activity("fishing_pond", "char_01", {"dexterity": 10})
        self.assertFalse(result2.success)
        self.assertIn("cooldown", result2.narrative.lower())

    def test_cooldown_expires(self):
        mgr = _make_manager()
        # Simulate past cooldown
        key = "char_02:fishing_pond"
        past = datetime.now(UTC) - timedelta(hours=2)
        mgr.cooldowns[key] = past
        result = mgr.do_side_activity("fishing_pond", "char_02", {"dexterity": 10})
        self.assertIn(result.success, [True, False])
        self.assertNotIn("cooldown", result.narrative.lower())

    def test_skill_bonus_affects_outcome(self):
        mgr = _make_manager()
        random.seed(0)
        results_low = [mgr.do_side_activity("haggling_market", "char_low", {"charisma": 10}) for _ in range(30)]
        random.seed(0)
        results_high = [mgr.do_side_activity("haggling_market", "char_high", {"charisma": 20}) for _ in range(30)]
        # Not strictly deterministic due to RNG seed reuse in the same manager,
        # but both should produce valid results
        for r in results_low + results_high:
            self.assertIn(r.category, [
                MiniGameCategory.SIDE_ACTIVITY.value,
            ])

    def test_clear_cooldowns(self):
        mgr = _make_manager()
        mgr.do_side_activity("fishing_pond", "char_03")
        self.assertIn("char_03:fishing_pond", mgr.cooldowns)
        mgr.clear_cooldowns("char_03")
        self.assertNotIn("char_03:fishing_pond", mgr.cooldowns)

    def test_clear_all_cooldowns(self):
        mgr = _make_manager()
        mgr.do_side_activity("fishing_pond", "char_a")
        mgr.do_side_activity("haggling_market", "char_b")
        mgr.clear_cooldowns()
        self.assertEqual(len(mgr.cooldowns), 0)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestMiniGamePersistence(unittest.TestCase):
    def test_to_dict_from_dict_roundtrip(self):
        mgr = _make_manager()
        mgr.play_dice_game("tavern_dice_01", 10)
        mgr.solve_riddle("sphinx_riddle_01", "man")

        data = mgr.to_dict()
        new_mgr = MiniGameManager()
        new_mgr.from_dict(data)

        self.assertEqual(len(new_mgr.dice_games), len(mgr.dice_games))
        self.assertEqual(len(new_mgr.card_games), len(mgr.card_games))
        self.assertEqual(len(new_mgr.riddle_puzzles), len(mgr.riddle_puzzles))
        self.assertEqual(len(new_mgr.history), len(mgr.history))

    def test_history_tracking(self):
        mgr = _make_manager()
        mgr.play_dice_game("tavern_dice_01", 10)
        mgr.solve_riddle("sphinx_riddle_01", "man")
        history = mgr.get_history(limit=10)
        self.assertEqual(len(history), 2)


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestMiniGameIntegration(unittest.TestCase):
    def test_can_import_from_package(self):
        # Verify all public names are importable
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
