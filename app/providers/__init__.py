"""Data providers for the live feed.

``get_provider`` picks the live Live Tennis API provider when a key is configured,
otherwise the built-in demo provider so the board runs publicly with no secrets.
"""

from __future__ import annotations

import os

from .base import Provider
from .demo import DemoProvider
from .livetennisapi import LiveTennisApiProvider


def get_provider() -> Provider:
    api_key = os.environ.get("LIVE_TENNIS_API_KEY", "").strip()
    if api_key:
        return LiveTennisApiProvider(
            api_key=api_key,
            base_url=os.environ.get(
                "LIVE_TENNIS_API_BASE", "https://api.livetennisapi.com/api/public/v1"
            ).rstrip("/"),
            timeout=float(os.environ.get("LIVE_TENNIS_API_TIMEOUT", "8")),
            model_fallback=os.environ.get("MODEL_FALLBACK", "1") != "0",
        )
    return DemoProvider()


__all__ = ["Provider", "DemoProvider", "LiveTennisApiProvider", "get_provider"]
