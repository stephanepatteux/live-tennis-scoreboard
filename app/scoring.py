"""Tennis scoring engine.

Implements standard tennis scoring (points -> games -> sets) with deuce/advantage
and tiebreak handling. The engine is intentionally UI-agnostic: it only tracks
state and exposes a serialisable snapshot that templates and JSON endpoints share,
so the practice/demo view and any future live view stay in parity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

POINT_LABELS = ["0", "15", "30", "40"]


@dataclass
class Player:
    name: str
    points: int = 0
    games: int = 0
    sets: int = 0
    tiebreak_points: int = 0


@dataclass
class TennisMatch:
    """A best-of-N-sets singles tennis match.

    Rules implemented:
      - A game is won at 4+ points with a 2-point margin (deuce/advantage).
      - A set is won at 6+ games with a 2-game margin.
      - At 6-6 a 7-point (margin 2) tiebreak decides the set.
      - The match is won by the first player to win ``sets_to_win`` sets.
    """

    player1: Player
    player2: Player
    sets_to_win: int = 2
    completed_sets: list[tuple[int, int]] = field(default_factory=list)
    in_tiebreak: bool = False
    winner: Optional[str] = None

    @classmethod
    def new(
        cls, name1: str = "Player 1", name2: str = "Player 2", sets_to_win: int = 2
    ) -> "TennisMatch":
        return cls(player1=Player(name1), player2=Player(name2), sets_to_win=sets_to_win)

    def _players(self) -> tuple[Player, Player]:
        return self.player1, self.player2

    def score_point(self, player_index: int) -> None:
        """Award a point to player 0 (player1) or 1 (player2)."""
        if self.winner is not None:
            return
        if player_index not in (0, 1):
            raise ValueError("player_index must be 0 or 1")

        scorer, opponent = self._players()
        if player_index == 1:
            scorer, opponent = opponent, scorer

        if self.in_tiebreak:
            self._score_tiebreak_point(scorer, opponent)
        else:
            self._score_game_point(scorer, opponent)

    def _score_game_point(self, scorer: Player, opponent: Player) -> None:
        scorer.points += 1
        if scorer.points >= 4 and scorer.points - opponent.points >= 2:
            self._win_game(scorer, opponent)

    def _score_tiebreak_point(self, scorer: Player, opponent: Player) -> None:
        scorer.tiebreak_points += 1
        if (
            scorer.tiebreak_points >= 7
            and scorer.tiebreak_points - opponent.tiebreak_points >= 2
        ):
            scorer.games += 1
            self._win_set(scorer, opponent)

    def _win_game(self, scorer: Player, opponent: Player) -> None:
        scorer.games += 1
        scorer.points = 0
        opponent.points = 0

        if scorer.games == 6 and opponent.games == 6:
            self.in_tiebreak = True
            return

        if scorer.games >= 6 and scorer.games - opponent.games >= 2:
            self._win_set(scorer, opponent)

    def _win_set(self, scorer: Player, opponent: Player) -> None:
        # Record the completed set from player1's perspective for the history strip.
        p1, p2 = self._players()
        self.completed_sets.append((p1.games, p2.games))

        scorer.sets += 1
        self.in_tiebreak = False
        scorer.games = opponent.games = 0
        scorer.points = opponent.points = 0
        scorer.tiebreak_points = opponent.tiebreak_points = 0

        if scorer.sets >= self.sets_to_win:
            self.winner = scorer.name

    def _display_point(self, player: Player, other: Player) -> str:
        if self.in_tiebreak:
            return str(player.tiebreak_points)
        if player.points >= 3 and other.points >= 3:
            if player.points == other.points:
                return "40"  # deuce shown as 40-40
            if player.points > other.points:
                return "Ad"
            return "40"
        return POINT_LABELS[min(player.points, 3)]

    def snapshot(self) -> dict:
        """Return a JSON/template-friendly view of the current match state."""
        p1, p2 = self.player1, self.player2
        deuce = (
            not self.in_tiebreak
            and p1.points >= 3
            and p2.points >= 3
            and p1.points == p2.points
        )
        return {
            "players": [
                {
                    "name": p1.name,
                    "sets": p1.sets,
                    "games": p1.games,
                    "point": self._display_point(p1, p2),
                    "serving": False,
                },
                {
                    "name": p2.name,
                    "sets": p2.sets,
                    "games": p2.games,
                    "point": self._display_point(p2, p1),
                    "serving": False,
                },
            ],
            "completed_sets": self.completed_sets,
            "in_tiebreak": self.in_tiebreak,
            "deuce": deuce,
            "winner": self.winner,
            "sets_to_win": self.sets_to_win,
        }
