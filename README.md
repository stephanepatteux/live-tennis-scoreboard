# Tennis Trader Board

A free, self-hosted **live tennis scoreboard built for Betfair tennis traders** —
ATP &amp; WTA sets, games, points, who is serving, **15–40 / 0–40 break-point
alerts**, and a **model win %** next to your ladder. It is a second-screen board:
it polls scores about every 8 seconds (not a per-point WebSocket) and keeps many
viewers on one shared refresh. Scores are informational — **not tips**.

This is the open-source version of the board hosted at
**[botblog.co.uk/tennis-trader-board](https://botblog.co.uk/tennis-trader-board/)**.
It runs out of the box in **demo mode** (simulated matches, no key), and switches
to real live scores when you add a Live Tennis API key.

> **Powered by Live Tennis API.** Get a key here (Ultra recommended for the
> point-by-point push feed + win-probability model):
> **[Subscribe via this affiliate link](https://affiliates.livetennisapi.com/r/botblog)**
> and use code **`botblog`** at checkout for 10% off.
> _[Affiliate disclosure](#affiliate-disclosure)._

## Features

- ATP / WTA filter, surface (clay / hard / grass), singles-only, search, and a
  personal ★ watchlist.
- Break-point alerts: `0–40`, `15–40`, `30–40`, any break point, deuce, tiebreak —
  with optional pinning, a sound cue, and toast notifications.
- Paste **player 1's decimal odds** to see the gap between the model win % and the
  market's implied % (in percentage points).
- Compact mode + **Pop out** for a slim second-monitor window (`?embed=1`).
- The API key lives **only on the server** — it is never sent to the browser and
  never committed to this repo.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env      # optional: add your LIVE_TENNIS_API_KEY for live scores
python wsgi.py            # → http://127.0.0.1:5000
```

With no key set, the board runs in **demo mode** with simulated matches so you can
see everything working. Add `LIVE_TENNIS_API_KEY` to `.env` for real live scores.

Run the tests with `pytest`.

## Configuration

All configuration is via environment variables — see [`.env.example`](.env.example):

| Variable                  | Default                                       | Purpose                                                        |
| ------------------------- | --------------------------------------------- | -------------------------------------------------------------- |
| `LIVE_TENNIS_API_KEY`     | _(blank → demo mode)_                          | Your Live Tennis API key. Kept server-side only.               |
| `LIVE_TENNIS_API_BASE`    | `https://api.livetennisapi.com/api/public/v1` | API base URL.                                                  |
| `LIVE_TENNIS_API_TIMEOUT` | `8`                                           | Upstream request timeout (seconds).                            |
| `MODEL_FALLBACK`          | `1`                                           | Fill the Model column with a local estimate when the provider gives none. |
| `FEED_CACHE_TTL`          | `8`                                           | Seconds one upstream refresh is cached and shared by viewers.  |
| `HOST` / `PORT`           | `127.0.0.1` / `5000`                          | Dev server bind.                                               |
| `FLASK_DEBUG`             | `0`                                           | `1` enables Flask auto-reload.                                 |

## How it works

```
Browser ──poll /api/tennis/live (≈8s)──▶ Flask (this app)
                                          │  short shared cache
                                          ▼
                          Live Tennis API  (key from env, server-side)
                                    or  Demo simulation (no key)
```

- The browser only ever calls this app's `/api/tennis/live`; it never sees the key.
- `app/providers/livetennisapi.py` calls `GET /matches?status=live` and maps the
  player-major response (`sets`, `games`, `points`, `server`, model win %) into the
  board's shape.
- `app/scoring/alerts.py` derives the break-point alerts; `app/scoring/model.py` is
  a transparent fallback win-probability estimate (the real model is Live Tennis
  API Ultra).

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for the HTTP surface and deployment.

## Deploy

Any WSGI host works:

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000
```

Set `LIVE_TENNIS_API_KEY` in the host's environment (never in the repo).

## Ultra: point-by-point push feed

This free board polls about every 8 seconds. **Live Tennis API Ultra** pushes each
point over a WebSocket to your own dashboard or bot with no 8-second wait, plus the
win-probability model. It is tennis data — **not** a Betfair betting key.
👉 **[Subscribe to Ultra (10% off)](https://affiliates.livetennisapi.com/r/botblog)**,
then use code **`botblog`**.

## Affiliate disclosure

Links to Live Tennis API on this page are affiliate links: if you subscribe
through them (optionally with code `botblog`), this project may earn a commission
at no extra cost to you. You are free to sign up directly at
[livetennisapi.com](https://livetennisapi.com) instead.

## Disclaimer

Not financial advice. Live scores and model win probability are informational only.
They are not tips and do not place bets for you.
