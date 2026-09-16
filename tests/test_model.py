"""Tests for the local win-probability heuristic."""

from app.scoring.model import estimate_win_prob_p1


def _p(**kw):
    base = dict(
        sets_p1=0,
        sets_p2=0,
        games_p1=0,
        games_p2=0,
        points_p1="0",
        points_p2="0",
        server=0,
        is_tiebreak=False,
    )
    base.update(kw)
    return estimate_win_prob_p1(**base)


def test_even_start_is_around_fifty():
    assert 45 <= _p() <= 55


def test_within_bounds():
    hi = _p(sets_p1=2, games_p1=6)
    lo = _p(sets_p2=2, games_p2=6)
    assert 2 <= lo <= 98 and 2 <= hi <= 98


def test_set_lead_favours_player():
    assert _p(sets_p1=1) > _p(sets_p2=1)


def test_game_lead_favours_player():
    assert _p(games_p1=4, games_p2=1) > 50


def test_serve_bonus():
    assert _p(server=1) > _p(server=2)


def test_tiebreak_points_matter():
    assert _p(is_tiebreak=True, points_p1="6", points_p2="2") > 50
