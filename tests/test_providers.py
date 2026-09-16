"""Tests for the demo and live providers, and provider selection."""

import os
from unittest import mock

from app.providers import DemoProvider, LiveTennisApiProvider, get_provider

REQUIRED_KEYS = {
    "id", "tour", "p1", "p2", "tournament", "surface", "format", "is_doubles",
    "sets_p1", "sets_p2", "games_p1", "games_p2", "points_p1", "points_p2",
    "server", "is_tiebreak", "set_history", "alerts", "alert_label",
    "alert_priority", "win_prob_p1",
}


def test_get_provider_defaults_to_demo_without_key():
    with mock.patch.dict(os.environ, {}, clear=True):
        assert isinstance(get_provider(), DemoProvider)


def test_get_provider_uses_live_with_key():
    with mock.patch.dict(os.environ, {"LIVE_TENNIS_API_KEY": "secret123"}, clear=True):
        p = get_provider()
        assert isinstance(p, LiveTennisApiProvider)
        assert p.api_key == "secret123"


def test_demo_provider_shape_and_model():
    matches = DemoProvider().get_live_matches()
    assert len(matches) >= 6
    for m in matches:
        assert REQUIRED_KEYS.issubset(m.keys())
        assert m["tour"] in ("atp", "wta")
        assert m["win_prob_p1"] is not None  # local model fills it


def test_live_provider_maps_api_schema():
    provider = LiveTennisApiProvider(api_key="x", base_url="http://api.test/v1")
    sample = {
        "data": [
            {
                "id": 42,
                "tournament": "Test Open",
                "tour": "ATP",
                "surface": "Hard",
                "format": "Bo3",
                "is_doubles": False,
                "players": {"p1": {"name": "Alice"}, "p2": {"name": "Bob"}},
                "score": {
                    "sets": [1, 0],
                    "games": [[6, 3], [4, 4]],
                    "points": ["40", "15"],
                    "server": 2,
                    "is_tiebreak": False,
                    "win_probability_p1": 0.72,
                },
            }
        ],
        "meta": {"count": 1},
    }
    with mock.patch.object(provider, "_fetch", return_value=sample):
        matches = provider.get_live_matches()

    assert len(matches) == 1
    m = matches[0]
    assert m["id"] == 42
    assert m["tour"] == "atp"
    assert m["surface"] == "hard"
    assert m["p1"] == "Alice" and m["p2"] == "Bob"
    assert m["sets_p1"] == 1 and m["sets_p2"] == 0
    # Current games = last entry of each per-set list.
    assert m["games_p1"] == 3 and m["games_p2"] == 4
    assert m["set_history"] == "6-4 3-4"
    assert m["points_p1"] == "40" and m["points_p2"] == "15"
    # p1 returning on p2's serve at 40-15 -> 30-40 style break point against p2.
    assert "break-point" in m["alerts"]
    # Provider model (0.72) is normalised to a percentage and preferred.
    assert m["win_prob_p1"] == 72.0


def test_live_provider_handles_withheld_games_and_null_score():
    provider = LiveTennisApiProvider(api_key="x", base_url="http://api.test/v1")
    sample = {
        "data": [
            {
                "id": 7,
                "players": {"p1": {"name": "A"}, "p2": {"name": "B"}},
                "score": {"sets": [0, 0], "games": None, "points": ["0", "0"], "server": 1},
            },
            {"id": 8, "players": {"p1": {"name": "C"}, "p2": {"name": "D"}}, "score": None},
        ]
    }
    with mock.patch.object(provider, "_fetch", return_value=sample):
        matches = provider.get_live_matches()
    assert len(matches) == 2
    assert matches[0]["games_p1"] == 0 and matches[0]["set_history"] == ""
    assert matches[1]["points_p1"] == "0"
