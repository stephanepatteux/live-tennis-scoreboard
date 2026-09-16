# Tennis Trader Board — container image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY wsgi.py ./

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 5000

# SSE needs a threaded worker, and a single worker shares one upstream Ultra
# WebSocket across viewers. --timeout 0 keeps long-lived streams from being
# reaped. Provide LIVE_TENNIS_API_KEY at runtime for real push (demo otherwise):
#   docker run -p 5000:5000 -e LIVE_TENNIS_API_KEY=... tennis-trader-board
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:5000", "--worker-class", "gthread", "--threads", "16", "--workers", "1", "--timeout", "0"]
