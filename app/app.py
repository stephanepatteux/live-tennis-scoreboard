"""Flask application factory for the Live Tennis Scoreboard.

A single in-memory match backs the scoreboard. The home page renders the current
state server-side (Jinja) and then keeps it live with a small vanilla-JS poller
that reads the same snapshot via the JSON API, keeping the rendered and live
views in parity.
"""

from __future__ import annotations

import os
import threading

from flask import Flask, jsonify, redirect, render_template, request, url_for

from .scoring import TennisMatch

# The match is shared across requests; guard mutations with a lock so concurrent
# scoring requests cannot interleave and corrupt the state.
_match_lock = threading.Lock()
_match: TennisMatch


def _reset_match(app: Flask) -> None:
    global _match
    _match = TennisMatch.new(
        app.config["PLAYER1_NAME"],
        app.config["PLAYER2_NAME"],
        app.config["SETS_TO_WIN"],
    )


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["PLAYER1_NAME"] = os.environ.get("PLAYER1_NAME", "Player 1")
    app.config["PLAYER2_NAME"] = os.environ.get("PLAYER2_NAME", "Player 2")
    app.config["SETS_TO_WIN"] = int(os.environ.get("SETS_TO_WIN", "2"))

    _reset_match(app)

    @app.route("/")
    def index():
        with _match_lock:
            state = _match.snapshot()
        return render_template("index.html", state=state)

    @app.route("/help")
    def help_page():
        return render_template("help.html")

    @app.route("/status")
    def status_page():
        with _match_lock:
            state = _match.snapshot()
        return render_template(
            "status.html",
            state=state,
            config={
                "sets_to_win": app.config["SETS_TO_WIN"],
                "player1": app.config["PLAYER1_NAME"],
                "player2": app.config["PLAYER2_NAME"],
            },
        )

    @app.get("/api/health")
    def api_health():
        return jsonify({"status": "ok"})

    @app.get("/api/score")
    def api_score():
        with _match_lock:
            return jsonify(_match.snapshot())

    @app.post("/api/point")
    def api_point():
        data = request.get_json(silent=True) or request.form
        try:
            player_index = int(data.get("player", -1))
        except (TypeError, ValueError):
            player_index = -1
        if player_index not in (0, 1):
            return jsonify({"error": "player must be 0 or 1"}), 400
        with _match_lock:
            _match.score_point(player_index)
            return jsonify(_match.snapshot())

    @app.post("/api/reset")
    def api_reset():
        with _match_lock:
            _reset_match(app)
            return jsonify(_match.snapshot())

    # Progressive-enhancement fallbacks so scoring works even without JS.
    @app.post("/point/<int:player_index>")
    def point_form(player_index: int):
        if player_index in (0, 1):
            with _match_lock:
                _match.score_point(player_index)
        return redirect(url_for("index"))

    @app.post("/reset")
    def reset_form():
        with _match_lock:
            _reset_match(app)
        return redirect(url_for("index"))

    return app
