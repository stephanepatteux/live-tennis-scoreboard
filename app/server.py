"""Flask application factory for the Tennis Trader Board (push-only).

The board receives updates over Server-Sent Events (``/api/tennis/stream``). That
stream is fed by a single push source: the Live Tennis API **Ultra** WebSocket when
an Ultra key is configured, or the demo simulation otherwise. There is no periodic
polling — real-time point-by-point updates require an Ultra key.
"""

from __future__ import annotations

import json
import os
import queue

from flask import Flask, Response, jsonify, render_template, send_from_directory

from .push import PushHub, get_push_source

AFFILIATE_URL = (
    "https://affiliates.livetennisapi.com/r/botblog"
    "?utm_campaign=live-tennis-ultra&utm_medium=tennis-board&utm_source=github"
)
AFFILIATE_CODE = "botblog"


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def create_app() -> Flask:
    app = Flask(__name__)

    source = get_push_source()
    hub = PushHub(source_name=source.name)
    source.start(hub)
    app.config["HUB"] = hub
    app.config["PUSH_SOURCE"] = source

    @app.route("/")
    def index():
        return render_template(
            "board.html",
            affiliate_url=AFFILIATE_URL,
            affiliate_code=AFFILIATE_CODE,
            source=source.name,
            is_live=source.name != "demo",
        )

    @app.get("/api/tennis/stream")
    def stream():
        def gen():
            q = hub.subscribe()
            try:
                yield _sse("snapshot", hub.snapshot())
                while True:
                    try:
                        match = q.get(timeout=15)
                        yield _sse("score", match)
                    except queue.Empty:
                        # Comment line keeps the connection alive through proxies.
                        yield ": keepalive\n\n"
            finally:
                hub.unsubscribe(q)

        return Response(
            gen(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @app.get("/api/tennis/snapshot")
    def snapshot():
        return jsonify(hub.snapshot())

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "source": source.name})

    @app.get("/audio/<path:filename>")
    def audio(filename):
        return send_from_directory(os.path.join(app.static_folder, "audio"), filename)

    return app
