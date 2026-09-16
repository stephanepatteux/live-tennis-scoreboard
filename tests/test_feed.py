"""Tests for the caching feed service."""

from app.feed import FeedService
from app.providers.base import Provider


class _StubProvider(Provider):
    name = "stub"

    def __init__(self):
        self.calls = 0
        self.fail = False

    def get_live_matches(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("upstream down")
        return [
            {"id": 1, "alert_priority": 4},
            {"id": 2, "alert_priority": 0},
        ]


def test_feed_shape_and_alert_count():
    svc = FeedService(_StubProvider(), cache_ttl=10)
    feed = svc.get_feed()
    assert feed["cached"] is False
    assert feed["alert_count"] == 1
    assert feed["source"] == "stub"
    assert "updated_at" in feed and len(feed["matches"]) == 2


def test_cache_reuses_result():
    p = _StubProvider()
    svc = FeedService(p, cache_ttl=100)
    svc.get_feed()
    second = svc.get_feed()
    assert p.calls == 1
    assert second["cached"] is True


def test_force_bypasses_cache():
    p = _StubProvider()
    svc = FeedService(p, cache_ttl=100)
    svc.get_feed()
    svc.get_feed(force=True)
    assert p.calls == 2


def test_error_falls_back_to_cache():
    p = _StubProvider()
    svc = FeedService(p, cache_ttl=0)  # always refetch
    svc.get_feed()
    p.fail = True
    feed = svc.get_feed()
    assert feed["cached"] is True  # served stale cache instead of failing


def test_error_without_cache_raises():
    p = _StubProvider()
    p.fail = True
    svc = FeedService(p, cache_ttl=0)
    try:
        svc.get_feed()
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError when no cache is available")
