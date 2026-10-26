"""
RPG-10-08: Mini-Games System
Gambling, puzzles, and side activities with rewards.

Integrates with the skill check system, economy, and character progression.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MiniGameCategory(Enum):
    GAMBLING = "gambling"
    PUZZLE = "puzzle"
    SIDE_ACTIVITY = "side_activity"


class MiniGameDifficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GamblingType(Enum):
    DICE = "dice"
    CARDS = "cards"


class PuzzleType(Enum):
    RIDDLE = "riddle"
    PATTERN = "pattern"
    LOGIC = "logic"


class SideActivityType(Enum):
    FISHING = "fishing"
    LOCKPICKING = "lockpicking"
    HAGGLING = "haggling"


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class MiniGameResult:
    """
    Outcome of a single mini-game session.
    """

    success: bool
    category: str
    game_type: str
    reward_gold: int = 0
    reward_xp: int = 0
    reward_items: list[dict[str, Any]] = field(default_factory=list)
    narrative: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "category": self.category,
            "game_type": self.game_type,
            "reward_gold": self.reward_gold,
            "reward_xp": self.reward_xp,
            "reward_items": [dict(i) for i in self.reward_items],
            "narrative": self.narrative,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MiniGameResult:
        return MiniGameResult(
            success=data["success"],
            category=data["category"],
            game_type=data["game_type"],
            reward_gold=data.get("reward_gold", 0),
            reward_xp=data.get("reward_xp", 0),
            reward_items=[dict(i) for i in data.get("reward_items", [])],
            narrative=data.get("narrative", ""),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Definitions (static data)
# ---------------------------------------------------------------------------

@dataclass
class DiceGameDefinition:
    """
    Static blueprint for a dice gambling game.
    """

    id: str
    name: str
    description: str
    min_bet: int = 1
    max_bet: int = 100
    house_edge: float = 0.05
    win_condition: str = "higher"
    target_number: int = 7
    dice_count: int = 2
    dice_sides: int = 6
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "min_bet": self.min_bet,
            "max_bet": self.max_bet,
            "house_edge": self.house_edge,
            "win_condition": self.win_condition,
            "target_number": self.target_number,
            "dice_count": self.dice_count,
            "dice_sides": self.dice_sides,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DiceGameDefinition:
        return DiceGameDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            min_bet=data.get("min_bet", 1),
            max_bet=data.get("max_bet", 100),
            house_edge=data.get("house_edge", 0.05),
            win_condition=data.get("win_condition", "higher"),
            target_number=data.get("target_number", 7),
            dice_count=data.get("dice_count", 2),
            dice_sides=data.get("dice_sides", 6),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CardGameDefinition:
    """
    Static blueprint for a card gambling game.
    """

    id: str
    name: str
    description: str
    min_bet: int = 1
    max_bet: int = 100
    game_type: str = "high_card"
    deck_size: int = 52
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "min_bet": self.min_bet,
            "max_bet": self.max_bet,
            "game_type": self.game_type,
            "deck_size": self.deck_size,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CardGameDefinition:
        return CardGameDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            min_bet=data.get("min_bet", 1),
            max_bet=data.get("max_bet", 100),
            game_type=data.get("game_type", "high_card"),
            deck_size=data.get("deck_size", 52),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RiddlePuzzleDefinition:
    """
    Static blueprint for a riddle puzzle.
    """

    id: str
    name: str
    description: str
    question: str
    answer: str
    hints: list[str] = field(default_factory=list)
    reward_gold: int = 0
    reward_xp: int = 0
    difficulty: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "question": self.question,
            "answer": self.answer,
            "hints": list(self.hints),
            "reward_gold": self.reward_gold,
            "reward_xp": self.reward_xp,
            "difficulty": self.difficulty,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RiddlePuzzleDefinition:
        return RiddlePuzzleDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            question=data["question"],
            answer=data["answer"],
            hints=data.get("hints", []),
            reward_gold=data.get("reward_gold", 0),
            reward_xp=data.get("reward_xp", 0),
            difficulty=data.get("difficulty", "medium"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PatternPuzzleDefinition:
    """
    Static blueprint for a pattern-completion puzzle.
    """

    id: str
    name: str
    description: str
    sequence: list[int]
    next_in_sequence: int
    hints: list[str] = field(default_factory=list)
    reward_gold: int = 0
    reward_xp: int = 0
    difficulty: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sequence": list(self.sequence),
            "next_in_sequence": self.next_in_sequence,
            "hints": list(self.hints),
            "reward_gold": self.reward_gold,
            "reward_xp": self.reward_xp,
            "difficulty": self.difficulty,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PatternPuzzleDefinition:
        return PatternPuzzleDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            sequence=list(data.get("sequence", [])),
            next_in_sequence=data["next_in_sequence"],
            hints=data.get("hints", []),
            reward_gold=data.get("reward_gold", 0),
            reward_xp=data.get("reward_xp", 0),
            difficulty=data.get("difficulty", "medium"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class LogicPuzzleDefinition:
    """
    Static blueprint for a simple logic puzzle.
    """

    id: str
    name: str
    description: str
    prompt: str
    correct_choice: str
    choices: list[str]
    hints: list[str] = field(default_factory=list)
    reward_gold: int = 0
    reward_xp: int = 0
    difficulty: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "correct_choice": self.correct_choice,
            "choices": list(self.choices),
            "hints": list(self.hints),
            "reward_gold": self.reward_gold,
            "reward_xp": self.reward_xp,
            "difficulty": self.difficulty,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> LogicPuzzleDefinition:
        return LogicPuzzleDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            prompt=data["prompt"],
            correct_choice=data["correct_choice"],
            choices=data.get("choices", []),
            hints=data.get("hints", []),
            reward_gold=data.get("reward_gold", 0),
            reward_xp=data.get("reward_xp", 0),
            difficulty=data.get("difficulty", "medium"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SideActivityDefinition:
    """
    Static blueprint for a side activity.
    """

    id: str
    name: str
    description: str
    activity_type: str  # SideActivityType.value
    difficulty: str
    min_reward_gold: int = 0
    max_reward_gold: int = 0
    min_reward_xp: int = 0
    max_reward_xp: int = 0
    required_item_id: str = ""
    cooldown_hours: int = 0
    success_chance: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "activity_type": self.activity_type,
            "difficulty": self.difficulty,
            "min_reward_gold": self.min_reward_gold,
            "max_reward_gold": self.max_reward_gold,
            "min_reward_xp": self.min_reward_xp,
            "max_reward_xp": self.max_reward_xp,
            "required_item_id": self.required_item_id,
            "cooldown_hours": self.cooldown_hours,
            "success_chance": self.success_chance,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SideActivityDefinition:
        return SideActivityDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            activity_type=data.get("activity_type", SideActivityType.FISHING.value),
            difficulty=data.get("difficulty", "easy"),
            min_reward_gold=data.get("min_reward_gold", 0),
            max_reward_gold=data.get("max_reward_gold", 0),
            min_reward_xp=data.get("min_reward_xp", 0),
            max_reward_xp=data.get("max_reward_xp", 0),
            required_item_id=data.get("required_item_id", ""),
            cooldown_hours=data.get("cooldown_hours", 0),
            success_chance=data.get("success_chance", 0.7),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class MiniGameManager:
    """
    Manages registration and resolution of mini-games.
    Tracks per-character cooldowns and activity history.
    """

    def __init__(self) -> None:
        self.dice_games: dict[str, DiceGameDefinition] = {}
        self.card_games: dict[str, CardGameDefinition] = {}
        self.riddle_puzzles: dict[str, RiddlePuzzleDefinition] = {}
        self.pattern_puzzles: dict[str, PatternPuzzleDefinition] = {}
        self.logic_puzzles: dict[str, LogicPuzzleDefinition] = {}
        self.side_activities: dict[str, SideActivityDefinition] = {}
        self.cooldowns: dict[str, datetime] = {}
        self.history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_dice_game(self, game: DiceGameDefinition) -> None:
        self.dice_games[game.id] = game

    def register_card_game(self, game: CardGameDefinition) -> None:
        self.card_games[game.id] = game

    def register_riddle(self, riddle: RiddlePuzzleDefinition) -> None:
        self.riddle_puzzles[riddle.id] = riddle

    def register_pattern_puzzle(self, puzzle: PatternPuzzleDefinition) -> None:
        self.pattern_puzzles[puzzle.id] = puzzle

    def register_logic_puzzle(self, puzzle: LogicPuzzleDefinition) -> None:
        self.logic_puzzles[puzzle.id] = puzzle

    def register_side_activity(self, activity: SideActivityDefinition) -> None:
        self.side_activities[activity.id] = activity

    # ------------------------------------------------------------------
    # Gambling
    # ------------------------------------------------------------------

    def play_dice_game(
        self,
        game_id: str,
        bet: int,
        character_attributes: dict[str, int] | None = None,
    ) -> MiniGameResult:
        """
        Resolve a dice gambling round.

        Rules (higher):
          - Roll `dice_count` d`dice_sides`.
          - Total must beat `target_number` to win.
          - House edge reduces payout on win.
        """
        character_attributes = character_attributes or {}
        game = self.dice_games.get(game_id)
        if game is None:
            return MiniGameResult(
                success=False,
                category=MiniGameCategory.GAMBLING.value,
                game_type=GamblingType.DICE.value,
                narrative=f"Unknown dice game: {game_id}",
            )

        if bet < game.min_bet or bet > game.max_bet:
            return MiniGameResult(
                success=False,
                category=MiniGameCategory.GAMBLING.value,
                game_type=GamblingType.DICE.value,
                narrative=f"Bet must be between {game.min_bet} and {game.max_bet}.",
            )

        # Luck bonus from character attributes (dexterity or luck if present)
        luck_mod = character_attributes.get("luck", 0)
        if luck_mod == 0:
            luck_mod = max(0, character_attributes.get("dexterity", 10) - 10) // 2

        dice = [random.randint(1, game.dice_sides) for _ in range(game.dice_count)]
        total = sum(dice) + luck_mod

        won = False
        if game.win_condition == "higher":
            won = total > game.target_number
        elif game.win_condition == "lower":
            won = total < game.target_number
        elif game.win_condition == "exact":
            won = total == game.target_number
        elif game.win_condition == "total":
            won = total >= game.target_number

        if won:
            payout = int(bet * (1 + game.house_edge))
            narrative = (
                f"Rolled {dice} (total {total}) — you win {payout} gold!"
            )
            result = MiniGameResult(
                success=True,
                category=MiniGameCategory.GAMBLING.value,
                game_type=GamblingType.DICE.value,
                reward_gold=payout,
                narrative=narrative,
                metadata={"dice": dice, "total": total, "bet": bet},
            )
        else:
            narrative = f"Rolled {dice} (total {total}) — house wins."
            result = MiniGameResult(
                success=False,
                category=MiniGameCategory.GAMBLING.value,
                game_type=GamblingType.DICE.value,
                reward_gold=-bet,
                narrative=narrative,
                metadata={"dice": dice, "total": total, "bet": bet},
            )

        self.history.append(result.to_dict())
        return result

    def play_card_game(
        self,
        game_id: str,
        bet: int,
    ) -> MiniGameResult:
        """
        Resolve a card gambling round.

        Supported types:
          - high_card: highest card wins (2-14, 14 = Ace)
          - blackjack: simplified — dealer hits to 17, player stays
        """
        game = self.card_games.get(game_id)
        if game is None:
            return MiniGameResult(
                success=False,
                category=MiniGameCategory.GAMBLING.value,
                game_type=GamblingType.CARDS.value,
                narrative=f"Unknown card game: {game_id}",
            )

        if bet < game.min_bet or bet > game.max_bet:
            return MiniGameResult(
                success=False,
                category=MiniGameCategory.GAMBLING.value,
                game_type=GamblingType.CARDS.value,
                narrative=f"Bet must be between {game.min_bet} and {game.max_bet}.",
            )

        if game.game_type == "high_card":
            player_card = random.randint(1, game.deck_size)
            dealer_card = random.randint(1, game.deck_size)
            won = player_card > dealer_card
            narrative = (
                f"You drew {player_card}, dealer drew {dealer_card}."
            )
            if won:
                payout = int(bet * 2)
                narrative += f" You win {payout} gold!"
                result = MiniGameResult(
                    success=True,
                    category=MiniGameCategory.GAMBLING.value,
                    game_type=GamblingType.CARDS.value,
                    reward_gold=payout - bet,
                    narrative=narrative,
                    metadata={"player_card": player_card, "dealer_card": dealer_card, "bet": bet},
                )
            else:
                if player_card == dealer_card:
                    narrative += " Push — bet returned."
                    result = MiniGameResult(
                        success=False,
                        category=MiniGameCategory.GAMBLING.value,
                        game_type=GamblingType.CARDS.value,
                        reward_gold=0,
                        narrative=narrative,
                        metadata={"player_card": player_card, "dealer_card": dealer_card, "bet": bet},
                    )
                else:
                    narrative += " House wins."
                    result = MiniGameResult(
                        success=False,
                        category=MiniGameCategory.GAMBLING.value,
                        game_type=GamblingType.CARDS.value,
                        reward_gold=-bet,
                        narrative=narrative,
                        metadata={"player_card": player_card, "dealer_card": dealer_card, "bet": bet},
                    )

        elif game.game_type == "blackjack":
            player_total = self._draw_blackjack_hand()
            dealer_total = self._dealer_blackjack_hand()
            player_bust = player_total > 21
            dealer_bust = dealer_total > 21

            if player_bust:
                narrative = f"You busted at {player_total}. Dealer had {dealer_total}."
                result = MiniGameResult(
                    success=False,
                    category=MiniGameCategory.GAMBLING.value,
                    game_type=GamblingType.CARDS.value,
                    reward_gold=-bet,
                    narrative=narrative,
                    metadata={"player_total": player_total, "dealer_total": dealer_total, "bet": bet},
                )
            elif dealer_bust:
                payout = int(bet * 1.5)
                narrative = f"Dealer busted at {dealer_total}. You win {payout} gold!"
                result = MiniGameResult(
                    success=True,
                    category=MiniGameCategory.GAMBLING.value,
                    game_type=GamblingType.CARDS.value,
                    reward_gold=payout - bet,
                    narrative=narrative,
                    metadata={"player_total": player_total, "dealer_total": dealer_total, "bet": bet},
                )
            elif player_total > dealer_total:
                payout = int(bet * 1.5)
                narrative = f"You have {player_total}, dealer has {dealer_total}. You win {payout} gold!"
                result = MiniGameResult(
                    success=True,
                    category=MiniGameCategory.GAMBLING.value,
                    game_type=GamblingType.CARDS.value,
                    reward_gold=payout - bet,
                    narrative=narrative,
                    metadata={"player_total": player_total, "dealer_total": dealer_total, "bet": bet},
                )
            else:
                narrative = f"You have {player_total}, dealer has {dealer_total}. House wins."
                result = MiniGameResult(
                    success=False,
                    category=MiniGameCategory.GAMBLING.value,
                    game_type=GamblingType.CARDS.value,
                    reward_gold=-bet,
                    narrative=narrative,
                    metadata={"player_total": player_total, "dealer_total": dealer_total, "bet": bet},
                )
        else:
            result = MiniGameResult(
                success=False,
                category=MiniGameCategory.GAMBLING.value,
                game_type=GamblingType.CARDS.value,
                narrative=f"Unsupported card game type: {game.game_type}",
            )

        self.history.append(result.to_dict())
        return result

    def _draw_blackjack_hand(self) -> int:
        hand = 0
        while hand < 17:
            card = random.randint(1, 11)
            hand += card
        return hand

    def _dealer_blackjack_hand(self) -> int:
        hand = 0
        while hand < 17:
            card = random.randint(1, 11)
            hand += card
        return hand

    # ------------------------------------------------------------------
    # Puzzles
    # ------------------------------------------------------------------

    def solve_riddle(
        self,
        puzzle_id: str,
        answer: str,
    ) -> MiniGameResult:
        """
        Submit an answer to a riddle puzzle.
        """
        puzzle = self.riddle_puzzles.get(puzzle_id)
        if puzzle is None:
            return MiniGameResult(
                success=False,
                category=MiniGameCategory.PUZZLE.value,
                game_type=PuzzleType.RIDDLE.value,
                narrative=f"Unknown riddle: {puzzle_id}",
            )

        correct = answer.strip().lower() == puzzle.answer.strip().lower()
        if correct:
            result = MiniGameResult(
                success=True,
                category=MiniGameCategory.PUZZLE.value,
                game_type=PuzzleType.RIDDLE.value,
                reward_gold=puzzle.reward_gold,
                reward_xp=puzzle.reward_xp,
                narrative=f"Correct! {puzzle.description}",
                metadata={"puzzle_id": puzzle_id, "difficulty": puzzle.difficulty},
            )
        else:
            result = MiniGameResult(
                success=False,
                category=MiniGameCategory.PUZZLE.value,
                game_type=PuzzleType.RIDDLE.value,
                narrative=f"Wrong answer. {puzzle.description}",
                metadata={"puzzle_id": puzzle_id, "difficulty": puzzle.difficulty},
            )

        self.history.append(result.to_dict())
        return result

    def solve_pattern(
        self,
        puzzle_id: str,
        player_answer: int,
    ) -> MiniGameResult:
        """
        Submit an answer to a pattern puzzle.
        """
        puzzle = self.pattern_puzzles.get(puzzle_id)
        if puzzle is None:
            return MiniGameResult(
                success=False,
                category=MiniGameCategory.PUZZLE.value,
                game_type=PuzzleType.PATTERN.value,
                narrative=f"Unknown pattern puzzle: {puzzle_id}",
            )

        correct = player_answer == puzzle.next_in_sequence
        if correct:
            result = MiniGameResult(
                success=True,
                category=MiniGameCategory.PUZZLE.value,
                game_type=PuzzleType.PATTERN.value,
                reward_gold=puzzle.reward_gold,
                reward_xp=puzzle.reward_xp,
                narrative=f"Correct! The next number is {puzzle.next_in_sequence}.",
                metadata={"puzzle_id": puzzle_id, "sequence": puzzle.sequence},
            )
        else:
            result = MiniGameResult(
                success=False,
                category=MiniGameCategory.PUZZLE.value,
                game_type=PuzzleType.PATTERN.value,
                narrative=f"Wrong. The sequence was {puzzle.sequence}. Next is {puzzle.next_in_sequence}.",
                metadata={"puzzle_id": puzzle_id, "sequence": puzzle.sequence},
            )

        self.history.append(result.to_dict())
        return result

    def solve_logic(
        self,
        puzzle_id: str,
        choice: str,
    ) -> MiniGameResult:
        """
        Submit a choice for a logic puzzle.
        """
        puzzle = self.logic_puzzles.get(puzzle_id)
        if puzzle is None:
            return MiniGameResult(
                success=False,
                category=MiniGameCategory.PUZZLE.value,
                game_type=PuzzleType.LOGIC.value,
                narrative=f"Unknown logic puzzle: {puzzle_id}",
            )

        correct = choice == puzzle.correct_choice
        if correct:
            result = MiniGameResult(
                success=True,
                category=MiniGameCategory.PUZZLE.value,
                game_type=PuzzleType.LOGIC.value,
                reward_gold=puzzle.reward_gold,
                reward_xp=puzzle.reward_xp,
                narrative=f"Correct! {puzzle.prompt}",
                metadata={"puzzle_id": puzzle_id, "difficulty": puzzle.difficulty},
            )
        else:
            result = MiniGameResult(
                success=False,
                category=MiniGameCategory.PUZZLE.value,
                game_type=PuzzleType.LOGIC.value,
                narrative=f"Incorrect. {puzzle.prompt}",
                metadata={"puzzle_id": puzzle_id, "difficulty": puzzle.difficulty},
            )

        self.history.append(result.to_dict())
        return result

    # ------------------------------------------------------------------
    # Side Activities
    # ------------------------------------------------------------------

    def do_side_activity(
        self,
        activity_id: str,
        character_id: str,
        character_attributes: dict[str, int] | None = None,
    ) -> MiniGameResult:
        """
        Perform a side activity. Success is determined by success_chance
        modified by character attributes.
        """
        character_attributes = character_attributes or {}
        activity = self.side_activities.get(activity_id)
        if activity is None:
            return MiniGameResult(
                success=False,
                category=MiniGameCategory.SIDE_ACTIVITY.value,
                game_type=activity_id,
                narrative=f"Unknown side activity: {activity_id}",
            )

        # Check cooldown
        cooldown_key = f"{character_id}:{activity_id}"
        now = datetime.now(UTC)
        if cooldown_key in self.cooldowns:
            last = self.cooldowns[cooldown_key]
            elapsed = (now - last).total_seconds() / 3600.0
            if elapsed < activity.cooldown_hours:
                remaining = activity.cooldown_hours - elapsed
                return MiniGameResult(
                    success=False,
                    category=MiniGameCategory.SIDE_ACTIVITY.value,
                    game_type=activity.activity_type,
                    narrative=f"Activity on cooldown for {remaining:.1f} more hours.",
                    metadata={"cooldown_remaining_hours": remaining},
                )

        # Check required item
        if activity.required_item_id:
            # Caller must verify inventory; manager only records the check
            pass

        # Skill modifier
        skill_bonus = 0.0
        if activity.activity_type == SideActivityType.FISHING.value or activity.activity_type == SideActivityType.LOCKPICKING.value:
            skill_bonus = max(0, character_attributes.get("dexterity", 10) - 10) / 20.0
        elif activity.activity_type == SideActivityType.HAGGLING.value:
            skill_bonus = max(0, character_attributes.get("charisma", 10) - 10) / 20.0

        effective_chance = min(1.0, max(0.0, activity.success_chance + skill_bonus))
        succeeded = random.random() < effective_chance

        if succeeded:
            gold = random.randint(activity.min_reward_gold, activity.max_reward_gold)
            xp = random.randint(activity.min_reward_xp, activity.max_reward_xp)
            narrative = f"{activity.name} succeeded! Earned {gold} gold and {xp} XP."
            result = MiniGameResult(
                success=True,
                category=MiniGameCategory.SIDE_ACTIVITY.value,
                game_type=activity.activity_type,
                reward_gold=gold,
                reward_xp=xp,
                narrative=narrative,
                metadata={"activity_id": activity_id, "effective_chance": effective_chance},
            )
        else:
            narrative = f"{activity.name} failed. Better luck next time."
            result = MiniGameResult(
                success=False,
                category=MiniGameCategory.SIDE_ACTIVITY.value,
                game_type=activity.activity_type,
                narrative=narrative,
                metadata={"activity_id": activity_id, "effective_chance": effective_chance},
            )

        self.cooldowns[cooldown_key] = now
        self.history.append(result.to_dict())
        return result

    # ------------------------------------------------------------------
    # Default content
    # ------------------------------------------------------------------

    def load_defaults(self) -> None:
        """
        Seed the manager with a small set of default mini-games.
        """
        self.register_dice_game(DiceGameDefinition(
            id="tavern_dice_01",
            name="Tavern Dice",
            description="Roll two dice and beat a 7.",
            min_bet=1,
            max_bet=50,
            house_edge=0.05,
            win_condition="higher",
            target_number=7,
            dice_count=2,
            dice_sides=6,
        ))

        self.register_card_game(CardGameDefinition(
            id="tavern_high_card",
            name="High Card",
            description="Simple high-card showdown.",
            min_bet=1,
            max_bet=100,
            game_type="high_card",
            deck_size=52,
        ))

        self.register_card_game(CardGameDefinition(
            id="tavern_blackjack",
            name="Blackjack",
            description="Simplified blackjack. Dealer stands on 17.",
            min_bet=5,
            max_bet=200,
            game_type="blackjack",
            deck_size=52,
        ))

        self.register_riddle(RiddlePuzzleDefinition(
            id="sphinx_riddle_01",
            name="Sphinx Riddle",
            description="The classic riddle of the Sphinx.",
            question="What walks on four legs in the morning, two at noon, and three in the evening?",
            answer="man",
            hints=["Think of a human's lifetime.", "Ages of man."],
            reward_gold=50,
            reward_xp=30,
            difficulty="medium",
        ))

        self.register_pattern_puzzle(PatternPuzzleDefinition(
            id="maze_pattern_01",
            name="Maze Sequence",
            description="A numeric pattern found on an ancient wall.",
            sequence=[2, 4, 8, 16, 32],
            next_in_sequence=64,
            hints=["Double the previous number.", "2^n."],
            reward_gold=40,
            reward_xp=25,
            difficulty="easy",
        ))

        self.register_logic_puzzle(LogicPuzzleDefinition(
            id="guard_logic_01",
            name="Guard Logic",
            description="A guard asks you to choose the truth.",
            prompt="One guard always lies, one always tells the truth. Which do you ask?",
            correct_choice="the truthful guard",
            choices=["the truthful guard", "the lying guard", "either guard", "neither guard"],
            hints=["You want reliable information.", "Truth is your ally."],
            reward_gold=30,
            reward_xp=20,
            difficulty="easy",
        ))

        self.register_side_activity(SideActivityDefinition(
            id="fishing_pond",
            name="Fishing at the Pond",
            description="Spend time fishing for food and gold.",
            activity_type=SideActivityType.FISHING.value,
            difficulty="easy",
            min_reward_gold=1,
            max_reward_gold=15,
            min_reward_xp=5,
            max_reward_xp=15,
            cooldown_hours=1,
            success_chance=0.8,
        ))

        self.register_side_activity(SideActivityDefinition(
            id="lockpick_tutorial",
            name="Lockpicking Practice",
            description="Pick a simple practice lock.",
            activity_type=SideActivityType.LOCKPICKING.value,
            difficulty="easy",
            min_reward_gold=5,
            max_reward_gold=25,
            min_reward_xp=10,
            max_reward_xp=20,
            cooldown_hours=2,
            success_chance=0.6,
        ))

        self.register_side_activity(SideActivityDefinition(
            id="haggling_market",
            name="Market Haggling",
            description="Negotiate with a merchant for a better deal.",
            activity_type=SideActivityType.HAGGLING.value,
            difficulty="medium",
            min_reward_gold=10,
            max_reward_gold=50,
            min_reward_xp=15,
            max_reward_xp=30,
            cooldown_hours=3,
            success_chance=0.5,
        ))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "dice_games": [g.to_dict() for g in self.dice_games.values()],
            "card_games": [g.to_dict() for g in self.card_games.values()],
            "riddle_puzzles": [r.to_dict() for r in self.riddle_puzzles.values()],
            "pattern_puzzles": [p.to_dict() for p in self.pattern_puzzles.values()],
            "logic_puzzles": [p.to_dict() for p in self.logic_puzzles.values()],
            "side_activities": [a.to_dict() for a in self.side_activities.values()],
            "cooldowns": {
                k: v.isoformat()
                for k, v in self.cooldowns.items()
            },
            "history": list(self.history),
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        self.dice_games = {g["id"]: DiceGameDefinition.from_dict(g) for g in data.get("dice_games", [])}
        self.card_games = {g["id"]: CardGameDefinition.from_dict(g) for g in data.get("card_games", [])}
        self.riddle_puzzles = {r["id"]: RiddlePuzzleDefinition.from_dict(r) for r in data.get("riddle_puzzles", [])}
        self.pattern_puzzles = {p["id"]: PatternPuzzleDefinition.from_dict(p) for p in data.get("pattern_puzzles", [])}
        self.logic_puzzles = {p["id"]: LogicPuzzleDefinition.from_dict(p) for p in data.get("logic_puzzles", [])}
        self.side_activities = {a["id"]: SideActivityDefinition.from_dict(a) for a in data.get("side_activities", [])}
        self.cooldowns = {k: datetime.fromisoformat(v) for k, v in data.get("cooldowns", {}).items()}
        self.history = list(data.get("history", []))

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(self.history[-limit:])

    def clear_cooldowns(self, character_id: str | None = None) -> None:
        if character_id is None:
            self.cooldowns.clear()
        else:
            keys_to_remove = [k for k in self.cooldowns if k.startswith(f"{character_id}:")]
            for k in keys_to_remove:
                del self.cooldowns[k]
