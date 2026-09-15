# Operations

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python wsgi.py            # dev server on http://127.0.0.1:5000
```

## Running tests

```bash
pytest
```

## Production-style run

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000
```

## Configuration

All configuration is via environment variables (see [`.env.example`](../.env.example)):

| Variable       | Default    | Purpose                                             |
| -------------- | ---------- | --------------------------------------------------- |
| `PLAYER1_NAME` | `Player 1` | Name shown for player 1.                            |
| `PLAYER2_NAME` | `Player 2` | Name shown for player 2.                            |
| `SETS_TO_WIN`  | `2`        | Sets required to win the match (2 = best of 3).     |
| `HOST`         | `127.0.0.1`| Dev server bind host.                               |
| `PORT`         | `5000`     | Dev server / gunicorn port.                         |
| `FLASK_DEBUG`  | `0`        | `1` enables Flask debug + auto-reload.              |

## HTTP surface

| Method & path        | Purpose                                    |
| -------------------- | ------------------------------------------ |
| `GET /`              | Live scoreboard (server-rendered + polled).|
| `GET /status`        | Match status summary.                      |
| `GET /help`          | Scoring rules and API reference.           |
| `GET /api/health`    | Liveness probe (`{"status":"ok"}`).        |
| `GET /api/score`     | Current match snapshot (JSON).             |
| `POST /api/point`    | Award a point: body `{"player": 0\|1}`.    |
| `POST /api/reset`    | Reset to a fresh match.                    |

## State model

A single match is held in memory in the app process and guarded by a lock.
Restarting the process resets the match. There is no database, so no data
backfill is ever required.

## Cloud Agent environment

The Cloud Agent environment is defined in [`.cursor/environment.json`](../.cursor/environment.json):

- `install` creates a `.venv` and installs `requirements-dev.txt` (idempotent).
- The `web` terminal runs the Flask dev server on port 5000.
