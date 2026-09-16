"""Integration tests for the Flask routes (demo mode, no API key)."""

import os
from unittest import mock

import pytest

from app import create_app


@pytest.fixture()
def client():
    # Ensure demo mode regardless of the host environment.
    with mock.patch.dict(os.environ, {"LIVE_TENNIS_API_KEY": ""}, clear=False):
        app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def test_board_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert 'id="ttb-board"' in body
    assert "Tennis Trader Board" in body
    # Affiliate link + code present on the page.
    assert "affiliates.livetennisapi.com/r/botblog" in body
    assert "botblog" in body


def test_health(client):
    data = client.get("/api/health").get_json()
    assert data["status"] == "ok"
    assert data["source"] == "demo"


def test_live_feed_demo(client):
    data = client.get("/api/tennis/live").get_json()
    assert "matches" in data and data["matches"]
    assert data["source"] == "demo"
    m = data["matches"][0]
    assert {"p1", "p2", "sets_p1", "games_p1", "points_p1", "win_prob_p1"} <= set(m)


def test_audio_asset_served(client):
    resp = client.get("/audio/tennis-hit.wav")
    assert resp.status_code == 200
    assert resp.data[:4] == b"RIFF"  # WAV header
