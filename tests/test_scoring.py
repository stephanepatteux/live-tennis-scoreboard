"""Unit tests for the tennis scoring engine."""

from app.scoring import TennisMatch


def play_points(match: TennisMatch, sequence: str) -> None:
    """Score points from a compact string, e.g. "0011" -> p1,p1,p2,p2."""
    for ch in sequence:
        match.score_point(int(ch))


def test_point_labels_progress():
    m = TennisMatch.new()
    assert m.snapshot()["players"][0]["point"] == "0"
    m.score_point(0)
    assert m.snapshot()["players"][0]["point"] == "15"
    m.score_point(0)
    assert m.snapshot()["players"][0]["point"] == "30"
    m.score_point(0)
    assert m.snapshot()["players"][0]["point"] == "40"


def test_win_a_love_game():
    m = TennisMatch.new()
    play_points(m, "0000")
    snap = m.snapshot()
    assert snap["players"][0]["games"] == 1
    assert snap["players"][0]["point"] == "0"
    assert snap["players"][1]["point"] == "0"


def test_deuce_and_advantage():
    m = TennisMatch.new()
    play_points(m, "010101")  # 40-40 deuce
    snap = m.snapshot()
    assert snap["deuce"] is True
    assert snap["players"][0]["point"] == "40"

    m.score_point(0)  # advantage p1
    snap = m.snapshot()
    assert snap["deuce"] is False
    assert snap["players"][0]["point"] == "Ad"

    m.score_point(1)  # back to deuce
    assert m.snapshot()["deuce"] is True

    m.score_point(0)  # advantage
    m.score_point(0)  # game
    assert m.snapshot()["players"][0]["games"] == 1


def test_win_a_set():
    m = TennisMatch.new()
    for _ in range(6):  # p1 wins 6 love games
        play_points(m, "0000")
    snap = m.snapshot()
    assert snap["players"][0]["sets"] == 1
    assert snap["players"][0]["games"] == 0
    assert snap["completed_sets"] == [(6, 0)]


def test_set_requires_two_game_margin():
    m = TennisMatch.new()
    # Reach 5-5.
    for _ in range(5):
        play_points(m, "0000")
    for _ in range(5):
        play_points(m, "1111")
    assert m.snapshot()["players"][0]["sets"] == 0
    play_points(m, "0000")  # 6-5, not enough
    assert m.snapshot()["players"][0]["sets"] == 0
    play_points(m, "0000")  # 7-5, set won
    assert m.snapshot()["players"][0]["sets"] == 1


def test_tiebreak_triggered_and_won():
    m = TennisMatch.new()
    # Reach 6-6 by alternating love games (neither player gets a 2-game margin).
    for _ in range(6):
        play_points(m, "0000")  # p1 holds
        play_points(m, "1111")  # p2 holds
    snap = m.snapshot()
    assert snap["players"][0]["games"] == 6
    assert snap["players"][1]["games"] == 6
    assert snap["in_tiebreak"] is True

    # p1 wins tiebreak 7-0.
    play_points(m, "0000000")
    snap = m.snapshot()
    assert snap["in_tiebreak"] is False
    assert snap["players"][0]["sets"] == 1


def test_match_winner_best_of_three():
    m = TennisMatch.new(sets_to_win=2)
    # p1 wins two sets 6-0, 6-0.
    for _ in range(12):
        play_points(m, "0000")
    snap = m.snapshot()
    assert snap["winner"] == "Player 1"


def test_no_scoring_after_match_won():
    m = TennisMatch.new(sets_to_win=1)
    for _ in range(6):
        play_points(m, "0000")
    assert m.snapshot()["winner"] == "Player 1"
    # Further points must be ignored.
    m.score_point(1)
    assert m.snapshot()["players"][1]["point"] == "0"


def test_invalid_player_index():
    m = TennisMatch.new()
    try:
        m.score_point(5)
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid player index")
