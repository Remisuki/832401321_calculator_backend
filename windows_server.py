"""Windows Server entry point: Waitress + existing API + persistent SQLite."""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Response, abort, send_from_directory
from waitress import serve

import storage
from wsgi import create_app as create_api_app

ROOT = Path(__file__).resolve().parent.parent


def create_app():
    settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8-sig"))
    origin = settings["public_origin"].rstrip("/")
    app = create_api_app({
        "DATABASE_URL": ROOT / "data" / "calculator.db",
        "STORAGE": storage,
        "ALLOWED_ORIGINS": origin,
    })
    frontend = ROOT / "frontend"

    @app.get("/")
    def homepage():
        return send_from_directory(frontend, "index.html")

    @app.get("/config.js")
    def public_configuration():
        return Response(
            "window.CALCULATOR_CONFIG = Object.freeze({"
            "apiBaseUrl: window.location.origin + '/api',"
            "requestTimeoutMs: 15000});",
            mimetype="application/javascript",
        )

    @app.get("/<filename>")
    def public_asset(filename):
        if filename not in {"styles.css", "app.js"}:
            abort(404)
        return send_from_directory(frontend, filename)

    return app


if __name__ == "__main__":
    (ROOT / "logs").mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        ROOT / "logs" / "server.log", maxBytes=1_000_000,
        backupCount=3, encoding="utf-8",
    )
    logging.basicConfig(
        level=logging.INFO, handlers=[handler, logging.StreamHandler()],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        application = create_app()
        serve(application, host="0.0.0.0", port=80, threads=4,
              channel_timeout=30, max_request_body_size=16384)
    except Exception:
        logging.exception("Server startup or runtime failed")
        raise
