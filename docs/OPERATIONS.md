# Operations

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # optional; add LIVE_TENNIS_API_KEY for live scores
python wsgi.py                # dev server on http://127.0.0.1:5000
```

Without `LIVE_TENNIS_API_KEY`, the board runs in **demo mode** (simulated matches).

## Running tests

```bash
pytest
```

## Production-style run

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000
```

Set `LIVE_TENNIS_API_KEY` in the host environment. Never commit it — `.env` is
git-ignored and `.env.example` documents every variable.

## HTTP surface

| Method & path          | Purpose                                                        |
| ---------------------- | -------------------------------------------------------------- |
| `GET /`                | The board page (server-rendered shell, then polled live).      |
| `GET /api/tennis/live` | Live feed JSON (`?force=1` bypasses the cache).                |
| `GET /api/health`      | Liveness probe: `{"status":"ok","source":"demo\|livetennisapi"}`. |
| `GET /audio/tennis-hit.wav` | Alert sound (the front-end also has a synth fallback).    |

### `/api/tennis/live` response

```json
{
  "matches": [
    {
      "id": 9001, "tour": "atp", "p1": "Sinner", "p2": "Alcaraz",
      "tournament": "ATP Finals", "surface": "hard", "format": "Bo3",
      "is_doubles": false,
      "sets_p1": 1, "sets_p2": 0, "games_p1": 4, "games_p2": 3,
      "points_p1": "40", "points_p2": "30", "server": 2, "is_tiebreak": false,
      "set_history": "6-4 4-3",
      "alerts": ["30-40", "break-point"], "alert_label": "30–40 · break point",
      "alert_priority": 3, "win_prob_p1": 61.2
    }
  ],
  "updated_at": "2026-09-16T06:10:00+00:00",
  "cached": false, "alert_count": 1, "source": "demo"
}
```

## Data flow & key safety

- The browser polls **only** this app's `/api/tennis/live`. The API key is read
  from the environment in `app/providers/livetennisapi.py` and sent to the upstream
  API as a request header. It is never rendered into the page or shipped to JS.
- `FEED_CACHE_TTL` caches one upstream refresh and shares it across all viewers, so
  many second screens cost the provider one request. On an upstream error the last
  good payload is served (marked `cached`) instead of blanking the board.

## Providers

| Provider                    | When it's used                        |
| --------------------------- | ------------------------------------- |
| `providers/livetennisapi.py`| `LIVE_TENNIS_API_KEY` is set.         |
| `providers/demo.py`         | No key set — simulated live matches.  |

## State model

There is no database. The demo simulation and the feed cache are in-memory, so
restarting the process resets them. No data backfill is ever required.

## Cloud Agent environment

Defined in [`.cursor/environment.json`](../.cursor/environment.json): idempotent
`install` (`scripts/cloud-install.sh`) creates `.venv` and installs deps; the `web`
terminal runs the dev server on port 5000 (demo mode unless a key is provided).
