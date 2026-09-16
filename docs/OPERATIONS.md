# Operations

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # add LIVE_TENNIS_API_KEY (Ultra) for real push
python wsgi.py                # dev server on http://127.0.0.1:5000
```

Without an Ultra key the board runs in **demo mode** (simulated points). Real
point-by-point push requires an Ultra key — see the README for why.

## Running tests

```bash
pytest
```

## Production-style run

The board holds long-lived Server-Sent Events connections, so use a worker class
that supports concurrent streaming (threads or gevent), and a **single worker** so
one upstream Ultra WebSocket is shared across viewers:

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000 --worker-class gthread --threads 16 --workers 1
```

With multiple sync workers, each worker would open its own upstream Ultra WebSocket
and could not share SSE clients. If you must scale out, put a shared message broker
(e.g. Redis pub/sub) behind `PushHub`. Set `LIVE_TENNIS_API_KEY` in the host
environment — never in the repo.

## HTTP surface

| Method & path            | Purpose                                                          |
| ------------------------ | ---------------------------------------------------------------- |
| `GET /`                  | The board page.                                                  |
| `GET /api/tennis/stream` | **Server-Sent Events.** Emits a `snapshot` event on connect, then a `score` event per point. |
| `GET /api/tennis/snapshot` | Current state as one-shot JSON (debug/health; the board uses the stream). |
| `GET /api/health`        | Liveness: `{"status":"ok","source":"demo\|livetennisapi-ultra"}`. |
| `GET /audio/tennis-hit.wav` | Alert sound (front-end also has a synth fallback).            |

### SSE frames

```
event: snapshot
data: {"matches": [ ...all current matches... ], "updated_at": "...", "alert_count": 1, "source": "livetennisapi-ultra"}

event: score
data: { "id": 9001, "p1": "Sinner", "p2": "Alcaraz", "sets_p1": 1, ... , "alerts": ["30-40","break-point"], "win_prob_p1": 61.2 }
```

`: keepalive` comment lines are sent when idle to hold the connection open.

## Data flow & Ultra WebSocket

```
Browser ──SSE──▶ Flask (PushHub) ──WebSocket──▶ Live Tennis API Ultra
```

1. `UltraPushSource` (`app/push/sources.py`) mints a token: `GET /ws-token` with
   `Authorization: Bearer <ULTRA key>` → `{token, ws_url, channels}`.
2. It opens `ws_url`, sends `{"connect":{"token":...}}`, subscribes to `slate:all`,
   and receives `{"push":{"pub":{"data": <score frame>}}}` on each score commit.
3. Each frame is mapped (`app/mapping.py`) into the board's match shape and
   published to the `PushHub`, which fans it out to all SSE clients.
4. Heartbeats (`{}`) are answered promptly; the token is short-lived, so the source
   mints a fresh one and re-subscribes on every reconnect.

With no key, `DemoPushSource` publishes simulated points instead — same hub, same
SSE frames, clearly labelled `source: "demo"`.

## Key safety

The Ultra key is read from the environment server-side and sent to Live Tennis API
as a request header. It is never rendered into the page, shipped to the browser, or
committed (`.env` is git-ignored; `.env.example` documents every variable).

## State model

No database. The hub state and demo simulation are in-memory, so restarting the
process resets them. No data backfill is ever required.

## Cloud Agent environment

Defined in [`.cursor/environment.json`](../.cursor/environment.json): idempotent
`install` (`scripts/cloud-install.sh`) creates `.venv` and installs deps; the `web`
terminal runs the dev server on port 5000 (demo mode unless an Ultra key is set).
```
