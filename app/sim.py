"""A tiny tennis match simulation used by the demo push source.

This exists only so the public repo is demonstrable with NO Ultra key: it fakes a
point-by-point stream. It is NOT a substitute for the real feed — real per-point
data requires a Live Tennis API Ultra key (see the README).
"""

from __future__ import annotations

import random

from .matches import build_match

# id, p1, p2, tour, tournament, surface, format, doubles
SEED_MATCHES = [
    (9001, "Sinner", "Alcaraz", "atp", "ATP Finals", "hard", "Bo3", False),
    (9002, "Swiatek", "Sabalenka", "wta", "WTA Finals", "hard", "Bo3", False),
    (9003, "Djokovic", "Medvedev", "atp", "Paris Masters", "hard", "Bo3", False),
    (9004, "Gauff", "Rybakina", "wta", "Stuttgart Open", "clay", "Bo3", False),
    (9005, "Zverev", "Rune", "atp", "Madrid Open", "clay", "Bo3", False),
    (9006, "Pegula", "Vondrousova", "wta", "Wimbledon", "grass", "Bo3", False),
    (9007, "Fritz", "De Minaur", "atp", "Queen's Club", "grass", "Bo3", False),
    (9008, "Errani / Paolini", "Dabrowski / Routliffe", "wta", "Rome Masters", "clay", "Bo3", True),
]


class MatchSim:
    """A best-of-3 singles/doubles state machine advanced one point at a time."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        self.completed_sets = []  # list of (g1, g2)
        self.sets_p1 = 0
        self.sets_p2 = 0
        self.games_p1 = 0
        self.games_p2 = 0
        self.pts_p1 = 0
        self.pts_p2 = 0
        self.tb_p1 = 0
        self.tb_p2 = 0
        self.server = self.rng.choice((1, 2))
        self.is_tiebreak = False
        self.done = False

    def play_point(self):
        if self.done:
            self.reset()
            return
        server_wins = self.rng.random() < 0.63
        winner = self.server if server_wins else (3 - self.server)
        if self.is_tiebreak:
            self._tiebreak_point(winner)
        else:
            self._game_point(winner)

    def _game_point(self, winner):
        if winner == 1:
            self.pts_p1 += 1
        else:
            self.pts_p2 += 1
        a, b = self.pts_p1, self.pts_p2
        if max(a, b) >= 4 and abs(a - b) >= 2:
            self._win_game(1 if a > b else 2)

    def _win_game(self, winner):
        if winner == 1:
            self.games_p1 += 1
        else:
            self.games_p2 += 1
        self.pts_p1 = self.pts_p2 = 0
        self.server = 3 - self.server
        g1, g2 = self.games_p1, self.games_p2
        if g1 == 6 and g2 == 6:
            self.is_tiebreak = True
            return
        if max(g1, g2) >= 6 and abs(g1 - g2) >= 2:
            self._win_set(1 if g1 > g2 else 2)

    def _tiebreak_point(self, winner):
        if winner == 1:
            self.tb_p1 += 1
        else:
            self.tb_p2 += 1
        a, b = self.tb_p1, self.tb_p2
        if max(a, b) >= 7 and abs(a - b) >= 2:
            if a > b:
                self.games_p1 += 1
                self._win_set(1)
            else:
                self.games_p2 += 1
                self._win_set(2)

    def _win_set(self, winner):
        self.completed_sets.append((self.games_p1, self.games_p2))
        if winner == 1:
            self.sets_p1 += 1
        else:
            self.sets_p2 += 1
        self.games_p1 = self.games_p2 = 0
        self.pts_p1 = self.pts_p2 = 0
        self.tb_p1 = self.tb_p2 = 0
        self.is_tiebreak = False
        if max(self.sets_p1, self.sets_p2) >= 2:
            self.done = True

    def _disp(self, a, b):
        if a >= 3 and b >= 3:
            if a == b:
                return "40"
            return "AD" if a > b else "40"
        return ["0", "15", "30", "40"][min(a, 3)]

    def points(self):
        if self.is_tiebreak:
            return str(self.tb_p1), str(self.tb_p2)
        return self._disp(self.pts_p1, self.pts_p2), self._disp(self.pts_p2, self.pts_p1)

    def set_history(self):
        parts = [f"{a}-{b}" for a, b in self.completed_sets]
        parts.append(f"{self.games_p1}-{self.games_p2}")
        return " ".join(parts)


def sim_to_match(sim: MatchSim, cfg) -> dict:
    mid, p1, p2, tour, tournament, surface, fmt, doubles = cfg
    pts1, pts2 = sim.points()
    return build_match(
        id=mid,
        p1=p1,
        p2=p2,
        tour=tour,
        tournament=tournament,
        surface=surface,
        fmt=fmt,
        is_doubles=doubles,
        sets_p1=sim.sets_p1,
        sets_p2=sim.sets_p2,
        games_p1=sim.games_p1,
        games_p2=sim.games_p2,
        points_p1=pts1,
        points_p2=pts2,
        server=sim.server,
        is_tiebreak=sim.is_tiebreak,
        set_history=sim.set_history(),
        win_prob_p1=None,
        model_fallback=True,
    )
