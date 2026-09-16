"""Live feed assembly with a short, shared cache.

The browser polls about every 8 seconds. We cache the last provider result for a
few seconds and hand the same payload to everyone, so many viewers cost the data
provider one refresh — exactly like the hosted board. On a provider error we serve
the last good payload (marked cached) rather than blanking the board.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from .providers import Provider


class FeedService:
    def __init__(self, provider: Provider, cache_ttl: float = 8.0):
        self.provider = provider
        self.cache_ttl = cache_ttl
        self._lock = threading.Lock()
        self._cached_payload = None
        self._cached_at = 0.0

    def get_feed(self, force: bool = False) -> dict:
        now = time.monotonic()
        with self._lock:
            fresh_enough = (
                self._cached_payload is not None
                and (now - self._cached_at) < self.cache_ttl
            )
            if fresh_enough and not force:
                payload = dict(self._cached_payload)
                payload["cached"] = True
                return payload

            try:
                matches = self.provider.get_live_matches()
            except Exception:
                if self._cached_payload is not None:
                    payload = dict(self._cached_payload)
                    payload["cached"] = True
                    return payload
                raise

            payload = {
                "matches": matches,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "cached": False,
                "alert_count": sum(1 for m in matches if m.get("alert_priority")),
                "source": self.provider.name,
            }
            self._cached_payload = payload
            self._cached_at = now
            return dict(payload)
