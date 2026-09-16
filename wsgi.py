"""WSGI/dev entrypoint.

Run locally with:  python wsgi.py         (Flask dev server)
Run in prod with:  gunicorn wsgi:app
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    import os

    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        # The board holds long-lived SSE connections; serve them concurrently.
        threaded=True,
    )
