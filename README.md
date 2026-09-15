# live-tennis-scoreboard

A small, real-time singles **tennis scoreboard** web app: Python + Flask + Jinja
templates + vanilla JS, with a pytest suite. Award points to either player and the
board updates live (server-rendered first paint, then polled from a JSON API so
multiple viewers stay in sync). Full tennis rules are implemented: 0/15/30/40,
deuce/advantage, sets with a two-game margin, 6–6 tiebreaks, and best-of-N match
play.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python wsgi.py         # → http://127.0.0.1:5000
pytest                 # run the test suite
```

## Pages

- `/` — live scoreboard with scoring controls
- `/status` — match status summary
- `/help` — scoring rules and API reference

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for configuration, the HTTP API,
and Cloud Agent environment details.
