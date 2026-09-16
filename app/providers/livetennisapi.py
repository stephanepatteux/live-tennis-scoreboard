"""Live provider backed by the Live Tennis API (https://livetennisapi.com).

The API key is read from the environment and sent as a request header — it is
never exposed to the browser and never committed to this repo. The browser only
ever talks to this app's ``/api/tennis/live`` endpoint.

Endpoint: GET {base}/matches?status=live
Docs:     https://docs.livetennisapi.com  (OpenAPI: /openapi.json)

Scores are PLAYER-MAJOR: ``sets=[p1,p2]``, ``games=[[p1 per set],[p2 per set]]``,
``points=[p1,p2]``, ``server`` is 1 or 2.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import Provider, build_match


class LiveTennisApiProvider(Provider):
    name = "livetennisapi"

    def __init__(self, api_key, base_url, timeout=8.0, model_fallback=True):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.model_fallback = model_fallback

    def _fetch(self, path, params):
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self.base_url}{path}?{query}"
        req = urllib.request.Request(url)
        # Header auth (preferred over ?token= so the key never lands in logs/URLs).
        req.add_header("X-API-Key", self.api_key)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "tennis-trader-board/1.0")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_live_matches(self) -> list[dict]:
        payload = self._fetch("/matches", {"status": "live"})
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        matches = []
        for row in rows:
            try:
                matches.append(self._map(row))
            except Exception:
                # A single malformed row must not sink the whole board.
                continue
        return matches

    def _map(self, m: dict) -> dict:
        players = m.get("players") or {}
        p1 = (players.get("p1") or {}).get("name") or "Player 1"
        p2 = (players.get("p2") or {}).get("name") or "Player 2"

        score = m.get("score") or {}
        sets = score.get("sets") or [0, 0]
        sets_p1, sets_p2 = _pair(sets)

        games = score.get("games")  # [[p1 per set], [p2 per set]] or null (withheld)
        games_p1_list = (games[0] if games and len(games) > 0 else []) or []
        games_p2_list = (games[1] if games and len(games) > 1 else []) or []
        games_p1 = games_p1_list[-1] if games_p1_list else 0
        games_p2 = games_p2_list[-1] if games_p2_list else 0
        set_history = " ".join(
            f"{a}-{b}" for a, b in zip(games_p1_list, games_p2_list)
        )

        points = score.get("points") or ["0", "0"]
        points_p1, points_p2 = _pair(points, default="0")

        win_prob = _to_percent(
            score.get("win_probability_p1_model")
            if score.get("win_probability_p1_model") is not None
            else score.get("win_probability_p1")
        )

        return build_match(
            id=m.get("id"),
            p1=p1,
            p2=p2,
            tour=m.get("tour"),
            tournament=m.get("tournament"),
            surface=m.get("surface"),
            fmt=m.get("format"),
            is_doubles=m.get("is_doubles", False),
            sets_p1=sets_p1,
            sets_p2=sets_p2,
            games_p1=games_p1,
            games_p2=games_p2,
            points_p1=points_p1,
            points_p2=points_p2,
            server=score.get("server") or 0,
            is_tiebreak=score.get("is_tiebreak", False),
            set_history=set_history,
            win_prob_p1=win_prob,
            model_fallback=self.model_fallback,
        )


def _pair(seq, default=0):
    try:
        a = seq[0]
    except (IndexError, TypeError):
        a = default
    try:
        b = seq[1]
    except (IndexError, TypeError):
        b = default
    return a, b


def _to_percent(value):
    """Normalise a win probability to a 0-100 percentage (accepts 0-1 or 0-100)."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if 0.0 <= v <= 1.0:
        v *= 100.0
    return round(v, 1)
