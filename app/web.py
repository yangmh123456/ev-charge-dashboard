from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from app.analytics import EVDataRepository, build_dashboard_payload, build_mapreduce_jobs, build_requirement_coverage


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
    app.config.update(
        MAX_CONTENT_LENGTH=1_000_000,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("EV_DASHBOARD_COOKIE_SECURE", "0") == "1",
    )

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'self'",
        )
        return response

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/api/dashboard")
    def dashboard():
        try:
            return jsonify(build_dashboard_payload(EVDataRepository()))
        except FileNotFoundError:
            return jsonify(error="Dataset missing. Add nvv2t_md.csv and dsv13r2.csv to data/ or set EV_DATA_DIR."), 503
        except ValueError:
            return jsonify(error="Dataset invalid. Check the CSV columns and valid numeric records."), 422

    @app.get("/api/requirements")
    def requirements():
        return jsonify(build_requirement_coverage())

    @app.get("/api/mapreduce-jobs")
    def mapreduce_jobs():
        try:
            return jsonify(build_mapreduce_jobs(EVDataRepository()))
        except FileNotFoundError:
            return jsonify(error="Dataset missing. Add nvv2t_md.csv and dsv13r2.csv to data/ or set EV_DATA_DIR."), 503
        except ValueError:
            return jsonify(error="Dataset invalid. Check the CSV columns and valid numeric records."), 422

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "ev-charge-bigdata-dashboard"}

    return app


if __name__ == "__main__":
    debug = os.getenv("EV_DASHBOARD_DEBUG", "0") == "1"
    create_app().run(host="127.0.0.1", port=5000, debug=debug)
