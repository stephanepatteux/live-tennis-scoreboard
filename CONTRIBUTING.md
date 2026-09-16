# Contributing

Thanks for your interest in improving the Tennis Trader Board!

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python wsgi.py        # http://127.0.0.1:5000 (demo mode without a key)
```

No API key is needed to develop — the board runs in demo mode with simulated
points. See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for the architecture.

## Tests

Please run the suite before opening a PR:

```bash
pytest
```

Add or update tests for any behaviour you change — scoring/alerts, the
win-probability model, API frame mapping, the push hub, or the routes.
CI runs `pytest` on every pull request.

## Guidelines

- **Never commit secrets.** No API keys — not real, not placeholder. Keep them in
  an untracked `.env`; document new variables in `.env.example`.
- Keep the browser board and the server feed in parity: both sides share the
  match shape produced by `app/matches.py`.
- Match the existing style (small, focused modules; standard library where
  reasonable). Keep comments about intent, not narration.
- Update the README / `docs/OPERATIONS.md` if you change env vars, routes, or the
  data flow.

## Pull requests

- Branch off `main`, keep PRs focused, and describe what changed and why.
- Make sure CI is green.

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
