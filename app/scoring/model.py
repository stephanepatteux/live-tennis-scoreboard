"""A lightweight, transparent in-play win-probability estimate for player 1.

This is intentionally simple and is NOT the Live Tennis API "Ultra" model. It is a
heuristic used so the board's Model column is populated in demo mode and when a
live key does not include model fields. When the provider supplies a real model
probability (Ultra), that value is used instead and this is not called.

The estimate combines set lead, game lead in the current set, the in-game point
situation, and a small serve bonus, squashed through a logistic function.
"""

from __future__ import annotations

import math

_POINT_RANK = {"0": 0, "15": 1, "30": 2, "40": 3, "ad": 4, "a": 4, "adv": 4}


def _rank(point) -> int:
    return _POINT_RANK.get(str(point).strip().lower(), 0)


def estimate_win_prob_p1(
    sets_p1,
    sets_p2,
    games_p1,
    games_p2,
    points_p1,
    points_p2,
    server,
    is_tiebreak,
) -> float:
    """Return player 1's win probability as a percentage in ``[2, 98]``."""
    score = 0.0

    # Sets are worth the most.
    score += 0.9 * (int(sets_p1 or 0) - int(sets_p2 or 0))

    # Games in the current set.
    score += 0.28 * (int(games_p1 or 0) - int(games_p2 or 0))

    # Small serve edge.
    if server == 1:
        score += 0.18
    elif server == 2:
        score -= 0.18

    # In-game points nudge (muted; a single point rarely swings a match).
    if not is_tiebreak:
        score += 0.12 * (_rank(points_p1) - _rank(points_p2))
    else:
        # In a tiebreak, points are numeric and matter more.
        try:
            score += 0.09 * (int(points_p1) - int(points_p2))
        except (TypeError, ValueError):
            pass

    prob = 1.0 / (1.0 + math.exp(-score))
    pct = max(2.0, min(98.0, prob * 100.0))
    return round(pct, 1)
