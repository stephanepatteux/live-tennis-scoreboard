"""Provider base class and the normalised match shape the front-end consumes.

Every provider returns a list of match dicts with EXACTLY these keys, so the
browser board (``static/js/tennis-trader.js``) does not care whether the data is
live or demo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..scoring import compute_alerts, estimate_win_prob_p1


class Provider(ABC):
    """A source of live matches."""

    name = "base"

    @abstractmethod
    def get_live_matches(self) -> list[dict]:
        """Return normalised match dicts (see :func:`build_match`)."""
        raise NotImplementedError


def _normalise_tour(tour) -> str:
    t = (str(tour or "")).strip().lower()
    if t in ("men", "atp"):
        return "atp"
    if t in ("women", "wta"):
        return "wta"
    return t or "unknown"


def build_match(
    *,
    id,
    p1,
    p2,
    tour=None,
    tournament=None,
    surface=None,
    fmt=None,
    is_doubles=False,
    sets_p1=0,
    sets_p2=0,
    games_p1=0,
    games_p2=0,
    points_p1="0",
    points_p2="0",
    server=0,
    is_tiebreak=False,
    set_history="",
    win_prob_p1=None,
    model_fallback=True,
) -> dict:
    """Assemble one normalised match, computing alerts and (optionally) the model.

    ``win_prob_p1`` may be supplied by the provider (e.g. Live Tennis API Ultra);
    when it is ``None`` and ``model_fallback`` is on, the local heuristic fills it.
    """
    alerts, alert_label, alert_priority = compute_alerts(
        points_p1, points_p2, server, is_tiebreak
    )

    if win_prob_p1 is None and model_fallback:
        win_prob_p1 = estimate_win_prob_p1(
            sets_p1,
            sets_p2,
            games_p1,
            games_p2,
            points_p1,
            points_p2,
            server,
            is_tiebreak,
        )

    return {
        "id": id,
        "tour": _normalise_tour(tour),
        "p1": p1,
        "p2": p2,
        "tournament": tournament,
        "surface": (surface or "").lower() or None,
        "format": fmt,
        "is_doubles": bool(is_doubles),
        "sets_p1": sets_p1,
        "sets_p2": sets_p2,
        "games_p1": games_p1,
        "games_p2": games_p2,
        "points_p1": points_p1,
        "points_p2": points_p2,
        "server": server if server in (1, 2) else 0,
        "is_tiebreak": bool(is_tiebreak),
        "set_history": set_history,
        "alerts": alerts,
        "alert_label": alert_label,
        "alert_priority": alert_priority,
        "win_prob_p1": win_prob_p1,
    }
