# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Instead, report privately via GitHub: open the repository's **Security** tab and
use **"Report a vulnerability"** (Private vulnerability reporting / security
advisories). Include steps to reproduce and the impact you found.

You can expect an initial response within a few days.

## Handling API keys

This project is designed so your Live Tennis API key **never** leaves the server:

- The key is read from the `LIVE_TENNIS_API_KEY` environment variable at runtime
  and sent to Live Tennis API only as a request header.
- It is never rendered into the page, sent to the browser, or logged.
- No key (real or placeholder) is committed to this repository; `.env` is
  git-ignored.

If you ever find a key exposed in the client, logs, or git history, please report
it using the process above. If a key of yours is leaked, rotate it in your Live
Tennis API dashboard immediately.
