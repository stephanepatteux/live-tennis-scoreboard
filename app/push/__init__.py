"""Real-time push: an in-memory hub that fans match updates out to SSE clients,
fed by either the Ultra WebSocket (real per-point data) or the demo simulation.
"""

from __future__ import annotations

import os

from .hub import PushHub
from .sources import DemoPushSource, UltraPushSource, get_push_source

__all__ = ["PushHub", "DemoPushSource", "UltraPushSource", "get_push_source"]
