"""Integration tests for the Flask routes and JSON API."""

import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        # Ensure each test starts from a clean match.
        c.post("/api/reset")
        yield c


def test_home_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Live Tennis Scoreboard" in resp.data
    assert b"Point" in resp.data


def test_help_and_status_pages(client):
    assert client.get("/help").status_code == 200
    status = client.get("/status")
    assert status.status_code == 200
    assert b"Match status" in status.data


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_score_endpoint_initial(client):
    data = client.get("/api/score").get_json()
    assert data["players"][0]["point"] == "0"
    assert data["winner"] is None


def test_point_endpoint_awards_point(client):
    data = client.post("/api/point", json={"player": 0}).get_json()
    assert data["players"][0]["point"] == "15"


def test_point_endpoint_validation(client):
    resp = client.post("/api/point", json={"player": 9})
    assert resp.status_code == 400


def test_reset_endpoint(client):
    client.post("/api/point", json={"player": 0})
    data = client.post("/api/reset").get_json()
    assert data["players"][0]["point"] == "0"


def test_form_fallback_scoring(client):
    resp = client.post("/point/0", follow_redirects=False)
    assert resp.status_code == 302
    data = client.get("/api/score").get_json()
    assert data["players"][0]["point"] == "15"


def test_full_match_via_api(client):
    # Player 2 wins best-of-3 with two 6-0 sets (24 love-game points).
    for _ in range(12):
        for _ in range(4):
            client.post("/api/point", json={"player": 1})
    data = client.get("/api/score").get_json()
    assert data["winner"] == "Player 2"
