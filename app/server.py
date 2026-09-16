"""Flask application factory for the Tennis Trader Board.

Serves the board page and the ``/api/tennis/live`` JSON feed. The Live Tennis API
key (when configured) stays server-side; the browser only ever calls this app.
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request, send_from_directory

from .feed import FeedService
from .providers import get_provider

AFFILIATE_URL = (
    "https://affiliates.livetennisapi.com/r/botblog"
    "?utm_campaign=live-tennis-ultra&utm_medium=tennis-board&utm_source=github"
)
AFFILIATE_CODE = "botblog"


def create_app() -> Flask:
    app = Flask(__name__)

    cache_ttl = float(os.environ.get("FEED_CACHE_TTL", "8"))
    feed = FeedService(get_provider(), cache_ttl=cache_ttl)
    app.config["FEED"] = feed

    @app.route("/")
    def index():
        return render_template(
            "board.html",
            affiliate_url=AFFILIATE_URL,
            affiliate_code=AFFILIATE_CODE,
            source=feed.provider.name,
        )

    @app.get("/api/tennis/live")
    def api_live():
        force = request.args.get("force") == "1"
        try:
            payload = feed.get_feed(force=force)
        except Exception as exc:  # provider failed and no cache to fall back on
            return (
                jsonify({"error": "feed_unavailable", "detail": str(exc)[:200]}),
                502,
            )
        return jsonify(payload)

    @app.get("/api/health")
    def api_health():
        return jsonify({"status": "ok", "source": feed.provider.name})

    @app.get("/audio/<path:filename>")
    def audio(filename):
        return send_from_directory(
            os.path.join(app.static_folder, "audio"), filename
        )

    return app
