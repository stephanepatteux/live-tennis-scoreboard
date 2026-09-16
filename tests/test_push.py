"""Tests for the push hub and sources."""

import json
import os
import time
from unittest import mock

from app.push import DemoPushSource, PushHub, UltraPushSource, get_push_source


def test_hub_publish_and_snapshot():
    hub = PushHub(source_name="test")
    hub.publish({"id": 1, "p1": "A", "alert_priority": 4})
    hub.publish({"id": 2, "p1": "B", "alert_priority": 0})
    snap = hub.snapshot()
    assert snap["source"] == "test"
    assert len(snap["matches"]) == 2
    assert snap["alert_count"] == 1
    assert snap["updated_at"] is not None


def test_hub_latest_state_per_match():
    hub = PushHub()
    hub.publish({"id": 1, "games_p1": 0})
    hub.publish({"id": 1, "games_p1": 3})
    matches = hub.snapshot()["matches"]
    assert len(matches) == 1 and matches[0]["games_p1"] == 3


def test_hub_subscribers_receive_updates():
    hub = PushHub()
    q = hub.subscribe()
    hub.publish({"id": 9, "p1": "X"})
    got = q.get(timeout=1)
    assert got["id"] == 9
    hub.unsubscribe(q)


def test_hub_static_for():
    hub = PushHub()
    hub.publish({"id": 3, "p1": "A", "p2": "B", "tour": "atp", "tournament": "T"})
    static = hub.static_for(3)
    assert static["p1"] == "A" and static["tour"] == "atp"
    assert hub.static_for(999) == {}


def test_get_push_source_selection():
    with mock.patch.dict(os.environ, {}, clear=True):
        assert isinstance(get_push_source(), DemoPushSource)
    with mock.patch.dict(os.environ, {"LIVE_TENNIS_API_KEY": "twjp_x"}, clear=True):
        src = get_push_source()
        assert isinstance(src, UltraPushSource)
        assert src.api_key == "twjp_x"


def test_demo_source_seeds_and_advances():
    hub = PushHub(source_name="demo")
    src = DemoPushSource(point_interval=0.02)
    src.start(hub)
    try:
        # Initial seed is published synchronously in start().
        assert len(hub.snapshot()["matches"]) >= 6
        first = {m["id"]: (m["points_p1"], m["games_p1"]) for m in hub.snapshot()["matches"]}
        time.sleep(0.2)  # let several points advance
        later = {m["id"]: (m["points_p1"], m["games_p1"]) for m in hub.snapshot()["matches"]}
        assert first != later  # something moved
    finally:
        src.stop()


def test_ultra_handle_raw_publishes_score_frame():
    hub = PushHub(source_name="livetennisapi-ultra")
    src = UltraPushSource(api_key="k", base_url="http://api.test/v1")
    frame = {
        "push": {
            "channel": "slate:all",
            "pub": {
                "data": {
                    "id": 100,
                    "tour": "wta",
                    "players": {"p1": {"name": "Iga"}, "p2": {"name": "Aryna"}},
                    "score": {"sets": [0, 0], "games": [[2], [1]],
                              "points": ["40", "0"], "server": 2},
                }
            },
        }
    }
    src.handle_raw(json.dumps(frame), hub)
    matches = hub.snapshot()["matches"]
    assert len(matches) == 1
    m = matches[0]
    assert m["id"] == 100 and m["p1"] == "Iga"
    assert "0-40" in m["alerts"]  # p1 at 40 on p2's serve, server on 0


def test_ultra_handle_raw_replies_to_heartbeat():
    hub = PushHub()
    src = UltraPushSource(api_key="k", base_url="http://api.test/v1")
    sent = []

    class FakeWs:
        def send(self, msg):
            sent.append(msg)

    src.handle_raw("{}", hub, ws=FakeWs())
    assert sent == ["{}"]
    assert hub.snapshot()["matches"] == []  # heartbeat is not a score


def test_ultra_handle_raw_ignores_connect_replies():
    hub = PushHub()
    src = UltraPushSource(api_key="k", base_url="http://api.test/v1")
    src.handle_raw(json.dumps({"id": 1, "connect": {"client": "abc"}}), hub)
    assert hub.snapshot()["matches"] == []


def test_ultra_handle_raw_batched_newline_delimited():
    hub = PushHub()
    src = UltraPushSource(api_key="k", base_url="http://api.test/v1")
    f1 = {"push": {"pub": {"data": {"id": 1, "players": {"p1": {"name": "A"}, "p2": {"name": "B"}},
                                     "score": {"sets": [0, 0], "points": ["0", "0"], "server": 1}}}}}
    f2 = {"push": {"pub": {"data": {"id": 2, "players": {"p1": {"name": "C"}, "p2": {"name": "D"}},
                                     "score": {"sets": [0, 0], "points": ["0", "0"], "server": 1}}}}}
    src.handle_raw(json.dumps(f1) + "\n" + json.dumps(f2), hub)
    assert len(hub.snapshot()["matches"]) == 2


def test_ultra_mint_ws_token_uses_bearer_auth():
    src = UltraPushSource(api_key="twjp_secret", base_url="http://api.test/v1")
    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(
                {"token": "tok", "ws_url": "wss://x/ws", "channels": {"slate": "slate:all"}}
            ).encode()

    def fake_urlopen(req, timeout=None):
        captured["auth"] = req.get_header("Authorization")
        captured["url"] = req.full_url
        return FakeResp()

    with mock.patch("urllib.request.urlopen", fake_urlopen):
        info = src.mint_ws_token()
    assert info["ws_url"] == "wss://x/ws"
    assert captured["auth"] == "Bearer twjp_secret"
    assert captured["url"].endswith("/ws-token")
