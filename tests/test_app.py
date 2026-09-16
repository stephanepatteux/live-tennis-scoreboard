"""Integration tests for the Flask routes (demo push mode, no API key)."""

import json
import os
from unittest import mock

import pytest

from app import create_app


@pytest.fixture()
def client():
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
    # Affiliate link + code present, and push messaging (no polling copy).
    assert "affiliates.livetennisapi.com/r/botblog" in body
    assert "botblog" in body
    assert "pushed the moment it is scored" in body


def test_health(client):
    data = client.get("/api/health").get_json()
    assert data["status"] == "ok"
    assert data["source"] == "demo"


def test_snapshot_has_matches(client):
    data = client.get("/api/tennis/snapshot").get_json()
    assert data["source"] == "demo"
    assert data["matches"]
    m = data["matches"][0]
    assert {"p1", "p2", "sets_p1", "games_p1", "points_p1", "win_prob_p1"} <= set(m)


def test_stream_is_sse_and_sends_snapshot(client):
    resp = client.get("/api/tennis/stream")
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"
    # Read just the first streamed chunk (the snapshot event) without blocking.
    gen = resp.response
    first = next(iter(gen))
    text = first.decode() if isinstance(first, bytes) else first
    assert "event: snapshot" in text
    payload = json.loads(text.split("data: ", 1)[1].strip())
    assert payload["source"] == "demo"
    assert "matches" in payload
    resp.close()


def test_audio_asset_served(client):
    resp = client.get("/audio/tennis-hit.wav")
    assert resp.status_code == 200
    assert resp.data[:4] == b"RIFF"
